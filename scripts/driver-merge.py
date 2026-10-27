#!/usr/bin/env python3
"""driver-merge.py — may the /plan driver merge its own PR, and if so merge it (scope 10 §4.3,
plan 10.3 tasks 3.1 + 3.2).

Approach: every condition is evaluated and printed, one line each, then the verdict. A PR is
eligible only when ALL hold:
  * driver   — the caller is a driver (packet.py's own is_driver: --driver or
               $HERDR_AGENT_NAME=driver). `check` reports it; `merge` refuses a lane outright
  * pr       — open, not a draft
  * base     — `main` for kalpa-docs / pmg-docs / ai-skills, `develop` for every other repo.
               Any other base is refused and never touched: a code repo's `main` is prod, and
               prod stays behind prod-merge-gate.py
  * checks   — every check finished green or skipped/neutral AND at least one real run is
               green. An empty list, or skipped/neutral only, is vacuous: WellMed staging PRs
               get zero checks, so "nothing failed" is not "green"
  * verdict  — the unit's latest review of this repo is SHIP, or an `acceptance` follows it
               (review.py accept); that review saw the PR head (later commits may touch only
               plans/); and verdict-gate.py --blocking reads `pass`. A reviewer other than codex (fallback /
               lean) still merges, flagged; a `none` reviewer is no review
  * floor    — door.py classifies merge-base..head with no floor path
  * mergeable — mergeStateStatus CLEAN / HAS_HOOKS merges; BLOCKED merges with --admin (branch
               protection is what blocks once every condition above holds — what Alex does by
               hand); anything else (DIRTY, BEHIND, UNSTABLE, DRAFT, UNKNOWN after retries) refuses
`merge` on an eligible PR runs `gh pr merge --match-head-commit <head>` (never --auto: GitHub
auto-merge stays off), reads the PR back as MERGED with its merge commit, then posts
`packet.py event --kind merged` with repo, PR and merge sha (task 3.2). On any failed condition
it writes a packet instead — one-way with the matched paths for a floor hit, two-way otherwise —
and prints why.

Failure stances (fail closed: every one of these is "no merge" with the reason):
  * gh error, unparseable gh JSON, unknown check type/state, mergeStateStatus still UNKNOWN
  * origin remote unreadable, git error, PR commits not fetchable (door.py then fails closed)
  * review log missing / malformed, no review of this repo in the unit, verdict-gate exit != 0,
    a verdict other than `pass` (advisory included), or unparseable output
  * merge reported success but the read-back is not MERGED -> not merged, packet written
  * packet.py fails to write the refusal packet -> still no merge; the reason is printed
  * merged but the `merged` event did not write -> exit 4: the merge stands (it landed and was
    read back), the ticker gap is reported rather than hidden

Usage:  driver-merge.py check|merge --repo PATH --pr N --scope DIR --unit N.P
                        [--driver] [--method squash|merge|rebase]
Output: one `[ok]`/`[FAIL]` line per condition, then `verdict: ELIGIBLE|REFUSED …`;
        merge adds `MERGED <owner/repo>#N <sha>` + the EVENT line, or the PACKET + `NOT MERGED`
Exit:   0 eligible (check) / merged and event written (merge) · 1 refused / not merged ·
        2 usage · 4 merged, event not written
"""
import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PACKET = os.path.join(HERE, "packet.py")
VERDICT_GATE = os.path.join(HERE, "verdict-gate.py")
REVIEW_PY = os.path.join(os.path.dirname(HERE), "review", "scripts", "review.py")
DOCS_MAIN = {"kalpa-docs", "pmg-docs", "ai-skills"}
INERT = {"SKIPPED", "NEUTRAL"}
MERGE_OK = {"CLEAN", "HAS_HOOKS"}
FIELDS = ("number,state,isDraft,baseRefName,headRefName,baseRefOid,headRefOid,"
          "mergeStateStatus,url,statusCheckRollup")
UNKNOWN_RETRIES, UNKNOWN_SLEEP = 3, 2.0
EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_NO_EVENT = 0, 1, 2, 4


class Refuse(Exception):
    """A condition that cannot even be evaluated; the run stops with this reason."""


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sh(cmd, cwd=None, timeout=120):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return 127, "", str(e)
    return p.returncode, p.stdout, p.stderr


