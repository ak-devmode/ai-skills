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
reported with exit 0 and an advisory marker; `--skip-verify` bypasses loudly. A unit the
table lists under `**Predates gate:**` was Done before the gate existed: exempt, exit 0.
`--all` is /closeout's view: every gated unit in the table, and any block is a failure
whatever the mode — the scope cannot report HEALED on it (scope 5 §4.3).

Usage:  verdict-gate.py --scope DIR (--unit N.P | --all) [--advisory|--blocking]
                        [--skip-verify REASON] [--projects DIR] [--json]
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


def coverage_blocks(review_log):
    """§6.3 / §5.2.1 — findings without a valid latest disposition."""
    recs = vl.read_jsonl(review_log)
    findings = [r for r in recs if r.get("record") == "finding"]
    latest = {}
    for r in recs:
        if r.get("record") == "disposition":
            latest[r.get("finding_id")] = r
    blocks = []
    ids = [f.get("finding_id") for f in findings]
    for fid in sorted({i for i in ids if ids.count(i) > 1}):
        # One disposition must never clear two findings (review 5.2-r1-04).
        blocks.append((fid, "duplicate finding ID", "one finding per finding_id",
                       f"{ids.count(fid)} findings share it", f"{review_log} · {fid}", "tooling"))
    for f in findings:
        fid, d = f.get("finding_id"), latest.get(f.get("finding_id"))
        where = f"{review_log} · {fid} ({f.get('file')}:{f.get('line')})"
        if d is None:
            blocks.append((fid, "review finding has no disposition", "`fixed <sha>` or `rejected <reason>`",
                           "no disposition recorded", where, "code"))
        elif d.get("disposition") == "fixed" and not d.get("sha"):
            blocks.append((fid, "`fixed` disposition without a commit", "the fixing commit's SHA",
                           "sha missing", where, "code"))
        elif d.get("disposition") == "fixed" and d.get("via") == "off-anchor" and not str(d.get("reason") or "").strip():
            blocks.append((fid, "`fixed` off the anchor without a reason",
                           "how a commit that touches neither the file nor a test beside it fixes the finding",
                           "reason missing", where, "code"))
        elif d.get("disposition") == "rejected" and not str(d.get("reason") or "").strip():
            blocks.append((fid, "`rejected` disposition without a reason", "the reason the finding is wrong",
                           "reason missing", where, "code"))
        elif d.get("disposition") == "deferred" and (
                f.get("severity") == "blocking"
                or not str(d.get("reason") or "").strip()
                or not vl.todo_has_item(os.path.dirname(os.path.dirname(review_log)), fid, open_only=False)):
            blocks.append((fid, "`deferred` disposition on a blocking finding, or its TO-DO item is gone",
                           "a non-blocking finding whose TO-DO item exists (open, or closed into the archive)",
                           f"severity {f.get('severity')}, reason {d.get('reason')!r}", where, "code"))
        elif d.get("disposition") not in ("fixed", "rejected", "deferred"):
            blocks.append((fid, "unknown disposition", "`fixed`, `rejected` or `deferred`",
                           repr(d.get("disposition")), where, "tooling"))
    return blocks, len(findings)


def accepted(review_log):
    """§6.4: the log's last finding/disposition is followed by an `acceptance` record."""
    last = None
    for r in vl.read_jsonl(review_log):
        if r.get("record") in ("finding", "disposition"):
            last = "open"
        elif r.get("record") == "acceptance" and str(r.get("by") or "").strip():
            last = "accepted"
    return last == "accepted"


