#!/usr/bin/env python3
"""lane-slot.py — reuse six fixed lane folders per repo instead of a fresh worktree per lane.

Approach: Claude Code's folder-trust dialog is keyed to the EXACT folder, per account, and a
lane that meets it stops until a human answers (lanes sat 6–20 h in the go-live retro). A fresh
worktree per lane is a fresh folder every time. So each repo gets six fixed git worktrees,
`<repo>.lanes/a1`..`a6` — one per `herdr` §5 grid slot — trusted once by `pretrust.py`, and every
run checks its branch out in a slot instead of creating a folder (Alex, 2026-11-16).

`claim` creates the slot's worktree the first time, or reuses it: it refuses a slot that has
uncommitted changes or whose current branch holds commits on no remote (work that a switch
would strand from view), then switches the slot to a new branch from the base ref. `release`
detaches the slot at the base ref so the next claim starts clean; the lane's branch is kept
for landing and is deleted by the wave teardown, never here. `status` lists the slots.

For a lane on homelab2026 run it there: `ssh homelab2026 ~/Projects/ai-skills/scripts/lane-slot.py …`
with `~/`-relative repo paths.

Usage:
  lane-slot.py claim   <repo> <slot a1..a6> --branch <name> --base <ref>
  lane-slot.py release <repo> <slot> [--base <ref>]      (default base: origin/HEAD)
  lane-slot.py status  <repo>
Exit: 0 ok · 1 refused or git failed (reason on stderr) · 2 usage
"""

import argparse
import os
import subprocess
import sys

SLOTS = [f"a{i}" for i in range(1, 7)]


def git(cwd, *args, check=True):
    p = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed in {cwd}: {(p.stderr or p.stdout).strip()}")
    return p.stdout.strip()


def paths(repo, slot):
    repo = os.path.abspath(os.path.expanduser(repo)).rstrip("/")
    return repo, f"{repo}.lanes/{slot}"


def stranded(slot_dir):
    """Commits on the slot's current branch that no remote has (empty when detached)."""
    branch = git(slot_dir, "symbolic-ref", "-q", "--short", "HEAD", check=False)
    if not branch:
        return ""
    return git(slot_dir, "log", "--oneline", branch, "--not", "--remotes", check=False)


def cmd_claim(a):
    repo, slot = paths(a.repo, a.slot)
    git(repo, "fetch", "-q", "origin")
    if git(repo, "rev-parse", "--verify", "-q", f"refs/heads/{a.branch}", check=False):
        raise RuntimeError(f"branch {a.branch} already exists in {repo} — pick a new name or land/delete it first")
    if not os.path.isdir(slot):
        os.makedirs(os.path.dirname(slot), exist_ok=True)
        git(repo, "worktree", "add", "-b", a.branch, slot, a.base)
        print(f"{slot} created on {a.branch} from {a.base} — run pretrust.py {repo} once if not yet done")
        return 0
    if git(slot, "status", "--porcelain"):
        raise RuntimeError(f"{slot} has uncommitted changes — the last lane in it is not finished")
    left = stranded(slot)
    if left:
        raise RuntimeError(f"{slot}'s branch has commits on no remote — push or land them first:\n{left}")
    git(slot, "switch", "-q", "-c", a.branch, a.base)
    print(f"{slot} switched to {a.branch} from {a.base}")
    return 0


def cmd_release(a):
    repo, slot = paths(a.repo, a.slot)
    if not os.path.isdir(slot):
        raise RuntimeError(f"{slot} does not exist")
    if git(slot, "status", "--porcelain"):
        raise RuntimeError(f"{slot} has uncommitted changes — not releasing")
    branch = git(slot, "symbolic-ref", "-q", "--short", "HEAD", check=False) or "(detached)"
    left = stranded(slot)
    git(repo, "fetch", "-q", "origin")
    git(slot, "switch", "-q", "--detach", a.base)
    if left:
        print(f"lane-slot: note — {branch} keeps {len(left.splitlines())} commit(s) on no remote; land or push them", file=sys.stderr)
    print(f"{slot} released (was {branch}; branch kept for landing) — detached at {a.base}")
    return 0


def cmd_status(a):
    repo, _ = paths(a.repo, "a1")
    for s in SLOTS:
        _, slot = paths(a.repo, s)
        if not os.path.isdir(slot):
            print(f"{s}  —  not created")
            continue
        branch = git(slot, "symbolic-ref", "-q", "--short", "HEAD", check=False) or "(detached)"
        dirty = "dirty" if git(slot, "status", "--porcelain") else "clean"
        left = len(stranded(slot).splitlines())
        print(f"{s}  {branch}  {dirty}  {left} unpushed")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="Fixed, reusable lane folders per repo.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("claim")
    c.add_argument("repo")
    c.add_argument("slot", choices=SLOTS)
    c.add_argument("--branch", required=True)
    c.add_argument("--base", required=True)
    r = sub.add_parser("release")
    r.add_argument("repo")
    r.add_argument("slot", choices=SLOTS)
    r.add_argument("--base", default="origin/HEAD")
    s = sub.add_parser("status")
    s.add_argument("repo")
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        return {"claim": cmd_claim, "release": cmd_release, "status": cmd_status}[a.cmd](a)
    except RuntimeError as exc:
        print(f"lane-slot: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
