#!/usr/bin/env python3
"""finish-table.py — the one writer of a scope's finish-conditions.md.

Approach: `/scope` (Step 5.10) and `/plan`'s self-heal (§5.6.2a) both need the same file
with the same standard rows, and every later change needs a Revision bump plus a
Changelog line — one right answer each time, so it is code (CLAUDE.md §3.6.1), not a
table an agent types. `init` fills templates/finish-conditions.md.template with the
standard rows of verify/SKILL.md §4 for each phase, then any extra rows; `add` appends
rows, bumps the Revision and logs the change. Both read the file back through
verify_lib.parse_table — the parser the runner and gate use — and restore the previous
file if it does not parse, so a write either lands valid or changes nothing.

Phases:  `N.P=repo[,repo]` commits to those repos (review runs, so names-resolve per
         repo + no-overbuild + rejections-justified) · `N.P` commits nothing (third-party
         wiring: scope-deliverables only). Repos are paths under ~/Projects.
Extra rows: JSONL, one object per row with the §3.2 columns. Defaults: class B, dir `.`,
         env `-`, timeout `-`, unreachable_ok `no`, rung 2 for `judge` / 4 class B / 5
         class A, evidence `judge reason` / `runner record`.

Usage:
  finish-table.py init --scope DIR --phase SPEC ... [--rows FILE] [--test-plan-owner N.P]
                       [--predates N.P,...] [--by NAME] [--dry-run]
  finish-table.py add  --scope DIR --rows FILE --change TEXT [--by NAME] [--dry-run]
    --predates  phases already started (Done or in progress) before the table existed;
                verdict-gate.py and plans-index.py validate exempt them (Alex, 2026-09-29:
                running scopes are never asked to reconcile verify)
Output: the written table's path, revision and row count (or the table, with --dry-run).
Exit:   0 written · 2 usage · 3 refused (table exists for init, missing for add, or the
        result would not parse — nothing written)
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_lib as vl  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "templates", "finish-conditions.md.template")
RESOLVER = "python3 ~/Projects/ai-skills/scripts/resolve-identifiers.py --repo . --range $VERIFY_BASE..HEAD"
DOCS = f"{vl.CONTRACT} §3"
UNIT = re.compile(r"^\d+\.\d+$")


def fail(what, expected, found, where, nxt, cause="code", code=vl.EXIT_EVAL):
    print(vl.message("ERROR", what, expected, found, where, cause, nxt, DOCS), file=sys.stderr)
    return code


def plans_repo(scope, projects):
    """The repo holding the scope folder, as a path under the projects root — where a
    commit-less phase's judge rows point."""
    p = subprocess.run(["git", "-C", scope, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if p.returncode != 0:
        return None
    top, root = os.path.realpath(p.stdout.strip()), os.path.realpath(projects)
    return os.path.relpath(top, root) if top.startswith(root + os.sep) else None


def slug(repo):
    return re.sub(r"[^a-z0-9]+", "-", os.path.basename(repo).lower()).strip("-")


def standard_rows(unit, repos, home):
    """verify/SKILL.md §4 for one phase. check_ids are `p<P>-…` so every phase of a scope
    can share one table."""
    p = f"p{unit.split('.')[1]}"
    rows = []
    for r in repos:
        suffix = f"-{slug(r)}" if len(repos) > 1 else ""
        rows.append(dict(check_id=f"{p}-names-resolve{suffix}", owner=unit, check=RESOLVER, repo=r,
                         deliverable=f"Every identifier phase {unit} references in {os.path.basename(r)} is declared"))
    judge_repo = repos[0] if repos else home
    rows.append(dict(check_id=f"{p}-scope-deliverables", owner=unit, check="judge", repo=judge_repo,
                     deliverable=f"The scope's phase {unit} deliverables landed as specified"))
    if repos:
        rows.append(dict(check_id=f"{p}-no-overbuild", owner=unit, check="judge", repo=judge_repo,
                         deliverable=f"No abstraction phase {unit} did not need"))
        rows.append(dict(check_id=f"{p}-rejections-justified", owner=unit, check="judge", repo=judge_repo,
                         deliverable=f"Every /review rejection recorded for {unit} is right"))
    return rows


def complete(row):
    """Fill §3.2 defaults; the parser rejects anything still wrong."""
    r = {k: str(v) for k, v in row.items()}
    r.setdefault("class", "B")
    judge = r.get("check") == "judge"
    for k, v in (("dir", "."), ("env", "-"), ("timeout", "-"), ("unreachable_ok", "no"),
                 ("rung", "2" if judge else ("5" if r["class"] == "A" else "4")),
                 ("evidence", "judge reason" if judge else "runner record")):
        r.setdefault(k, v)
    return r


def cell(col, v):
    v = v.replace("|", "\\|")
    return f"`{v}`" if col == "check" and v != "judge" else v


def render_row(r):
    return "| " + " | ".join(cell(c, r.get(c, "")) for c in vl.COLUMNS) + " |"


def read_rows(path):
    if not path:
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            if line.strip():
                try:
                    out.append(complete(json.loads(line)))
                except (ValueError, AttributeError) as exc:
                    raise vl.ContractError(vl.message("ERROR", "extra rows file has a malformed line",
                                                      "one JSON object per line", str(exc), f"{path}:{i}",
                                                      "code", "fix the line", DOCS))
    return out


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def changelog_line(rev, change, by):
    return f"| {rev} | {datetime.date.today().isoformat()} | {change.replace('|', '/')} | {by} |"


def write_checked(path, text, dry_run):
    """Write, then parse it back with the runner's parser; restore on failure."""
    if dry_run:
        print(text)
        return vl.parse_table_text(text, path)
    old = read(path) if os.path.exists(path) else None
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    try:
        return vl.parse_table(path)
    except vl.ContractError:
        if old is None:
            os.remove(path)
        else:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(old)
        raise


def cmd_init(a):
    path = os.path.join(a.scope, "finish-conditions.md")
    if os.path.exists(path):
        return fail("finish-conditions.md already exists", "no table (init creates one)", path, path,
                    f"finish-table.py add --scope {a.scope} --rows <file> --change \"…\"")
    home = plans_repo(a.scope, a.projects)
    rows, units = [], []
    for spec in a.phase:
        unit, _, repos = spec.partition("=")
        if not UNIT.match(unit):
            return fail("bad --phase", "`N.P` or `N.P=repo[,repo]`", spec, "--phase", "fix the argument",
                        code=vl.EXIT_USAGE)
        repos = [r for r in repos.split(",") if r]
        if not repos and home is None:
            return fail("commit-less phase needs a repo for its judge rows", f"{a.scope} inside a git repo "
                        f"under {a.projects}", "not found", a.scope, "run from a scope folder in a docs repo",
                        cause="environment")
        units.append(unit)
        rows += standard_rows(unit, repos, home)
    if a.test_plan_owner:
        rows.append(dict(check_id="test-plan-followed", owner=a.test_plan_owner, check="judge",
                         repo=home or rows[0]["repo"],
                         deliverable="The /plan-eng-review test plan's edge cases and critical paths are covered"))
    rows = [complete(r) for r in rows] + read_rows(a.rows)
    predates = [u.strip() for u in (a.predates or "").split(",") if u.strip()]
    bad = [u for u in predates if not UNIT.match(u) or u in units]
    if bad:
        return fail("bad --predates", "started phases `N.P`, none of them also a --phase", ", ".join(bad),
                    "--predates", "list only phases already started", code=vl.EXIT_USAGE)
    text = read(TEMPLATE)
    name = os.path.basename(os.path.normpath(a.scope))
    text = text.replace("{{SCOPE_SLUG}}", name).replace("{{SCOPE_PATH}}", os.path.join(a.scope, "scope.md"))
    if predates:
        text = text.replace("**Revision:** 1\n", f"**Revision:** 1\n**Predates gate:** {', '.join(predates)}\n", 1)
    sep = "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    text = text.replace(sep, sep + "".join(render_row(r) + "\n" for r in rows), 1)
    change = "Created" + (f"; {', '.join(predates)} predate the gate" if predates else "")
    text = text.rstrip("\n") + "\n" + changelog_line(1, change, a.by) + "\n"
    t = write_checked(path, text, a.dry_run)
    print(f"{'would write' if a.dry_run else 'wrote'}: {path} · revision {t['revision']} · {len(t['rows'])} rows")
    return vl.EXIT_PASS


def cmd_add(a):
    path = os.path.join(a.scope, "finish-conditions.md")
    if not os.path.exists(path):
        return fail("no finish-conditions.md to add to", "an existing table", "none", path,
                    f"finish-table.py init --scope {a.scope} --phase …")
    table = vl.parse_table(path)
    new = read_rows(a.rows)
    if not new:
        return fail("no rows to add", "at least one JSON row", "0", a.rows, "write the rows file",
                    code=vl.EXIT_USAGE)
    lines = read(path).splitlines()
    last = max(r["_line"] for r in table["rows"]) if table["rows"] else \
        next(i + 2 for i, l in enumerate(lines) if vl._cells(l)[:1] == ["check_id"])
    rev = table["revision"] + 1
    lines[last:last] = [render_row(r) for r in new]
    lines = [re.sub(r"^\*\*Revision:\*\*\s*\d+", f"**Revision:** {rev}", l) for l in lines]
    text = "\n".join(lines).rstrip("\n") + "\n" + changelog_line(rev, a.change, a.by) + "\n"
    t = write_checked(path, text, a.dry_run)
    print(f"{'would write' if a.dry_run else 'wrote'}: {path} · revision {t['revision']} · {len(t['rows'])} rows")
    return vl.EXIT_PASS


def main(argv):
    ap = argparse.ArgumentParser(description="Write a scope's finish-conditions.md (verify-contracts.md §3).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "add"):
        s = sub.add_parser(name)
        s.add_argument("--scope", required=True)
        s.add_argument("--rows")
        s.add_argument("--by", default=subprocess.run(["git", "config", "user.name"], capture_output=True,
                                                      text=True).stdout.strip() + " / Claude")
        s.add_argument("--projects", default=vl.PROJECTS)
        s.add_argument("--dry-run", action="store_true")
    sub.choices["init"].add_argument("--phase", action="append", required=True)
    sub.choices["init"].add_argument("--test-plan-owner")
    sub.choices["init"].add_argument("--predates")
    sub.choices["add"].add_argument("--change", required=True)
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return vl.EXIT_USAGE if exc.code else vl.EXIT_PASS
    if a.cmd == "add" and not a.rows:
        return fail("add needs --rows", "a JSONL file of rows", "none", "--rows", "pass --rows FILE",
                    code=vl.EXIT_USAGE)
    try:
        return cmd_init(a) if a.cmd == "init" else cmd_add(a)
    except vl.ContractError as exc:
        print(exc.msg, file=sys.stderr)
        return vl.EXIT_EVAL


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
