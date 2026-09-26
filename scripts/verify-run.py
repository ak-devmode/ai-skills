#!/usr/bin/env python3
"""verify-run.py — the deterministic runner, and the only writer of the verdict log.

Approach: three subcommands, one per run state (templates/verify-contracts.md §4).
`run` executes each owned finish-table row's command in its declared repo / dir / env
with its timeout and appends one `pending` record per row — resolved context, SHA, exit
code, output hash and tail — so the judge reads evidence instead of a claim. `judged`
records the judge's verdicts for that run from the judge's output file. `finalize`
applies the §5.1 authority rule (the judge may only downgrade a runner row; a judge row
takes the judge's verdict) and appends ONE `final` line for the whole run, so a run is
final entirely or not at all. Every append is read back before the script reports
success. Class-A evidence is refused into a public or non-git destination (§7).

Usage:
  verify-run.py run      --table FILE --log FILE [--owner UNIT] [--projects DIR]
  verify-run.py judged   --log FILE --run-id ID --judge LINE --input FILE
  verify-run.py finalize --log FILE --run-id ID [--judge LINE]
    --owner     plan (`5.1`) or unit (`5.1/1.3`); omitted = every row (closeout)
    --input     JSON list (or JSONL) of {check_id, verdict, rung_reached, reason}
    --judge     `codex <model>` · `claude-fallback <reason>` · `none <reason>`; finalize
                needs it only when the run has no judged records (then it must be `none …`)
Output: one line per row, the run_id, §10 messages for anything that failed.
Exit:   0 every runner row passed / recorded · 1 a row failed, or refused · 2 usage
        · 3 could not evaluate (malformed table or judge input, write did not land)
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_lib as vl  # noqa: E402

DOCS = f"{vl.CONTRACT} §4"
PUBLIC_REMOTES = {"ak-devmode/ai-skills", "garrytan/gstack"}  # §7.1 denylist
TAIL_LINES, TAIL_CHARS = 40, 4000


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(path, *args):
    p = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True)
    return p.returncode, p.stdout.strip()


# ---------- §7 destination check ---------------------------------------------------

def destination(log_path):
    """(toplevel or None, 'owner/repo' or None) of the repo the log is written into."""
    d = os.path.dirname(os.path.abspath(log_path))
    while not os.path.isdir(d):
        d = os.path.dirname(d)
    rc, top = git(d, "rev-parse", "--show-toplevel")
    if rc != 0:
        return None, None
    _, url = git(top, "remote", "get-url", "origin")
    m = re.search(r"[:/]([\w.-]+/[\w.-]+?)(?:\.git)?/?$", url)
    return os.path.realpath(top), (m.group(1) if m else None)


def refuse_placement(rows, log_path, projects):
    """Return a §10 message if any row's evidence may not be written to log_path."""
    top, slug = destination(log_path)
    public = slug in PUBLIC_REMOTES
    for r in rows:
        if r["class"] == "A" and (top is None or public):
            why = "a directory outside any git repo" if top is None else f"public repo {slug}"
            return vl.message(
                "BLOCK", f"class-A evidence for `{r['check_id']}` refused", "class-A evidence written "
                "only to a private repo (kalpa-docs scope folder or the product test-suite)",
                f"destination {log_path} is in {why}", f"finish table line {r['_line']}", "code",
                "point --log at the product's private scope folder", f"{vl.CONTRACT} §7.1")
        if r["class"] == "B" and public:
            row_repo = os.path.realpath(os.path.join(projects, r["repo"]))
            if row_repo != top:
                return vl.message(
                    "BLOCK", f"class-B evidence about another repo refused for `{r['check_id']}`",
                    f"a public repo holds verdicts on its own content only ({top})",
                    f"row targets {r['repo']}", f"finish table line {r['_line']}", "code",
                    "write this verdict log in the target repo's private scope folder",
                    f"{vl.CONTRACT} §7.2")
    return None


# ---------- run --------------------------------------------------------------------

