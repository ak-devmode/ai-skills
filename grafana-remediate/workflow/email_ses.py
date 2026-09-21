#!/usr/bin/env python3
# SES ES-email composer + sender (scope 146, Phase 2, Task 2.4).
#
# Approach: reuse Grafana's already-configured SES path (sender alerts@kalpahealth.com,
# recipient alex@kalpahealth.com) rather than the Gmail MCP. The house ES format is
# structural, not left to the agent's discretion: the FIRST TWO SENTENCES are the core
# problem and core solution, then the body. The agent's email stage fills those three
# fields; this module assembles the wire format and enforces the redaction footer.
#
# PR path vs proposal path (per Alex, 2026-09-21): when a PR exists, its Sonnet-generated
# summary is reused verbatim as the body — we do NOT run the email agent again to
# re-summarize (no redundant second evaluation). The proposal path uses the email agent.
#
# EGRESS ORDER: the caller runs phi_gate on the assembled (subject+body) BEFORE calling
# send(). This module refuses to send a payload that still trips the PHI gate, as a
# belt-and-braces second check — no unredacted egress even on a caller bug.
#
# Stdlib + boto3 (already a dep of the observability tooling). --dry-run never sends.

import json
import subprocess
import tempfile

import phi_scrub

SENDER = "alerts@kalpahealth.com"
RECIPIENT = "alex@kalpahealth.com"


def subject_for(incident):
    lab = incident.get("labels", {})
    return (f"[alarm-resolver] {incident.get('class','?')}: "
            f"{incident.get('alertName','?')} ({lab.get('env','?')})")


def compose(incident, agent_email=None, pr_summary=None, redacted_count=0):
    """Assemble (subject, body). PR path: pr_summary reused verbatim. Proposal path:
    agent_email = the dict from run_agent('email'). Exactly one must be provided."""
    subject = subject_for(incident)
    if pr_summary is not None:
        body = pr_summary
    elif agent_email is not None:
        lead = f"{agent_email['problem'].strip()} {agent_email['solution'].strip()}"
        body = f"{lead}\n\n{agent_email['body'].strip()}"
    else:
        raise ValueError("compose needs pr_summary (PR path) or agent_email (proposal path)")
    if redacted_count:
        body += (f"\n\n---\n[PHI gate redacted {redacted_count} sensitive token(s) "
                 f"from this message before sending.]")
    return subject, body


def send(subject, body, recipient=RECIPIENT, dry_run=True):
    """Send via SES. dry_run returns the payload without sending. A final PHI check is
    enforced here regardless of the caller — refuse unredacted egress."""
    ok, findings, _ = phi_scrub.gate(subject + "\n" + body)
    if not ok:
        raise RuntimeError(
            f"REFUSED egress: PHI gate tripped at send() on {[t for t,_ in findings]}. "
            f"Caller must redact before send.")
    if dry_run:
        return {"sent": False, "dry_run": True, "subject": subject,
                "recipient": recipient, "bytes": len(body)}
    # Real send reuses Grafana's SES identity (no new IAM surface). Pass a JSON payload
    # via --cli-input-json so newlines/special chars in the body never hit shell quoting.
    payload = {"Source": SENDER, "Destination": {"ToAddresses": [recipient]},
               "Message": {"Subject": {"Data": subject},
                           "Body": {"Text": {"Data": body}}}}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        f.flush()
        p = subprocess.run(["aws", "ses", "send-email", "--cli-input-json",
                            f"file://{f.name}"], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"SES send failed: {p.stderr[:300]}")
    msg_id = ""
    try:
        msg_id = json.loads(p.stdout).get("MessageId", "")
    except json.JSONDecodeError:
        pass
    return {"sent": True, "dry_run": False, "subject": subject,
            "recipient": recipient, "message_id": msg_id}
