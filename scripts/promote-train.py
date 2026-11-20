#!/usr/bin/env python3
"""promote-train.py — promote a set of repos develop -> staging, one at a time, and prove each deploy.

Approach (Alex, 2026-11-20: promotion trains should not need babysitting): for each repo, in the
order given (emitters before consumers), it opens — or reuses — the `develop -> staging` PR, waits
for that PR's checks, records the image tag the staging host runs, merges, waits for the staging CD
run of the merge commit, and reads the host again: the repo is promoted only when the running tag
changed to the merge commit's `sha-<short>`. Any step that fails stops the train with the repo and
the reason; repos already promoted stay promoted. It never touches `main` and never deploys prod —
Padma prod follows Kalpa staging on its own schedule (infra #603), and prod is Alex's gate.

Usage:
  promote-train.py --org ORG --host INSTANCE_ID --label TEXT REPO[=CONTAINER] ...
    REPO=CONTAINER   the container name to read on the host (default: REPO without `wellmed-`)
    --dry-run        print what each repo would do; open, merge and deploy nothing
    --log FILE       append one JSON line per repo outcome (default ~/.cache/promote-train.jsonl)
Output: one line per step; a final `TRAIN DONE` or `TRAIN STOPPED <repo>: <reason>`.
Exit:   0 every repo promoted or already in step · 1 stopped · 2 usage
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

CD_NAMES = re.compile(r"(?i)^(cd|deploy)")


def sh(cmd, timeout=600):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def gh_json(args):
    rc, out, err = sh(["gh", *args])
    if rc != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])}: {err or out}")
    return json.loads(out or "null")


def host_tag(host, container):
    """The image tag the host runs for `container` (blue/green: whichever is up), or ''."""
    script = f"docker ps --format '{{{{.Names}}}} {{{{.Image}}}}' | grep -E '^{container}(-blue|-green)? ' | head -1"
    rc, cid, err = sh(["aws", "ssm", "send-command", "--instance-ids", host, "--document-name",
                       "AWS-RunShellScript", "--parameters", json.dumps({"commands": [script]}),
                       "--query", "Command.CommandId", "--output", "text"])
    if rc != 0:
        raise RuntimeError(f"ssm send-command: {err}")
    for _ in range(20):
        time.sleep(3)
        rc, out, _ = sh(["aws", "ssm", "get-command-invocation", "--command-id", cid, "--instance-id", host,
                         "--query", "[Status,StandardOutputContent]", "--output", "json"])
        if rc == 0:
            status, text = json.loads(out)
            if status in ("Success", "Failed", "Cancelled", "TimedOut"):
                m = re.search(r":(sha-[0-9a-f]+)", text)
                return m.group(1) if m else ""
    raise RuntimeError("ssm read of the host did not finish")


def failed_runs(rows):
    """The Actions run ids behind the failed check rows, from each row's link (…/runs/<id>/job/<id>)."""
    ids = []
    for r in rows:
        m = re.search(r"/actions/runs/(\d+)", r.get("link") or "")
        if r["state"] not in ("SUCCESS", "SKIPPED", "NEUTRAL") and m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def wait_checks(org, repo, pr, retries=1):
    """Watch the PR's checks; a failed check gets its failed jobs re-run once before the train stops
    (WellMed 231: backbone's golangci-lint timed out with 0 issues on the staging PR and stopped it)."""
    full = f"{org}/{repo}"
    while True:
        sh(["gh", "pr", "checks", str(pr), "-R", full, "--watch", "--interval", "30"], timeout=3600)
        rows = gh_json(["pr", "checks", str(pr), "-R", full, "--json", "name,state,link"]) or []
        bad = [r["name"] for r in rows if r["state"] not in ("SUCCESS", "SKIPPED", "NEUTRAL")]
        runs = failed_runs(rows)
        if not bad or retries <= 0 or not runs:
            return bad
        retries -= 1
        print(f"{repo}: PR #{pr} checks not green ({', '.join(bad)}); re-running the failed jobs once")
        for run in runs:
            sh(["gh", "run", "rerun", run, "-R", full, "--failed"])
        time.sleep(30)