def result_for(exit_code):
    """§4.7 exit-code mapping for a command that ran to completion."""
    if exit_code == 0:
        return "pass", "exit 0"
    if exit_code == 1:
        return "fail", "exit 1"
    if exit_code == 2:
        return "inconclusive", "exit 2 (usage/config)"
    if exit_code == 3:
        return "verified-unreachable", "exit 3 (unreachable)"
    if exit_code in (126, 127):
        return "inconclusive", f"not executable: exit {exit_code}"
    return "fail", f"exit {exit_code}"


def deployed_version(stdout):
    """§9: a class-A verb's JSON output may report the deployed version; else None."""
    try:
        doc = json.loads(stdout)
    except ValueError:
        return None
    v = doc.get("deployed_version") if isinstance(doc, dict) else None
    return str(v) if v else None


def decode(b):
    return b.decode("utf-8", "replace") if isinstance(b, bytes) else (b or "")


def execute(row, projects, run_id, unit, rev):
    rec = {"schema": vl.SCHEMA, "ts": now(), "run_id": run_id, "run_state": "pending", "unit": unit,
           "check_id": row["check_id"], "deliverable": row["deliverable"], "class": row["class"],
           "rung_required": row["rung"], "rung_reached": 0, "table_rev": rev, "repo": row["repo"],
           "dir": row["dir"], "env": row["env"], "sha": None, "dirty": None,
           "deployed_version": None, "command": row["check"], "exit_code": None,
           "duration_s": 0, "output_sha256": None, "output_tail": None}
    repo_path = os.path.join(projects, row["repo"])
    cwd = os.path.normpath(os.path.join(repo_path, row["dir"]))
    rec["cwd"] = cwd
    rc, sha = git(repo_path, "rev-parse", "HEAD") if os.path.isdir(repo_path) else (1, "")
    if rc == 0:
        rec["sha"] = sha
        rec["dirty"] = bool(git(repo_path, "status", "--porcelain")[1])
    if row["is_judge"]:
        rec.update(result="inconclusive", reason="judge row: awaiting judge")
        return rec
    if rc != 0 or not os.path.isdir(cwd):
        rec.update(result="inconclusive",
                   reason=f"not executable: {'repo' if rc != 0 else 'dir'} missing or not a git repo ({cwd})")
        return rec
    env = dict(os.environ, **row["env"])
    t0 = datetime.datetime.now()
    stdout = ""
    try:
        p = subprocess.run(["bash", "-o", "pipefail", "-c", row["check"]], cwd=cwd, env=env,
                           capture_output=True, text=True, timeout=row["timeout"])
        stdout, code = p.stdout or "", p.returncode
        out = stdout + (p.stderr or "")
        result, reason = result_for(code)
    except subprocess.TimeoutExpired as exc:
        out = decode(exc.stdout) + decode(exc.stderr)
        code, result, reason = None, "inconclusive", f"timed out after {row['timeout']}s"
    except OSError as exc:
        out, code, result, reason = "", None, "inconclusive", f"not executable: {exc}"
    rec["duration_s"] = round((datetime.datetime.now() - t0).total_seconds(), 3)
    rec["exit_code"] = code
    rec["output_sha256"] = hashlib.sha256(out.encode()).hexdigest()
    rec["output_tail"] = "\n".join(out.splitlines()[-TAIL_LINES:])[-TAIL_CHARS:]
    if code is not None:
        rec["rung_reached"] = 5 if row["class"] == "A" else 4
    if row["class"] == "A":
        rec["deployed_version"] = deployed_version(stdout)
    rec.update(result=result, reason=reason)
    return rec


