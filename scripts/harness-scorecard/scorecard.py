#!/usr/bin/env python3
"""Harness scorecard — the baseline tables (scope 10, baseline 2026-10-25) re-run on demand.

Usage:
  scorecard.py pull [--logs DIR] [--host HOST]
  scorecard.py run  [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--logs DIR] [--store DIR]
                    [--no-sessions] [--no-git] [--no-save]

Approach: `pull` refreshes the log cache, `run` analyses it. The cache layout is the baseline's:
`mba/` holds symlinks to this machine's `~/.claude/projects` and `~/.codex/sessions`;
`homelab/` is copied from homelab2026 over ssh; `mba-plans/` and `homelab-plans/` hold every
`plans/**/artifacts/**` file under `~/Projects` and `~/.herdr/worktrees` on each host. Copies are
never pruned (no `--delete`): worktrees are removed after merge, and their review logs live on
only here. The pull runs from the MBA only (MBA → homelab), reads homelab only (rsync's sender
side), and reads the destination back before reporting success.

`run` prints §1 volume, §2 activity cost, §3 reviewers and §3.1–§3.3 review rounds (rounds per
lineage, review.py's own `rounds()`, once per unit), the effort trial, and §4 attention with
pasted queue answers tagged, each with a Δ column against the previous stored run. The numbers
are saved as JSON under `--store` (default `~/.cache/harness-scorecard/`) — aggregates only,
never prompt or transcript text: logs can carry patient data.

Exit codes: 0 ok; 1 a pull/run step failed (named on stderr); 2 usage.
"""

import argparse
import datetime as dt
import os
import platform
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import review_loop  # noqa: E402
import sessions  # noqa: E402
import store  # noqa: E402

HOME = os.path.expanduser("~")
LOGS = os.path.join(HOME, ".cache", "harness-logs")
STORE = os.path.join(HOME, ".cache", "harness-scorecard")
PULLED = ".pulled"  # the cache's last successful pull time, read by `run`
RSYNC_KEEP = ["--exclude=.git/", "--exclude=node_modules/", "--exclude=vendor/"]
PLANS_FILTER = ["--include=*/", "--include=**/plans/**/artifacts/**", "--exclude=*", "--prune-empty-dirs"]
PLAN_SOURCES = ("Projects", ".herdr/worktrees")


def die(msg):
    print(f"[FAIL] {msg}", file=sys.stderr)
    return 1


def day(s, end=False):
    d = dt.datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
    return (d + dt.timedelta(days=1) - dt.timedelta(seconds=1)).timestamp() if end else d.timestamp()


def count_files(root, suffix):
    n = 0
    for _, _, fs in os.walk(root, followlinks=True):
        n += sum(1 for f in fs if f.endswith(suffix))
    return n


def rsync(src, dst, extra=()):
    os.makedirs(dst, exist_ok=True)
    p = subprocess.run(["rsync", "-a", *RSYNC_KEEP, *extra, src, dst], capture_output=True, text=True)
    # 24 = source files vanished mid-copy (a live session rotated a file): the rest copied
    if p.returncode not in (0, 24):
        raise RuntimeError(f"rsync {src} → {dst} exit {p.returncode}: {p.stderr.strip()[-300:]}")


def cmd_pull(a):
    if platform.system() != "Darwin":
        return die("pull runs on the MBA only (MBA → homelab); this host is not macOS")
    logs = a.logs
    # MBA sessions: symlinks, as the baseline cache has them
    for name, target in (("claude-projects", os.path.join(HOME, ".claude", "projects")),
                         ("codex-sessions", os.path.join(HOME, ".codex", "sessions"))):
        link = os.path.join(logs, "mba", name)
        os.makedirs(os.path.dirname(link), exist_ok=True)
        if os.path.islink(link):
            if os.path.realpath(link) != os.path.realpath(target):
                return die(f"{link} points at {os.readlink(link)}, expected {target} — fix by hand, not overwritten")
        elif os.path.exists(link):
            return die(f"{link} exists and is not a symlink — fix by hand, not overwritten")
        else:
            os.symlink(target, link)
    try:
        for src in PLAN_SOURCES:
            if os.path.isdir(os.path.join(HOME, src)):
                rsync(os.path.join(HOME, src) + "/", os.path.join(logs, "mba-plans", src) + "/", PLANS_FILTER)
        # homelab: one read-only probe for which sources exist, then rsync pulls (sender side only)
        probe = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", a.host,
                                "for d in .claude/projects .codex/sessions " + " ".join(PLAN_SOURCES)
                                + "; do [ -d \"$d\" ] && echo \"$d\"; done"],
                               capture_output=True, text=True, timeout=60)
        if probe.returncode != 0:
            return die(f"ssh {a.host} unreachable (exit {probe.returncode}): {probe.stderr.strip()[-200:]} — cache not refreshed")
        have = set(probe.stdout.split())
        for d in (".claude/projects", ".codex/sessions"):
            if d not in have:
                return die(f"{a.host}:~/{d} missing — cache not refreshed")
            rsync(f"{a.host}:{d}/", os.path.join(logs, "homelab", d) + "/")
        for src in PLAN_SOURCES:
            if src in have:
                rsync(f"{a.host}:{src}/", os.path.join(logs, "homelab-plans", src) + "/", PLANS_FILTER)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        return die(str(exc))
    # read the destination back: a pull that copied nothing is a failure, whatever rsync said
    counts = {"mba sessions": count_files(os.path.join(logs, "mba", "claude-projects"), ".jsonl"),
              "homelab sessions": count_files(os.path.join(logs, "homelab", ".claude", "projects"), ".jsonl"),
              "review logs": sum(1 for p in review_loop.glob.glob(os.path.join(logs, "*-plans", "**", "review-*.jsonl"),
                                                                   recursive=True))}
    empty = [k for k, v in counts.items() if not v]
    if empty:
        return die(f"pull finished but {', '.join(empty)} read back empty under {logs}")
    with open(os.path.join(logs, PULLED), "w") as fh:
        fh.write(dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + "\n")
    print("pulled: " + " · ".join(f"{k} {v}" for k, v in counts.items()))
    return 0


