#!/usr/bin/env python3
"""verdict-gate.py — may this unit be marked Done? Reads the finish table, the verdict
log, the review log and the ledger's base SHAs; decides nothing a script can't.

Approach: for every finish-table row the unit owns, find the latest `final` verdict and
block on anything templates/verify-contracts.md §5.2 names — no verdict, an unfinished
newer run, fail / inconclusive, undeclared unreachable, under-rung, a table revision
change, or evidence whose SHA sits outside the unit's `base..HEAD` (base = the SHA
ledger-init.sh recorded at phase start; with no base, evidence must be at HEAD). Then
§5.2.1: every review finding carries a disposition. A non-codex judge on a deciding
verdict yields the `⚠ judge:` marker (§5.3). In advisory mode (§5.4) the same blocks are
reported with exit 0 and an advisory marker; `--skip-verify` bypasses loudly.

Usage:  verdict-gate.py --scope DIR --unit N.P [--advisory|--blocking] [--skip-verify REASON]
                        [--projects DIR] [--json]
        paths: DIR/finish-conditions.md · DIR/artifacts/verify-<unit>.jsonl ·
               DIR/artifacts/review-<unit>.jsonl (optional) · DIR/closeout-prep.md (bases)
Output: one line per owned check, a §10 message per block, then `verdict: …` and, when
        set, `marker: …` (the text plans-index.py appends to the index status).
Exit:   0 pass / advisory / skipped · 1 blocked · 2 usage · 3 could not evaluate
"""

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_lib as vl  # noqa: E402

DOCS = f"{vl.CONTRACT} §5"


def git_ok(path, *args):
    return subprocess.run(["git", "-C", path, *args], capture_output=True, text=True).returncode == 0


def git_out(path, *args):
    p = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


