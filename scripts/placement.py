#!/usr/bin/env python3
"""placement.py — the facts behind /concurrency's "where does this run" step.

Approach: placement has a judgment half (job size, what Alex is doing) and a fact half
(which machine is up, whose login is live, how much of each account's usage is left).
The fact half has one right answer, so it lives here (CLAUDE.md §3.6.1); /concurrency §5.2
reads it and adds the judgment. Usage comes from dev-workbench's herdr-usage merged file
(`~/.cache/herdr-usage/merged.json`, schema 1), which already merges both machines'
fetches; machines and accounts come from dev-workbench's accounts.tsv. Usage is
account-wide, so it is the same on every machine; what differs per machine is whether
it is reachable and whether the account's login there is live.

  recommend   every machine x account x seat (opus = the account's Claude windows,
              codex = its OpenAI windows), ranked. A window that is inferred (its reset
              passed since the last fetch) or older than --max-age is not evidence of
              headroom: it counts as unknown and says why. An unreachable machine, a
              dead login or an exhausted seat (0% left) is listed, never recommended.
              Ties go to the account's home machine (accounts.tsv default=yes).
  check-base  box placement needs the lane's base commit on origin, because the box
              builds from its own clone (scope 3 CODEX-1). Exit 1 = refuse, with why.
  fetch-back  bring a finished box lane's branch to this clone by fetching it from the
              box over ssh — workers never push. Reads the fetched ref back.

Usage:  placement.py recommend [--seat opus|codex|all] [--merged F] [--accounts F]
                              [--max-age S] [--timeout S] [--json]
        placement.py check-base --repo DIR [--base REV]
        placement.py fetch-back --repo DIR --machine HOST --branch B [--remote-url URL]
Exit:   0 ok · 1 check-base refused / fetch-back failed · 2 usage · 3 could not check
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time

MERGED = os.path.expanduser("~/.cache/herdr-usage/merged.json")
ACCOUNTS = os.environ.get("WORKBENCH_ACCOUNTS") or os.path.expanduser(
    "~/Projects/dev-workbench/config/accounts/accounts.tsv")
SEATS = {"opus": ("claude", "claude-{key} auth status --json"),
         "codex": ("oai", "codex-{key} login status")}


def sh(cmd, timeout):
    """Run cmd (list); (rc, stdout, stderr). A timeout or missing binary is rc 124 / 127."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", ""
    except FileNotFoundError:
        return 127, "", ""


def this_host():
    rc, out, _ = sh(["hostname", "-s"], 5)        # same key the accounts map and launchers use
    return (out.strip() if rc == 0 and out.strip() else socket.gethostname().split(".")[0]).lower()


def read_accounts(path):
    """accounts.tsv -> list of {host, key, display, default}."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 7 or f[1] == "key":
                continue
            rows.append({"host": f[0], "key": f[1], "display": f[2], "default": f[6] == "yes"})
    return rows


def reachable(host, local, timeout):
    if host == local:
        return True, "local"
    rc, _, _ = sh(["herdr", "--machine", host, "workspace", "list"], timeout)
    return rc == 0, "herdr server answers" if rc == 0 else f"herdr --machine {host} failed (rc {rc})"


def login_live(host, local, key, seat, timeout):
    cmd = SEATS[seat][1].format(key=key)
    argv = ["sh", "-c", cmd] if host == local else \
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host, cmd]
    rc, out, err = sh(argv, timeout)
    if seat == "opus":
        try:
            ok = rc == 0 and json.loads(out).get("loggedIn") is True
        except ValueError:
            ok = False
    else:
        ok = rc == 0 and "logged in" in (out + err).lower()   # codex prints its status on stderr
    return ok, "login live" if ok else f"{cmd.split()[0]} not logged in (rc {rc})"


def headroom(windows, now, max_age):
    """(percent left or None, used 5h, used 7d, notes) from one provider's windows."""
    notes, used = [], {}
    for w in ("5h", "7d"):
        v = (windows or {}).get(w)
        if not v:
            notes.append(f"{w} no data")
            continue
        used[w] = v.get("used_pct")
        if v.get("inferred"):
            notes.append(f"{w} inferred (reset passed since the last fetch)")
        elif now - (v.get("observed_at") or 0) > max_age:
            notes.append(f"{w} stale ({(now - (v.get('observed_at') or 0)) // 60} min old)")
    known = not notes and all(isinstance(u, (int, float)) for u in used.values())
    left = round(100 - max(used.values())) if known else None
    return left, used.get("5h"), used.get("7d"), notes