def cmd_run(a):
    table = vl.parse_table(a.table)
    rows = vl.select(table["rows"], a.owner)
    if not rows:
        print(vl.message("ERROR", "no finish-table rows selected", f"at least one row owned by {a.owner}",
                         "0 rows", a.table, "code", "check the owner column, or pass --owner",
                         f"{vl.CONTRACT} §3.4"), file=sys.stderr)
        return vl.EXIT_EVAL
    refusal = refuse_placement(rows, a.log, a.projects)
    if refusal:
        print(refusal, file=sys.stderr)
        return vl.EXIT_FAIL
    unit = a.owner.split("/")[0] if a.owner else rows[0]["owner"].split("/")[0]
    run_id = f"{unit}-{datetime.datetime.now(datetime.timezone.utc):%Y%m%dT%H%M%S}-{secrets.token_hex(2)}"
    recs = [execute(r, a.projects, run_id, unit, table["revision"]) for r in rows]
    vl.append_verified(a.log, recs)
    failed = False
    for r in recs:
        print(f"{r['result']:<21} {r['check_id']}  ({r['reason']})")
        if r["command"] != "judge" and r["result"] != "pass":
            failed = True
            cause = "environment" if r["result"] in ("inconclusive", "verified-unreachable") else "code"
            print(vl.message("FAIL", f"`{r['check_id']}` did not pass", "exit 0 from the row's command",
                             f"{r['result']}: {r['reason']}", f"{r['repo']}/{r['dir']} @ {r['sha']} — "
                             f"`{r['command']}`", cause,
                             f"cd {r['cwd']} && {r['command']}", DOCS))
    print(f"run_id: {run_id}  ({len(recs)} pending record(s) -> {a.log}; not a verdict until finalize + gate)")
    return vl.EXIT_FAIL if failed else vl.EXIT_PASS


# ---------- judged / finalize ------------------------------------------------------

def run_records(log, run_id):
    recs = [r for r in vl.read_jsonl(log) if r.get("run_id") == run_id]
    if not any(r["run_state"] == "pending" for r in recs):
        raise vl.ContractError(vl.message("ERROR", f"run `{run_id}` has no pending records",
                                          "a run started by `verify-run.py run`", "no such run",
                                          log, "tooling", f"verify-run.py run --log {log} ...", DOCS))
    return recs


def cmd_judged(a):
    recs = run_records(a.log, a.run_id)
    if any(r["run_state"] == "final" for r in recs):
        raise vl.ContractError(vl.message("ERROR", "run is already final", "a pending run",
                                          f"run {a.run_id} has a final record", a.log, "tooling",
                                          "start a new run", DOCS))
    pending = {r["check_id"] for r in recs if r["run_state"] == "pending"}
    try:
        with open(a.input, encoding="utf-8") as fh:
            text = fh.read()
        items = json.loads(text) if text.lstrip().startswith("[") else \
            [json.loads(x) for x in text.splitlines() if x.strip()]
        problems = []
        for it in items:
            if it.get("check_id") not in pending:
                problems.append(f"unknown check_id {it.get('check_id')!r}")
            if it.get("verdict") not in ("pass", "fail", "inconclusive"):
                problems.append(f"verdict {it.get('verdict')!r}")
            if not isinstance(it.get("rung_reached"), int) or not 0 <= it["rung_reached"] <= 5:
                problems.append(f"rung_reached {it.get('rung_reached')!r}")
            if not str(it.get("reason", "")).strip():
                problems.append(f"empty reason for {it.get('check_id')!r}")
        if not items:
            problems.append("no verdicts")
    except (OSError, ValueError, AttributeError) as exc:
        problems = [str(exc)]
    if problems:
        raise vl.ContractError(vl.message(
            "ERROR", "judge output is malformed — no judged records written",
            "{check_id, verdict: pass|fail|inconclusive, rung_reached: 0-5, reason} per owned check",
            "; ".join(problems[:5]), a.input, "tooling",
            f"finalize without a judge: verify-run.py finalize --log {a.log} --run-id {a.run_id} "
            f"--judge 'none malformed judge output'", f"{vl.CONTRACT} §4.4, §4.6"))
    out = [{"schema": vl.SCHEMA, "ts": now(), "run_id": a.run_id, "run_state": "judged",
            "unit": recs[0]["unit"], "check_id": it["check_id"], "judge": a.judge,
            "verdict": it["verdict"], "rung_reached": it["rung_reached"], "reason": it["reason"]}
           for it in items]
    vl.append_verified(a.log, out)
    print(f"judged: {len(out)} record(s) for {a.run_id} (judge: {a.judge})")
    return vl.EXIT_PASS


