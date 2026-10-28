#!/usr/bin/env python3
"""dispatch-log.py — append one record to the /concurrency dispatch log.

Approach: build the record from flags (never from hand-typed JSON, which is where
quoting breaks), append it as one JSONL line, then read the file's last line back
and compare. A log line that didn't land is exit 1, because /concurrency's hard
rail 6 ("every dispatch and every outcome lands in the JSONL log") is only as good
as the write.

--status driver is the driver registering its OWN pane (Alex 86): a record of kind `driver`,
--task defaulting to `driver`, machine always this host (placement.this_host — `hostname -s`,
lowercased). packet.py's driver_identity reads this log, and inside herdr only a pane whose
latest record on this host is that registration is the driver; every other pane is a lane.
A --machine naming another host is a usage error for a registration: a driver registers where
it runs; placement.py unloadable raises and writes nothing (fail closed — a registration under
a name packet.py would not match is no registration). Lanes never write this status. Any later record for the pane id closes the
registration.

--pane is required (and non-blank) for every status: a record with no pane could neither
register a driver nor close a registration, so it is a usage error, not a write.

Usage:
  dispatch-log.py --scope S --status driver --pane "$HERDR_PANE_ID"   (the driver, /plan Phase 0)
  dispatch-log.py --scope S --task T --status {dispatched,done,blocked,failed} --pane P
                  [--seat X] [--branch B] [--worktree W] [--tail TEXT]
                  [--machine HOST] [--account KEY]   (a box lane: pane ids are per server)
                  [--log PATH]          (default ~/.config/herdr/concurrency-log.jsonl)
Output: the written JSON line on stdout.
Exit:   0 written + verified · 1 write did not land · 2 usage
"""

import argparse
import datetime
import importlib.util
import json
import os
import pathlib
import sys

STATUSES = ("dispatched", "done", "blocked", "failed", "driver")


def this_host():
    """placement.this_host — the one normalization packet.py compares against (10.3-r4-03)."""
    path = pathlib.Path(__file__).resolve().parent / "placement.py"
    spec = importlib.util.spec_from_file_location("placement", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.this_host()


def main(argv):
    ap = argparse.ArgumentParser(description="Append a /concurrency dispatch-log record.")
    ap.add_argument("--scope", required=True)
    ap.add_argument("--task")
    ap.add_argument("--status", required=True, choices=STATUSES)
    ap.add_argument("--pane", required=True)
    for opt in ("seat", "branch", "worktree", "machine", "account", "tail"):
        ap.add_argument(f"--{opt}")
    ap.add_argument("--log", default=os.path.expanduser("~/.config/herdr/concurrency-log.jsonl"))
    a = ap.parse_args(argv)
    if not a.pane.strip():
        ap.error("--pane must name the herdr pane")
    if a.status == "driver":
        host = this_host()
        if a.machine and a.machine.strip().lower() != host:
            ap.error(f"--status driver registers this host ({host}); --machine {a.machine} is another")
        a.machine, a.task = host, a.task or "driver"
    elif not a.task:
        ap.error("--task is required for a lane record")

    rec = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           **({"kind": "driver"} if a.status == "driver" else {}), "scope": a.scope, "task": a.task, "seat": a.seat, "branch": a.branch,
           "worktree": a.worktree, "pane_id": a.pane, "status": a.status}
    # pane ids are per herdr server, so a box lane's record says which machine (scope 3, plan 3.4)
    for key in ("machine", "account"):
        if getattr(a, key):
            rec[key] = getattr(a, key)
    if a.tail:
        rec["tail"] = a.tail
    line = json.dumps(rec, ensure_ascii=False)

    os.makedirs(os.path.dirname(a.log) or ".", exist_ok=True)
    with open(a.log, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    # parallel lanes append to the same log, so ours may no longer be the last line
    with open(a.log, encoding="utf-8") as fh:
        recent = fh.read().splitlines()[-64:]
    if line not in recent:
        print(f"dispatch-log: record did not land in {a.log}", file=sys.stderr)
        return 1
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
