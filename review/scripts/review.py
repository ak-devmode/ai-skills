#!/usr/bin/env python3
"""review.py — the deterministic half of /review: render the gate's prompt for an explicit
revision range, record the reviewer's raw findings under stable IDs, and record a
disposition for each. The review-log writer named in templates/verify-contracts.md §6.

Approach: the reviewer (codex, or the Claude fallback) only ever sees a prompt rendered
here — the range, the project, and the rule files to read — and its JSON answer only
lands through `record`, which validates it, assigns `<unit>-r<n>-NN` IDs in severity
order, appends one `finding` record per finding (write-then-read-back), and writes the
human report, including what the review did not cover. `dispose` is the only way a
finding gets a disposition, and it refuses a `fixed <sha>` whose commit does not touch
the finding's file — that check has one right answer, so it is enforced at write time.
verdict-gate.py then refuses Done while any finding lacks one (§5.2.1).

Usage:
  review.py prepare --repo PATH --range BASE..HEAD [--kalpa-only | --engine-only] [--out-dir DIR]
  review.py record  --repo PATH --range BASE..HEAD --reviewer LINE --input FILE
                    [--scope DIR --unit N.P] [--passes TEXT]
  review.py dispose --scope DIR --unit N.P --finding ID (--fixed SHA | --rejected REASON | --deferred TODO) [--by NAME]
  review.py accept  --scope DIR --unit N.P --by NAME     (the user's yes to the outcomes, §6.4)
Output: prepare prints `prompt:`, `schema:`, `passes:`; record prints the report path (or the
        report, with no scope); dispose prints the disposition.
Exit:   0 ok · 1 disposition refused · 2 usage · 3 could not evaluate (empty range, malformed answer)
"""

import argparse
import datetime
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
SCRIPTS = os.path.join(os.path.dirname(SKILL), "scripts")
sys.path.insert(0, SCRIPTS)
import verify_lib as vl  # noqa: E402

PROMPT = os.path.join(SKILL, "prompts", "review.md")
SCHEMA = os.path.join(SKILL, "schemas", "review-output.schema.json")
DOMAIN = os.path.join(SKILL, "rules", "domain.md")
LENSES = os.path.join(SKILL, "rules", "lenses.md")
ENGINE = os.path.expanduser("~/.claude/skills/gstack/review/checklist.md")
DOCS = f"{vl.CONTRACT} §6 · review/SKILL.md"
SEVERITIES = ("blocking", "should-fix", "note")
# SKILL.md §5.1 convergence: past this many rounds on one unit, only blocking findings are
# fixed in the loop; a file drawing findings REPEAT rounds running is a design problem.
ROUND_CAP, REPEAT = 3, 3
CATEGORIES = ("engine", "domain", "local-maxima", "silent-failure", "dirty-comment", "doc-claim", "fail-open")
GROUPS = {"wellmed": "§3.1–§3.8", "pmg": "§3.1, §3.5, §3.6, §3.7 only",
          "iris": "§3.1, §3.2, §3.5, §3.6 (module paths + parameterized queries only), §3.7, §3.8, §3.9 — "
                  "never §3.3/§3.4, which are WellMed ADRs IRIS does not inherit"}
# Standalone graphs that live under another project's directory. Matched before the
# top-level project, so kalpa-iris never inherits WellMed's ADR checks (IRIS CLAUDE.md §3.1).
SUBPROJECTS = {"wellmed/kalpa-iris": "iris"}


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(repo, *args):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def err(what, expected, found, where, nxt, cause="tooling", code=vl.EXIT_EVAL):
    print(vl.message("ERROR" if code == vl.EXIT_EVAL else "BLOCK", what, expected, found, where, cause, nxt, DOCS),
          file=sys.stderr)
    return code


def repo_key(repo):
    rel = os.path.relpath(os.path.realpath(repo), os.path.realpath(vl.PROJECTS))
    return os.path.basename(os.path.realpath(repo)) if rel.startswith("..") else rel