def gh(*args):
    """The one gh entry point (tests replace it). Returns (rc, stdout, stderr)."""
    return sh(["gh", *args])


def git(repo, *args):
    return sh(["git", "-C", repo, *args], timeout=60)


def first_err(err, rc):
    return next((x.strip() for x in reversed(err.splitlines()) if x.strip()), f"exit {rc}")[:200]


def repo_slug(repo):
    """owner/name from origin's URL, whatever the host alias (git@github-x:Owner/name.git)."""
    rc, out, err = git(repo, "remote", "get-url", "origin")
    if rc:
        raise Refuse(f"origin remote unreadable in {repo}: {first_err(err, rc)}")
    m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", out.strip())
    if not m:
        raise Refuse(f"origin URL {out.strip()!r} does not name owner/repo")
    return f"{m.group(1)}/{m.group(2)}", m.group(2)


def pr_view(slug, n, fields=FIELDS):
    rc, out, err = gh("pr", "view", str(n), "-R", slug, "--json", fields)
    if rc:
        raise Refuse(f"gh pr view {slug}#{n} failed: {first_err(err, rc)}")
    try:
        doc = json.loads(out)
    except ValueError:
        raise Refuse(f"gh pr view {slug}#{n}: output is not JSON")
    if not isinstance(doc, dict):
        raise Refuse(f"gh pr view {slug}#{n}: output is not an object")
    return doc


def pr_view_settled(slug, n):
    """GitHub computes mergeStateStatus lazily: UNKNOWN on a first read is normal. Re-read a
    few times; still UNKNOWN is a refusal (the mergeable condition fails), never a guess."""
    doc = pr_view(slug, n)
    for _ in range(UNKNOWN_RETRIES - 1):
        if doc.get("mergeStateStatus") != "UNKNOWN" or doc.get("state") != "OPEN":
            break
        time.sleep(UNKNOWN_SLEEP)
        doc = pr_view(slug, n)
    return doc


# ---------- conditions: each returns (ok, detail) ----------------------------------

def cond_pr(doc):
    if doc.get("state") != "OPEN":
        return False, f"PR is {doc.get('state') or 'in an unknown state'}, not OPEN"
    if doc.get("isDraft") is not False:
        return False, "PR is a draft" if doc.get("isDraft") else "draft flag unreadable"
    return True, "open, not a draft"


def cond_base(name, base):
    want = "main" if name.lower() in DOCS_MAIN else "develop"
    if base == want:
        return True, f"{base} ({'docs/skills repo' if want == 'main' else 'code repo'})"
    if base == "main":
        return False, (f"base `main` on code repo {name} is prod — refused, never touched; "
                       "prod merges go through prod-merge-gate.py")
    return False, f"base `{base}` is not this repo's merge target `{want}`"


def cond_checks(rollup):
    if not isinstance(rollup, list):
        return False, "check list unreadable"
    real, inert, bad = 0, 0, []
    for c in rollup:
        if not isinstance(c, dict):
            bad.append("unreadable check entry")
            continue
        kind, name = c.get("__typename"), c.get("name") or c.get("context") or "?"
        if kind == "CheckRun":
            if c.get("status") != "COMPLETED":
                bad.append(f"{name}: {c.get('status') or 'no status'}")
                continue
            res = str(c.get("conclusion") or "").upper()
        elif kind == "StatusContext":
            res = str(c.get("state") or "").upper()
        else:
            bad.append(f"{name}: unknown check type {kind!r}")
            continue
        if res == "SUCCESS":
            real += 1
        elif res in INERT:
            inert += 1
        else:
            bad.append(f"{name}: {res or 'no result'}")
    if bad:
        return False, "not green — " + "; ".join(bad[:5]) + (f" (+{len(bad) - 5})" if len(bad) > 5 else "")
    if not real:
        return False, ("vacuous green — no checks reported" if not inert else
                       f"vacuous green — {inert} check(s), all skipped/neutral, none ran")
    return True, f"{real} real run(s) green" + (f", {inert} skipped/neutral" if inert else "")


def cond_mergeable(state):
    if state in MERGE_OK:
        return True, state, False
    if state == "BLOCKED":
        return True, "BLOCKED by branch protection — merges with --admin when every other condition holds", True
    return False, f"mergeStateStatus {state or 'missing'} — not mergeable as is", False


