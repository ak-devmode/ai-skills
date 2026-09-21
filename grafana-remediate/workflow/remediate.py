#!/usr/bin/env python3
# Orchestrator spine of the alarm-remediation workflow (scope 146, Phase 2, Task 2.1).
#
# Approach: this is the substrate-agnostic driver Alex chose (decision 1a, 2026-09-21) —
# ONE artifact that runs identically in a dev shell now and as the 5a-WITA CC cloud
# routine later (Phase 4 swaps the scheduler, not the logic). It wires the already-built
# deterministic front-end (classify.py) to the agentic stages (agent.py + prompts/) via
# discrete gates (gates.py), the per-alarm worktree (worktree.py), dedup (dedup.py),
# egress (email_ses.py) and liveness (heartbeat.py).
#
# The HARD SAFETY FLOOR is structural: this module has no code path that merges,
# deploys, or silences. The only write actions are "send a proposal email" and "open a
# PR" (never merge). Every egress passes the PHI gate first. Repro-or-nothing: a defect
# reaches a PR only through the repro gate (fails pre-fix) + verify gate (passes
# post-fix, tied to the original signal); anything short degrades to a proposal email.
#
# Per-incident state machine (by classify route):
#   DROP                 -> skip (noise / known / deduped)
#   PROPOSE / INVESTIGATE-> root-cause -> proposal email -> PHI gate -> SES
#   PIPELINE             -> root-cause -> [honesty gate: annotation may abort to PROPOSE]
#                           -> worktree -> repro gate (fail-closed) -> fix -> verify gate
#                           -> PR (+ reuse PR summary in email) -> PHI gate -> SES
#                           degrade to PROPOSE on any repro/verify failure; keep the
#                           worktree only on a verify-gate failure.
#
# --dry-run (DEFAULT): runs only the deterministic front-end + routing, NO LLM calls and
# NO egress. This is the Task 2.5 read-only calibration pass. --once runs the live
# pipeline over one corpus/day. Egress stays dry unless --send / --allow-pr are given.
#
# Stdlib only.

import argparse
import json
import subprocess
import sys
from pathlib import Path

import classify
import dedup
import gates
import heartbeat
import email_ses
import worktree as wt
from agent import run_agent

HERE = Path(__file__).parent
DEFAULT_CORPUS = HERE.parent / "september-alarms.json"
# Base checkouts the worktree gate clones from (blast radius = gateway-go only, t0).
REPO_ROOT = Path.home() / "Projects" / "wellmed"


def _agent_ctx(inc, extra=None):
    lab = inc.get("labels", {})
    ctx = {"alertName": inc.get("alertName", "?"), "class": inc.get("class", "?"),
           "route": inc.get("route", "?"), "env": lab.get("env", "?"),
           "tier": lab.get("tier", "?"), "firings": inc.get("firings", 0),
           "repo": inc.get("repo", ""),
           "root_cause": inc.get("root_cause", "(not yet determined)"),
           "recommended_lever": inc.get("recommended_lever", "(none)"),
           "annotation": inc.get("annotation", "(no rule annotation available)"),
           "evidence": json.dumps(lab, ensure_ascii=False)}
    if extra:
        ctx.update(extra)
    return ctx


def _egress_email(inc, agent_email=None, pr_summary=None, send=False):
    """Compose -> PHI gate -> (redact if needed) -> send. Returns an outcome dict.
    Nothing leaves the estate unredacted: the PHI gate runs on the assembled payload
    and send() enforces it a second time."""
    subject, body = email_ses.compose(inc, agent_email=agent_email, pr_summary=pr_summary)
    ok, findings, redacted_body = gates.phi_gate(subject + "\n" + body)
    if not ok:
        # HOLD raw; re-compose from the redacted body so a human still gets the gist.
        subject2, body2 = email_ses.compose(
            inc, pr_summary=redacted_body.split("\n", 1)[-1], redacted_count=len(findings))
        res = email_ses.send(subject2, body2, dry_run=not send)
        res.update(phi_held=True, redacted=[t for t, _ in findings])
        return res
    return {**email_ses.send(subject, body, dry_run=not send), "phi_held": False}