def cmd_run(a):
    until = day(a.until, end=True) if a.until else time.time()
    since = day(a.since) if a.since else until - 21 * 86400
    if since >= until:
        return die("--since must be before --until")
    try:
        with open(os.path.join(a.logs, PULLED)) as fh:
            pulled = fh.read().strip()
    except OSError:
        pulled = "unknown (no .pulled stamp — run `pull`)"
    units, lstats = review_loop.load_logs(a.logs, until)
    if not units:
        return die(f"no review logs under {a.logs}/*-plans — run `pull` first")
    print(f"[scorecard] window {fmt(since)} → {fmt(until)} · logs pulled {pulled} · {len(units)} units", file=sys.stderr)
    rv = review_loop.load_review_module()
    loop = review_loop.analyze(units, rv, since=since, git=review_loop.Git(rv.vl.PROJECTS, enabled=not a.no_git))
    tables = dict()
    if not a.no_sessions:
        tables.update(sessions.tables(sessions.scan(a.logs, since, until)))
    tables.update(loop["tables"])
    result = {"window": {"since": fmt(since), "until": fmt(until)}, "logs_pulled": pulled,
              "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "notes": {**loop["notes"], "review_logs": lstats}, "tables": tables}
    ppath, prev = store.previous(a.store)
    d = store.delta(tables, prev["tables"]) if prev else None
    print(f"# Harness scorecard — {result['window']['since']} → {result['window']['until']}\n")
    if ppath and prev:
        print(f"Δ against {os.path.basename(ppath)} (window {prev['window']['since']} → {prev['window']['until']})\n")
    elif ppath:
        print(f"[WARN] previous run {ppath} unreadable — no Δ this run\n")
    else:
        print("No previous run — no Δ.\n")
    n = loop["notes"]
    if n["failed_units"]:
        print(f"[WARN] {len(n['failed_units'])} unit(s) failed lineage resolution and are NOT counted: "
              + ", ".join(n["failed_units"][:10]) + "\n")
    for name, t in tables.items():
        print(store.render(name, t, d.get(name) if d is not None else None) + "\n")
    print(f"effort tiers (trial, codex): {n['trial_effort_tiers'] or 'none'} · stamped-round mismatches "
          f"{n['stamped_round_mismatches']} · rounds() calls {n['rounds_calls']} (one per unit)")
    if not a.no_save:
        try:
            print(f"saved {store.save(a.store, result)}")
        except (OSError, ValueError) as exc:
            return die(f"could not save this run under {a.store}: {exc}")
    return 0


def fmt(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d %H:%M")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Harness scorecard (scope 10)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pull", help="refresh the log cache (MBA → homelab, read-only)")
    p.add_argument("--logs", default=LOGS)
    p.add_argument("--host", default="homelab2026")
    r = sub.add_parser("run", help="run the analyses and print the tables with a Δ")
    r.add_argument("--since", help="YYYY-MM-DD (UTC, inclusive); default until − 21 days")
    r.add_argument("--until", help="YYYY-MM-DD (UTC, inclusive); default now")
    r.add_argument("--logs", default=LOGS)
    r.add_argument("--store", default=STORE)
    r.add_argument("--no-sessions", action="store_true", help="review tables only (skip the transcript scan)")
    r.add_argument("--no-git", action="store_true", help="skip §3.2/§3.3's git diff analyses")
    r.add_argument("--no-save", action="store_true", help="print only; do not store this run")
    a = ap.parse_args(argv)
    try:
        return {"pull": cmd_pull, "run": cmd_run}[a.cmd](a)
    except ValueError as exc:
        print(f"[USAGE] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
