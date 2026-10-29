#!/usr/bin/env python3
"""phase-report.py — what a phase did, printed at its end and kept for later (scope 10.5).

Approach: compose, don't re-judge (reframe 10.5-r1). The owned finish rows come from the
table's parser, row validity and review acceptance from verdict-gate.py's own JSON, and the
judge's checks and findings (weak rows and misfiled nits included) from the verify report
judge.py already wrote. This script adds only what nothing else renders: review rounds and
outcomes, the unit's decisions and the driver's merges. Nothing is asked and nothing is
decided here; the report replaces the finish-table approval question
(verify-contracts.md §3.1.1): Alex reads the rows after the fact and amends one through
`finish-table.py add --replace`.

  phase-report.py --scope DIR --unit N.P [--no-write]

Writes <scope>/artifacts/phase-report-<unit>.md (unless --no-write), reads it back, and
prints the same text. A missing or damaged record is reported as such in its section,
never as zero.
Exit: 0 written/printed · 2 usage (no scope folder) · 3 the report did not read back.
"""
import argparse
import collections
import datetime
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_lib as vl  # noqa: E402

GATE = os.path.join(HERE, "verdict-gate.py")


def cell(text):
    """A markdown table cell: pipes escaped, newlines folded, nothing cut."""
    return " ".join(str(text if text is not None else "-").split()).replace("|", "\\|")


def records(path, what):
    """(records, problem) — strict: a malformed line is a problem to show, not a line to skip."""
    if not os.path.exists(path):
        return None, f"No {what}."
    try:
        return vl.read_jsonl(path), None
    except vl.ContractError as e:
        return None, f"{what.capitalize()} damaged — {str(e).splitlines()[0].strip()} ({path})"


def gate_state(scope, unit):
    p = subprocess.run([sys.executable, GATE, "--scope", scope, "--unit", unit, "--advisory", "--json"],
                       capture_output=True, text=True, timeout=300)
    try:
        return json.loads(p.stdout), None
    except ValueError:
        return None, f"verdict-gate.py could not evaluate (exit {p.returncode}): {cell(p.stderr.strip()[-300:])}"


def rows_section(scope, unit, gate):
    out = ["## 1. Finish rows", ""]
    try:
        table = vl.parse_table(os.path.join(scope, "finish-conditions.md"))
    except (OSError, vl.ContractError) as e:
        return out + [f"No finish table read ({cell(str(e).splitlines()[0])})."]
    owned = [r for r in table["rows"] if r["owner"] == unit or r["owner"].startswith(unit + "/")]
    if not owned:
        return out + [f"No rows owned by {unit} (table rev {table['revision']})."]
    state = {}
    for line in (gate or {}).get("report", []):
        parts = line.split()
        if len(parts) >= 2:
            state[parts[1]] = line.split(parts[1], 1)[1].strip()
    appr = table.get("approval")
    out += [f"Table rev {table['revision']} · " + ("no approval line (predates the contract)" if appr is None else
            f"approved rev {appr}" if isinstance(appr, int) else f"approval {cell(appr)}"), "",
            "| row | deliverable | proven by | where | gate |", "|---|---|---|---|---|"]
    for r in owned:
        env = " ".join(f"{k}={v}" for k, v in r["env"].items()) if isinstance(r.get("env"), dict) else r.get("env")
        where = f"{r['repo']}/{r['dir']}" + (f" · env {env}" if env not in (None, "-", "") else "")
        out.append(f"| {cell(r['check_id'])} | {cell(r['deliverable'])} | `{cell(r['check'])}` (rung {r['rung']}) "
                   f"| {cell(where)} | {cell(state.get(r['check_id'], 'not evaluated'))} |")
    return out


def gate_section(gate, problem):
    out = ["## 2. Gate", ""]
    if problem:
        return out + [problem]
    out.append(f"- Verdict: {gate.get('verdict')}{' · ' + gate['marker'] if gate.get('marker') else ''}")
    out += [f"- block `{b.get('id')}` — {cell(b.get('what'))}" for b in gate.get("blocks", [])]
    return out


