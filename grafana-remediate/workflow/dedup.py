#!/usr/bin/env python3
# Dedup + known-issues + handled-store + reopen semantics (scope 146, Phase 2, Task 2.2).
#
# Approach (scope Key Decisions): dedup = (a PR already links the alarm signature) OR
# (the signature is in a handled store). Either way, drop — this also caps daily token
# burn on alarms Alex simply hasn't reviewed yet. But dedup is on the NOTIFICATION, not
# the incident: a known-issue REOPENS on severity change, recurrence past a threshold,
# age, or a deploy-SHA change (autoplan finding — a worsening known-issue must not be
# silently suppressed).
#
# The store is a flat JSON file in the workflow home — no Postgres for a dedup ledger
# (scope Table Identity Map). classify.py already applies the static known_issues.json
# short-circuit; this module adds the dynamic, run-to-run handled memory + the gh
# linked-PR check + the reopen rule.
#
# Stdlib only (the gh check shells out to `gh`, which the caller may disable in dry-run).

import json
import subprocess
from pathlib import Path

STORE = Path(__file__).parent / "handled_store.json"


def signature_key(incident):
    """Stable identity of an alarm NOTIFICATION. Deliberately excludes volatile fields
    (timestamps, firing count) so the same recurring alarm keys consistently, while
    keeping the axes a reopen turns on (severity, deploy_sha) OUT of the key so a change
    in them produces a *different* record the reopen rule can compare against."""
    lab = incident.get("labels", {})
    return "|".join([
        incident.get("alertName", "?"),
        lab.get("env", "?"),
        lab.get("instance", ""),
    ])


def _reopen_axes(incident):
    lab = incident.get("labels", {})
    return {"severity": lab.get("severity", ""),
            "deploy_sha": lab.get("deploy_sha", ""),
            "firings": incident.get("firings", 0)}


def load_store(path=STORE):
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_store(store, path=STORE):
    Path(path).write_text(json.dumps(store, indent=2, sort_keys=True))


def should_reopen(incident, prior, recurrence_threshold=3):
    """A handled alarm reopens (is NOT deduped) when it has gotten worse:
    severity escalated, redeployed (new SHA), or recurrence crossed the threshold."""
    now = _reopen_axes(incident)
    if now["severity"] and now["severity"] != prior.get("severity", ""):
        return True, "severity changed"
    if now["deploy_sha"] and now["deploy_sha"] != prior.get("deploy_sha", ""):
        return True, "deploy SHA changed"
    if now["firings"] - prior.get("firings", 0) >= recurrence_threshold:
        return True, f"recurred +{now['firings'] - prior.get('firings', 0)}x"
    return False, ""


def linked_pr_exists(incident, repo, enabled=True):
    """A PR whose title/body references this alarm signature => already being handled.
    Best-effort: any gh failure returns False (do not dedup on a broken query)."""
    if not enabled or not repo:
        return False
    sig = incident.get("alertName", "")
    try:
        p = subprocess.run(
            ["gh", "pr", "list", "--repo", repo, "--state", "all",
             "--search", sig, "--json", "number", "--limit", "1"],
            capture_output=True, text=True, timeout=30)
        if p.returncode != 0:
            return False
        return len(json.loads(p.stdout or "[]")) > 0
    except Exception:
        return False


def is_duplicate(incident, store, repo=None, gh_enabled=True):
    """(drop, reason). Drop when a linked PR exists, OR the signature is in the handled
    store and the reopen rule does not fire."""
    if linked_pr_exists(incident, repo, enabled=gh_enabled):
        return True, "linked PR exists"
    sig = signature_key(incident)
    prior = store.get(sig)
    if prior:
        reopen, why = should_reopen(incident, prior)
        if reopen:
            return False, f"reopened: {why}"
        return True, "in handled store"
    return False, "new"


def record_handled(incident, store, outcome):
    """Remember that this notification was handled (emitted an email/PR), with the axes
    a future reopen compares against."""
    store[signature_key(incident)] = {**_reopen_axes(incident), "outcome": outcome}
    return store
