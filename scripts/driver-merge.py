#!/usr/bin/env python3
"""driver-merge.py — may the /plan driver merge its own PR, and if so merge it (scope 10 §4.3,
plan 10.3 tasks 3.1 + 3.2).

Approach: every condition is evaluated and printed, one line each, then the verdict. A PR is
eligible only when ALL hold:
  * driver   — packet.py's driver_identity: --driver, and inside herdr only from a pane the
               driver registered as itself on this host in the dispatch log; every unregistered
               pane is a lane, and an unreadable log refuses (Alex 86). `check` reports it;
               `merge` refuses before any gh call
  * pr       — open, not a draft
  * base     — `main` for kalpa-docs / pmg-docs / ai-skills, `develop` for every other repo.
               Any other base is refused and never touched: a code repo's `main` is prod, and
               prod stays behind prod-merge-gate.py
  * checks   — every check finished green or skipped/neutral AND at least one real run is
               green. An empty list, or skipped/neutral only, is vacuous: WellMed staging PRs
               get zero checks, so "nothing failed" is not "green"
  * verdict  — the unit's latest review of this repo is SHIP, or an `acceptance` follows it
               (review.py accept); that review saw the PR head (later commits may touch only
               plans/); every non-plans/ commit in merge-base..head sits inside some review's
               base..head for this repo in the unit (10.3-r1-04: the latest review seeing the
               head says nothing about the PR's start); and verdict-gate.py --blocking reads `pass`. A reviewer other than codex (fallback /
               lean) still merges, flagged; a `none` reviewer is no review
  * floor    — door.py classifies merge-base..head with no floor path
  * ci       — merge-base..head touches no CI definition file (CI_DEFINITIONS: workflows,
               actions, CODEOWNERS, …). A PR editing one of those files never auto-merges; scripts
               the workflows invoke (`run: ./scripts/ci.sh`, `make test`) are not on the list —
               the review range covers those edits, not this condition. CI edits are reversible, so this is a two-way "CI change" packet — Alex
               reviews and merges by hand — not a floor path (10.3-r2-04)
  * mergeable — mergeStateStatus CLEAN / HAS_HOOKS merges; BLOCKED merges with --admin (what
               Alex does by hand) ONLY when GitHub says a review approval is missing
               (reviewDecision REVIEW_REQUIRED), the base requires nothing beyond required checks
               and reviews — no classic signatures, conversation resolution, deployments, lock,
               linear history or unmodelled field, no ruleset rule but required_status_checks /
               pull_request, no review-thread resolution (10.3-r4-01) — AND every required check of the base branch
               (classic protection AND rulesets) is satisfied on the head: present (a check
               bound to an app by a check run from that app, 10.3-r2-03) and EVERY entry of that
               name SUCCESS or SKIPPED/NEUTRAL (10.3-r2-05) — a failing status beside a green
               run is not satisfied (Alex 83, 10.3-r3-01). The rollup lists only checks that
               ran, so a required check that never reported is invisible to `checks` (10.3-r1-03).
               Any other BLOCKED, and DIRTY, BEHIND, UNSTABLE, DRAFT, UNKNOWN after retries,
               refuses: a two-way packet
`merge` on an eligible PR runs `gh pr merge --match-head-commit <head>` (never --auto: GitHub
auto-merge stays off), reads the PR back as MERGED with its merge commit, then posts
`packet.py event --kind merged` with repo, PR and merge sha (task 3.2). On any failed condition
it writes a packet instead — one-way with the matched paths for a floor hit, two-way otherwise —
and prints why.

Failure stances (fail closed: every one of these is "no merge" with the reason):
  * gh error, unparseable gh JSON, unknown check type/state, mergeStateStatus still UNKNOWN
  * BLOCKED with reviewDecision other than REVIEW_REQUIRED (missing included) -> no --admin
  * BLOCKED and the base's protection or rulesets unreadable -> no --admin, no merge
  * BLOCKED and the base requires anything beyond checks + reviews, or a protection field or
    ruleset rule type this script does not model -> no --admin (a requirement it cannot evaluate
    is one --admin would bypass unread)
  * BLOCKED, a required check bound to an app, and the head's check runs unreadable -> the
    binding cannot be verified -> no --admin, no merge
  * origin remote unreadable, git error, PR commits not fetchable (door.py then fails closed;
    the ci condition too)
  * a PR commit outside every review range of this repo in the unit, an unparseable or
    unresolvable review range
  * review log missing / malformed, no review of this repo in the unit, verdict-gate exit != 0,
    a verdict other than `pass` (advisory included), or unparseable output
  * merge reported success but the read-back is not MERGED -> not merged, packet written
  * gh pr merge exited non-zero -> read back anyway: MERGED with a merge commit AT the checked
    head is merged (the gh error flagged on the event); anything else is not merged
  * read back MERGED at another (or an unreadable) headRefOid -> `MERGED-ELSEWHERE`: not this
    run's merge, no `merged` event, a two-way packet for Alex, exit 1 (10.3-r2-02)
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
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
PACKET = os.path.join(HERE, "packet.py")
VERDICT_GATE = os.path.join(HERE, "verdict-gate.py")
REVIEW_PY = os.path.join(os.path.dirname(HERE), "review", "scripts", "review.py")
DOCS_MAIN = {"kalpa-docs", "pmg-docs", "ai-skills"}
INERT = {"SKIPPED", "NEUTRAL"}
MERGE_OK = {"CLEAN", "HAS_HOOKS"}
FIELDS = ("number,state,isDraft,baseRefName,headRefName,baseRefOid,headRefOid,"
          "mergeStateStatus,reviewDecision,url,statusCheckRollup")
UNKNOWN_RETRIES, UNKNOWN_SLEEP = 3, 2.0
# Never auto-merged, in door.py's glob syntax (10.3-r2-04): a PR editing a CI definition file
# here rides a self-referential green. Scripts those files invoke are not listed: the review
# range covers them (10.3-r3-05). Root-anchored, as GitHub runs root workflows only. Reversible, so NOT on the one-way floor (that
# would park every lane that touches CI) — a two-way packet: Alex reviews and merges by hand.
CI_DEFINITIONS = """
.github/workflows/
.github/actions/
CODEOWNERS
.circleci/
.gitlab-ci.yml
Jenkinsfile
buildspec*.yml
buildspec*.yaml
"""
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

def cond_driver(a, pk):
    """packet.py's driver_identity decides (Alex 86): --driver, and inside herdr an open driver
    registration for this pane on this host. One decision for the merge here and every POST
    packet.py makes."""
    ok, detail = pk.driver_identity(a)
    return ok, detail if ok else f"{detail} — lanes never merge"


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


def gh_json(path):
    rc, out, err = gh("api", path)
    if rc:
        return None, first_err(err, rc)
    try:
        return json.loads(out), ""
    except ValueError:
        return None, "output is not JSON"


def gh_pages(path, key=None):
    """Every item of a paginated list endpoint (10.3-r2-06): `--paginate --slurp` wraps each page
    in an outer array. (items, '') or (None, why). Incomplete is unreadable: a gh error mid-way,
    or any page that is not a list (or, with `key`, an object carrying a list under it)."""
    rc, out, err = gh("api", "--paginate", "--slurp", path)
    if rc:
        return None, first_err(err, rc)
    try:
        pages = json.loads(out)
    except ValueError:
        return None, "output is not JSON"
    if not isinstance(pages, list) or not pages:
        return None, "no pages read"
    items = []
    for i, page in enumerate(pages):
        page = page.get(key) if key and isinstance(page, dict) else page
        if not isinstance(page, list):
            return None, f"page {i + 1} of {len(pages)} unreadable — read incomplete"
        items += page
    return items, ""


def app_binding(v):
    """A required check's app binding: None = any source (unset, null, or -1, GitHub's explicit
    "any app"), an int = only that GitHub App's check run counts. Anything else is unreadable."""
    if v is None or v == -1:
        return None, True
    return (v, True) if isinstance(v, int) and not isinstance(v, bool) and v > 0 else (None, False)