def fallback_markers(review_log, projects):
    """`review <reviewer>` for each fallback review no later codex review covers (review/SKILL.md
    §3). Covered = same repo, codex base an ancestor of the fallback's base, fallback head an
    ancestor of codex head (review 5.2-r2-01). Records without resolved `shas` cannot prove
    coverage, so they keep the marker; logs predating `review` records use the latest
    finding's reviewer."""
    recs = vl.read_jsonl(review_log)
    reviews = [r for r in recs if r.get("record") == "review"]
    if not reviews:
        f = [r for r in recs if r.get("record") == "finding"]
        return [f"review {f[-1].get('reviewer', 'unrecorded')}"] if f and not \
            str(f[-1].get("reviewer", "")).startswith("codex ") else []

    def covers(c, f):
        (repo, _), = f["range"].items()
        cs, fs = c.get("shas") or {}, f.get("shas") or {}
        path = os.path.join(projects, repo)
        return (repo in c.get("range", {}) and all(cs.get(k) and fs.get(k) for k in ("base", "head"))
                and git_ok(path, "merge-base", "--is-ancestor", cs["base"], fs["base"])
                and git_ok(path, "merge-base", "--is-ancestor", fs["head"], cs["head"]))

    out = []
    for i, f in enumerate(reviews):
        if str(f.get("reviewer", "")).startswith("codex "):
            continue
        if not any(str(c.get("reviewer", "")).startswith("codex ") and covers(c, f) for c in reviews[i + 1:]):
            out.append(f"review {f.get('reviewer', 'unrecorded')}")
    return out