def wait_cd(org, repo, sha):
    """The CD run for the merge commit on staging, watched to its end. None if none ever starts."""
    for _ in range(40):
        runs = gh_json(["run", "list", "-R", f"{org}/{repo}", "--branch", "staging", "-L", "10",
                        "--json", "databaseId,workflowName,headSha"]) or []
        run = next((r for r in runs if r["headSha"] == sha and CD_NAMES.search(r["workflowName"])), None)
        if run:
            rc, _, _ = sh(["gh", "run", "watch", str(run["databaseId"]), "-R", f"{org}/{repo}", "--exit-status"],
                          timeout=3600)
            return run["databaseId"], rc == 0
        time.sleep(15)
    return None, False


def promote(a, repo, container, log):
    full = f"{a.org}/{repo}"
    cmp = gh_json(["api", f"repos/{full}/compare/staging...develop", "--jq", "{ahead: .ahead_by}"])
    if not cmp["ahead"]:
        print(f"{repo}: staging already holds develop")
        return "in step", None
    print(f"{repo}: develop is {cmp['ahead']} commit(s) ahead of staging")
    if a.dry_run:
        return "would promote", None
    prs = gh_json(["pr", "list", "-R", full, "--base", "staging", "--head", "develop", "--state", "open",
                   "--json", "number"]) or []
    if prs:
        pr = prs[0]["number"]
        print(f"{repo}: reusing open PR #{pr}")
    else:
        rc, out, err = sh(["gh", "pr", "create", "-R", full, "--base", "staging", "--head", "develop",
                           "--title", f"chore(promote): develop → staging ({a.label})",
                           "--body", f"Promotion train: {a.label}. develop → staging; Padma prod follows staging "
                                     "on its own schedule.\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)"])
        if rc != 0:
            return "stopped", f"PR create failed: {err}"
        pr = int(out.rstrip("/").rsplit("/", 1)[-1])
        print(f"{repo}: opened PR #{pr}")
    time.sleep(20)
    bad = wait_checks(a.org, repo, pr)
    if bad:
        return "stopped", f"PR #{pr} checks not green: {', '.join(bad)}"
    before = host_tag(a.host, container)
    print(f"{repo}: staging runs {before or 'nothing'} before the merge")
    rc, _, err = sh(["gh", "pr", "merge", str(pr), "-R", full, "--merge", "--admin"])
    if rc != 0:
        return "stopped", f"merge of PR #{pr} failed: {err}"
    sha = gh_json(["pr", "view", str(pr), "-R", full, "--json", "mergeCommit", "--jq", "{s: .mergeCommit.oid}"])["s"]
    print(f"{repo}: merged PR #{pr} as {sha[:8]}")
    run, ok = wait_cd(a.org, repo, sha)
    if not ok:
        return "stopped", f"staging CD {'run ' + str(run) + ' failed' if run else 'never started'} for {sha[:8]}"
    after = host_tag(a.host, container)
    want = f"sha-{sha[:7]}"
    if not after.startswith(want):
        return "stopped", f"staging still runs {after or 'nothing'} after CD run {run}, want {want}"
    print(f"{repo}: staging runs {after} (was {before or 'nothing'})")
    with open(log, "a") as fh:
        fh.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "label": a.label, "repo": repo, "pr": pr,
                             "merge": sha, "before": before, "after": after}) + "\n")
    return "promoted", None


def main(argv):
    sys.stdout.reconfigure(line_buffering=True)  # a background run's log shows each step as it happens
    ap = argparse.ArgumentParser(description="Promote repos develop -> staging and prove each deploy.")
    ap.add_argument("--org", required=True)
    ap.add_argument("--host", required=True, help="the staging app host's instance id (SSM)")
    ap.add_argument("--label", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--log", default=os.path.expanduser("~/.cache/promote-train.jsonl"))
    ap.add_argument("repos", nargs="+")
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    os.makedirs(os.path.dirname(a.log), exist_ok=True)
    for spec in a.repos:
        repo, _, container = spec.partition("=")
        container = container or repo.removeprefix("wellmed-")
        try:
            state, why = promote(a, repo, container, a.log)
        except (RuntimeError, subprocess.TimeoutExpired, ValueError, KeyError) as exc:
            state, why = "stopped", str(exc)
        if state == "stopped":
            print(f"TRAIN STOPPED {repo}: {why}")
            return 1
    print("TRAIN DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