# Classic protection fields --admin may pass: the two modelled requirements (checks, reviews) and
# settings that are not a merge requirement. A field outside this set and REQUIREMENTS is not
# modelled, so it refuses --admin (10.3-r4-01: fail closed on what this script cannot evaluate).
CLASSIC_OK = {"url", "required_status_checks", "required_pull_request_reviews", "enforce_admins",
              "allow_force_pushes", "allow_deletions", "block_creations", "allow_fork_syncing",
              "restrictions"}
# Classic requirements beyond checks + reviews: enabled -> GitHub may block on it, --admin would
# bypass it unread -> no --admin (10.3-r4-01)
REQUIREMENTS = ("required_signatures", "required_conversation_resolution", "required_deployments",
                "lock_branch", "required_linear_history")
RULES_OK = {"required_status_checks", "pull_request"}


def flag_on(v):
    """A classic protection flag: (on, readable). {"enabled": bool} is the documented shape; an
    absent / null field is off; a list or other object (required_deployments' environments) is on
    when non-empty. Anything else is unreadable."""
    if v is None:
        return False, True
    if isinstance(v, dict) and "enabled" in v:
        return (v["enabled"], True) if isinstance(v["enabled"], bool) else (False, False)
    if isinstance(v, (list, dict)):
        return bool(v), True
    return (v, True) if isinstance(v, bool) else (False, False)