def recommend(a):
    try:
        rows = read_accounts(a.accounts)
    except OSError as exc:
        print(f"placement: cannot read accounts map {a.accounts}: {exc.strerror}", file=sys.stderr)
        return 3
    merged, why = {}, ""
    try:
        with open(a.merged, encoding="utf-8") as fh:
            merged = json.load(fh)
        if merged.get("schema") != 1:
            why, merged = f"unknown merged.json schema {merged.get('schema')!r}", {}
    except (OSError, ValueError) as exc:
        why = f"no usable merged.json ({exc})"
    now, local = int(time.time()), this_host()
    seats = list(SEATS) if a.seat == "all" else [a.seat]
    up = {h: reachable(h, local, a.timeout) for h in sorted({r["host"] for r in rows})}
    out = []
    for r in rows:
        for seat in seats:
            prov = ((merged.get("accounts") or {}).get(r["key"]) or {}).get(SEATS[seat][0]) or {}
            left, u5, u7, notes = headroom(prov.get("windows"), now, a.max_age)
            if why:
                notes = [why]
            ok_up, up_note = up[r["host"]]
            if ok_up:
                ok_login, login_note = login_live(r["host"], local, r["key"], seat, a.timeout)
            else:
                ok_login, login_note = False, "login not checked (unreachable)"
            out.append({"machine": r["host"], "local": r["host"] == local, "account": r["key"],
                        "display": r["display"], "seat": seat, "home": r["default"],
                        "reachable": ok_up, "login": ok_login,
                        "eligible": ok_up and ok_login, "headroom": left,
                        "used_5h": u5, "used_7d": u7,
                        "notes": notes + ([] if ok_up else [up_note]) + ([] if ok_login else [login_note])})
    # eligible first; an exhausted seat (0% left) last among them, below unknown headroom
    out.sort(key=lambda c: (not c["eligible"], c["headroom"] == 0, c["headroom"] is None,
                            -(c["headroom"] or 0), not c["home"], c["machine"], c["account"], c["seat"]))
    pick = {}
    for c in out:
        if c["eligible"] and c["headroom"] != 0 and c["seat"] not in pick:
            pick[c["seat"]] = c
    if a.json:
        print(json.dumps({"generated_at": now, "local": local, "candidates": out,
                          "recommended": pick}, indent=2))
        return 0
    fmt = "{:<14} {:<13} {:<6} {:<4} {:>8} {:>5} {:>5}  {}"
    print(fmt.format("machine", "account", "seat", "ok", "headroom", "5h", "7d", "notes"))
    for c in out:
        show = lambda v: "-" if v is None else f"{round(v)}%"
        print(fmt.format(c["machine"] + (" *" if c["local"] else ""), c["display"], c["seat"],
                         "yes" if c["eligible"] else "no",
                         "?" if c["headroom"] is None else f"{c['headroom']}%",
                         show(c["used_5h"]), show(c["used_7d"]), "; ".join(c["notes"])))
    for seat in seats:
        c = pick.get(seat)
        print(f"recommended {seat}: " + (f"{c['machine']} as {c['display']}"
              + ("" if c["headroom"] is not None else " (headroom unknown — see notes)")
              if c else "none — no reachable machine with a live login and usage left"))
    return 0


def git(repo, *args, timeout=60):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=timeout)


def check_base(a):
    f = git(a.repo, "fetch", "--quiet", "origin")
    if f.returncode:
        print(f"cannot check: git fetch origin failed in {a.repo}: {f.stderr.strip()}")
        return 3
    sha = git(a.repo, "rev-parse", "--verify", f"{a.base}^{{commit}}")
    if sha.returncode:
        print(f"cannot check: {a.base!r} is not a commit in {a.repo}")
        return 3
    sha = sha.stdout.strip()
    refs = git(a.repo, "branch", "-r", "--contains", sha).stdout.split()
    refs = [r for r in refs if r.startswith("origin/") and r != "->"]
    if refs:
        print(f"ok: {sha[:7]} is on origin ({', '.join(refs[:3])})")
        return 0
    print(f"refuse: {sha[:7]} ({a.base}) is not on origin — the box builds from its own clone "
          f"and cannot see it. Push it (Alex's go) or place this lane on the local machine.")
    return 1


def fetch_back(a):
    repo = os.path.abspath(a.repo)
    rel = os.path.relpath(repo, os.path.expanduser("~"))
    url = a.remote_url or f"{a.machine}:{rel}"
    f = git(repo, "fetch", url, f"refs/heads/{a.branch}:refs/heads/{a.branch}", timeout=120)
    if f.returncode:
        print(f"failed: git fetch {url} {a.branch}: {f.stderr.strip().splitlines()[-1:]}")
        return 1
    want = subprocess.run(["git", "ls-remote", url, f"refs/heads/{a.branch}"],
                          capture_output=True, text=True, timeout=60).stdout.split()
    have = git(repo, "rev-parse", "--verify", f"refs/heads/{a.branch}").stdout.strip()
    if not want or want[0] != have:
        print(f"failed: {a.branch} here is {have[:7] or 'missing'}, on {a.machine} "
              f"{want[0][:7] if want else 'missing'}")
        return 1
    print(f"fetched {a.branch} {have[:7]} from {a.machine} into {repo}")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="Facts for /concurrency placement.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("recommend")
    r.add_argument("--seat", choices=["opus", "codex", "all"], default="all")
    r.add_argument("--merged", default=MERGED)
    r.add_argument("--accounts", default=ACCOUNTS)
    r.add_argument("--max-age", type=int, default=900)
    r.add_argument("--timeout", type=int, default=15)
    r.add_argument("--json", action="store_true")
    c = sub.add_parser("check-base")
    c.add_argument("--repo", required=True)
    c.add_argument("--base", default="HEAD")
    b = sub.add_parser("fetch-back")
    b.add_argument("--repo", required=True)
    b.add_argument("--machine", required=True)
    b.add_argument("--branch", required=True)
    b.add_argument("--remote-url")
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    return {"recommend": recommend, "check-base": check_base, "fetch-back": fetch_back}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