def main_worktree(repo):
    """The primary checkout behind `repo` — a herdr worktree under ~/.herdr/worktrees/ sits
    outside ~/Projects, so its own path cannot say which project it belongs to."""
    code, common, _ = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return os.path.dirname(common) if code == 0 and common else repo


def project(repo):
    key = repo_key(main_worktree(repo))
    for prefix, name in SUBPROJECTS.items():
        if key == prefix or key.startswith(prefix + "/"):
            return name
    top = key.split("/")[0]
    return top if top in GROUPS else "generic"


def count_range(repo, rng):
    """Commits in rng, or a §10 error code."""
    if rng.count("..") != 1 or "..." in rng:
        return None, err(f"range `{rng}` is not BASE..HEAD", "an explicit BASE..HEAD range", rng, "--range",
                         "pass e.g. --range abc1234..HEAD", code=vl.EXIT_USAGE)
    rc, out, e = git(repo, "rev-list", "--count", rng)
    if rc != 0:
        return None, err(f"range {rng} is not valid in {repo}", "BASE..HEAD of real commits", e[:200], repo,
                         f"git -C {repo} log --oneline {rng}", cause="environment")
    if out == "0":
        return None, err("the range is empty", "at least one commit to review", f"{rng} has 0 commits", repo,
                         "an empty range is a failure, not a clean review — check the base SHA", cause="code")
    return int(out), None


def resolve_range(repo, rng):
    """(`<base sha>..<head sha>`, None), or (None, a §10 error code). prepare renders the prompt
    with this immutable range and record requires it, so a commit landing mid-review can't be
    logged as reviewed (review 5.2-r3-01); a failed rev-parse is an error, never an empty SHA
    (5.2-r3-02)."""
    shas = []
    for side in rng.split(".."):
        rc, sha, e = git(repo, "rev-parse", "--verify", f"{side}^{{commit}}")
        if rc != 0 or not re.fullmatch(r"[0-9a-f]{40}", sha):
            return None, err(f"`{side}` does not resolve to a commit in {repo}", "a commit SHA",
                             e[:200] or repr(sha), repo, f"git -C {repo} rev-parse {side}", cause="environment")
        shas.append(sha)
    return "..".join(shas), None


# ---------- prepare ----------------------------------------------------------------

def cmd_prepare(a):
    n, code = count_range(a.repo, a.range)
    if code is not None:
        return code
    a.range, code = resolve_range(a.repo, a.range)
    if code is not None:
        return code
    proj = project(a.repo)
    rules, passes = [], []
    if a.kalpa_only:
        passes.append("engine SKIPPED (--kalpa-only)")
    elif os.path.exists(ENGINE):
        rules.append(f"- `{ENGINE}` — the generic review checklist")
        passes.append("engine ✓")
    else:
        passes.append("engine SKIPPED (gstack checklist not installed)")
        print(vl.message("WARN", "gstack's review checklist is missing — engine checks skipped",
                         f"a file at {ENGINE}", "none", "review.py prepare", "environment",
                         "cd ~/Projects/ai-skills && ./setup.sh (installs gstack)", DOCS), file=sys.stderr)
    if a.engine_only:
        passes.append("domain SKIPPED (--engine-only)")
    elif proj == "generic":
        passes.append("domain n/a — generic repo")
    else:
        rules.append(f"- `{DOMAIN}` — domain checks; this repo is {proj}: apply {GROUPS[proj]}")
        passes.append(f"domain ✓ ({proj})")
    rules.append(f"- `{LENSES}` — lenses for every repo (adjacent code, fail-open, silent failure, "
                 "local maxima, dirty comments, doc claims)")
    passes.append("lenses ✓")
    fill = {"REPO": os.path.realpath(a.repo), "PROJECT": proj, "RANGE": a.range, "COMMITS": str(n),
            "RULES": "\n".join(rules)}
    with open(PROMPT, encoding="utf-8") as fh:
        text = fh.read()
    for k, v in fill.items():
        text = text.replace("{{" + k + "}}", v)
    out_dir = a.out_dir or tempfile.mkdtemp(prefix="review-")
    os.makedirs(out_dir, exist_ok=True)
    prompt = os.path.join(out_dir, "review-prompt.md")
    with open(prompt, "w", encoding="utf-8") as fh:
        fh.write(text)
    effort, why = vl.effort_for([vl.diff_stat(a.repo, a.range)])
    print(f"prompt: {prompt}\nschema: {SCHEMA}\npasses: {' · '.join(passes)}\nrange: {a.range}\n"
          f"effort: {effort} ({why})")
    return vl.EXIT_PASS