def protection(slug, base):
    """(required, extra, '') or (None, None, why unreadable).

    required = {(context, app id or None)} from both sources: classic branch protection
    (`checks[].app_id`; `contexts` is its unbound legacy mirror) and repository rulesets
    (`integration_id`). The app is GitHub's binding of a required check to who must report it,
    and --admin bypasses GitHub enforcing it, so it is carried (10.3-r2-03).
    extra = every requirement beyond required checks and reviews (10.3-r4-01, Alex 83): classic
    REQUIREMENTS enabled, a classic field not modelled, a ruleset rule of a type other than
    required_status_checks / pull_request, or a pull_request rule with
    required_review_thread_resolution. --admin bypasses all of them unread, so any one refuses it.
    Classic protection answering "not protected" is a readable empty set; any other error is
    unreadable, and unreadable is never read as "nothing required"."""
    b = urllib.parse.quote(base, safe="")
    req, extra = set(), []
    doc, why = gh_json(f"repos/{slug}/branches/{b}/protection")
    if doc is None:
        if "Branch not protected" not in why:
            return None, None, f"branch protection unreadable ({why})"
    elif isinstance(doc, dict):
        for k in sorted(doc):
            if k in REQUIREMENTS:
                on, ok = flag_on(doc[k])
                if not ok:
                    return None, None, f"branch protection: {k} unreadable"
                if on:
                    extra.append(k)
            elif k not in CLASSIC_OK:
                extra.append(f"{k} (not modelled)")
        rsc = doc.get("required_status_checks")
        if rsc is not None and not isinstance(rsc, dict):
            return None, None, "branch protection: required_status_checks unreadable"
        checked = set()
        for c in (rsc or {}).get("checks") or []:
            app, ok = app_binding(c.get("app_id")) if isinstance(c, dict) else (None, False)
            if not (ok and c.get("context")):
                return None, None, "branch protection: required check unreadable"
            req.add((c["context"], app))
            checked.add(c["context"])
        req |= {(c, None) for c in (rsc or {}).get("contexts") or [] if isinstance(c, str) and c not in checked}
    else:
        return None, None, "branch protection: output is not an object"
    rules, why = gh_pages(f"repos/{slug}/rules/branches/{b}?per_page=100")
    if rules is None:
        return None, None, f"rulesets unreadable ({why})"
    for r in rules:
        if not isinstance(r, dict) or not isinstance(r.get("parameters") or {}, dict):
            return None, None, "ruleset rule unreadable"
        kind, params = r.get("type"), r.get("parameters") or {}
        if kind not in RULES_OK:
            extra.append(f"ruleset {kind}")
        elif kind == "pull_request" and params.get("required_review_thread_resolution"):
            extra.append("ruleset required_review_thread_resolution")  # unset is off, anything set is on
        elif kind == "required_status_checks":
            for c in params.get("required_status_checks") or []:
                app, ok = app_binding(c.get("integration_id")) if isinstance(c, dict) else (None, False)
                if not (ok and c.get("context")):
                    return None, None, "ruleset required check unreadable"
                req.add((c["context"], app))
    return req, extra, ""