def _pipeline(inc, runner=None, send=False, allow_pr=False, tree_factory=None):
    """The code-defect path. Returns (outcome, kept_worktree)."""
    tree_factory = tree_factory or (lambda repo, sig: wt.Worktree(
        repo, base_ref="origin/main", signature=sig).create())
    ctx = _agent_ctx(inc)
    rc = run_agent("root_cause", ctx, runner=runner)
    inc["root_cause"] = rc["root_cause"]
    inc["recommended_lever"] = rc["recommended_lever"]
    # Honesty gate (HPACK negative test): annotation can abort PIPELINE to PROPOSE.
    if not gates.root_cause_allows_pipeline(rc):
        em = run_agent("email", _agent_ctx(inc, {"candidate_diff": ""}), runner=runner)
        out = _egress_email(inc, agent_email=em, send=send)
        return {"route": "PROPOSE(degraded:root-cause)", **out}, False

    tree = tree_factory(REPO_ROOT / inc["repo"], dedup.signature_key(inc))
    try:
        repro = gates.repro_gate(inc, _agent_ctx(inc, {"root_cause": rc["root_cause"],
                                 "recommended_lever": rc["recommended_lever"]}),
                                 tree, runner=runner)
        if not repro["available"]:
            em = run_agent("email", _agent_ctx(inc, {"candidate_diff": ""}), runner=runner)
            out = _egress_email(inc, agent_email=em, send=send)
            tree.prune()
            return {"route": "PROPOSE(degraded:no-repro)", "notes": repro["notes"], **out}, False

        # The fix stage runs INSIDE the worktree so the agent can read the code.
        fix = run_agent("fix", _agent_ctx(inc, {"root_cause": rc["root_cause"],
                        "repro_cmd": repro["repro_cmd"],
                        "signal_assertion": repro["signal_assertion"]}),
                        runner=runner, cwd=str(tree.path))
        applied, err = tree.apply_diff(fix["diff"])
        if not applied:
            em = run_agent("email", _agent_ctx(inc, {"candidate_diff": fix["diff"]}), runner=runner)
            out = _egress_email(inc, agent_email=em, send=send)
            tree.prune()
            return {"route": "PROPOSE(degraded:patch-failed)", "notes": err[:200], **out}, False

        post_rc, post_out = tree.run(repro["repro_cmd"])
        verdict = gates.verify_gate(repro, post_rc, post_out, _agent_ctx(inc), runner=runner)
        if not verdict["accepted"]:
            tree.keep = True  # kept for inspection (only case we do not prune)
            em = run_agent("email", _agent_ctx(inc, {"candidate_diff": fix["diff"]}), runner=runner)
            out = _egress_email(inc, agent_email=em, send=send)
            return {"route": "PROPOSE(degraded:verify-failed)",
                    "verdict": verdict["verdict"], "worktree": str(tree.path), **out}, True

        # verify passed -> PR path (never merge). Reuse the PR summary in the email.
        pr = open_pr(inc, fix, repro, tree, allow=allow_pr)
        out = _egress_email(inc, pr_summary=pr["summary"], send=send)
        tree.prune()
        return {"route": "PR", "pr": pr, **out}, False
    finally:
        if not tree.keep and tree.path.exists():
            tree.prune()