# ---------- record -----------------------------------------------------------------

def validate(doc):
    with open(SCHEMA, encoding="utf-8") as fh:
        problems = vl.schema_problems(doc, json.load(fh))
    if problems:
        return problems
    for i, f in enumerate(doc["findings"], 1):
        if not f.get("file") or not isinstance(f.get("line"), int):
            problems.append(f"finding {i} has no file:line")
        if f.get("severity") not in SEVERITIES:
            problems.append(f"finding {i} severity {f.get('severity')!r}")
        if f.get("category") not in CATEGORIES:
            problems.append(f"finding {i} category {f.get('category')!r}")
        if not str(f.get("text", "")).strip():
            problems.append(f"finding {i} has no text")
    if doc["verdict"] not in ("SHIP", "SHIP AFTER BLOCKING", "DO NOT SHIP"):
        problems.append(f"verdict {doc['verdict']!r}")
    return problems


def render(doc, findings, header):
    lines = header + [""]
    for sev, title in (("blocking", "BLOCKING"), ("should-fix", "SHOULD FIX"), ("note", "NOTE")):
        group = [f for f in findings if f["severity"] == sev]
        lines.append(f"## {title} ({len(group)})")
        lines.append("")
        for f in group:
            tag = f"{f['category']}{' ' + f['group'] if f.get('group') else ''}"
            lines.append(f"- **{f['finding_id']}** `{f['file']}:{f['line']}` ({tag}) — {f['text']}"
                         + (f" → {f['fix']}" if f.get("fix") else ""))
        lines.append("")
    lines += ["## Checked and clear", "", ", ".join(doc["checked_clear"]) or "—", "",
              "## Not applicable", "", ", ".join(doc["not_applicable"]) or "—", "",
              f"**Verdict:** {doc['verdict']}", "", "## What this review did not cover", ""]
    lines += [f"- {c}" for c in doc["cannot_do"]] or ["- (reviewer listed nothing)"]
    return lines


