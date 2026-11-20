#!/usr/bin/env python3
"""lane-brief.py — deliver lane briefs to the machine a lane runs on, and prove they landed.

Approach: copy each file (scp to --machine, or a plain copy without one), then read every
destination back by sha256 on that machine and compare with the source. A launch that follows
a failed copy starts a lane on a brief that is not there (WellMed 231, 2026-11-20: `scp:
Connection closed`, exit ignored, the lane listed an empty directory). So the launch gates on
this exit code, never on the copy's.

Usage:
  lane-brief.py put [--machine HOST] --dir DIR FILE...
    --dir   destination directory (`~/…` expands on the destination machine)
Output: one `ok <name> <sha12>` line per file, or a FAIL line naming the file.
Exit:   0 every file landed byte for byte · 1 a copy or read-back failed · 2 usage
"""
import argparse
import hashlib
import os
import shlex
import shutil
import subprocess
import sys


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def remote(machine, script):
    p = subprocess.run(["ssh", "-o", "ConnectTimeout=15", machine, script],
                       capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout, p.stderr.strip()


def put(a):
    want = {os.path.basename(f): sha(f) for f in a.files}
    if a.machine:
        rc, _, err = remote(a.machine, f"mkdir -p {a.dir}")
        if rc != 0:
            print(f"FAIL mkdir {a.dir} on {a.machine}: {err}")
            return 1
        dest = a.dir[2:] if a.dir.startswith("~/") else a.dir  # scp paths are relative to $HOME
        p = subprocess.run(["scp", "-q", "-o", "ConnectTimeout=15", *a.files, f"{a.machine}:{dest}/"],
                           capture_output=True, text=True, timeout=300)
        if p.returncode != 0:
            print(f"FAIL scp to {a.machine}: {p.stderr.strip() or 'exit ' + str(p.returncode)}")
        names = " ".join(shlex.quote(n) for n in want)
        rc, out, err = remote(a.machine, f"cd {a.dir} && {{ sha256sum {names} 2>/dev/null || shasum -a 256 {names}; }}")
        got = {}
        for line in out.splitlines():
            h, _, n = line.partition("  ")
            got[n.strip()] = h
    else:
        d = os.path.expanduser(a.dir)
        os.makedirs(d, exist_ok=True)
        got = {}
        for f in a.files:
            shutil.copyfile(f, os.path.join(d, os.path.basename(f)))
            got[os.path.basename(f)] = sha(os.path.join(d, os.path.basename(f)))
    bad = 0
    for n, h in want.items():
        if got.get(n) == h:
            print(f"ok {n} {h[:12]}")
        else:
            bad += 1
            print(f"FAIL {n}: {'missing' if n not in got else 'differs'} at {a.machine or 'local'}:{a.dir}")
    return 1 if bad else 0


def main(argv):
    ap = argparse.ArgumentParser(description="Deliver lane briefs and prove they landed.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("put")
    p.add_argument("--machine")
    p.add_argument("--dir", required=True)
    p.add_argument("files", nargs="+")
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    missing = [f for f in a.files if not os.path.isfile(f)]
    if missing:
        print(f"lane-brief: no such file: {' '.join(missing)}", file=sys.stderr)
        return 2
    return put(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
