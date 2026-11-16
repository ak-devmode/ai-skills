#!/usr/bin/env python3
"""lane-signal.py — lane completion that does not depend on a model printing exact text.

Approach: watchers that regex a lane's pane for `PARTITION-DONE <task>` miss whenever the model
prints it slightly differently (the go-live retro's 3-hour unnoticed fix writer, 2026-11-03), and
fire falsely when the marker is quoted in the prompt. So completion is a FILE, written by a
process, never by prose:

  * a headless lane (`claude -p`, `codex exec`) is wrapped by `run`, which writes the file with
    the command's exit code when the process ends — the exit is the signal;
  * an interactive lane ends by running `done` as a tool call — a fixed command, so a model that
    paraphrases its summary still writes the same file.

`wait` is the driver's watcher. It returns on the FIRST event among the named lanes and prints
one line, so a background job notifies the driver; the driver re-arms it for the rest (reported
lanes are remembered per run). Events: `DONE` (the file exists), `BLOCKED` (herdr reports an
approval/question UI), `IDLE-NO-SIGNAL` (the agent has sat idle for --idle-min with no file — the
case regex watchers slept through: read the pane), and `TIMEOUT`.

Files live in ~/.cache/lanes/<run>/<lane>.done on the machine the lanes run on; `wait --machine`
reads them there over ssh and asks that machine's herdr server for pane state.

Usage:
  lane-signal.py run  <run> <lane> -- <command...>       (exit code = the command's)
  lane-signal.py done <run> <lane> [note...]
  lane-signal.py wait <run> --lane NAME=PANE [--lane ...] [--machine HOST]
                      [--idle-min 15] [--timeout-min 240] [--poll 30]
Exit: 0 an event was printed · 1 timeout · 2 usage
"""

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time

ROOT = "~/.cache/lanes"


def lane_dir(run, local=True):
    d = os.path.join(ROOT, run)
    return os.path.expanduser(d) if local else d


def write_done(run, lane, body):
    d = lane_dir(run)
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, f".{lane}.tmp")
    with open(tmp, "w") as f:
        f.write(body + "\n")
    os.replace(tmp, os.path.join(d, f"{lane}.done"))


def now():
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def cmd_run(a):
    if not a.command:
        return 2
    started = now()
    try:
        rc = subprocess.call(a.command)
    except OSError as exc:
        print(f"lane-signal: could not start {a.command[0]}: {exc}", file=sys.stderr)
        rc = 127
    write_done(a.run, a.lane, f"exit={rc} started={started} ended={now()}")
    return rc


def cmd_done(a):
    write_done(a.run, a.lane, f"exit=0 at={now()} note={' '.join(a.note)}".rstrip())
    print(f"lane-signal: {a.lane} done")
    return 0


def sh(machine, script):
    """Run a shell snippet locally or on `machine`; return stdout ('' on failure)."""
    argv = ["ssh", "-o", "BatchMode=yes", machine, script] if machine else ["sh", "-c", script]
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def pane_status(machine, pane):
    h = ["herdr"] + (["--machine", machine] if machine else [])
    try:
        out = subprocess.run(h + ["pane", "get", pane], capture_output=True, text=True, timeout=30).stdout
        return json.loads(out)["result"]["pane"].get("agent_status") or "unknown"
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError):
        return "unreachable"


def cmd_wait(a):
    lanes = {}
    for spec in a.lane:
        name, _, pane = spec.partition("=")
        if not name or not pane:
            print(f"lane-signal: --lane wants NAME=PANE, got {spec!r}", file=sys.stderr)
            return 2
        lanes[name] = pane
    seen_path = os.path.join(lane_dir(a.run), ".reported")
    os.makedirs(lane_dir(a.run), exist_ok=True)
    seen = set(open(seen_path).read().split()) if os.path.exists(seen_path) else set()
    idle_since = {}
    deadline = time.time() + a.timeout_min * 60
    rdir = lane_dir(a.run, local=not a.machine)

    def report(line, key):
        with open(seen_path, "a") as f:
            f.write(key + "\n")
        print(line)
        return 0

    while time.time() < deadline:
        files = sh(a.machine, f"cd {rdir} 2>/dev/null && for f in *.done; do [ -f \"$f\" ] && printf '%s\\t' \"$f\" && cat \"$f\"; done")
        done = {}
        for row in files.splitlines():
            fname, _, body = row.partition("\t")
            done[fname[:-5]] = body.strip()
        for name, pane in lanes.items():
            if f"done:{name}" not in seen and name in done:
                return report(f"DONE {name} {done[name]}", f"done:{name}")
        for name, pane in lanes.items():
            if f"done:{name}" in seen or name in done:
                continue
            st = pane_status(a.machine, pane)
            if st == "blocked" and f"blocked:{name}" not in seen:
                return report(f"BLOCKED {name} {pane}", f"blocked:{name}")
            if st in ("idle", "done"):
                idle_since.setdefault(name, time.time())
                mins = (time.time() - idle_since[name]) / 60
                if mins >= a.idle_min and f"idle:{name}" not in seen:
                    return report(f"IDLE-NO-SIGNAL {name} {pane} {int(mins)}m — read the pane", f"idle:{name}")
            else:
                idle_since.pop(name, None)
        if all(f"done:{n}" in seen for n in lanes):
            print("ALL-DONE")
            return 0
        time.sleep(a.poll)
    print(f"TIMEOUT {a.timeout_min}m — lanes without a signal: "
          + " ".join(n for n in lanes if f"done:{n}" not in seen))
    return 1


def main(argv):
    ap = argparse.ArgumentParser(description="Lane completion by file, not by printed text.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("run")
    r.add_argument("lane")
    r.add_argument("command", nargs=argparse.REMAINDER)
    d = sub.add_parser("done")
    d.add_argument("run")
    d.add_argument("lane")
    d.add_argument("note", nargs="*")
    w = sub.add_parser("wait")
    w.add_argument("run")
    w.add_argument("--lane", action="append", required=True)
    w.add_argument("--machine")
    w.add_argument("--idle-min", type=float, default=15)
    w.add_argument("--timeout-min", type=float, default=240)
    w.add_argument("--poll", type=float, default=30)
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if a.cmd == "run":
        if a.command and a.command[0] == "--":
            a.command = a.command[1:]
        return cmd_run(a)
    return cmd_done(a) if a.cmd == "done" else cmd_wait(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
