#!/usr/bin/env python3
"""repo-graph-check.py — validate a scope's `## Repo Graph` snapshot against
current repo state (/plan §5.6.1).

Approach: parse the table repo-graph-snapshot.sh wrote into scope.md, locate each
repo under ~/Projects, and classify it with pure git — no judgment involved:

  unchanged  HEAD == recorded SHA
  advanced   recorded SHA is an ancestor of HEAD, same branch   (confirm, default proceed)
  diverged   branch changed, SHA not an ancestor, or newly dirty (STOP: re-scope/override/abort)
  missing    repo no longer on disk                             (STOP)

The script validates; it never re-researches the graph or edits scope.md. What to
do about drift stays a human call, which is why the exit code tiers it.

Usage:  repo-graph-check.py <scope.md> [--projects DIR]
Output: one line per repo + a verdict line on stdout.
Exit:   0 all unchanged · 1 advanced only (confirm) · 3 diverged/missing (stop)
        · 4 no Repo Graph section (older scope — skip, note it) · 2 usage
"""

import os
import re
import subprocess
import sys


def git(path, *args):
    p = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True)
    return p.returncode, p.stdout.strip()


def parse_table(text):
    m = re.search(r"^## Repo Graph\s*$", text, re.M)
    if not m:
        return None
    rows, header = [], None
    for line in text[m.end():].splitlines():
        s = line.strip()
        if s.startswith("## "):
            break
        if not s.startswith("|"):
            if rows or header:
                if s == "":
                    continue
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def locate(name, projects):
    for cand in (os.path.join(projects, name), *(os.path.join(projects, g, name)
                 for g in sorted(os.listdir(projects)) if os.path.isdir(os.path.join(projects, g)))):
        if os.path.exists(os.path.join(cand, ".git")):
            return cand
    return None


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__.split("Usage:")[1].split("Output:")[0].strip(), file=sys.stderr)
        return 2
    scope = argv[0]
    projects = os.path.expanduser("~/Projects")
    if "--projects" in argv:
        projects = argv[argv.index("--projects") + 1]
    try:
        rows = parse_table(open(scope, encoding="utf-8").read())
    except OSError as exc:
        print(f"repo-graph-check: {exc}", file=sys.stderr)
        return 2
    if rows is None:
        print("no Repo Graph section — scope predates the contract; freshness validation skipped")
        return 4

    worst = 0
    for r in rows:
        name = re.sub(r"[`*]", "", r.get("repo", "")).strip()
        sha = re.sub(r"[`*]", "", r.get("head sha", "")).strip()
        branch = re.sub(r"[`*]", "", r.get("current branch", "")).strip()
        dirty_then = r.get("dirty", "").strip().lower() == "yes"
        if not name:
            continue
        path = locate(name, projects)
        if not path:
            print(f"missing    {name}  (not found under {projects})")
            worst = max(worst, 3)
            continue
        _, head = git(path, "rev-parse", "--short", "HEAD")
        _, cur = git(path, "branch", "--show-current")
        _, porcelain = git(path, "status", "--porcelain")
        dirty_now = bool(porcelain)
        if sha and head.startswith(sha[:7]) and cur == branch and not (dirty_now and not dirty_then):
            print(f"unchanged  {name}  {head} on {cur}")
            continue
        anc, _ = git(path, "merge-base", "--is-ancestor", sha, "HEAD") if sha else (1, "")
        n = git(path, "rev-list", "--count", f"{sha}..HEAD")[1] if anc == 0 else "?"
        if cur == branch and anc == 0 and not (dirty_now and not dirty_then):
            print(f"advanced   {name}  {sha} -> {head} on {cur} ({n} commits)")
            worst = max(worst, 1)
        else:
            why = []
            if cur != branch:
                why.append(f"branch {branch} -> {cur}")
            if anc != 0:
                why.append(f"{sha} not an ancestor of {head}")
            if dirty_now and not dirty_then:
                why.append("uncommitted changes since snapshot")
            print(f"diverged   {name}  " + "; ".join(why))
            worst = max(worst, 3)

    verdict = {0: "all unchanged — proceed",
               1: "advanced only — confirm proceed or name files of concern",
               3: "DRIFT — stop: re-scope, override (acknowledge), or abort"}[worst]
    print(f"verdict: {verdict}")
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
