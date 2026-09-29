#!/usr/bin/env python3
"""clone-behind.py — one line when the local ai-skills clone is behind origin/main.

Approach: skills are consumed by symlink, so a teammate on a stale clone runs stale
rules and produces verdicts against a superseded contract without knowing it (CLAUDE.md
§2.1). `/verify` and `/plan` call this at start. It fetches at most once per
`--max-age` seconds (FETCH_HEAD's mtime), with a timeout, then counts commits in
HEAD..origin/main. Silent when current. It never blocks or fails the caller, but it is
never silent about not knowing: a failed fetch prints one "freshness unknown" line.

Usage:  clone-behind.py [--repo DIR] [--max-age SECONDS] [--timeout SECONDS]
        --repo defaults to the ai-skills clone this script lives in
Output: nothing when current; otherwise exactly one line.
Exit:   0 always · 2 usage
"""

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git(repo, *args, timeout=None):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=timeout)


def main(argv):
    ap = argparse.ArgumentParser(description="Warn when the ai-skills clone is behind origin/main.")
    ap.add_argument("--repo", default=HERE)
    ap.add_argument("--max-age", type=int, default=3600)
    ap.add_argument("--timeout", type=int, default=10)
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    name = os.path.basename(os.path.normpath(a.repo))
    gitdir = git(a.repo, "rev-parse", "--absolute-git-dir")
    if gitdir.returncode != 0:
        print(f"{name}: freshness unknown — not a git clone ({gitdir.stderr.strip()})")
        return 0
    fetch_head = os.path.join(gitdir.stdout.strip(), "FETCH_HEAD")
    stale = not os.path.exists(fetch_head) or time.time() - os.path.getmtime(fetch_head) > a.max_age
    if stale:
        try:
            f = git(a.repo, "fetch", "--quiet", "origin", "main", timeout=a.timeout)
            why = f.stderr.strip().splitlines()[-1] if f.returncode else ""
        except subprocess.TimeoutExpired:
            why = f"timed out after {a.timeout}s"
        if why:
            print(f"{name}: freshness unknown — fetch failed ({why})")
            return 0
    n = git(a.repo, "rev-list", "--count", "HEAD..origin/main")
    if n.returncode != 0:
        print(f"{name}: freshness unknown — {n.stderr.strip() or 'no origin/main'}")
    elif int(n.stdout.strip() or 0) > 0:
        print(f"{name} is {n.stdout.strip()} commit(s) behind origin/main — run: "
              f"git -C {a.repo} pull && {os.path.join(a.repo, 'setup.sh')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
