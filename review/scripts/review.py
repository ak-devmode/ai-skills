#!/usr/bin/env python3
"""review.py — the deterministic half of /review: render the gate's prompt for an explicit
revision range, record the reviewer's raw findings under stable IDs, and record a
disposition for each. The review-log writer named in templates/verify-contracts.md §6.

Approach: the reviewer (codex, or the Claude fallback) only ever sees a prompt rendered
here — the range, the project, and the rule files to read — and its JSON answer only
lands through `record`, which validates it, assigns `<unit>-r<n>-NN` IDs in severity
order, appends one `finding` record per finding (write-then-read-back), and writes the
human report, including what the review did not cover. `dispose` is the only way a
finding gets a disposition, and it refuses a `fixed <sha>` whose commit touches neither
the finding's file nor (non-blocking only) that file's own test beside it, unless
`--off-anchor "<how>"` says why
— that check has one right answer, so it is enforced at write time.
verdict-gate.py then refuses Done while any finding lacks one (§5.2.1).

Usage:
  review.py prepare --repo PATH --range BASE..HEAD [--kalpa-only | --engine-only] [--out-dir DIR]
  review.py record  --repo PATH --range BASE..HEAD --reviewer LINE --input FILE
                    [--scope DIR --unit N.P] [--passes TEXT]
  review.py dispose --scope DIR --unit N.P --finding ID (--fixed SHA [--off-anchor REASON] | --rejected REASON |
                    --deferred TODO) [--by NAME]
  review.py dispose ... --fixed SHA --fixed-in REPO_PATH     (the fix lives in another repo)
  review.py accept  --scope DIR --unit N.P --by NAME     (the user's yes to the outcomes, §6.4)
  review.py misfiled --scope DIR --unit N.P              (rejections that say "FIXED by <sha>" → dispose lines)
Output: prepare prints `prompt:`, `schema:`, `passes:`; record prints the report path (or the
        report, with no scope); dispose prints the disposition.
Exit:   0 ok · 1 disposition refused · 2 usage · 3 could not evaluate (empty range, malformed answer)
"""

import argparse
import calendar
import contextlib
import datetime
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import time

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
    repo, rnd = repo_round(vl.read_jsonl(log), a.unit, review_id)
    print(f"review {review_id}: {len(findings)} finding(s) logged -> {log}\nreport: {out}\nverdict: {doc['verdict']}\n"
          f"round: {rnd} of {repo} in {a.unit}")
    for line in convergence(vl.read_jsonl(log), a.unit):
        print(line)
    return vl.EXIT_PASS


def reviews_of(recs, unit):
    """[(review_id, repo, files with findings)] for `unit`, in review order. Logs from before
    `review` records existed (§6.0) carry the repo on each finding."""
    pat, by = re.compile(rf"^{re.escape(unit)}-r(\d+)$"), {}
    for r in recs:
        m = pat.match(str(r.get("review_id", "")))
        if not m or r.get("record") not in ("review", "finding"):
            continue
        e = by.setdefault(int(m.group(1)), [r["review_id"], None, set()])
        e[1] = e[1] or next(iter(r.get("range") or {}), None)
        if r.get("record") == "finding":
            e[2].add(r.get("file"))
    return [tuple(by[n]) for n in sorted(by)]


def repo_round(recs, unit, review_id):
    """(repo, round): the round counts THAT repo's reviews within the unit, never the unit's.
    IDs stay `<unit>-r<n>` across every repo, but 149.2 reviewed 13 repos in one unit, so
    bpjs's first look was r5 and the round cap fired on it (review/SKILL.md §5.1)."""
    revs = reviews_of(recs, unit)
    ids = [rid for rid, _, _ in revs]
    if review_id not in ids:
        return None, 0  # an unknown review is round 0: below every cap, so nothing is released early
    i = ids.index(review_id)
    return revs[i][1], sum(1 for _, rp, _ in revs[:i + 1] if rp == revs[i][1])


