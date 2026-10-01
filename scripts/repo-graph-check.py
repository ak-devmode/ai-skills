#!/usr/bin/env python3
"""repo-graph-check.py — validate a scope's `## Repo Graph` snapshot against
current repo state (/plan §5.6.1).

Approach: parse the table repo-graph-snapshot.sh wrote into scope.md, locate each
repo under ~/Projects, and classify it with pure git — no judgment involved:

  unchanged  HEAD == recorded SHA
  advanced   recorded SHA is an ancestor of HEAD, same branch   (confirm, default proceed)
  diverged   branch changed, SHA not an ancestor, or newly dirty (STOP: re-scope/override/abort)
  missing    repo no longer on disk                             (STOP)
  skipped    no SHA recorded (`—`, `-`, empty) or `In Scope?` starts with NO
             — printed, never counted toward the verdict

What the SHA is compared against comes from the SHA column header:

  `HEAD SHA`                  the local checkout's HEAD (what repo-graph-snapshot.sh
                              records). Branch and dirtiness are checked too.
  `HEAD SHA (origin/develop)` that remote ref, fetched quietly first. The snapshot
                              pinned the remote, not a checkout, so local branch,
                              lag and dirtiness are not drift. If the fetch fails the
                              line says so and the last-fetched ref is used (local
                              HEAD if there is none) — never silently.

The script validates; it never re-researches the graph or edits scope.md. What to
do about drift stays a human call, which is why the exit code tiers it.

Usage:  repo-graph-check.py <scope.md> [--projects DIR]
Output: one line per repo + a verdict line on stdout.
Exit:   0 all unchanged · 1 advanced only (confirm) · 3 diverged/missing (stop)
        · 4 no Repo Graph snapshot table (older scope, or a prose-only section —
          skip, note it), or every row skipped · 2 usage

The heading may be numbered (`## 2. Repo Graph`) — /markdown-style numbers every
heading. A section with no table rows is exit 4, never a pass: zero rows checked is
not "all unchanged". Same for a table whose every row was skipped.
"""

import os
import re
import subprocess
import sys


NO_SHA = {"", "-", "—", "–", "n/a"}


def git(path, *args):
    p = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True)
    return p.returncode, p.stdout.strip()


def clean(cell):
    return re.sub(r"[`*]", "", cell or "").strip()


def column(header, prefix):
    """First header cell starting with `prefix` (headers carry qualifiers like `(origin/x)`)."""
    return next((h for h in header if h.startswith(prefix)), None)


def remote_ref(sha_col):
    """`head sha (origin/develop)` -> ("origin", "develop"); plain `head sha` -> None."""
    m = re.search(r"\(\s*([A-Za-z0-9._-]+)/([A-Za-z0-9._/-]+)\s*\)", sha_col or "")
    return (m.group(1), m.group(2)) if m else None


def resolve_target(path, ref):
    """Fetch `remote/branch` quietly; return (rev to compare against, note or "")."""
    remote, branch = ref
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        p = subprocess.run(["git", "-C", path, "fetch", "--quiet", remote, branch],
                           capture_output=True, text=True, env=env, timeout=60)
        ok = p.returncode == 0
    except subprocess.TimeoutExpired:
        ok = False
    tracking = f"refs/remotes/{remote}/{branch}"
    have = git(path, "rev-parse", "--verify", "--quiet", tracking)[0] == 0
    if ok and have:
        return tracking, ""
    if have:
        return tracking, f"fetch {remote} {branch} failed — compared against last-fetched {remote}/{branch}"
    return "HEAD", f"fetch {remote} {branch} failed and no {remote}/{branch} ref — compared against local HEAD"


def parse_table(text):
    m = re.search(r"^##[ \t]+(?:\d+(?:\.\d+)*\.?[ \t]+)?Repo Graph\b.*$", text, re.M)
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
    if not any(re.sub(r"[`*]", "", r.get("repo", "")).strip() for r in rows):
        print("Repo Graph section has no snapshot table (no rows with a `repo` column) — "
              "freshness validation skipped; nothing was checked")
        return 4

    header = list(rows[0]) if rows else []
    sha_col = column(header, "head sha")
    scope_col = column(header, "in scope")
    ref = remote_ref(sha_col)

    worst, checked = 0, 0
    for r in rows:
        name = clean(r.get("repo"))
        sha = clean(r.get(sha_col))
        branch = clean(r.get("current branch"))
        dirty_then = r.get("dirty", "").strip().lower() == "yes"
        if not name:
            continue
        if scope_col and clean(r.get(scope_col)).upper().startswith("NO"):
            print(f"skipped    {name}  (In Scope? = {clean(r.get(scope_col))})")
            continue
        if sha.lower() in NO_SHA:
            print(f"skipped    {name}  (no SHA recorded)")
            continue
        checked += 1
        path = locate(name, projects)
        if not path:
            print(f"missing    {name}  (not found under {projects})")
            worst = max(worst, 3)
            continue
        if ref:
            target, note = resolve_target(path, ref)
            label = f"{ref[0]}/{ref[1]}" if target != "HEAD" else "HEAD"
            note = f"  [{note}]" if note else ""
            _, tip = git(path, "rev-parse", "--short", target)
            same = git(path, "rev-parse", f"{sha}^{{commit}}")[1] == git(path, "rev-parse", target)[1]
            anc, _ = git(path, "merge-base", "--is-ancestor", sha, target)
            if same:
                print(f"unchanged  {name}  {tip} on {label}{note}")
            elif anc == 0:
                n = git(path, "rev-list", "--count", f"{sha}..{target}")[1]
                print(f"advanced   {name}  {sha} -> {tip} on {label} ({n} commits){note}")
                worst = max(worst, 1)
            else:
                print(f"diverged   {name}  {sha} not an ancestor of {label} {tip}{note}")
                worst = max(worst, 3)
            continue
        _, head = git(path, "rev-parse", "--short", "HEAD")
        _, cur = git(path, "branch", "--show-current")
        _, porcelain = git(path, "status", "--porcelain")
        dirty_now = bool(porcelain)
        if head.startswith(sha[:7]) and cur == branch and not (dirty_now and not dirty_then):
            print(f"unchanged  {name}  {head} on {cur}")
            continue
        anc, _ = git(path, "merge-base", "--is-ancestor", sha, "HEAD")
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

    if not checked:
        print("verdict: every Repo Graph row was skipped — nothing was checked")
        return 4
    verdict = {0: "all unchanged — proceed",
               1: "advanced only — confirm proceed or name files of concern",
               3: "DRIFT — stop: re-scope, override (acknowledge), or abort"}[worst]
    print(f"verdict: {verdict}")
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
