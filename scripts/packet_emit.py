"""packet_emit.py — emit one decision packet from review / verify (scope 10 §4.2, plan 10.2 Task 2.5).

Approach: a thin importable wrapper over `packet.py new` run as a subprocess with cwd = the repo
under review, so the packet lands in that repo's outbox (the driver POSTs; with
DECISION_QUEUE_URL unset the outbox write is all that happens). Harness errors never stop the
caller: every failure (no packet.py output, nonzero exit, timeout, no git repo) returns None
after a stderr warning, and the caller keeps its inline numbered question — the fail-open
direction is deliberate, because the packet is an add-on to a question the user can still be
asked inline. On success it prints `PACKET <id>` (packet.py's own first stdout line) and
returns the id.
"""
import os
import re
import subprocess
import sys

PACKET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "packet.py")


def stable_id(*parts):
    """A packet id derived from its parts, so re-emitting one case is idempotent (packet.py new --id
    re-sends an existing packet instead of minting a second)."""
    return ("pk-" + "-".join(re.sub(r"[^A-Za-z0-9_-]", "-", str(x)) for x in parts))[:64]


def emit(repo, unit, title, options, body, door="one-way", range_=None, blocks="", pid=None, timeout=30):
    """Write a `generic` packet into `repo`'s outbox. `options` is [label, ...]; the first is the
    recommendation. Returns the packet id, or None (warned on stderr) on any failure."""
    cmd = [sys.executable, PACKET, "new", "--door", door, "--type", "generic", "--title", title,
           "--unit", unit, "--recommended", "1", "--body", body]
    for label in options:
        cmd += ["--option", label]
    if pid:
        cmd += ["--id", pid]
    if range_:
        cmd += ["--range", range_]
    if blocks:
        cmd += ["--blocks", blocks]
    try:
        p = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"packet_emit: warning: packet not written ({exc}); ask the question inline", file=sys.stderr)
        return None
    first = next((x for x in p.stdout.splitlines() if x.startswith("PACKET ")), "")
    if p.returncode != 0 or not first:
        why = next((x.strip() for x in reversed(p.stderr.splitlines()) if x.strip()), f"exit {p.returncode}")
        print(f"packet_emit: warning: packet not written ({why[:200]}); ask the question inline", file=sys.stderr)
        return None
    print(first)
    return first.split(None, 1)[1].split()[0]