def cmd_record(a):
    n, code = count_range(a.repo, a.range)
    if code is not None:
        return code
    fixed, code = resolve_range(a.repo, a.range)
    if code is not None:
        return code
    if fixed != a.range:
        return err("record needs the immutable range prepare printed", "`<base sha>..<head sha>` (full SHAs)",
                   a.range, "--range", "pass the `range:` line from `review.py prepare`", code=vl.EXIT_USAGE)
    if not vl.JUDGE_LINE.match(a.reviewer):
        return err("reviewer line is malformed", "`codex <model>` / `claude-fallback <reason>` / `none <reason>`",
                   a.reviewer, "--reviewer", "pass the line codex-exec.py printed", code=vl.EXIT_USAGE)
    try:
        with open(a.input, encoding="utf-8") as fh:
            doc = json.load(fh)
        problems = validate(doc)
    except (OSError, ValueError) as exc:
        doc, problems = None, [str(exc)]
    if problems:
        return err("review answer is malformed — nothing recorded", "findings with file:line, severity and "
                   "category per review/schemas/review-output.schema.json", "; ".join(problems[:6]), a.input,
                   "re-run the reviewer; if codex keeps failing, run the Claude fallback (review/SKILL.md §3)")
    # the primary checkout's key, never a worktree's directory name: the gate and
    # `dispose --fixed` look the repo up under ~/Projects (review adhoc-01)
    key = repo_key(main_worktree(a.repo))
    rank = {s: i for i, s in enumerate(SEVERITIES)}
    ordered = sorted(doc["findings"], key=lambda f: rank[f["severity"]])
    if not (a.scope and a.unit):
        print(build(a, doc, ordered, key, n, "adhoc")[2])
        print("(no --scope/--unit: nothing logged; findings are not tracked for dispositions)", file=sys.stderr)
        return vl.EXIT_PASS
    art = os.path.join(a.scope, "artifacts")
    os.makedirs(art, exist_ok=True)
    log = os.path.join(art, f"review-{a.unit}.jsonl")
    # Allocate the review ID and append under one exclusive lock, and always write a
    # `review` record — even with zero findings — so concurrent or clean reviews can't
    # mint the same ID (review 5.2-r1-04, -07).
    with open(log, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        taken = [int(m.group(1)) for r in vl.read_jsonl(log)
                 for m in [re.match(rf"^{re.escape(a.unit)}-r(\d+)$", str(r.get("review_id", "")))] if m]
        review_id = f"{a.unit}-r{max(taken, default=0) + 1}"
        records, findings, report = build(a, doc, ordered, key, n, review_id)
        vl.append_verified(log, records)
        out = os.path.join(art, f"review-{review_id}.md")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(report)
    print(f"review {review_id}: {len(findings)} finding(s) logged -> {log}\nreport: {out}\nverdict: {doc['verdict']}")
    for line in convergence(vl.read_jsonl(log), a.unit):
        print(line)
    return vl.EXIT_PASS


def convergence(recs, unit):
    """SKILL.md §5.1 signals for the latest round of `unit`: [CONVERGENCE] lines, or none.
    A loop that keeps finding edge cases in one place is patching a design that is wrong
    (5.3 ran 12 rounds on one heuristic, two findings ending on opposite sides)."""
    rounds = {}
    for r in recs:
        m = re.match(rf"^{re.escape(unit)}-r(\d+)$", str(r.get("review_id", "")))
        if m and r.get("record") == "finding":
            rounds.setdefault(int(m.group(1)), set()).add(r["file"])
        elif m:
            rounds.setdefault(int(m.group(1)), set())
    if not rounds:
        return []
    last, out = max(rounds), []
    if last > ROUND_CAP:
        out.append(f"[CONVERGENCE] round {last} > {ROUND_CAP}: fix blocking findings only; defer should-fix/note "
                   "with `dispose --deferred \"<TO-DO item>\"` (review/SKILL.md §5.1)")
    window = [rounds.get(n, set()) for n in range(last - REPEAT + 1, last + 1)]
    if last >= REPEAT:
        for f in sorted(set.intersection(*window)):
            out.append(f"[CONVERGENCE] {f} drew findings in each of the last {REPEAT} rounds: stop patching — "
                       "raise it to the user as a design finding (replace, narrow, or cut) before another fix")
    return out


def build(a, doc, ordered, key, n, review_id):
    """(records, findings, report) for one review: a `review` record, then its findings."""
    ts = now()
    findings = [dict(f, finding_id=f"{review_id}-{i:02d}") for i, f in enumerate(ordered, 1)]
    records = [{"schema": vl.SCHEMA, "ts": ts, "record": "finding", "review_id": review_id,
                "finding_id": f["finding_id"], "reviewer": a.reviewer, "range": {key: a.range},
                "file": f["file"], "line": f["line"], "category": f["category"], "group": f.get("group", ""),
                "severity": f["severity"], "text": f["text"], "fix": f.get("fix", "")} for f in findings]
    degraded = [] if a.reviewer.startswith("codex ") else [
        f"**DEGRADED:** reviewer is `{a.reviewer}` — not the codex gate; the gate reports `⚠ judge: review {a.reviewer}` "
        "(and the index carries it) until a codex re-review of this unit."]
    header = [f"# /review — {key} @ `{a.range}` ({n} commits)", "",
              f"**Review:** `{review_id}` · **Reviewer:** {a.reviewer} · **Passes:** {a.passes or 'unrecorded'}"] \
        + degraded + [f"**Findings:** {len(findings)} — every ID needs a disposition: "
                      f"`review.py dispose --scope <scope> --unit {a.unit or '<unit>'} --finding <ID> "
                      "(--fixed <sha> | --rejected \"<reason>\" | --deferred \"<TO-DO>\")`"]
    report = "\n".join(render(doc, findings, header)) + "\n"
    # record only accepts the immutable range, so it is the commits the reviewer saw
    # (review 5.2-r2-01, -r3-01).
    shas = dict(zip(("base", "head"), a.range.split("..")))
    review = {"schema": vl.SCHEMA, "ts": ts, "record": "review", "review_id": review_id, "reviewer": a.reviewer,
              "range": {key: a.range}, "shas": shas, "passes": a.passes or "", "findings": len(findings),
              "verdict": doc["verdict"]}
    return [review] + records, findings, report


# ---------- accept -----------------------------------------------------------------

def cmd_accept(a):
    """Record the user's acceptance of every disposition so far (§6.4). Refused while any
    finding lacks one — the user accepts outcomes, not an open list."""
    log = os.path.join(a.scope, "artifacts", f"review-{a.unit}.jsonl")
    recs = vl.read_jsonl(log) if os.path.exists(log) else []
    findings = [r["finding_id"] for r in recs if r.get("record") == "finding"]
    latest = {r["finding_id"]: r["disposition"] for r in recs if r.get("record") == "disposition"}
    open_ids = [f for f in findings if f not in latest]
    if not findings:
        return err("nothing to accept", "a review log with findings", "no findings", log,
                   "no acceptance is needed for a clean review", code=vl.EXIT_USAGE)
    if open_ids:
        return err(f"{len(open_ids)} finding(s) have no disposition", "every finding dispositioned first",
                   ", ".join(open_ids[:6]), log, "dispose them, then accept", cause="code", code=vl.EXIT_FAIL)
    if not a.by.strip():
        return err("accept needs --by", "the person accepting", "empty", "--by", "--by \"<name>\"",
                   code=vl.EXIT_USAGE)
    counts = {k: sum(1 for f in findings if latest[f] == k) for k in ("fixed", "rejected", "deferred")}
    vl.append_verified(log, [{"schema": vl.SCHEMA, "ts": now(), "record": "acceptance", "by": a.by.strip(),
                              "findings": len(findings), **counts}])
    print(f"{a.unit}: outcomes accepted by {a.by.strip()} — {len(findings)} findings "
          f"({counts['fixed']} fixed, {counts['rejected']} rejected, {counts['deferred']} deferred)")
    return vl.EXIT_PASS


# ---------- dispose ----------------------------------------------------------------

def cmd_dispose(a):
    log = os.path.join(a.scope, "artifacts", f"review-{a.unit}.jsonl")
    recs = vl.read_jsonl(log)
    f = next((r for r in recs if r.get("record") == "finding" and r.get("finding_id") == a.finding), None)
    if f is None:
        return err(f"no finding `{a.finding}`", "a finding_id recorded by review.py record", "none", log,
                   f"grep finding_id {log}", code=vl.EXIT_USAGE)
    if a.fixed:
        repo_rel, _ = next(iter(f["range"].items()))
        repo = os.path.join(vl.PROJECTS, repo_rel)
        rc, touched, e = git(repo, "show", "--name-only", "--format=", a.fixed)
        if rc != 0:
            return err(f"`{a.fixed}` is not a commit in {repo_rel}", "the fixing commit", e[:200], repo,
                       f"git -C {repo} log --oneline -5", cause="code", code=vl.EXIT_FAIL)
        if f["file"] not in touched.splitlines():
            return err(f"`fixed {a.fixed}` does not touch the finding's file", f"a commit changing {f['file']}",
                       f"it changes: {', '.join(touched.splitlines()[:6]) or 'nothing'}",
                       f"{a.finding} ({f['file']}:{f['line']})", "fix in a commit that touches the file, or "
                       "record `--rejected \"<why>\"` if it isn't a defect", cause="code", code=vl.EXIT_FAIL)
    if a.rejected is not None and not a.rejected.strip():
        return err("`rejected` needs a reason", "the reason the finding is wrong", "empty", a.finding,
                   "--rejected \"<why the finding is wrong>\"", cause="code", code=vl.EXIT_FAIL)
    if a.deferred is not None:
        if not a.deferred.strip():
            return err("`deferred` needs the TO-DO item", "the TO-DO entry that carries it", "empty", a.finding,
                       "--deferred \"<TO-DO item>\"", cause="code", code=vl.EXIT_FAIL)
        if f.get("severity") == "blocking":
            return err("a blocking finding cannot be deferred", "`--fixed <sha>` or `--rejected \"<why>\"`",
                       "severity blocking", a.finding, "fix it, or reject it with the reason it is wrong",
                       cause="code", code=vl.EXIT_FAIL)
    by = a.by
    if not by:
        rc, name, _ = git(a.scope, "config", "user.name")
        by = f"{name or 'unknown'} / Claude"
    kind = "fixed" if a.fixed else ("deferred" if a.deferred is not None else "rejected")
    reason = a.deferred if kind == "deferred" else a.rejected
    rec = {"schema": vl.SCHEMA, "ts": now(), "record": "disposition", "finding_id": a.finding,
           "disposition": kind, "sha": a.fixed, "reason": reason, "by": by}
    vl.append_verified(log, [rec])
    print(f"{a.finding}: {rec['disposition']} {a.fixed or reason}")
    return vl.EXIT_PASS


def main(argv):
    ap = argparse.ArgumentParser(description="/review plumbing (prepare | record | dispose).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--repo", required=True)
    p.add_argument("--range", required=True)
    m = p.add_mutually_exclusive_group()
    m.add_argument("--kalpa-only", action="store_true")
    m.add_argument("--engine-only", action="store_true")
    p.add_argument("--out-dir")
    r = sub.add_parser("record")
    for opt in ("--repo", "--range", "--reviewer", "--input"):
        r.add_argument(opt, required=True)
    r.add_argument("--scope")
    r.add_argument("--unit")
    r.add_argument("--passes")
    d = sub.add_parser("dispose")
    d.add_argument("--scope", required=True)
    d.add_argument("--unit", required=True)
    d.add_argument("--finding", required=True)
    x = d.add_mutually_exclusive_group(required=True)
    x.add_argument("--fixed", metavar="SHA")
    x.add_argument("--rejected", metavar="REASON")
    x.add_argument("--deferred", metavar="TODO", help="non-blocking only: the TO-DO item that carries it")
    d.add_argument("--by")
    c = sub.add_parser("accept")
    c.add_argument("--scope", required=True)
    c.add_argument("--unit", required=True)
    c.add_argument("--by", required=True)
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return vl.EXIT_USAGE if exc.code else vl.EXIT_PASS
    if a.cmd == "record" and bool(a.scope) != bool(a.unit):
        return err("--scope and --unit go together", "both or neither", "one of them", "record",
                   "pass both to log findings for dispositions", code=vl.EXIT_USAGE)
    try:
        return {"prepare": cmd_prepare, "record": cmd_record, "dispose": cmd_dispose, "accept": cmd_accept}[a.cmd](a)
    except vl.ContractError as exc:
        print(exc.msg, file=sys.stderr)
        return vl.EXIT_EVAL


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