def satisfied(res):
    return str(res or "").upper() in {"SUCCESS"} | INERT


def entry_ok(c, rollup=True):
    """One check entry satisfied: a completed check run whose conclusion is SUCCESS or
    SKIPPED/NEUTRAL (GitHub's rule for a required job skipped by `if:`, 10.3-r2-05), or a commit
    status in those states. Rollup entries are typed (`__typename`, UPPER case); REST check runs
    are not (lower case). An unknown shape is not satisfied."""
    if not isinstance(c, dict):
        return False
    if rollup and c.get("__typename") == "StatusContext":
        return satisfied(c.get("state"))
    if rollup and c.get("__typename") != "CheckRun":
        return False
    return str(c.get("status") or "").upper() == "COMPLETED" and satisfied(c.get("conclusion"))


def cond_mergeable(state, slug=None, base=None, rollup=None, head=None, review=None):
    """(ok, detail, admin). BLOCKED earns --admin ONLY when GitHub says a review approval is
    missing (reviewDecision REVIEW_REQUIRED), the base requires nothing beyond required checks
    and reviews (10.3-r4-01: REVIEW_REQUIRED does not say the review is the ONLY thing missing —
    an unresolved conversation or a signature rule also holds BLOCKED), AND every required (check, app) of the base
    (classic protection and rulesets) is satisfied on the head (Alex 83, 10.3-r3-01): at least
    one entry exists — for a check bound to an app, a check run FROM that app, read from the
    head's check-runs since the rollup carries no app (10.3-r2-03) — and EVERY entry of that
    name, rollup or check run, any source, is satisfied. A failing status beside a green check
    run, or one failing run of two, is not satisfied: GitHub requires both. Any other BLOCKED
    (reviewDecision APPROVED / none / unreadable) is something this script cannot see: no
    --admin. Protection, rulesets, the rollup or the check runs unreadable -> no --admin."""
    if state in MERGE_OK:
        return True, state, False
    if state != "BLOCKED":
        return False, f"mergeStateStatus {state or 'missing'} — not mergeable as is", False
    if review != "REVIEW_REQUIRED":
        return False, (f"BLOCKED with reviewDecision {review or 'none'} — something other than a missing "
                       "review approval blocks; no --admin"), False
    req, extra, why = protection(slug, base)
    if req is None:
        return False, f"BLOCKED and {why} — no --admin without the base's protection", False
    if extra:
        return False, (f"BLOCKED and the base requires more than checks and a review: {', '.join(extra[:6])}"
                       " — --admin would bypass it unread; no --admin"), False
    if not (isinstance(rollup, list) and all(isinstance(c, dict) for c in rollup)):
        return False, "BLOCKED and the head's check list unreadable — no --admin", False
    runs = []
    if any(app for _, app in req):
        runs, why = gh_pages(f"repos/{slug}/commits/{head}/check-runs?per_page=100", key="check_runs")
        if runs is None or not all(isinstance(r, dict) for r in runs):
            return False, (f"BLOCKED and the head's check runs unreadable ({why or 'bad entry'}) — a required "
                           "check's app binding cannot be verified; no --admin"), False
    unmet = []
    for ctx, app in sorted(req, key=lambda x: (x[0], x[1] or 0)):
        named = [entry_ok(c) for c in rollup if (c.get("name") or c.get("context")) == ctx]
        mine = [r for r in runs if r.get("name") == ctx]
        named += [entry_ok(r, rollup=False) for r in mine]
        present = (any(entry_ok(r, rollup=False) for r in mine if (r.get("app") or {}).get("id") == app)
                   if app else bool(named))
        if not (present and all(named)):
            unmet.append(f"{ctx} (app {app})" if app else ctx)
    if unmet:
        return False, (f"BLOCKED and required check(s) not satisfied on the head: {', '.join(unmet[:6])}"
                       " — missing, pending, failed, not from the bound app, or one entry of that name"
                       " not satisfied; no --admin"), False
    return True, (f"BLOCKED only on a missing review approval — {len(req)} required check(s) satisfied; "
                  "merges with --admin when every other condition holds"), True


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