def review_presence_blocks(review_log, base, projects):
    """§5.2.1 — a unit with commits must have been reviewed (review 5.3-r1-03).

    For every repo whose ledger base has commits in base..HEAD, some `review` record must
    name that repo and cover the unit's start: its base at or before the unit's base, its head
    after it AND on the current branch (a review of a discarded branch covers nothing —
    5.3-r2-03). Later commits (progress notes) don't force a re-review. The fix of every
    *blocking* finding must itself sit inside a later review's range, which is /plan §6.8's
    "review the fixes again" (5.3-r2-03). A git call that fails is a block, never a zero
    (5.3-r2-02)."""
    recs = vl.read_jsonl(review_log) if os.path.exists(review_log) else []
    reviews = [r for r in recs if r.get("record") == "review"]
    # Logs from before `review` records existed (§6.0) carry the range on each finding.
    for f in recs:
        if f.get("record") == "finding" and not any(r.get("review_id") == f.get("review_id") for r in reviews):
            for repo_, rng in (f.get("range") or {}).items():
                fb, _, fh = rng.partition("..")
                if fb and fh:
                    reviews.append({"review_id": f.get("review_id"), "range": {repo_: rng},
                                    "shas": {"base": fb, "head": fh}})
    blocks = []

    def inside(path, r, sha):
        """sha in (r.base, r.head], and r.head on the current branch."""
        sh = r.get("shas") or {}
        return bool(sh.get("base") and sh.get("head")) and not sha.startswith(sh["base"]) \
            and not sh["base"].startswith(sha) \
            and git_ok(path, "merge-base", "--is-ancestor", sh["base"], sha) \
            and git_ok(path, "merge-base", "--is-ancestor", sha, sh["head"]) \
            and git_ok(path, "merge-base", "--is-ancestor", sh["head"], "HEAD")

    for repo, b in sorted(base.items()):
        path = os.path.join(projects, repo)
        n = git_out(path, "rev-list", "--count", f"{b}..HEAD")
        if n is None:
            blocks.append((f"review:{repo}", "cannot count the unit's commits", f"git rev-list {b[:10]}..HEAD "
                           f"in {repo}", "git failed", f"{path}", "environment"))
            continue
        if n == "0":
            continue
        mine = [r for r in reviews if repo in r.get("range", {})]
        # the unit's first commit must sit inside a review on this branch
        oldest = (git_out(path, "rev-list", "--reverse", f"{b}..HEAD") or "").splitlines()[:1]
        if not any(oldest and inside(path, r, oldest[0]) for r in mine):
            blocks.append((f"review:{repo}", "commits in range were never reviewed",
                           f"a /review record on this branch covering {b[:10]}.. in {repo}",
                           f"{n} commit(s) in {b[:10]}..HEAD, {len(mine)} review record(s) for {repo}, none covering it",
                           f"{review_log} · {repo}", "code"))
    latest = {}
    for r in recs:
        if r.get("record") == "disposition":
            latest[r.get("finding_id")] = r
    for f in recs:
        d = latest.get(f.get("finding_id"))
        if f.get("record") != "finding" or not d or d.get("disposition") != "fixed" or not d.get("sha"):
            continue
        # the reviewed code is never its own fix: the commit that introduced a finding touches
        # its file (review adhoc-01); dispose refuses it, a hand-written record blocks here
        own, rng = next(iter((f.get("range") or {}).items()), ("", ""))
        head = rng.partition("..")[2]  # the head this finding's reviewer saw
        if own and head and d.get("repo", own) == own \
                and git_ok(os.path.join(projects, own), "merge-base", "--is-ancestor", d["sha"], head):
            blocks.append((f"predates:{f['finding_id']}", "a `fixed` commit predates the finding",
                           f"a commit made after {head[:10]}, the head {f.get('review_id')} reviewed",
                           f"{d['sha'][:10]} is an ancestor of it", f"{review_log} · {f['finding_id']}", "code"))
        if f.get("severity") != "blocking":
            continue
        # a fix recorded in another repo (`dispose --fixed-in`) is re-reviewed THERE
        for repo in ([d["repo"]] if d.get("repo") else (f.get("range") or {})):
            path = os.path.join(projects, repo)
            if not any(inside(path, r, d["sha"]) for r in reviews if repo in r.get("range", {})):
                blocks.append((f"rereview:{f['finding_id']}", "a blocking finding's fix was never reviewed",
                               f"a later /review whose range contains {d['sha'][:10]}",
                               f"no review record covers it", f"{review_log} · {f['finding_id']}", "code"))
    return blocks


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
    base = vl.bases(os.path.join(scope, "closeout-prep.md"), unit)
    report, blocks, judges = [], [], set()
    if not owned:
        raise vl.ContractError(vl.message("ERROR", f"no finish-table rows owned by {unit}",
                                          f"at least one row whose owner is {unit} or {unit}/…", "0 rows",
                                          table["path"], "code", "add the unit's rows, bump Revision",
                                          f"{vl.CONTRACT} §3.4"))
    appr = table.get("approval")
    if appr is not None and appr != table["revision"]:
        found = "pending" if appr == "pending" else f"rev {appr} approved, table is rev {table['revision']}"
        blocks.append(("table-approval", "the finish table's current revision is not approved by a human",
                       f"**Approved:** rev {table['revision']} — <who>, <date>", found, table["path"], "code",
                       f"show the user the rows; on their yes: finish-table.py approve --scope {scope} --by <name>"))
        report.append("BLOCK  table-approval  finish table not approved")
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
        # §5.1 re-check: the final result must follow from its own evidence. A final record
        # edited by hand (or written by anything but verify-run.py) is caught here.
        if pend is not None:
            jud = [r for r in recs if r.get("run_state") == "judged" and r.get("run_id") == final["run_id"]
                   and r.get("check_id") == cid]
            want = vl.authority(pend, jud[-1] if jud else None)
            if (want["result"], want["rung_reached"]) != (res["result"], res["rung_reached"]):
                block("final verdict contradicts its own evidence",
                      f"{want['result']} · rung {want['rung_reached']} (authority rule over run {final['run_id']})",
                      f"{res['result']} · rung {res['rung_reached']} in the final record", "tooling",
                      "re-run the checks; never edit a final record")
                continue
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
    for bid, what, exp, found, where, cause in review_presence_blocks(review, base, projects):
        blocks.append((bid, what, exp, found, where, cause,
                       f"/review --scope {scope} --unit {unit} on the unit's base..HEAD"))
        report.append(f"BLOCK  {bid}  {what}")
    if os.path.exists(review):
        cov, n = coverage_blocks(review)
        for fid, what, exp, found, where, cause in cov:
            blocks.append((fid, what, exp, found, where, cause, "record the disposition through /review's log writer"))
            report.append(f"BLOCK  {fid}  {what}")
        if appr is not None and n and not cov and not accepted(review):
            # §6.4 — a table under the human checkpoint puts review outcomes there too
            blocks.append(("review-acceptance", "review outcomes not accepted by a human since the last "
                           "finding or disposition", "an `acceptance` record after every finding and disposition",
                           "none, or an older one", review, "code",
                           f"show the user the outcomes; on their yes: review.py accept --scope {scope} "
                           f"--unit {unit} --by <name>"))
            report.append("BLOCK  review-acceptance  review outcomes not accepted")
        report.append(f"review {n} finding(s), {n - len(cov)} dispositioned")
        for line in fallback_markers(review, projects):
            judges.add(line)
    return report, blocks, sorted(j for j in judges if j)


