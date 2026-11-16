#!/usr/bin/env python3
"""pretrust.py — pre-accept Claude Code's folder-trust dialog for a repo's lane folders, for
every account on this machine. Run by Alex, once per repo per machine.

Approach: a lane launched in a folder Claude Code has not trusted stops at the trust dialog,
and only a human can answer it — lanes sat 6–20 h this way in the go-live retro (2026-11). Trust
is stored per EXACT path, per account (each account's `.claude.json` `projects[<path>]
.hasTrustDialogAccepted`); a trusted parent does not cover a child (2026-09-29). So this sets the
flag on: the repo itself, its six fixed lane slots `<repo>.lanes/a1`..`a6` (one per `herdr` §5
grid slot — lanes that reuse them never meet the dialog again), and every worktree of the repo
that already exists (`<repo>.worktrees/*`, `~/.herdr/worktrees/<name>/*`). Accounts come from
dev-workbench `config/accounts/accounts.tsv` for this host: the default account's file is
`~/.claude.json`, any other account's is `<claude_dir>/.claude.json`.

Claude Code rewrites `.claude.json` often, so each file is loaded, changed and atomically
replaced in one step, a timestamped backup is kept beside it, and the flag is read back.
Claude itself must not run this (an agent editing its own trust config is refused as
self-modification) — it is a hand-run step.

Usage: pretrust.py <repo-path> [<repo-path> ...] [--dry-run]
Exit:  0 all set and read back · 1 a write or read-back failed · 2 usage
"""

import argparse
import datetime as dt
import glob
import json
import os
import socket
import sys

ACCOUNTS = os.path.expanduser("~/Projects/dev-workbench/config/accounts/accounts.tsv")


def accounts():
    host = socket.gethostname().split(".")[0].lower()
    out = []
    for line in open(ACCOUNTS):
        if not line.strip() or line.startswith("#") or line.startswith("host\t"):
            continue
        f = line.rstrip("\n").split("\t")
        if len(f) >= 7 and f[0] == host:
            claude_dir = os.path.expanduser(f[3])
            path = os.path.expanduser("~/.claude.json") if f[6] == "yes" else os.path.join(claude_dir, ".claude.json")
            out.append((f[1], path))
    return out


def folders(repo):
    repo = os.path.abspath(os.path.expanduser(repo)).rstrip("/")
    name = os.path.basename(repo)
    paths = [repo] + [f"{repo}.lanes/a{i}" for i in range(1, 7)]
    paths += sorted(glob.glob(f"{repo}.worktrees/*")) + sorted(glob.glob(os.path.expanduser(f"~/.herdr/worktrees/{name}/*")))
    return [p for p in dict.fromkeys(paths)]


def main(argv):
    ap = argparse.ArgumentParser(description="Pre-accept the folder-trust dialog for a repo's lane folders.")
    ap.add_argument("repos", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    accts = accounts()
    if not accts:
        print(f"pretrust: no accounts for this host in {ACCOUNTS}", file=sys.stderr)
        return 2
    want = [p for r in a.repos for p in folders(r)]
    rc = 0
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    for key, path in accts:
        if not os.path.exists(path):
            print(f"  {key}: {path} missing — log in to that account once first, then re-run")
            rc = 1
            continue
        with open(path) as f:
            raw = f.read()
        d = json.loads(raw)
        projects = d.setdefault("projects", {})
        new = [p for p in want if not projects.get(p, {}).get("hasTrustDialogAccepted")]
        if not new:
            print(f"  {key}: all {len(want)} folders already trusted")
            continue
        if a.dry_run:
            print(f"  {key}: would trust {len(new)}: " + ", ".join(new))
            continue
        with open(f"{path}.pretrust-{stamp}.bak", "w") as f:
            f.write(raw)
        for p in new:
            projects.setdefault(p, {})["hasTrustDialogAccepted"] = True
        tmp = f"{path}.pretrust.tmp"
        with open(tmp, "w") as f:
            json.dump(d, f, indent=2)
        os.replace(tmp, path)
        back = json.load(open(path)).get("projects", {})
        missing = [p for p in new if not back.get(p, {}).get("hasTrustDialogAccepted")]
        if missing:
            print(f"  {key}: READ-BACK FAILED for {len(missing)} (another session rewrote the file?) — re-run")
            rc = 1
        else:
            print(f"  {key}: trusted {len(new)} folder(s), read back ok (backup {os.path.basename(path)}.pretrust-{stamp}.bak)")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