def _trunk_of(repo_path):
    """Per-repo trunk: develop for wellmed repos, else main (memory: branch defaults)."""
    for cand in ("develop", "main"):
        r = subprocess.run(["git", "-C", str(repo_path), "ls-remote", "--heads",
                            "origin", cand], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return cand
    return "main"


def open_pr(inc, fix, repro, tree, allow=False):
    """Open a PR against the blast-radius repo. NEVER merges. The PR summary is the
    Sonnet-generated fix explanation (reused downstream in the email, no re-eval)."""
    summary = (f"## Auto-remediation candidate: {inc['alertName']}\n\n"
               f"**Root cause:** {inc.get('root_cause','')}\n\n"
               f"**Fix:** {fix['explanation']}\n\n"
               f"**Repro (fails pre-fix, passes post-fix):** `{repro['repro_cmd']}`\n"
               f"**Signal asserted:** {repro['signal_assertion']}\n\n"
               f"Files: {', '.join(fix['files_touched'])}\n\n"
               f"_Opened by the alarm-remediation workflow. NOT merged — human review "
               f"required. The workflow never merges or deploys._")
    if not allow:
        return {"opened": False, "reason": "allow_pr=False (default; guarded)", "summary": summary}

    repo = inc.get("repo", "")
    branch = "alarm-remediation/" + "".join(
        c if c.isalnum() else "-" for c in dedup.signature_key(inc))[:60].strip("-")
    trunk = _trunk_of(tree.repo_path)

    def g(*a):
        return subprocess.run(["git", "-C", str(tree.path), *a], capture_output=True, text=True)

    steps = []
    for args in (["checkout", "-b", branch],
                 ["add", "-A"],
                 ["commit", "-m", f"fix: {inc['alertName']} (auto-remediation candidate, scope 146)"],
                 ["push", "-u", "origin", branch]):
        r = g(*args)
        steps.append((args[0], r.returncode))
        if r.returncode != 0:
            return {"opened": False, "reason": f"git {args[0]} failed: {r.stderr[:200]}",
                    "summary": summary, "steps": steps}

    slug = f"kalpa-health/{repo}"
    pr = subprocess.run(
        ["gh", "pr", "create", "--repo", slug, "--base", trunk, "--head", branch,
         "--title", f"[auto-remediation] {inc['alertName']}", "--body", summary],
        capture_output=True, text=True, cwd=str(tree.path))
    if pr.returncode != 0:
        return {"opened": False, "reason": f"gh pr create failed: {pr.stderr[:200]}",
                "summary": summary, "branch": branch}
    return {"opened": True, "url": pr.stdout.strip(), "branch": branch,
            "base": trunk, "summary": summary}


def process(incidents, dry_run=True, runner=None, send=False, allow_pr=False,
            gh_enabled=True, tree_factory=None):
    store = dedup.load_store()
    results, counts = [], {"emails": 0, "prs": 0, "held": 0, "errors": 0, "dropped": 0}
    for inc in incidents:
        route = inc["route"]
        dup, why = dedup.is_duplicate(inc, store, repo=inc.get("repo"), gh_enabled=gh_enabled)
        if route == "DROP" or dup:
            results.append({"alertName": inc["alertName"], "route": "DROP",
                            "class": inc["class"], "why": why if dup else inc["why"]})
            counts["dropped"] += 1
            continue
        if dry_run:
            # Read-only calibration: record intended route, no LLM, no egress.
            results.append({"alertName": inc["alertName"], "route": route,
                            "class": inc["class"], "firings": inc["firings"],
                            "env": inc["labels"].get("env", "?"), "why": inc["why"]})
            continue
        try:
            if route in ("PROPOSE", "INVESTIGATE"):
                ctx = _agent_ctx(inc)
                rc = run_agent("root_cause", ctx, runner=runner)
                inc["root_cause"] = rc["root_cause"]
                inc["recommended_lever"] = rc["recommended_lever"]
                em = run_agent("email", _agent_ctx(inc, {"candidate_diff": ""}), runner=runner)
                out = _egress_email(inc, agent_email=em, send=send)
                results.append({"alertName": inc["alertName"], "route": route, **out})
                counts["held" if out.get("phi_held") else "emails"] += 1
            elif route == "PIPELINE":
                out, _kept = _pipeline(inc, runner=runner, send=send, allow_pr=allow_pr,
                                       tree_factory=tree_factory)
                results.append({"alertName": inc["alertName"], **out})
                counts["prs" if out.get("route") == "PR" else "emails"] += 1
            dedup.record_handled(inc, store, results[-1]["route"])
        except Exception as e:  # fail-loud per incident; the run continues + heartbeats
            results.append({"alertName": inc["alertName"], "route": "ERROR", "error": str(e)})
            counts["errors"] += 1
    if not dry_run:
        dedup.save_store(store)
    return results, counts


def load_incidents(corpus):
    anns = json.loads(Path(corpus).read_text())
    incidents = classify.collapse_to_incidents(anns)
    routed = []
    for inc in incidents:
        cls, route, why = classify.classify(inc)
        # t0 blast radius: only gateway-go is auto-PR eligible; force others off PIPELINE.
        repo = "wellmed-gateway-go" if "gateway" in (inc["alertName"] or "").lower() else ""
        if route == "PIPELINE" and not repo:
            route, why = "INVESTIGATE", why + " [not in blast radius -> investigate]"
        routed.append({**inc, "class": cls, "route": route, "why": why, "repo": repo})
    return routed


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grafana alarm auto-remediation workflow")
    ap.add_argument("corpus", nargs="?", default=str(DEFAULT_CORPUS),
                    help="alarm JSON (default: September corpus)")
    ap.add_argument("--once", action="store_true", help="run the live pipeline (LLM stages)")
    ap.add_argument("--send", action="store_true", help="actually send SES email (else dry)")
    ap.add_argument("--allow-pr", action="store_true", help="allow live PR creation (Phase 3+)")
    ap.add_argument("--no-gh", action="store_true", help="skip gh linked-PR dedup check")
    ap.add_argument("--only", default=None,
                    help="process only incidents whose alertName contains this substring")
    args = ap.parse_args(argv)

    reaped = wt.age_sweep()
    incidents = load_incidents(args.corpus)
    if args.only:
        incidents = [i for i in incidents if args.only.lower() in (i["alertName"] or "").lower()]
    dry = not args.once
    results, counts = process(incidents, dry_run=dry, send=args.send,
                              allow_pr=args.allow_pr, gh_enabled=not args.no_gh)

    hb = heartbeat.emit({"incidents": len(incidents), "reaped_worktrees": len(reaped),
                         **counts}, ok=counts["errors"] == 0)
    print(f"mode={'DRY-RUN' if dry else 'LIVE'}  corpus={Path(args.corpus).name}  "
          f"incidents={len(incidents)}")
    for r in results:
        print(f"  [{r['route']:<26}] {r['alertName']}"
              + (f"  ({r.get('why','')})" if r.get("why") else ""))
    print(heartbeat.status_line(hb))
    return results


if __name__ == "__main__":
    main()