# Blocks that mean "no complete verdict yet" — /closeout runs /verify for these, and only these.
NEEDS_VERIFY = ("no final verdict", "an unfinished run is newer than the verdict")


def closeout_view(a, table):
    """Every gated unit, blocks as failures. Output ends `verdict: PASS|FAILED …` and, when
    anything is off, `marker: ⚠ verify failed <ids>` (+ judge markers) — the text /closeout
    puts on the archived index row."""
    units = sorted({r["owner"].split("/")[0] for r in table["rows"]}, key=lambda u: [int(x) for x in u.split(".")])
    per, failed, judges, msgs = [], [], set(), []
    for u in units:
        report, blocks, js = evaluate(a.scope, u, a.projects)
        judges.update(js)
        failed += [b[0] for b in blocks]
        msgs += [vl.message("FAIL", f"{u}: {what}", exp, found, where, cause, nxt, DOCS)
                 for _, what, exp, found, where, cause, nxt in blocks]
        per.append({"unit": u, "blocks": [{"id": b[0], "what": b[1], "cause": b[5]} for b in blocks],
                    "needs_verify": any(b[1] in NEEDS_VERIFY for b in blocks)})
    markers = [f"⚠ judge: {j}" for j in sorted(judges) if not j.startswith("codex ")]
    if not units:
        # Every phase predates the gate: nothing was verified, so this is not a pass
        # (it must never count toward the blocking flip — review 5.3-r1-05).
        doc = {"verdict": "ungated", "units": [], "predates": table["predates"], "failed": [], "marker": "",
               "messages": []}
        print(json.dumps(doc) if a.json else f"verdict: UNGATED (every phase predates the gate: "
                                             f"{', '.join(table['predates']) or 'no rows'})")
        return vl.EXIT_PASS
    if failed:
        markers.insert(0, f"⚠ verify failed {', '.join(failed)}")
    marker = " ".join(markers)
    verdict = "failed" if failed else "pass"
    if a.json:
        print(json.dumps({"verdict": verdict, "units": per, "predates": table["predates"],
                          "failed": failed, "marker": marker, "messages": msgs}))
    else:
        for p in per:
            print(f"{'FAIL' if p['blocks'] else 'pass'}  {p['unit']}  "
                  f"{', '.join(b['id'] for b in p['blocks']) if p['blocks'] else 'every owned check passes'}"
                  + ("  (verdict missing or unfinished — run /verify)" if p["needs_verify"] else ""))
        for u in table["predates"]:
            print(f"n/a   {u}  predates the gate")
        for m in msgs:
            print(m)
        print(f"verdict: {verdict.upper()} (scope, {len(units)} gated unit(s), {len(failed)} failed check(s))")
        if marker:
            print(f"marker: {marker}")
    return vl.EXIT_FAIL if failed else vl.EXIT_PASS


def main(argv):
    ap = argparse.ArgumentParser(description="Verification gate (templates/verify-contracts.md §5).")
    ap.add_argument("--scope", required=True)
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument("--unit")
    target.add_argument("--all", action="store_true")
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
    try:
        a.mode = a.mode or vl.gate_mode(a.scope)
    except vl.ContractError as exc:
        print(exc.msg, file=sys.stderr)
        return vl.EXIT_EVAL

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
        table = vl.parse_table(os.path.join(a.scope, "finish-conditions.md"))
        if a.all:
            return closeout_view(a, table)
        if a.unit in table["predates"]:
            msg = f"{a.unit} predates the gate (finish-conditions.md **Predates gate:**) — exempt"
            print(json.dumps({"verdict": "predates-gate", "unit": a.unit, "blocks": [], "marker": ""})
                  if a.json else f"verdict: PREDATES GATE ({msg})")
            return vl.EXIT_PASS
        report, blocks, judges = evaluate(a.scope, a.unit, a.projects)
    except vl.ContractError as exc:
        if a.json:
            print(json.dumps({"verdict": "error", "unit": a.unit or "all", "error": exc.msg}))
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