def cond_ci(repo, rng):
    """(ok, detail). merge-base..head touches no CI definition. Fails closed: no range, or a git
    error reading the touched paths, is a CI change for this purpose (Alex merges by hand)."""
    if not rng:
        return False, "fail-closed: no merge-base range to read for CI definitions"
    door = _load("door", os.path.join(HERE, "door.py"))
    try:
        rules = door.compile_rules(CI_DEFINITIONS)
        base, head = door.parse_range(rng)
        paths = door.touched(repo, door.resolve(repo, base), door.resolve(repo, head))
    except door.Failed as e:
        return False, f"fail-closed: CI definitions unreadable ({e})"
    hits = [f"{p} ({t})" for _, p in paths for t, rx in rules if rx.match(p)]
    if hits:
        return False, (f"CI change — Alex reviews and merges by hand: {', '.join(hits[:6])}"
                       + (f" (+{len(hits) - 6})" if len(hits) > 6 else ""))
    return True, "no CI definition touched"


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


def cond_verdict(repo, scope, unit, pr_base, pr_head):
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
    uncovered, why = unreviewed(repo, key, [r for _, r in mine], pr_base, pr_head)
    if why:
        return False, why, "", ""
    if uncovered:
        return False, (f"unreviewed commits: {len(uncovered)} in merge-base..{pr_head[:12]} sit in no review of "
                       f"{key} in unit {unit}: {', '.join(c[:12] for c in uncovered[:6])}"
                       + (f" (+{len(uncovered) - 6})" if len(uncovered) > 6 else "")), "", ""
    degraded = "" if reviewer.startswith("codex ") else reviewer.split()[0]
    gok, gdetail, marker = run_gate(scope, unit)
    if not gok:
        return False, gdetail, "", ""
    detail = f"{last.get('review_id')} {how}{cover}; {gdetail}" + (f" · degraded review: {degraded}" if degraded else "")
    return True, detail, degraded, marker


def rev_list(repo, rng):
    rc, out, err = git(repo, "rev-list", rng, "--")
    return (out.split(), "") if not rc else (None, first_err(err, rc))


def commit_paths(repo, c):
    """Paths a commit changes against its first parent (all of them for a root commit), or None."""
    rc, out, _ = git(repo, "rev-list", "--parents", "-n", "1", c)
    if rc or not out.split():
        return None
    parents = out.split()[1:]
    args = ["diff", "--name-only", "--no-renames", parents[0], c, "--"] if parents else \
        ["diff-tree", "--root", "-r", "--name-only", "--no-commit-id", "--no-renames", c]
    rc, out, _ = git(repo, *args)
    return None if rc else [p for p in out.splitlines() if p]


