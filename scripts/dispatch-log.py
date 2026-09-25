#!/usr/bin/env python3
"""dispatch-log.py — append one record to the /concurrency dispatch log.

Approach: build the record from flags (never from hand-typed JSON, which is where
quoting breaks), append it as one JSONL line, then read the file's last line back
and compare. A log line that didn't land is exit 1, because /concurrency's hard
rail 6 ("every dispatch and every outcome lands in the JSONL log") is only as good
as the write.

Usage:
  dispatch-log.py --scope S --task T --status {dispatched,done,blocked,failed}
                  [--seat X] [--branch B] [--worktree W] [--pane P] [--tail TEXT]
                  [--log PATH]          (default ~/.config/herdr/concurrency-log.jsonl)
Output: the written JSON line on stdout.
Exit:   0 written + verified · 1 write did not land · 2 usage
"""

import argparse
import datetime
import json
import os
import sys

STATUSES = ("dispatched", "done", "blocked", "failed")


def main(argv):
    ap = argparse.ArgumentParser(description="Append a /concurrency dispatch-log record.")
    ap.add_argument("--scope", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--status", required=True, choices=STATUSES)
    for opt in ("seat", "branch", "worktree", "pane", "tail"):
        ap.add_argument(f"--{opt}")
    ap.add_argument("--log", default=os.path.expanduser("~/.config/herdr/concurrency-log.jsonl"))
    a = ap.parse_args(argv)

    rec = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "scope": a.scope, "task": a.task, "seat": a.seat, "branch": a.branch,
           "worktree": a.worktree, "pane_id": a.pane, "status": a.status}
    if a.tail:
        rec["tail"] = a.tail
    line = json.dumps(rec, ensure_ascii=False)

    os.makedirs(os.path.dirname(a.log), exist_ok=True)
    with open(a.log, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    with open(a.log, encoding="utf-8") as fh:
        last = fh.read().rstrip("\n").rsplit("\n", 1)[-1]
    if last != line:
        print(f"dispatch-log: record did not land in {a.log}", file=sys.stderr)
        return 1
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