def authority(p, j):
    """§5.1 — final {result, rung_reached, reason} for one check."""
    if p["command"] == "judge":
        if j is None:
            return {"result": "inconclusive", "rung_reached": 0, "reason": "judge row: no judge verdict"}
        return {"result": j["verdict"], "rung_reached": j["rung_reached"], "reason": f"judge: {j['reason']}"}
    if j is None:
        return {"result": p["result"], "rung_reached": p["rung_reached"], "reason": f"runner: {p['reason']}"}
    if vl.ORDER[j["verdict"]] < vl.ORDER[p["result"]]:
        return {"result": j["verdict"], "rung_reached": min(p["rung_reached"], j["rung_reached"]),
                "reason": f"judge downgraded runner {p['result']}: {j['reason']}"}
    return {"result": p["result"], "rung_reached": min(p["rung_reached"], j["rung_reached"]),
            "reason": f"runner: {p['reason']}; judge concurs"}


def cmd_finalize(a):
    recs = run_records(a.log, a.run_id)
    if any(r["run_state"] == "final" for r in recs):
        raise vl.ContractError(vl.message("ERROR", "run is already final", "one final record per run",
                                          f"run {a.run_id} already finalized", a.log, "tooling",
                                          "start a new run to change the verdict", f"{vl.CONTRACT} §4.1"))
    pending = {}
    for r in recs:
        if r["run_state"] == "pending":
            pending[r["check_id"]] = r
    judged = {}
    for r in recs:
        if r["run_state"] == "judged":
            judged[r["check_id"]] = r  # latest judged record per check wins
    lines = {r["judge"] for r in judged.values()}
    if len(lines) > 1:
        raise vl.ContractError(vl.message("ERROR", "judged records disagree on the judge", "one judge per run",
                                          ", ".join(sorted(lines)), a.log, "tooling", "start a new run", DOCS))
    if lines:
        judge = lines.pop()
    elif a.judge and a.judge.startswith("none "):
        judge = a.judge
    else:
        raise vl.ContractError(vl.message("ERROR", "no judge verdicts and no `--judge 'none <reason>'`",
                                          "judged records, or an explicit `none <reason>` judge line",
                                          a.judge or "nothing", a.log, "tooling",
                                          f"verify-run.py finalize --log {a.log} --run-id {a.run_id} "
                                          "--judge 'none <why the judge did not run>'", f"{vl.CONTRACT} §4.6"))
    results = {cid: authority(p, judged.get(cid)) for cid, p in pending.items()}
    revs = {p["table_rev"] for p in pending.values()}
    final = {"schema": vl.SCHEMA, "ts": now(), "run_id": a.run_id, "run_state": "final",
             "unit": next(iter(pending.values()))["unit"], "judge": judge, "table_rev": max(revs),
             "results": results}
    vl.append_verified(a.log, [final])
    for cid, res in results.items():
        print(f"{res['result']:<21} {cid}  rung {res['rung_reached']}  ({res['reason']})")
    print(f"final: {a.run_id}  judge: {judge}")
    return vl.EXIT_FAIL if any(r["result"] != "pass" for r in results.values()) else vl.EXIT_PASS


# ---------- entry ------------------------------------------------------------------

def main(argv):
    ap = argparse.ArgumentParser(description="Verification runner (templates/verify-contracts.md §4).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--table", required=True)
    r.add_argument("--log", required=True)
    r.add_argument("--owner")
    r.add_argument("--projects", default=vl.PROJECTS)
    j = sub.add_parser("judged")
    j.add_argument("--log", required=True)
    j.add_argument("--run-id", required=True)
    j.add_argument("--judge", required=True)
    j.add_argument("--input", required=True)
    f = sub.add_parser("finalize")
    f.add_argument("--log", required=True)
    f.add_argument("--run-id", required=True)
    f.add_argument("--judge")
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return vl.EXIT_USAGE if exc.code else vl.EXIT_PASS
    if getattr(a, "judge", None) and not vl.JUDGE_LINE.match(a.judge):
        print(vl.message("ERROR", "judge line is malformed", "`codex <model>`, `claude-fallback <reason>` or "
                         "`none <reason>`", a.judge, "--judge", "tooling", "pass a well-formed judge line",
                         f"{vl.CONTRACT} §4.6"), file=sys.stderr)
        return vl.EXIT_USAGE
    try:
        return {"run": cmd_run, "judged": cmd_judged, "finalize": cmd_finalize}[a.cmd](a)
    except vl.ContractError as exc:
        print(exc.msg, file=sys.stderr)
        return vl.EXIT_EVAL


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