def unreviewed(repo, key, reviews, base_oid, head):
    """(uncovered shas, '') or ([], why it could not be decided). Every commit of the PR
    (merge-base..head) must sit inside some review record's base..head for this repo; a commit
    touching plans/ only is bookkeeping and exempt. An empty commit, or one whose paths
    cannot be read, is not exempt. Any git failure or unparseable review range refuses."""
    rc, mb, err = git(repo, "merge-base", base_oid, head)
    if rc or not mb.strip():
        return [], f"coverage: no merge-base for {base_oid[:12]}..{head[:12]} ({first_err(err, rc)})"
    pr, why = rev_list(repo, f"{mb.strip()}..{head}")
    if pr is None:
        return [], f"coverage: git rev-list of the PR failed ({why})"
    seen = set()
    for r in reviews:
        rng = str((r.get("range") or {}).get(key) or "")
        if not re.fullmatch(r"[0-9a-fA-F]{7,64}\.\.[0-9a-fA-F]{7,64}", rng):
            return [], f"coverage: review {r.get('review_id')} range {rng!r} is not base..head"
        shas, why = rev_list(repo, rng)
        if shas is None:
            return [], f"coverage: review {r.get('review_id')} range {rng} unresolvable ({why})"
        seen.update(shas)
    out = []
    for c in pr:
        if c in seen:
            continue
        paths = commit_paths(repo, c)
        if not paths or any(not p.startswith("plans/") for p in paths):
            out.append(c)
    return out, ""


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

def emit_packet(repo, unit, label, failed, hits, rng, head, title=None, options=None, kind="merge"):
    """Write the refusal packet. Its id must change whenever the case does, or packet.py `new
    --id` re-sends the OLD card (10.3-r3-03): it carries the kind (`merge-elsewhere` is keyed on
    the merge commit that landed, passed as `head`), the head, the door and the failed condition
    names. Those lead the id because stable_id cuts at 64 chars and a long owner/repo label
    would otherwise cut them off; the label goes last. A new id for a kind + head + label that
    already has an open card marks that card stale (supersede, 10.3-r4-06); a case whose card
    supersede already made stale (pending -> UNSTABLE -> pending) bumps a generation into the
    id, or the re-send would revive nothing and leave no open card."""
    one_way = bool(hits) or any(name == "floor" for name, _ in failed)
    door = "one-way" if one_way else "two-way"
    names, dirs = "+".join(sorted({n for n, _ in failed})), outbox_dirs(repo)
    stable_id = _load("packet_emit", os.path.join(HERE, "packet_emit.py")).stable_id
    for gen in range(32):  # a case that comes back after supersede made its card stale gets a new id
        conds = hashlib.sha1((names + (f"#{gen}" if gen else "")).encode()).hexdigest()[:6]
        pid = stable_id(kind, head[:12], door, conds, label.replace("/", "-").replace("#", "-"))
        if packet_status(dirs, pid) != "stale":
            break
    body = "\n".join([f"driver-merge.py did not merge {label}:"] + [f"- {n}: {d}" for n, d in failed]
                     + [f"- floor path: {h['path']} ({h['pattern']}, {h['change']})" for h in hits])
    ci = any(name == "ci" for name, _ in failed)
    # Cards v2 (10.4 cards lane): title = the question, short context, option label + one-line why,
    # the per-condition detail goes to evidence (collapsed on the card).
    options = options or ([("Merge it by hand after review", "You review the floor change and merge it yourself."),
                           ("Rework the PR off the floor", "The lane moves the change off the floor path; the driver re-runs.")]
                          if one_way else
                          [("Merge it by hand after review", "You review the CI change and merge it yourself."),
                           ("Driver fixes the rest, re-runs", "Other failed conditions get fixed first; the CI change still needs you.")]
                          if ci else
                          [("Driver fixes it and re-runs", "The driver fixes the failed condition and re-runs driver-merge."),
                           ("Merge it by hand", "You merge it yourself now.")])
    title = title or ("Floor path" if one_way else "CI change" if ci else "Not merged")
    context = (f"driver-merge did not merge {label}: " + ", ".join(n for n, _ in failed))[:400]
    cmd = [sys.executable, PACKET, "new", "--door", door, "--type", "generic", "--title",
           f"{title}: {label}"[:100], "--unit", unit, "--recommended", "1",
           "--context", context, "--evidence", body[:4000], "--id", pid, "--driver"]
    for lbl, why in options:
        cmd += ["--option", f"{lbl}::{why}"]
    if one_way and rng:
        cmd += ["--range", rng]
    rc, out, err = sh(cmd, cwd=repo, timeout=60)
    first = next((x for x in out.splitlines() if x.startswith("PACKET ")), "")
    if rc or not first:
        print(f"driver-merge: warning: refusal packet not written ({first_err(err, rc)})", file=sys.stderr)
        return None
    print(out.rstrip())
    pid = first.split()[1]
    supersede(repo, kind, head, label, pid)
    return pid