def bases(ledger, unit):
    """{repo: sha} — the FIRST `- base: <unit> <repo> <sha>` per repo (a resumed phase
    must not shrink the range)."""
    out = {}
    if not os.path.exists(ledger):
        return out
    with open(ledger, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^\s*-\s*base:\s*(\S+)\s+(\S+)\s+([0-9a-f]{7,40})\s*$", line)
            if m and m.group(1) == unit:
                out.setdefault(m.group(2), m.group(3))
    return out


def coverage_blocks(review_log):
    """§6.3 / §5.2.1 — findings without a valid latest disposition."""
    recs = vl.read_jsonl(review_log)
    findings = [r for r in recs if r.get("record") == "finding"]
    latest = {}
    for r in recs:
        if r.get("record") == "disposition":
            latest[r.get("finding_id")] = r
    blocks = []
    for f in findings:
        fid, d = f.get("finding_id"), latest.get(f.get("finding_id"))
        where = f"{review_log} · {fid} ({f.get('file')}:{f.get('line')})"
        if d is None:
            blocks.append((fid, "review finding has no disposition", "`fixed <sha>` or `rejected <reason>`",
                           "no disposition recorded", where, "code"))
        elif d.get("disposition") == "fixed" and not d.get("sha"):
            blocks.append((fid, "`fixed` disposition without a commit", "the fixing commit's SHA",
                           "sha missing", where, "code"))
        elif d.get("disposition") == "rejected" and not str(d.get("reason") or "").strip():
            blocks.append((fid, "`rejected` disposition without a reason", "the reason the finding is wrong",
                           "reason missing", where, "code"))
        elif d.get("disposition") not in ("fixed", "rejected"):
            blocks.append((fid, "unknown disposition", "`fixed` or `rejected`", repr(d.get("disposition")),
                           where, "tooling"))
    return blocks, len(findings)


def evidence_line(pend):
    """The one output line that says why: the first [FAIL]/[BLOCK]/[ERROR] line, else the last
    non-empty line of the runner's output_tail (§10: actual values, not adjectives)."""
    lines = [x.strip() for x in ((pend or {}).get("output_tail") or "").splitlines() if x.strip()]
    flagged = [x for x in lines if re.match(r"^\[(FAIL|BLOCK|ERROR)\]", x)]
    line = (flagged or lines or [""])[0 if flagged else -1]
    return f" — output: {line[:200]}" if line else ""


def evaluate(scope, unit, projects):
    """Return (rows_report, blocks, judge_lines). Raises vl.ContractError."""
    table = vl.parse_table(os.path.join(scope, "finish-conditions.md"))
    owned = vl.select(table["rows"], unit)
    log = os.path.join(scope, "artifacts", f"verify-{unit}.jsonl")
    recs = vl.read_jsonl(log)
    base = bases(os.path.join(scope, "closeout-prep.md"), unit)
    report, blocks, judges = [], [], set()
    if not owned:
        raise vl.ContractError(vl.message("ERROR", f"no finish-table rows owned by {unit}",
                                          f"at least one row whose owner is {unit} or {unit}/…", "0 rows",
                                          table["path"], "code", "add the unit's rows, bump Revision",
                                          f"{vl.CONTRACT} §3.4"))
    heads = {}
    for row in owned:
        cid = row["check_id"]
        run_cmd = (f"verify-run.py run --table {table['path']} --log {log} --owner {unit}")

        def block(what, expected, found, cause, nxt=run_cmd):
            blocks.append((cid, what, expected, found, f"{cid} · {log}", cause, nxt))
            report.append(f"BLOCK  {cid}  {what}")

        finals = [(i, r) for i, r in enumerate(recs) if r.get("run_state") == "final" and cid in r.get("results", {})]
        if not finals:
            block("no final verdict", "a finalized run covering this check", "none in the verdict log", "tooling")
            continue
        fi, final = finals[-1]
        newer = [r for r in recs[fi + 1:] if r.get("run_state") == "pending" and r.get("check_id") == cid]
        if newer:
            block("an unfinished run is newer than the verdict", "every run judged and finalized",
                  f"pending run {newer[-1]['run_id']}", "tooling",
                  f"verify-run.py finalize --log {log} --run-id {newer[-1]['run_id']} ...")
            continue
        res = final["results"][cid]
        pend = next((r for r in recs if r.get("run_state") == "pending" and r.get("run_id") == final["run_id"]
                     and r.get("check_id") == cid), None)
        judges.add(final.get("judge", ""))
        if final.get("table_rev") != table["revision"]:
            block("verdict predates the current finish table", f"table_rev {table['revision']}",
                  f"table_rev {final.get('table_rev')}", "code")
            continue
        if res["result"] in ("fail", "inconclusive"):
            block(f"verdict is {res['result']}", "pass", f"{res['result']}: {res['reason']}{evidence_line(pend)}",
                  "code" if res["result"] == "fail" else "environment")
            continue
        if res["result"] == "verified-unreachable" and not row["unreachable_ok"]:
            block("unreachable, and the table does not allow it", "pass (unreachable_ok is `no`)",
                  f"verified-unreachable: {res['reason']}", "environment")
            continue
        if res["rung_reached"] < row["rung"]:
            block("verdict is under the required rung", f"rung ≥ {row['rung']}", f"rung {res['rung_reached']}", "code")
            continue
        if pend is None or not pend.get("sha"):
            block("verdict has no evidence SHA", "the pending record with the tested SHA", "none", "tooling")
            continue
        repo, sha = pend["repo"], pend["sha"]
        repo_path = os.path.join(projects, repo)
        if repo not in heads:
            heads[repo] = git_out(repo_path, "rev-parse", "HEAD")
        head = heads[repo]
        if head is None:
            block("cannot read the evidence repo", f"a git repo at {repo_path}", "not readable", "environment",
                  f"git -C {repo_path} status")
            continue
        if repo in base:
            b = base[repo]
            inside = git_ok(repo_path, "merge-base", "--is-ancestor", b, sha) and \
                git_ok(repo_path, "merge-base", "--is-ancestor", sha, head)
            if not inside:
                block("evidence SHA is outside the unit's range", f"{b[:10]}..{head[:10]} in {repo}",
                      f"evidence at {sha[:10]}", "code")
                continue
        elif sha != head:
            block("evidence is stale and no base SHA is recorded", f"evidence at HEAD {head[:10]} of {repo}",
                  f"evidence at {sha[:10]}", "code")
            continue
        report.append(f"pass   {cid}  {res['result']} · rung {res['rung_reached']}/{row['rung']} · "
                      f"{final.get('judge')}")
    review = os.path.join(scope, "artifacts", f"review-{unit}.jsonl")
    if os.path.exists(review):
        cov, n = coverage_blocks(review)
        for fid, what, exp, found, where, cause in cov:
            blocks.append((fid, what, exp, found, where, cause, "record the disposition through /review's log writer"))
            report.append(f"BLOCK  {fid}  {what}")
        report.append(f"review {n} finding(s), {n - len(cov)} dispositioned")
    return report, blocks, sorted(j for j in judges if j)


def main(argv):
    ap = argparse.ArgumentParser(description="Verification gate (templates/verify-contracts.md §5).")
    ap.add_argument("--scope", required=True)
    ap.add_argument("--unit", required=True)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--advisory", dest="mode", action="store_const", const="advisory")
    mode.add_argument("--blocking", dest="mode", action="store_const", const="blocking")
    ap.add_argument("--skip-verify", metavar="REASON")
    ap.add_argument("--projects", default=vl.PROJECTS)
    ap.add_argument("--json", action="store_true")
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return vl.EXIT_USAGE if exc.code else vl.EXIT_PASS
    a.mode = a.mode or vl.GATE_MODE

    if a.skip_verify is not None:
        if not a.skip_verify.strip():
            print(vl.message("ERROR", "--skip-verify needs a reason", "a reason a reader can judge", "empty",
                             "--skip-verify", "tooling", '--skip-verify "<why verification cannot run>"',
                             f"{vl.CONTRACT} §5.4"), file=sys.stderr)
            return vl.EXIT_USAGE
        marker = f"⚠ verify skipped: {a.skip_verify.strip()}"
        out = {"verdict": "skipped", "unit": a.unit, "blocks": [], "marker": marker}
        print(json.dumps(out) if a.json else f"verdict: SKIPPED ({a.unit})\nmarker: {marker}")
        return vl.EXIT_PASS

    try:
        report, blocks, judges = evaluate(a.scope, a.unit, a.projects)
    except vl.ContractError as exc:
        if a.json:
            print(json.dumps({"verdict": "error", "unit": a.unit, "error": exc.msg}))
        print(exc.msg, file=sys.stderr)
        return vl.EXIT_EVAL

    markers = [f"⚠ judge: {j}" for j in judges if not j.startswith("codex ")]
    if blocks and a.mode == "advisory":
        ids = ", ".join(b[0] for b in blocks)
        markers.append(f"⚠ verify advisory: {len(blocks)} blocked ({ids})")
    verdict = "pass" if not blocks else ("advisory" if a.mode == "advisory" else "blocked")
    marker = " ".join(markers)
    level = "WARN" if a.mode == "advisory" else "BLOCK"
    msgs = [vl.message(level, what, exp, found, where, cause, nxt, DOCS)
            for _, what, exp, found, where, cause, nxt in blocks]
    if a.json:
        print(json.dumps({"verdict": verdict, "unit": a.unit, "marker": marker, "report": report,
                          "blocks": [{"id": b[0], "what": b[1], "cause": b[5]} for b in blocks],
                          "messages": msgs}))
    else:
        print("\n".join(report))
        for m in msgs:
            print(m)
        label = {"pass": "PASS", "advisory": "ADVISORY — would block", "blocked": "BLOCKED"}[verdict]
        print(f"verdict: {label} ({a.unit}, {len(blocks)} block(s), mode {a.mode})")
        if marker:
            print(f"marker: {marker}")
    return vl.EXIT_FAIL if verdict == "blocked" else vl.EXIT_PASS


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