def verify_section(scope, unit):
    path = os.path.join(scope, "artifacts", f"verify-{unit}-report.md")
    out = ["## 3. Verify report", ""]
    if not os.path.exists(path):
        return out + ["No verify report."]
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    out.append(f"From `artifacts/verify-{unit}-report.md` — checks and findings (weak rows and misfiled "
               "nits included):")
    for title in ("Checks", "Findings"):
        m = re.search(rf"^## \d+\. {title}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
        out += ["", f"### {title}", "", (m.group(1).strip() if m else f"(no {title} section)")]
    return out


def review_section(scope, unit, gate):
    out = ["## 4. Review", ""]
    review, problem = records(os.path.join(scope, "artifacts", f"review-{unit}.jsonl"), "review log")
    if problem:
        return out + [problem]
    reviews = [r for r in review if r.get("record") == "review"]
    findings = {r["finding_id"]: r for r in review if r.get("record") == "finding"}
    latest = {r["finding_id"]: r for r in review if r.get("record") == "disposition"}
    who = collections.Counter(("codex" if str(r.get("reviewer", "")).startswith("codex")
                               else str(r.get("reviewer", "?")).split()[0]) for r in reviews)
    sev = collections.Counter(f.get("severity") for f in findings.values())
    kinds = collections.Counter(d.get("disposition") for d in latest.values())
    out.append(f"- Rounds: {len(reviews)} reviews ({', '.join(f'{k} ×{v}' for k, v in sorted(who.items()))})")
    if reviews:
        out.append(f"- Last: {reviews[-1].get('review_id')} — {reviews[-1].get('verdict')} ({reviews[-1].get('reviewer')})")
    out.append(f"- Findings: {len(findings)} ({', '.join(f'{k} {v}' for k, v in sorted(sev.items())) or 'none'})")
    undisposed = len(set(findings) - set(latest))
    out.append(f"- Outcomes: {', '.join(f'{k} {v}' for k, v in sorted(kinds.items())) or 'none'}"
               + (f" · {undisposed} without a disposition" if undisposed else ""))
    blocks = {b.get("id") for b in (gate or {}).get("blocks", [])}
    out.append("- Accepted: unknown (gate not evaluated)" if gate is None else
               "- Accepted: no — outcomes not accepted since the last finding" if "review-acceptance" in blocks else
               "- Accepted: yes")
    out += ["", "Rejections and accepted nits:", ""]
    picked = [(fid, d) for fid, d in latest.items() if d.get("disposition") in ("rejected", "accepted")]
    out += [f"- {'rejected' if d['disposition'] == 'rejected' else 'nit'} `{fid}` — {cell(d.get('reason'))}"
            for fid, d in picked] or ["None."]
    return out


DECISION_REF = re.compile(r"\bAlex,? (\d{2,4})\b|\b(\d{2,4}) \(Alex\)")


def decision_refs(text, review):
    """Decision numbers the unit cites — `Alex 98` / `86 (Alex)` in its progress section or a
    review disposition — so a Decisions Log line that never names the unit still belongs to it."""
    found = DECISION_REF.findall(text) + [m for r in review or []
                                          for m in DECISION_REF.findall(str(r.get("reason") or ""))]
    return {a or b for a, b in found}


def decisions_section(scope, unit):
    out = ["## 5. Decisions", ""]
    path = vl.progress_file(scope)
    if not path:
        return out + ["No progress file (progress.md or *-PROGRESS.md)."]
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"^## Decisions Log\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        return out + [f"No Decisions Log section in {os.path.basename(path)}."]
    sec = re.search(rf"^## Plan {re.escape(unit)}:.*?(?=^## |\Z)", text, re.M | re.S)
    review, _ = records(os.path.join(scope, "artifacts", f"review-{unit}.jsonl"), "review log")
    # a standalone plan's progress file is the unit's own section
    refs = decision_refs(sec.group(0) if sec else ("" if path.endswith("progress.md") else text), review)
    pat = re.compile(rf"(?<![\d.]){re.escape(unit)}(?![\d])")
    num = re.compile(rf"(?<![\d.-])({'|'.join(sorted(refs))})(?![\d.-])") if refs else None
    hits = [l for l in m.group(1).splitlines()
            if l.startswith("- ") and (pat.search(l) or (num and num.search(l)))]
    return out + ([f"- {cell(l[2:])}" for l in hits] or [f"None mention {unit}."])


def merges_section(scope, unit):
    out = ["## 6. Merges", ""]
    recs, problem = records(os.path.join(scope, "artifacts", f"merges-{unit}.jsonl"), "merge log")
    if problem:
        return out + (["None recorded by driver-merge.py."] if recs is None and problem.startswith("No ") else [problem])
    return out + ([f"- {r.get('slug')}#{r.get('pr')} → {r.get('base')} @ {str(r.get('sha'))[:12]} "
                   f"({str(r.get('ts', ''))[:16]}){' · ' + ', '.join(r['flags']) if r.get('flags') else ''}"
                   for r in recs] or ["None recorded by driver-merge.py."])


def render(scope, unit):
    gate, problem = gate_state(scope, unit)
    lines = [f"# Phase report — {unit}", "",
             f"**Generated:** {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')} · "
             f"**Scope:** {scope}", ""]
    for sec in (rows_section(scope, unit, gate), gate_section(gate, problem), verify_section(scope, unit),
                review_section(scope, unit, gate), decisions_section(scope, unit), merges_section(scope, unit)):
        lines += sec + [""]
    return "\n".join(lines).rstrip("\n") + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scope", required=True)
    ap.add_argument("--unit", required=True)
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    scope = os.path.abspath(os.path.expanduser(a.scope))
    if not os.path.isdir(scope):
        print(f"phase-report: no scope folder {scope}", file=sys.stderr)
        return 2
    text = render(scope, a.unit)
    if not a.no_write:
        path = os.path.join(scope, "artifacts", f"phase-report-{a.unit}.md")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            with open(path, encoding="utf-8") as fh:
                ok = fh.read() == text  # written, then read back (ARCHITECTURE §3.9)
        except OSError as e:
            ok, text = False, text + f"\n(not saved: {e})\n"
        if not ok:
            sys.stdout.write(text)
            print(f"phase-report: {path} did not read back — the report above is not saved", file=sys.stderr)
            return 3
        print(f"report: {path}", file=sys.stderr)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