def outbox_dirs(repo):
    """Where packet.py writes for `repo`: $PACKET_OUTBOX, else <toplevel>/.decision-queue/outbox."""
    rc, top, _ = sh(["git", "-C", repo, "rev-parse", "--show-toplevel"], timeout=30)
    return [d for d in (os.environ.get("PACKET_OUTBOX"),
                        os.path.join(top.strip(), ".decision-queue", "outbox") if rc == 0 else None) if d]


def packet_status(dirs, pid):
    """The outbox status of `pid` — None when absent, 'unreadable' when its state cannot be read."""
    for d in dirs:
        if os.path.exists(os.path.join(d, f"{pid}.json")):
            try:
                with open(os.path.join(d, f"{pid}.state.json"), encoding="utf-8") as fh:
                    return json.load(fh).get("status")
            except (OSError, ValueError, AttributeError):
                return "unreadable"
    return None


def supersede(repo, kind, head, label, pid):
    """Mark stale every OPEN outbox packet for the same kind + head + label under another id
    (10.3-r4-06): a new failure set on the same head mints a new card, and the earlier one is
    superseded, not a second open card for one PR. Matched on the id's `pk-<kind>-<head12>-`
    prefix and the title's `: <label>` tail (the label may be cut off the id at 64 chars).
    Fail-open on purpose, warned on stderr: marking stale discards a pending decision, so an
    unreadable outbox, packet or a failed `stale` leaves the earlier card open — an extra card
    is the safe failure, a wrongly closed one is not."""
    d = next((x for x in outbox_dirs(repo) if os.path.exists(os.path.join(x, f"{pid}.json"))), None)
    if d is None:
        print(f"driver-merge: warning: outbox of {pid} not found; earlier cards not superseded", file=sys.stderr)
        return
    prefix = f"pk-{kind}-{head[:12]}-"
    for f in sorted(os.listdir(d)):
        old = f[:-len(".json")]
        if not (f.startswith(prefix) and f.endswith(".json")) or f.endswith(".state.json") or old == pid:
            continue
        try:
            with open(os.path.join(d, f), encoding="utf-8") as fh:
                doc = json.load(fh)
            with open(os.path.join(d, f"{old}.state.json"), encoding="utf-8") as fh:
                status = json.load(fh).get("status")
        except (OSError, ValueError, AttributeError) as e:
            print(f"driver-merge: warning: {old} unreadable ({e}); not superseded", file=sys.stderr)
            continue
        if status != "open" or not str(doc.get("title") or "").endswith(f": {label}"):
            continue
        src, out, err = sh([sys.executable, PACKET, "stale", old, "--force", "--reason", f"superseded by {pid}",
                            "--outbox", d, "--driver"], cwd=repo, timeout=60)
        print(out.rstrip() if src == 0 else
              f"driver-merge: warning: {old} not marked stale ({first_err(err, src)})", file=sys.stdout if src == 0 else sys.stderr)


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
    rows = [("driver",) + cond_driver(a, pk)]
    rows.append(("pr",) + cond_pr(doc))
    rows.append(("base",) + cond_base(name, base))
    rows.append(("checks",) + cond_checks(doc.get("statusCheckRollup")))
    ensure_commits(a.repo, a.pr, base, (base_oid, head_oid))
    vok, vdetail, degraded, marker = cond_verdict(a.repo, a.scope, a.unit, base_oid, head_oid)
    rows.append(("verdict", vok, vdetail))
    fok, fdetail, hits, rng = cond_floor(a.repo, base_oid, head_oid)
    rows.append(("floor", fok, fdetail))
    rows.append(("ci",) + cond_ci(a.repo, rng))
    mok, mdetail, admin = cond_mergeable(doc.get("mergeStateStatus"), slug, base, doc.get("statusCheckRollup"),
                                         head_oid, doc.get("reviewDecision"))
    rows.append(("mergeable", mok, mdetail))
    facts = {"slug": slug, "label": f"{slug}#{a.pr}", "base": base, "head": head_oid, "admin": admin,
             "degraded": degraded, "marker": marker, "hits": hits, "range": rng}
    return rows, facts