def ensure_commits(repo, n, base_ref, shas):
    """Fetch the PR head and base when they are not local. A failed fetch is not fatal here:
    door.py and the coverage check fail closed on an unresolved sha."""
    missing = [s for s in shas if git(repo, "cat-file", "-e", f"{s}^{{commit}}")[0]]
    if missing:
        git(repo, "fetch", "--quiet", "--no-tags", "origin", f"pull/{n}/head", base_ref)


def cond_floor(repo, base_oid, head_oid):
    """(ok, detail, hits, range). Fails closed: no merge-base is a one-way result."""
    rc, out, err = git(repo, "merge-base", base_oid, head_oid)
    if rc or not out.strip():
        return False, f"fail-closed: no merge-base for {base_oid[:12]}..{head_oid[:12]} ({first_err(err, rc)})", [], None
    rng = f"{out.strip()}..{head_oid}"
    res = _load("door", os.path.join(HERE, "door.py")).classify(repo, rng)
    if res.get("door") == "two-way":
        return True, res.get("reason", "no floor path touched"), [], rng
    hits = res.get("paths") or []
    shown = ", ".join(f"{h['path']} ({h['pattern']})" for h in hits[:6]) + (f" (+{len(hits) - 6})" if len(hits) > 6 else "")
    return False, f"{res.get('reason')}" + (f": {shown}" if shown else ""), hits, rng


def run_gate(scope, unit):
    """verdict-gate.py in --blocking mode, and its JSON verdict must be `pass` with exit 0.
    Its exit code alone means "reported", not "passed": advisory mode exits 0 on every block
    (10.3-r1-01). So any other verdict — advisory, not-judged, skipped, predates-gate (a unit
    Done before the gate existed has no verdict to merge on), or one this script does not
    know — is no merge."""
    rc, out, err = sh([sys.executable, VERDICT_GATE, "--scope", scope, "--unit", unit, "--blocking", "--json"])
    line = next((x for x in reversed(out.splitlines()) if x.strip().startswith("{")), "")
    try:
        doc = json.loads(line)
    except ValueError:
        return False, f"verdict-gate.py output unreadable (exit {rc}): {first_err(err, rc)}", ""
    verdict = doc.get("verdict") if isinstance(doc, dict) else None
    if rc != 0 or verdict != "pass":
        return False, f"verdict-gate.py --blocking: {verdict or 'no verdict'} (exit {rc}) — only `pass` merges", ""
    return True, "gate pass", doc.get("marker") or ""


def cond_verdict(repo, scope, unit, pr_head):
    """(ok, detail, degraded label or '', gate marker)."""
    rv = _load("review_py", REVIEW_PY)
    log = os.path.join(scope, "artifacts", f"review-{unit}.jsonl")
    if not os.path.exists(log):
        return False, f"no review log for {unit} ({log})", "", ""
    try:
        recs = rv.vl.read_jsonl(log)
    except rv.vl.ContractError as e:
        return False, f"review log malformed: {str(e.msg).splitlines()[0][:160]}", "", ""
    key = rv.repo_key(rv.main_worktree(repo))
    mine = [(i, r) for i, r in enumerate(recs)
            if r.get("record") == "review" and key in (r.get("range") or {})]
    if not mine:
        return False, f"no review of {key} in unit {unit}", "", ""
    at, last = mine[-1]
    reviewer = str(last.get("reviewer") or "")
    if not reviewer or reviewer.startswith("none"):
        return False, f"review {last.get('review_id')} had no reviewer ({reviewer or 'unrecorded'})", "", ""
    verdict = str(last.get("verdict") or "").strip()
    accepted = any(r.get("record") == "acceptance" and str(r.get("by") or "").strip() for r in recs[at + 1:])
    if verdict == "SHIP":
        how = "SHIP"
    elif accepted:
        how = f"{verdict or 'no verdict'}, accepted"
    else:
        return False, f"review {last.get('review_id')} is {verdict or 'unrecorded'} and not accepted", "", ""
    seen = str((last.get("shas") or {}).get("head") or "")
    ok, cover = covered(repo, seen, pr_head, last.get("review_id"))
    if not ok:
        return False, cover, "", ""
    degraded = "" if reviewer.startswith("codex ") else reviewer.split()[0]
    gok, gdetail, marker = run_gate(scope, unit)
    if not gok:
        return False, gdetail, "", ""
    detail = f"{last.get('review_id')} {how}{cover}; {gdetail}" + (f" · degraded review: {degraded}" if degraded else "")
    return True, detail, degraded, marker


