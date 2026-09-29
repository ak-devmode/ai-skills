#!/usr/bin/env python3
"""judge.py — the deterministic half of /verify's judge step: render the prompt from
disk, validate and record whatever the judge answered, and write the report.

Approach: the judge (codex, or a fresh Claude subagent as fallback) only ever sees a
prompt rendered here from the finish table, the run's pending records and the unit's
revision range — never the author's narrative — and its answer only lands through
`record`, which checks every owned check_id got exactly one verdict and every finding
names a known check before handing the verdicts to verify-run.py (the sole verdict-log
writer). Both executors go through the same two calls, so the fallback cannot take a
shortcut the primary can't. `report` renders the final verdict, findings and lever
candidates for a human; a check that ends inconclusive or unreachable is always a lever
candidate, whether or not the judge named one.

Usage:
  judge.py prepare --scope DIR --unit N.P --run-id ID [--range REPO=BASE..HEAD ...] [--out-dir DIR]
  judge.py record  --scope DIR --unit N.P --run-id ID --judge LINE --input FILE
  judge.py report  --scope DIR --unit N.P --run-id ID
    --range   overrides the ledger's base for REPO (older scopes have no recorded base)
Output: prepare prints `prompt: <path>` and `schema: <path>`; record/report print what they wrote.
Exit:   0 ok · 2 usage · 3 could not evaluate (no range, empty range, malformed judge output)
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SCRIPTS = os.path.join(os.path.dirname(SKILL), "scripts")
sys.path.insert(0, SCRIPTS)
import verify_lib as vl  # noqa: E402

PROMPT = os.path.join(SKILL, "prompts", "judge.md")
SCHEMA = os.path.join(SKILL, "schemas", "judge-output.schema.json")
DOCS = f"{vl.CONTRACT} §4.4 · verify/SKILL.md"
LENSES = ("conformance", "test-plan", "rejection-audit", "faithful-port", "over-build",
          "invented-reality", "evidence")


def paths(scope, unit):
    art = os.path.join(scope, "artifacts")
    return {"table": os.path.join(scope, "finish-conditions.md"), "art": art,
            "log": os.path.join(art, f"verify-{unit}.jsonl"), "ledger": os.path.join(scope, "closeout-prep.md"),
            "review": os.path.join(art, f"review-{unit}.jsonl"), "scope_md": os.path.join(scope, "scope.md")}


def err(what, expected, found, where, nxt, cause="tooling"):
    print(vl.message("ERROR", what, expected, found, where, cause, nxt, DOCS), file=sys.stderr)
    return vl.EXIT_EVAL


def pending_of(log, run_id):
    recs = [r for r in vl.read_jsonl(log) if r.get("run_id") == run_id]
    return [r for r in recs if r.get("run_state") == "pending"], recs


def git_head(path):
    p = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


def cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


# ---------- prepare ----------------------------------------------------------------

def cmd_prepare(a):
    p = paths(a.scope, a.unit)
    table = vl.parse_table(p["table"])
    pend, _ = pending_of(p["log"], a.run_id)
    if not pend:
        return err(f"run {a.run_id} has no pending records", "a run started by verify-run.py run",
                   "none", p["log"], f"verify-run.py run --table {p['table']} --log {p['log']} --owner {a.unit}")
    overrides = dict(r.split("=", 1) for r in a.range)
    base = vl.bases(p["ledger"], a.unit)
    repos = sorted({r["repo"] for r in pend})
    ranges = []
    for repo in repos:
        path = os.path.join(a.projects, repo)
        head = git_head(path)
        if head is None:
            return err(f"cannot read repo {repo}", f"a git repo at {path}", "not readable", repo,
                       f"git -C {path} status", cause="environment")
        if repo in overrides:
            rng = overrides[repo]
        elif repo in base:
            rng = f"{base[repo]}..{head}"
        else:
            return err(f"no revision range for {repo}", "a base SHA in the ledger (ledger-init.sh --repo) or "
                       "--range REPO=BASE..HEAD", "neither", p["ledger"],
                       f"judge.py prepare ... --range {repo}=<base>..HEAD")
        b, _, h = rng.partition("..")
        n = subprocess.run(["git", "-C", path, "rev-list", "--count", rng], capture_output=True, text=True)
        if n.returncode != 0:
            return err(f"range {rng} is not valid in {repo}", "BASE..HEAD of real commits", n.stderr.strip()[:200],
                       repo, f"git -C {path} log --oneline {rng}")
        if n.stdout.strip() == "0":
            return err(f"the unit's range is empty in {repo}", "at least one commit in the unit's range",
                       f"{rng} has 0 commits", repo,
                       "an empty range is a failure, not a clean pass — check the base SHA", cause="code")
        ranges.append(f"  - `{path}`: `{rng}` ({n.stdout.strip()} commits)")
    by_id = {r["check_id"]: r for r in table["rows"]}
    checks = []
    for r in pend:
        row = by_id.get(r["check_id"], {})
        kind = "judge" if r["command"] == "judge" else "runner"
        checks.append(f"| {r['check_id']} | {kind} | {row.get('rung', r['rung_required'])} | {cell(r['deliverable'])} "
                      f"| {r['result'] if kind == 'runner' else '—'} | {cell(r['reason'])} |")
    plans = sorted(glob.glob(os.path.join(p["art"], "*test-plan*.md")))
    fill = {"UNIT": a.unit, "RUN_ID": a.run_id, "SCOPE_MD": p["scope_md"], "TABLE": p["table"],
            "TABLE_REV": str(table["revision"]), "LOG": p["log"], "RANGES": "\n".join(ranges),
            "TEST_PLAN": ", ".join(f"`{x}`" for x in plans) or "none",
            "REVIEW_LOG": f"`{p['review']}`" if os.path.exists(p["review"]) else "none",
            "CHECKS": "\n".join(checks)}
    with open(PROMPT, encoding="utf-8") as fh:
        text = fh.read()
    for k, v in fill.items():
        text = text.replace("{{" + k + "}}", v)
    out_dir = a.out_dir or tempfile.mkdtemp(prefix=f"verify-{a.unit}-")
    os.makedirs(out_dir, exist_ok=True)
    prompt = os.path.join(out_dir, f"judge-{a.run_id}.md")
    with open(prompt, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"prompt: {prompt}\nschema: {SCHEMA}")
    return vl.EXIT_PASS


# ---------- record -----------------------------------------------------------------

def validate(doc, check_ids):
    problems = []
    if not isinstance(doc, dict):
        return ["answer is not a JSON object"]
    for key in ("verdicts", "findings", "lever_candidates", "feature_map"):
        if key not in doc:
            problems.append(f"missing `{key}`")
    if problems:
        return problems
    seen = [v.get("check_id") for v in doc["verdicts"] if isinstance(v, dict)]
    for cid in sorted(set(check_ids) - set(seen)):
        problems.append(f"no verdict for `{cid}`")
    for cid in sorted(set(seen) - set(check_ids)):
        problems.append(f"verdict for unknown check `{cid}`")
    for cid in sorted({c for c in seen if seen.count(c) > 1}):
        problems.append(f"{seen.count(cid)} verdicts for `{cid}`")
    for v in doc["verdicts"]:
        if v.get("verdict") not in ("pass", "fail", "inconclusive"):
            problems.append(f"verdict {v.get('verdict')!r} for `{v.get('check_id')}`")
        if not isinstance(v.get("rung_reached"), int) or not 0 <= v["rung_reached"] <= 5:
            problems.append(f"rung_reached {v.get('rung_reached')!r} for `{v.get('check_id')}`")
        if not str(v.get("reason", "")).strip():
            problems.append(f"empty reason for `{v.get('check_id')}`")
    for f in doc["findings"]:
        if f.get("check_id") not in set(check_ids) | {"unowned"}:
            problems.append(f"finding names unknown check `{f.get('check_id')}`")
        if f.get("lens") not in LENSES:
            problems.append(f"finding lens {f.get('lens')!r}")
        if f.get("severity") not in ("high", "medium", "low"):
            problems.append(f"finding severity {f.get('severity')!r}")
    if doc["feature_map"] not in ("clean", "changed", "blocked", "n/a"):
        problems.append(f"feature_map {doc['feature_map']!r}")
    return problems


def cmd_record(a):
    p = paths(a.scope, a.unit)
    pend, _ = pending_of(p["log"], a.run_id)
    ids = [r["check_id"] for r in pend]
    try:
        with open(a.input, encoding="utf-8") as fh:
            doc = json.load(fh)
        problems = validate(doc, ids)
    except (OSError, ValueError) as exc:
        problems = [str(exc)]
    if problems:
        return err("judge output is malformed — nothing recorded", "one verdict per owned check, findings on "
                   "known checks, per verify/schemas/judge-output.schema.json", "; ".join(problems[:6]), a.input,
                   f"verify-run.py finalize --log {p['log']} --run-id {a.run_id} --judge 'none malformed judge output'")
    verdicts = os.path.join(tempfile.mkdtemp(prefix="verify-judged-"), "verdicts.json")
    with open(verdicts, "w", encoding="utf-8") as fh:
        json.dump(doc["verdicts"], fh)
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "verify-run.py"), "judged", "--log", p["log"],
                        "--run-id", a.run_id, "--judge", a.judge, "--input", verdicts],
                       capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    if r.returncode != 0:
        return r.returncode
    raw = os.path.join(p["art"], f"verify-{a.unit}-judge-{a.run_id}.json")
    with open(raw, "w", encoding="utf-8") as fh:
        json.dump(dict(doc, judge=a.judge, run_id=a.run_id), fh, indent=2, ensure_ascii=False)
    with open(raw, encoding="utf-8") as fh:
        if json.load(fh).get("run_id") != a.run_id:
            return err("raw judge output did not land", "the file just written", "different content", raw,
                       "re-run record")
    print(f"raw judge output: {raw}")
    return vl.EXIT_PASS


# ---------- report -----------------------------------------------------------------

def cmd_report(a):
    p = paths(a.scope, a.unit)
    pend, recs = pending_of(p["log"], a.run_id)
    final = next((r for r in recs if r.get("run_state") == "final"), None)
    if final is None:
        return err(f"run {a.run_id} is not final", "a finalized run", "no final record", p["log"],
                   f"verify-run.py finalize --log {p['log']} --run-id {a.run_id} ...")
    raw_path = os.path.join(p["art"], f"verify-{a.unit}-judge-{a.run_id}.json")
    raw = {}
    if os.path.exists(raw_path):
        with open(raw_path, encoding="utf-8") as fh:
            raw = json.load(fh)
    gate = subprocess.run([sys.executable, os.path.join(SCRIPTS, "verdict-gate.py"), "--scope", a.scope,
                           "--unit", a.unit, "--projects", a.projects], capture_output=True, text=True)
    gate_line = next((x for x in gate.stdout.splitlines() if x.startswith("verdict:")), None)
    if gate_line is None:
        why = next((x.strip() for x in gate.stderr.splitlines() if x.strip()), f"exit {gate.returncode}")
        gate_line = f"verdict: GATE ERROR (exit {gate.returncode}) — {why}"
    marker = next((x for x in gate.stdout.splitlines() if x.startswith("marker:")), "")
    by_pend = {r["check_id"]: r for r in pend}
    lines = [f"# Verify report — unit {a.unit}", "",
             f"**Run:** `{a.run_id}` · **Judge:** {final['judge']} · **Table revision:** {final['table_rev']}",
             f"**Gate:** {gate_line.replace('verdict: ', '')}" + (f" · {marker.replace('marker: ', '')}" if marker else ""),
             "", "## 1. Checks", "", "| Check | Result | Rung | Reason |", "|---|---|---|---|"]
    for cid, res in final["results"].items():
        need = by_pend.get(cid, {}).get("rung_required", "?")
        lines.append(f"| {cid} | {res['result']} | {res['rung_reached']}/{need} | {cell(res['reason'])} |")
    lines += ["", "## 2. Findings", ""]
    findings = raw.get("findings", [])
    if not findings:
        lines.append("None." if raw else "No judge output (judge line: " + final["judge"] + ").")
    for sev in ("high", "medium", "low"):
        for f in [f for f in findings if f["severity"] == sev]:
            lines.append(f"- **{sev}** · {f['lens']} · `{f['check_id']}` · {f['where']} — {f['text']}")
    levers = {c["check_id"]: c for c in raw.get("lever_candidates", [])}
    for cid, res in final["results"].items():
        if res["result"] in ("inconclusive", "verified-unreachable") and cid not in levers:
            levers[cid] = {"check_id": cid, "gap": res["reason"], "lever": "(judge named none — decide at /closeout)"}
    lines += ["", "## 3. Lever candidates", "",
              "Recorded, not built: a lever is built on the second sighting (verify-contracts.md §4)."]
    lines += [f"- `{c['check_id']}` — gap: {c['gap']} · lever: {c['lever']} · run `{a.run_id}`"
              for c in levers.values()] or ["None."]
    lines += ["", "## 4. Feature map", "", f"`{raw.get('feature_map', 'n/a')}`", ""]
    out = os.path.join(p["art"], f"verify-{a.unit}-report.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"report: {out}\n{gate_line}" + (f"\n{marker}" if marker else ""))
    # The report is written either way; the gate's diagnostics and exit status pass through
    # (1 blocked, 3 gate error) rather than being flattened to success (review 5.2-r1-05).
    sys.stderr.write(gate.stderr)
    return gate.returncode


def main(argv):
    ap = argparse.ArgumentParser(description="/verify judge plumbing (prepare | record | report).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("prepare", "record", "report"):
        s = sub.add_parser(name)
        s.add_argument("--scope", required=True)
        s.add_argument("--unit", required=True)
        s.add_argument("--run-id", required=True)
        s.add_argument("--projects", default=vl.PROJECTS)
        if name == "prepare":
            s.add_argument("--range", action="append", default=[])
            s.add_argument("--out-dir")
        if name == "record":
            s.add_argument("--judge", required=True)
            s.add_argument("--input", required=True)
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return vl.EXIT_USAGE if exc.code else vl.EXIT_PASS
    if getattr(a, "judge", None) and not vl.JUDGE_LINE.match(a.judge):
        return err("judge line is malformed", "`codex <model>` / `claude-fallback <reason>` / `none <reason>`",
                   a.judge, "--judge", "pass the line codex-exec.py printed")
    try:
        return {"prepare": cmd_prepare, "record": cmd_record, "report": cmd_report}[a.cmd](a)
    except vl.ContractError as exc:
        print(exc.msg, file=sys.stderr)
        return vl.EXIT_EVAL


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
