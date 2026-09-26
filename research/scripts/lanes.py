#!/usr/bin/env python3
"""Research lanes: the deterministic half of /research pane mode.

Approach: the driver session (Opus) owns judgment (scoping, briefs, synthesis);
this script owns everything with one right answer: building the tab, launching
the lane agents, ranking claims under the verify cap, and classifying lane state.
Lane state comes from files and herdr agent state, never from reading scrollback:

    done    <run>/<lane>.json parses and is not marked "complete": false
    failed  pane/agent gone, or agent idle|done|blocked with no output file for
            longer than --grace-sec (an Esc interrupt lands here)
    stall   agent revision unchanged for --stall-min; flagged once, never killed

`wait` is event-driven so it fits a background Bash call: it exits as soon as any
lane changes state (or on --once), printing the change, and persists state to
<run>/status.json so the next call reports only what is new.

Commands
    open    --run-dir D --label L --lanes a,b,c   tab in the caller's workspace + one pane per lane
    launch  --run-dir D --lane NAME [--model sonnet]   start claude in the lane's pane, point it at brief-NAME.md
    claims  --run-dir D --cap N --lanes a,b,c     round-robin claims under the cap -> claims.json
    wait    --run-dir D --lanes a,b,c [--once]    block until a lane changes state; print it

Exit codes: 0 ok · 1 herdr/runtime failure · 2 bad arguments. Stdlib only.
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

# Lanes start in one fixed, pre-trusted folder. Claude Code 2.1.280 shows its
# folder-trust dialog in any untrusted cwd even with --dangerously-skip-permissions,
# and a per-run scratch dir is always untrusted. Lanes still write their output
# into the run dir by absolute path.
LANE_HOME = Path.home() / ".cache" / "research-lanes"
TERMINAL = {"done", "failed"}
IMP = {"central": 0, "supporting": 1, "tangential": 2}
QUAL = {"primary": 0, "secondary": 1, "blog": 2, "forum": 3, "unreliable": 4}


def herdr(*args):
    """Run a herdr command and return .result; raise on a non-JSON or error reply."""
    out = subprocess.run(["herdr", *args], capture_output=True, text=True)
    if out.returncode == 0 and not out.stdout.strip():
        return {}  # some commands (pane report-metadata) succeed silently
    try:
        reply = json.loads(out.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"herdr {' '.join(args)}: {out.stdout or out.stderr}".strip())
    if "error" in reply:
        raise RuntimeError(f"herdr {' '.join(args)}: {reply['error']}")
    return reply["result"]


def load(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return default


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2))


def agent_name(run_dir, lane):
    # Unique per run so reruns never collide with a lane left open from an earlier tab.
    # herdr caps names at 32 chars of [a-z0-9_-], so the run is a stable 6-char hash,
    # not its folder name (2026-09-26: "r-poteto-verify-r1-a1-pstack-repo" was refused).
    run = hashlib.sha1(Path(run_dir).name.encode()).hexdigest()[:6]
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in lane.lower())
    return f"r{run}-{safe}"[:32]


def cmd_open(a):
    ws = os.environ.get("HERDR_WORKSPACE_ID")
    if not ws:
        sys.exit("open: HERDR_WORKSPACE_ID unset — not inside a herdr pane; use Workflow mode")
    projects = load(Path.home() / ".claude.json", {}).get("projects", {})
    if not projects.get(str(LANE_HOME), {}).get("hasTrustDialogAccepted"):
        sys.exit(f"open: {LANE_HOME} is not a trusted Claude Code folder. One-time setup: "
                 f"mkdir -p {LANE_HOME}, start `claude` there, choose 'Yes, I trust this folder', exit.")
    run = Path(a.run_dir)
    run.mkdir(parents=True, exist_ok=True)
    lanes = a.lanes.split(",")
    cwd = str(LANE_HOME)
    made = herdr("tab", "create", "--workspace", ws, "--cwd", cwd, "--label", a.label)
    tab, root = made["tab"]["tab_id"], made["root_pane"]["pane_id"]
    # Grid: up to 4 lanes in one row, else two rows. Columns are equalised by
    # splitting the rightmost column with ratio 1/remaining (ratio = share kept).
    cols = len(lanes) if len(lanes) <= 4 else math.ceil(len(lanes) / 2)
    column_panes = [root]
    for i in range(1, cols):
        ratio = 1 / (cols - i + 1)
        split = herdr("pane", "split", column_panes[-1], "--direction", "right",
                      "--ratio", f"{ratio:.3f}", "--cwd", cwd, "--no-focus")
        column_panes.append(split["pane"]["pane_id"])
    panes = list(column_panes)
    for col in column_panes:
        if len(panes) >= len(lanes):
            break
        split = herdr("pane", "split", col, "--direction", "down", "--ratio", "0.5",
                      "--cwd", cwd, "--no-focus")
        panes.append(split["pane"]["pane_id"])
    # Row-major order: top row first, then the second row left to right.
    mapping = dict(zip(lanes, panes))
    save(run / "panes.json", {"tab": tab, "label": a.label, "lanes": mapping})
    print(json.dumps({"tab": tab, "lanes": mapping}))


def cmd_launch(a):
    run = Path(a.run_dir)
    pane = load(run / "panes.json", {}).get("lanes", {}).get(a.lane)
    brief = run / f"brief-{a.lane}.md"
    if not pane:
        sys.exit(f"launch: no pane for lane {a.lane} in {run}/panes.json — run `open` first")
    if not brief.is_file():
        sys.exit(f"launch: missing {brief}")
    name = agent_name(run, a.lane)
    label = f"{a.lane} @{a.model}"
    herdr("pane", "rename", pane, label)
    herdr("pane", "report-metadata", pane, "--source", "research", "--display-agent", label)
    # Bypass mode clears every tool prompt (not the trust dialog — LANE_HOME handles that):
    # a lane reads the web and writes only inside the run dir, so nothing needs a human.
    herdr("agent", "start", name, "--kind", "claude", "--pane", pane, "--timeout", "60000",
          "--", "--model", a.model, "--dangerously-skip-permissions")
    herdr("agent", "prompt", name,
          f"Read {brief} and carry it out exactly. It is your whole task.")
    print(json.dumps({"lane": a.lane, "agent": name, "pane": pane}))


def cmd_claims(a):
    # Same ranking as deep-research-lean: within an angle by importance then source
    # quality, then round-robin across angles so no angle starves the others.
    run = Path(a.run_dir)
    queues, extracted = [], {}
    for lane in a.lanes.split(","):
        claims = load(run / f"{lane}.json", {}).get("claims", [])
        extracted[lane] = len(claims)
        claims.sort(key=lambda c: (IMP.get(c.get("importance"), 3), QUAL.get(c.get("sourceQuality"), 5)))
        queues.append([{**c, "angle": lane} for c in claims])
    picked = []
    while len(picked) < a.cap and any(queues):
        for q in queues:
            if q and len(picked) < a.cap:
                picked.append(q.pop(0))
    for i, c in enumerate(picked):
        c["id"] = f"c{i + 1}"
    coverage = {lane: {"extracted": n, "toVerify": sum(c["angle"] == lane for c in picked)}
                for lane, n in extracted.items()}
    save(run / "claims.json", {"claims": picked, "unverified": [c for q in queues for c in q],
                               "coverage": coverage})
    print(json.dumps({"toVerify": len(picked), "coverage": coverage}))


def classify(run, lane, prior, now, grace, stall):
    out = run / f"{lane}.json"
    data = load(out, None) if out.is_file() else None
    # The verify lane checkpoints with "complete": false so an interrupt keeps its
    # partial verdicts; only a complete file (or one without the flag) means done.
    if isinstance(data, dict) and data.get("complete", True) is True:
        return {"state": "done"}
    try:
        info = herdr("agent", "get", agent_name(run, lane))["agent"]
    except RuntimeError:
        return {"state": "failed", "reason": "pane or agent gone"}
    status, rev = info.get("agent_status"), info.get("revision")
    rec = dict(prior)
    if rev != rec.get("revision"):
        rec.update(revision=rev, revisionSince=now, stallFlagged=False)
    if status in ("idle", "done", "blocked"):
        rec.setdefault("quietSince", now)
        if now - rec["quietSince"] >= grace:
            return {"state": "failed", "reason": f"agent {status} with no {out.name}"}
    else:
        rec.pop("quietSince", None)
    rec["state"] = "running"
    if not rec.get("stallFlagged") and now - rec.get("revisionSince", now) >= stall:
        rec.update(state="stall", stallFlagged=True)
    return rec


def cmd_wait(a):
    run = Path(a.run_dir)
    lanes = a.lanes.split(",")
    status = load(run / "status.json", {})
    while True:
        now = time.time()
        events = []
        for lane in lanes:
            prior = status.get(lane, {})
            if prior.get("state") in TERMINAL:
                continue
            rec = classify(run, lane, prior, now, a.grace_sec, a.stall_min * 60)
            if rec["state"] != prior.get("state") and rec["state"] != "running":
                events.append({"lane": lane, **{k: rec[k] for k in ("state", "reason") if k in rec}})
            if rec["state"] == "stall":
                rec["state"] = "running"  # flagged once; keep waiting on it
            status[lane] = rec
        save(run / "status.json", status)
        remaining = [l for l in lanes if status[l].get("state") not in TERMINAL]
        if events or not remaining or a.once:
            print(json.dumps({"events": events, "remaining": remaining,
                              "states": {l: status[l].get("state") for l in lanes}}))
            return
        time.sleep(a.poll_sec)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("open"); o.add_argument("--run-dir", required=True)
    o.add_argument("--label", required=True); o.add_argument("--lanes", required=True)
    l = sub.add_parser("launch"); l.add_argument("--run-dir", required=True)
    l.add_argument("--lane", required=True); l.add_argument("--model", default="sonnet")
    c = sub.add_parser("claims"); c.add_argument("--run-dir", required=True)
    c.add_argument("--cap", type=int, required=True); c.add_argument("--lanes", required=True)
    w = sub.add_parser("wait"); w.add_argument("--run-dir", required=True)
    w.add_argument("--lanes", required=True); w.add_argument("--once", action="store_true")
    w.add_argument("--grace-sec", type=int, default=60); w.add_argument("--stall-min", type=int, default=15)
    w.add_argument("--poll-sec", type=int, default=20)
    a = p.parse_args()
    if a.cmd == "claims" and a.cap < 1:
        p.error("--cap must be a positive integer")
    try:
        {"open": cmd_open, "launch": cmd_launch, "claims": cmd_claims, "wait": cmd_wait}[a.cmd](a)
    except RuntimeError as e:
        print(f"lanes: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