def covered(repo, seen, head, rid):
    """The review saw the PR head, or the commits after it touch plans/ only (bookkeeping)."""
    if not seen:
        return False, f"review {rid} recorded no head sha"
    rc1, a, _ = git(repo, "rev-parse", "--verify", "--quiet", f"{seen}^{{commit}}")
    rc2, b, _ = git(repo, "rev-parse", "--verify", "--quiet", f"{head}^{{commit}}")
    if rc1 or rc2:
        return False, f"cannot resolve review head {seen[:12]} / PR head {head[:12]} locally"
    a, b = a.strip(), b.strip()
    if a == b:
        return True, ""
    if git(repo, "merge-base", "--is-ancestor", a, b)[0]:
        return False, f"PR head {b[:12]} does not contain review {rid}'s head {a[:12]} — review the PR head"
    rc, out, err = git(repo, "diff", "--name-only", "--no-renames", a, b, "--")
    if rc:
        return False, f"git diff {a[:12]}..{b[:12]} failed: {first_err(err, rc)}"
    code = [p for p in out.splitlines() if p and not p.startswith("plans/")]
    if code:
        return False, (f"PR head {b[:12]} has commits past review {rid} ({a[:12]}) touching "
                       f"{', '.join(code[:4])} — review them first")
    return True, f" (+ plans/-only commits past {a[:12]})"


# ---------- packet / event ---------------------------------------------------------

def emit_packet(repo, unit, label, failed, hits, rng, head):
    one_way = bool(hits) or any(name == "floor" for name, _ in failed)
    door = "one-way" if one_way else "two-way"
    pid = _load("packet_emit", os.path.join(HERE, "packet_emit.py")).stable_id(
        "merge", label.replace("/", "-").replace("#", "-"), head[:12], door)
    body = "\n".join([f"driver-merge.py did not merge {label}:"] + [f"- {n}: {d}" for n, d in failed]
                     + [f"- floor path: {h['path']} ({h['pattern']}, {h['change']})" for h in hits])
    options = (["Alex reviews the floor change and merges by hand", "Rework the PR off the floor"] if one_way else
               ["Driver fixes the failed condition and re-runs driver-merge", "Alex merges by hand"])
    cmd = [sys.executable, PACKET, "new", "--door", door, "--type", "generic", "--title",
           f"{'Floor path' if one_way else 'Not merged'}: {label}", "--unit", unit, "--recommended", "1",
           "--body", body, "--id", pid, "--driver"]
    for o in options:
        cmd += ["--option", o]
    if one_way and rng:
        cmd += ["--range", rng]
    rc, out, err = sh(cmd, cwd=repo, timeout=60)
    first = next((x for x in out.splitlines() if x.startswith("PACKET ")), "")
    if rc or not first:
        print(f"driver-merge: warning: refusal packet not written ({first_err(err, rc)})", file=sys.stderr)
        return None
    print(out.rstrip())
    return first.split()[1]


def post_event(repo, body):
    rc, out, err = sh([sys.executable, PACKET, "event", "--kind", "merged", "--body", body, "--driver"],
                      cwd=repo, timeout=60)
    if rc or not out.startswith("EVENT "):
        print(f"driver-merge: merged, but the `merged` event was not written ({first_err(err, rc)})",
              file=sys.stderr)
        return False
    print(out.rstrip())
    return True


# ---------- main --------------------------------------------------------------------