def merge(a, facts):
    """(sha or None, why-not, flag, elsewhere). The read-back decides, not gh's exit code: gh can
    exit non-zero after GitHub merged (a dropped connection after the mutation, a post-merge
    step) — that is the merged path with the gh error flagged (10.3-r1-06). It is THIS merge only
    when the read-back headRefOid is the head every condition checked: a failed gh can also mean
    the head moved and someone else merged it there (10.3-r2-02). MERGED at another or an
    unreadable head is `elsewhere` (no `merged` event); unreadable or not MERGED with a merge
    commit is not merged, whatever gh said."""
    cmd = ["pr", "merge", str(a.pr), "-R", facts["slug"], f"--{a.method}", "--match-head-commit", facts["head"]]
    if facts["admin"]:
        cmd.append("--admin")
    rc, _, err = gh(*cmd)
    gh_err = f"gh pr merge failed: {first_err(err, rc)}" if rc else ""
    try:
        back = pr_view(facts["slug"], a.pr, "state,mergeCommit,headRefOid")
    except Refuse as e:
        return None, (gh_err + "; " if gh_err else "") + f"merge not read back: {e}", "", ""
    sha = (back.get("mergeCommit") or {}).get("oid") if isinstance(back.get("mergeCommit"), dict) else None
    if back.get("state") != "MERGED" or not sha:
        return None, (gh_err or f"gh pr merge exited 0 but the PR reads back {back.get('state')}"
                      f" (merge commit {sha or 'none'})"), "", ""
    at = back.get("headRefOid")
    if at != facts["head"]:
        at = at[:12] if isinstance(at, str) and at else "an unreadable head"
        return None, (f"{facts['label']} reads back MERGED as {sha} at {at}, not the checked head "
                      f"{facts['head'][:12]} — not this run's merge" + (f" ({gh_err})" if gh_err else "")), "", sha
    return sha, "", (f"⚠ {gh_err} — read back MERGED" if gh_err else ""), ""


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
    dok, ddetail = cond_driver(a, pk)
    if a.cmd == "merge" and not dok:
        print(f"driver-merge: refused — merge is driver-only: {ddetail}")
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
        sha, why, gh_flag, elsewhere = merge(a, facts)
        if elsewhere:
            print(f"MERGED-ELSEWHERE {facts['label']} {elsewhere} — {why}; no `merged` event")
            emit_packet(a.repo, a.unit, facts["label"], [("merge", why)], [], None, elsewhere,
                        title="Merged past the checked head",
                        options=[("Review the unchecked commits", "You read what merged past the checked head and keep it."),
                                 ("Revert and re-run the unit", "The merge is reverted and the unit goes through the gate again.")],
                        kind="merge-elsewhere")
            return EXIT_REFUSED
        if sha:
            flags += [gh_flag] if gh_flag else []
            print(f"MERGED {facts['label']} {sha}" + (f" · {gh_flag}" if gh_flag else ""))
            body = f"repo={facts['slug']} pr={a.pr} base={facts['base']} sha={sha}" + "".join(f" · {f}" for f in flags)
            return EXIT_OK if post_event(a.repo, body) else EXIT_NO_EVENT
        failed = [("merge", why)]
        print(f"  [FAIL] merge: {why}")
    emit_packet(a.repo, a.unit, facts["label"], failed, facts["hits"], facts["range"], facts["head"])
    print("NOT MERGED — " + "; ".join(f"{n}: {d}" for n, d in failed))
    return EXIT_REFUSED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
