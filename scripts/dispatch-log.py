#!/usr/bin/env python3
"""dispatch-log.py — append one record to the /concurrency dispatch log.

Approach: build the record from flags (never from hand-typed JSON, which is where
quoting breaks), append it as one JSONL line, then read the file's last line back
and compare. A log line that didn't land is exit 1, because /concurrency's hard
rail 6 ("every dispatch and every outcome lands in the JSONL log") is only as good
as the write.

--status driver is the driver registering its OWN pane (Alex 86): a record of kind `driver`,
--task defaulting to `driver`, machine always this host (placement.this_host — `hostname -s`,
lowercased) and `session` = this agent session's id (packet.session_id: $CLAUDE_CODE_SESSION_ID,
$CLAUDE_SESSION_ID, $CODEX_SESSION_ID). packet.py's driver_identity reads this log, and inside
herdr only a pane whose latest record on this host is that registration, made by the same
session, is the driver; every other pane is a lane (Alex 97: a pane id reused by a new session
is not the driver, so a registration nobody closed is harmless). A registration is REFUSED
(exit 3, nothing written) when:
  * the pane's latest record (this host, or naming no machine) is an open lane record —
    dispatched or blocked. /concurrency writes a lane's record with --pane BEFORE the lane
    runs (Alex 97), so a lane that follows /plan Phase 0 is refused here, not registered
  * no session id is in the environment — an unbound registration could be inherited by
    whatever session herdr later puts in the pane id
  * the log cannot be read — an open lane record cannot be ruled out (fail closed)
A --machine naming another host is a usage error for a registration: a driver registers where
it runs; placement.py unloadable raises and writes nothing (fail closed — a registration under
a name packet.py would not match is no registration). Any later record for the pane id closes
the registration; the driver closes its own with --status done at scope end (/plan).

--pane is required (and non-blank) for every status: a `driver` record registers the driver,
and any later record for the pane id — a lane dispatched into it, the driver's `done` — closes
it; a record with no pane could do neither, so it is a usage error, not a write.

Usage:
  dispatch-log.py --scope S --status driver --pane "$HERDR_PANE_ID"   (the driver, /plan Phase 0)
  dispatch-log.py --scope S --task T --status {dispatched,done,blocked,failed} --pane P
                  [--seat X] [--branch B] [--worktree W] [--tail TEXT]
                  [--machine HOST] [--account KEY]   (default this host; a box lane names the box:
                                                       pane ids are per server)
                  [--log PATH]          (default ~/.config/herdr/concurrency-log.jsonl)
Output: the written JSON line on stdout.
Exit:   0 written + verified · 1 write did not land · 2 usage · 3 driver registration refused
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


def packet():
    """packet.py, for session_id and latest_record — the one log scan packet.py also decides by."""
    path = pathlib.Path(__file__).resolve().parent / "packet.py"
    spec = importlib.util.spec_from_file_location("packet", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def refuse_registration(pane, log):
    """'' when `pane` may register as the driver, else why not (module docstring). The message
    a lane sees names no way through: a lane stops."""
    pk = packet()
    if not pk.session_id():
        return ("no session id in the environment ($CLAUDE_CODE_SESSION_ID / $CLAUDE_SESSION_ID / "
                "$CODEX_SESSION_ID) — a registration binds to the session")
    rec, why = pk.latest_record(pane, blank_is_here=True, path=log)
    if why:
        return f"dispatch log unreadable ({why}) — an open lane record cannot be ruled out"
    if rec and rec.get("kind") != "driver" and rec.get("status") in pk.OPEN_LANE:
        return (f"pane {pane} is a lane (task {rec.get('task')}, {rec.get('status')} {rec.get('ts') or ''}). "
                "A lane never registers, merges or posts: stop.")
    return ""


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
        why = refuse_registration(a.pane, a.log)
        if why:
            print(f"dispatch-log: driver registration refused: {why}", file=sys.stderr)
            return 3
    elif not a.task:
        ap.error("--task is required for a lane record")
    else:  # a record with no machine is invisible to packet.py, so it would close no registration
        a.machine = a.machine or this_host()

    rec = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           **({"kind": "driver"} if a.status == "driver" else {}), "scope": a.scope, "task": a.task, "seat": a.seat, "branch": a.branch,
           "worktree": a.worktree, "pane_id": a.pane, "status": a.status}
    # pane ids are per herdr server, so a box lane's record says which machine (scope 3, plan 3.4)
    if a.status == "driver":
        rec["session"] = packet().session_id()
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