def evaluate(a):
    """[(name, ok, detail)], plus the facts merge needs. Raises Refuse when the PR cannot be read."""
    slug, name = repo_slug(a.repo)
    doc = pr_view_settled(slug, a.pr)
    base, base_oid, head_oid = doc.get("baseRefName"), doc.get("baseRefOid"), doc.get("headRefOid")
    if not (isinstance(base, str) and isinstance(base_oid, str) and isinstance(head_oid, str) and head_oid):
        raise Refuse(f"gh pr view {slug}#{a.pr}: base/head refs missing")
    pk = _load("packet", PACKET)
    rows = [("driver", pk.is_driver(a), "driver" if pk.is_driver(a) else
             "not a driver (--driver or $HERDR_AGENT_NAME=driver) — lanes never merge")]
    rows.append(("pr",) + cond_pr(doc))
    rows.append(("base",) + cond_base(name, base))
    rows.append(("checks",) + cond_checks(doc.get("statusCheckRollup")))
    ensure_commits(a.repo, a.pr, base, (base_oid, head_oid))
    vok, vdetail, degraded, marker = cond_verdict(a.repo, a.scope, a.unit, head_oid)
    rows.append(("verdict", vok, vdetail))
    fok, fdetail, hits, rng = cond_floor(a.repo, base_oid, head_oid)
    rows.append(("floor", fok, fdetail))
    mok, mdetail, admin = cond_mergeable(doc.get("mergeStateStatus"))
    rows.append(("mergeable", mok, mdetail))
    facts = {"slug": slug, "label": f"{slug}#{a.pr}", "base": base, "head": head_oid, "admin": admin,
             "degraded": degraded, "marker": marker, "hits": hits, "range": rng}
    return rows, facts


def merge(a, facts):
    cmd = ["pr", "merge", str(a.pr), "-R", facts["slug"], f"--{a.method}", "--match-head-commit", facts["head"]]
    if facts["admin"]:
        cmd.append("--admin")
    rc, _, err = gh(*cmd)
    if rc:
        return None, f"gh pr merge failed: {first_err(err, rc)}"
    try:
        back = pr_view(facts["slug"], a.pr, "state,mergeCommit")
    except Refuse as e:
        return None, f"merge not read back: {e}"
    sha = (back.get("mergeCommit") or {}).get("oid") if isinstance(back.get("mergeCommit"), dict) else None
    if back.get("state") != "MERGED" or not sha:
        return None, f"gh pr merge exited 0 but the PR reads back {back.get('state')} (merge commit {sha or 'none'})"
    return sha, ""


def main(argv):
    ap = argparse.ArgumentParser(prog="driver-merge.py")
    ap.add_argument("cmd", choices=["check", "merge"])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--pr", required=True, type=int)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--unit", required=True)
    ap.add_argument("--driver", action="store_true")
    ap.add_argument("--method", default="squash", choices=["squash", "merge", "rebase"])
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return EXIT_USAGE if e.code else EXIT_OK
    a.repo = os.path.abspath(os.path.expanduser(a.repo))
    pk = _load("packet", PACKET)
    if a.cmd == "merge" and not pk.is_driver(a):
        print("driver-merge: refused — merge is driver-only (--driver or $HERDR_AGENT_NAME=driver); "
              "lanes never merge")
        return EXIT_REFUSED
    try:
        rows, facts = evaluate(a)
    except Refuse as e:
        print(f"driver-merge: {a.cmd} #{a.pr}: could not evaluate — {e}")
        print("verdict: REFUSED (fail-closed)")
        if a.cmd == "merge":
            emit_packet(a.repo, a.unit, f"{os.path.basename(a.repo)}#{a.pr}", [("evaluate", str(e))],
                        [], None, "unread")
            print("NOT MERGED")
        return EXIT_REFUSED
    print(f"driver-merge {a.cmd}: {facts['label']} -> {facts['base']} @ {facts['head'][:12]}")
    for name, ok, detail in rows:
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: {detail}")
    failed = [(n, d) for n, ok, d in rows if not ok]
    flags = ([f"degraded review: {facts['degraded']}"] if facts["degraded"] else []) + \
        (["admin: branch protection"] if facts["admin"] and not failed else []) + ([facts["marker"]] if facts["marker"] else [])
    print(f"verdict: {'ELIGIBLE' if not failed else f'REFUSED ({len(failed)} failed)'}"
          + "".join(f" · {f}" for f in flags))
    if a.cmd == "check":
        return EXIT_REFUSED if failed else EXIT_OK
    if not failed:
        sha, why = merge(a, facts)
        if sha:
            print(f"MERGED {facts['label']} {sha}")
            body = f"repo={facts['slug']} pr={a.pr} base={facts['base']} sha={sha}" + "".join(f" · {f}" for f in flags)
            return EXIT_OK if post_event(a.repo, body) else EXIT_NO_EVENT
        failed = [("merge", why)]
        print(f"  [FAIL] merge: {why}")
    emit_packet(a.repo, a.unit, facts["label"], failed, facts["hits"], facts["range"], facts["head"])
    print("NOT MERGED — " + "; ".join(f"{n}: {d}" for n, d in failed))
    return EXIT_REFUSED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