def convergence(recs, unit):
    """SKILL.md §5.1 signals for the latest review of `unit`, counted over the reviews of
    that review's repo: [CONVERGENCE] lines, or none. A loop that keeps finding edge cases
    in one place is patching a design that is wrong (5.3 ran 12 rounds on one heuristic,
    two findings ending on opposite sides)."""
    revs = reviews_of(recs, unit)
    if not revs:
        return []
    repo = revs[-1][1]
    mine = [files for _, rp, files in revs if rp == repo]
    last, out = len(mine), []
    if last > ROUND_CAP:
        out.append(f"[CONVERGENCE] {repo} round {last} > {ROUND_CAP}: fix blocking findings only; defer "
                   "should-fix/note with `dispose --deferred \"<TO-DO item>\"` (review/SKILL.md §5.1)")
    if last >= REPEAT:
        for f in sorted(set.intersection(*mine[-REPEAT:])):
            out.append(f"[CONVERGENCE] {f} drew findings in each of the last {REPEAT} {repo} rounds: stop "
                       "patching — raise it to the user as a design finding (replace, narrow, or cut) before "
                       "another fix")
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

@contextlib.contextmanager
def log_lock(log):
    """The review log's exclusive lock — the same one `record` takes. Every writer that
    reads the log and then appends holds it across both, so no record can land between
    what was checked and what was written (review adhoc-04)."""
    with open(log, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        yield


def cmd_accept(a):
    """Record the user's acceptance of every disposition so far (§6.4). Refused while any
    finding lacks one — the user accepts outcomes, not an open list."""
    log = os.path.join(a.scope, "artifacts", f"review-{a.unit}.jsonl")
    if not os.path.exists(log):
        return err("nothing to accept", "a review log with findings", "no review log", log,
                   "no acceptance is needed without a review", code=vl.EXIT_USAGE)
    with log_lock(log):
        return _accept(a, log)


def _accept(a, log):
    recs = vl.read_jsonl(log)
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
    if not os.path.exists(log):
        return err(f"no review log for {a.unit}", "a log written by review.py record", "none", log,
                   "run the review with --scope/--unit first", code=vl.EXIT_USAGE)
    with log_lock(log):
        return _dispose(a, log)


def _dispose(a, log):
    recs = vl.read_jsonl(log)
    f = next((r for r in recs if r.get("record") == "finding" and r.get("finding_id") == a.finding), None)
    if f is None:
        return err(f"no finding `{a.finding}`", "a finding_id recorded by review.py record", "none", log,
                   f"grep finding_id {log}", code=vl.EXIT_USAGE)
    fix = {}
    if a.off_anchor is not None and not a.fixed:
        return err("`--off-anchor` qualifies a fix", "`--fixed <sha> --off-anchor \"<how>\"`", "no --fixed",
                   a.finding, "drop --off-anchor, or pass the fixing commit", code=vl.EXIT_USAGE)
    if a.fixed_in is not None and not a.fixed:
        return err("`--fixed-in` qualifies a fix", "`--fixed <sha> --fixed-in <repo path>`", "no --fixed",
                   a.finding, "drop --fixed-in, or pass the fixing commit", code=vl.EXIT_USAGE)
    if a.fixed:
        path, key = fix_repo(f, a.fixed_in)
        if path is None:
            return err(f"`--fixed-in {a.fixed_in}` is not a git repository under {vl.PROJECTS}", "the path of the "
                       "repo holding the fix", key, "--fixed-in", "pass a checkout or worktree path, e.g. "
                       "~/Projects/wellmed/<repo>",
                       cause="code", code=vl.EXIT_USAGE)
        fix, code = fix_check(f, a.fixed, path, key, recs)
        if code is not None:
            return code
        if fix["predates"]:
            return err(f"`fixed {a.fixed}` predates the finding: {fix['predates']}",
                       f"a commit made after review {f.get('review_id')} raised {a.finding}", fix["sha"],
                       f"{a.finding} ({f['file']}:{f['line']})", "fix it in a new commit; if the code was "
                       "already right when reviewed, record `--rejected \"<why>\"`", cause="code", code=vl.EXIT_FAIL)
        if fix["via"] is None:
            if a.off_anchor is None:
                where_ = "is not in " + key if fix["anchor"] is None else "is not touched"
                return err(f"`fixed {a.fixed}` does not reach the finding: {f['file']} {where_}",
                           f"a commit in {key} changing {fix['anchor'] or f['file']}" + ("" if f.get("severity") == "blocking"
                           else " or its own test beside it"),
                           f"it changes: {fix['touched'] or 'nothing'}", f"{a.finding} ({f['file']}:{f['line']})",
                           "fix in a commit that touches the file; if this commit fixes it elsewhere, add "
                           "`--off-anchor \"<how it fixes the finding>\"`; or record `--rejected \"<why>\"` if "
                           "it isn't a defect", cause="code", code=vl.EXIT_FAIL)
            if not a.off_anchor.strip():
                return err("`--off-anchor` needs the reason", "how this commit fixes a finding it does not "
                           "touch", "empty", a.finding, "--off-anchor \"<how it fixes the finding>\"",
                           cause="code", code=vl.EXIT_FAIL)
            fix["via"] = "off-anchor"
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
        # SKILL.md §5.1: deferral is the round cap's release valve, not a way to skip a
        # finding early, and the follow-up must exist (review adhoc-03). The round is the
        # finding's repo's, not the unit's (149.2-r10-05 was satu-sehat's first review).
        repo, rnd = repo_round(recs, a.unit, f.get("review_id"))
        if rnd <= ROUND_CAP:
            return err(f"deferral before the round cap ({repo} round {rnd} ≤ {ROUND_CAP})",
                       f"a finding from round {ROUND_CAP + 1} or later of {repo}", f"round {rnd}", a.finding,
                       "fix it, or reject it with the reason it is wrong", cause="code", code=vl.EXIT_FAIL)
        if not vl.todo_has_item(a.scope, a.finding, open_only=True):
            return err(f"no open TO-DO item carries `{a.finding}`",
                       f"an unchecked `- [ ]` item line in the project's TO-DO.md naming {a.finding}",
                       "none", f"TO-DO.md above {a.scope}",
                       f"write `- [ ] [review {a.finding}] <what is left>` to TO-DO.md, then defer", cause="code",
                       code=vl.EXIT_FAIL)
    by = a.by
    if not by:
        rc, name, _ = git(a.scope, "config", "user.name")
        by = f"{name or 'unknown'} / Claude"
    kind = "fixed" if a.fixed else ("deferred" if a.deferred is not None else "rejected")
    reason = {"fixed": a.off_anchor, "deferred": a.deferred, "rejected": a.rejected}[kind]
    rec = {"schema": vl.SCHEMA, "ts": now(), "record": "disposition", "finding_id": a.finding,
           "disposition": kind, "sha": fix.get("sha"), "reason": reason, "by": by}
    if fix:
        rec.update(repo=fix["repo"], via=fix["via"])
    vl.append_verified(log, [rec])
    print(f"{a.finding}: {kind} {rec['sha'] or reason}" + (f" in {fix['repo']} (via {fix['via']})" if fix else ""))
    return vl.EXIT_PASS


# a test file by name, for the languages the fleet uses (Go, Python, JS/TS, PHP, Ruby); the
# group that matched is the stem of the file it tests (res_test.go, test_res.py -> res)
TEST_FILE = re.compile(r"^(?:(.+)_test\.(?:go|py)|test_(.+)\.py|(.+)\.(?:test|spec)\.[cm]?[jt]sx?|(.+)Test\.php|(.+)_spec\.rb)$")


def tests_anchor(t, anchor):
    """Is `t` the anchor's own test: beside it, named for it? Any test in the directory is
    not — a change to validation_test.go says nothing about res.go (review adhoc-02)."""
    m = TEST_FILE.match(os.path.basename(t))
    stem = next((g for g in m.groups() if g), None) if m else None
    return stem is not None and os.path.dirname(t) == os.path.dirname(anchor) \
        and stem == os.path.splitext(os.path.basename(anchor))[0]


def fix_repo(f, fixed_in):
    """(path, key) of the repo holding the fix: the finding's own repo, or `--fixed-in` — a
    finding can be fixed at its source in another repo (149.2-r5-01: bpjs, fixed in
    wellmed-gateway-go) or in a docs repo (a hand-back file). (None, why) when not a repo."""
    if fixed_in is None:
        own = next(iter(f["range"]))
        return os.path.join(vl.PROJECTS, own), own
    path = os.path.realpath(os.path.expanduser(fixed_in))
    rc, top, e = git(path, "rev-parse", "--show-toplevel") if os.path.isdir(path) else (1, "", "no such directory")
    if rc != 0 or not top:
        return None, e[:200] or "not a repository"
    # a repo outside the projects root keys by basename — lossy, and the gate could never find
    # it to re-review the fix (review adhoc-04)
    main = os.path.realpath(main_worktree(top))
    if os.path.relpath(main, os.path.realpath(vl.PROJECTS)).startswith(".."):
        return None, f"{main} is outside {vl.PROJECTS}"
    # the toplevel, not a subdirectory: `git show` names files from the repo root
    return top, repo_key(main)


def same_repo(f, path, key):
    """Is `path` the finding's own repo — by git identity (the primary checkout), never by key:
    two repos can share a key, and a key match would let a stranger's same-named file count
    as the anchor (review adhoc-04). A finding whose repo is gone matches nothing."""
    own_path = os.path.join(vl.PROJECTS, next(iter(f["range"])))
    return os.path.isdir(own_path) and \
        os.path.realpath(main_worktree(own_path)) == os.path.realpath(main_worktree(path))


def anchor_in(f, path, key):
    """The finding's file as a path inside repo `path`, or None when it lives elsewhere. A
    relative anchor names a file in the finding's own repo; in another repo it counts only
    when absolute under it or led by its directory name (a hand-back doc cited as
    `kalpa-docs/plans/...`) — never a bare relative match: bpjs's `go.mod` is not gateway-go's."""
    file = f["file"]
    if os.path.isabs(file):
        for root in {os.path.realpath(main_worktree(path)), os.path.realpath(path)}:
            rel = os.path.relpath(os.path.realpath(file), root)
            if rel != "." and not rel.startswith(".."):
                return rel
        return None
    if same_repo(f, path, key):
        return file
    lead = os.path.basename(key) + "/"
    return file[len(lead):] if file.startswith(lead) else None


def finding_review(recs, f):
    """(head sha, ts) of the review that raised finding `f`: the head of the finding's own range
    (what its reviewer saw — `record` only accepts resolved SHAs) and its timestamp."""
    head = next(iter((f.get("range") or {}).values()), "").partition("..")[2]
    return head or None, f.get("ts")


def predates(f, full, path, recs):
    """Why commit `full` in repo `path` cannot be the fix of `f`, or None. The commit that
    introduced a finding touches its file, so without this the reviewed code itself could be
    recorded as its own fix. Exact by ancestry where the review's head is in `path`; elsewhere
    (a fix in another repo) the commit must not be older than the review."""
    head, ts = finding_review(recs, f)
    if head:
        rc = git(path, "merge-base", "--is-ancestor", full, head)[0]
        if rc == 0:
            return f"it is in the code that review reviewed (an ancestor of {head[:10]})"
        if rc == 1:
            return None
    rc, ct, _ = git(path, "show", "-s", "--format=%ct", full)
    try:
        before = rc == 0 and ts and int(ct) < calendar.timegm(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        before = False
    return f"it was committed before the review ({ts})" if before else None


def fix_check(f, sha, path, key, recs):
    """({sha, repo, via, anchor, touched, predates}, None) or (None, a §10 error code). `via` is
    how commit `sha` in repo `path` reaches the finding: `anchor` (it changes the finding's
    file), `test` (it changes the anchor's own test beside it — a missing-coverage finding
    is fixed by a test-only commit, 149.2-r11-02; never for a blocking finding, whose fix a
    test alone cannot be) or None (neither, or the file is
    not in that repo: refused unless the caller passes an explicit `--off-anchor` reason).
    `predates` says why the commit is older than the finding (always refused). One right
    answer, so it is checked at write time."""
    rc, full, e = git(path, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}")
    rc2, touched, e2 = git(path, "show", "--name-only", "--format=", full) if rc == 0 else (1, "", e)
    if rc2 != 0:
        return None, err(f"`{sha}` is not a commit in {key}", "the fixing commit", (e2 or "unknown revision")[:200],
                         path, f"git -C {path} log --oneline -5; a fix in another repo needs `--fixed-in <path>`",
                         cause="code", code=vl.EXIT_FAIL)
    files, anchor = touched.splitlines(), anchor_in(f, path, key)
    tests = anchor is not None and f.get("severity") != "blocking" and any(tests_anchor(t, anchor) for t in files)
    via = "anchor" if anchor in files else ("test" if tests else None)
    return {"sha": full, "repo": key, "via": via, "anchor": anchor, "touched": ", ".join(files[:6]),
            "predates": predates(f, full, path, recs)}, None


# ---------- misfiled ---------------------------------------------------------------

# A rejection whose own reason says the finding was fixed: what `dispose --fixed` refused
# to record before test-only and cross-repo fixes were accepted (149.2: eleven of them).
MISFILED = re.compile(r"\bFIXED\b|not rejected on merit")
SHA = re.compile(r"\b[0-9a-f]{7,40}\b")


def cmd_misfiled(a):
    """List each finding whose LATEST disposition is a rejection that says it was fixed, with
    the `dispose` line that re-records it. The latest disposition decides (§6.3), so the new
    record supersedes the rejection; nothing is re-disposed here, because an off-anchor fix
    needs a person's reason and a candidate SHA needs a person's eye."""
    log = os.path.join(a.scope, "artifacts", f"review-{a.unit}.jsonl")
    if not os.path.exists(log):
        return err(f"no review log for {a.unit}", "a log written by review.py record", "none", log,
                   "check --scope/--unit", code=vl.EXIT_USAGE)
    recs = vl.read_jsonl(log)
    latest = {r.get("finding_id"): r for r in recs if r.get("record") == "disposition"}
    hits = [(f, latest[f["finding_id"]]) for f in recs if f.get("record") == "finding"
            and latest.get(f["finding_id"], {}).get("disposition") == "rejected"
            and MISFILED.search(str(latest[f["finding_id"]].get("reason") or ""))]
    base = f"{os.path.abspath(sys.argv[0])} dispose --scope {a.scope} --unit {a.unit} --finding"
    for f, d in hits:
        print(f"{f['finding_id']} {f['severity']} {f['file']}:{f['line']}\n  rejected: {d['reason']}")
        lines = []
        for sha in dict.fromkeys(SHA.findall(d["reason"])):
            hit = [(p, k) for p, k in candidate_repos(f)
                   if git(p, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}")[0] == 0]
            for path, key in hit:
                fix, _ = fix_check(f, sha, path, key, recs)
                if fix["predates"]:
                    lines.append(f"  {sha}: not a fix — {fix['predates']} ({key})")
                    continue
                cmd = f"{base} {f['finding_id']} --fixed {sha}"
                cmd += "" if same_repo(f, path, key) else f" --fixed-in {path}"
                cmd += "" if fix["via"] else ' --off-anchor "<how this commit fixes the finding>"'
                lines.append(f"  {cmd}    # {key}, via {fix['via'] or 'off-anchor (reason needed)'}")
            if not hit and not sha.isdigit():  # a digit-only token resolving nowhere is a date or a count
                lines.append(f"  {sha}: no commit in the finding's repo or the repos beside it")
        print("\n".join(lines) or "  no SHA in the reason resolves — find the fixing commit, then dispose --fixed it")
    print(f"{len(hits)} misfiled rejection(s) in {a.unit}" + ("" if hits else " — nothing to re-dispose"))
    return vl.EXIT_PASS


def candidate_repos(f):
    """[(path, key)]: the finding's repo, then every git repo beside it under the same
    project directory (a fix at the source, or a docs repo)."""
    own = next(iter(f["range"]))
    out = [(os.path.join(vl.PROJECTS, own), own)]
    top = os.path.join(vl.PROJECTS, own.split("/")[0])
    for name in sorted(os.listdir(top)) if os.path.isdir(top) else []:
        path = os.path.join(top, name)
        if os.path.exists(os.path.join(path, ".git")) and os.path.realpath(path) != os.path.realpath(out[0][0]):
            out.append((path, repo_key(path)))
    return [(p, k) for p, k in out if os.path.isdir(p)]


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
    d.add_argument("--fixed-in", metavar="REPO_PATH", help="with --fixed: the repo holding the fix, when it is "
                   "not the finding's own (a fix at the source, or in a docs repo)")
    d.add_argument("--off-anchor", metavar="REASON",
                   help="with --fixed: the commit touches neither the file nor a test beside it; say how it fixes it")
    d.add_argument("--by")
    mf = sub.add_parser("misfiled")
    mf.add_argument("--scope", required=True)
    mf.add_argument("--unit", required=True)
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
        return {"prepare": cmd_prepare, "record": cmd_record, "dispose": cmd_dispose, "accept": cmd_accept,
                "misfiled": cmd_misfiled}[a.cmd](a)
    except vl.ContractError as exc:
        print(exc.msg, file=sys.stderr)
        return vl.EXIT_EVAL


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
