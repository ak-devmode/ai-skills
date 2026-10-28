"""Tests for scripts/driver-merge.py (scope 10 §4.3, plan 10.3 tasks 3.1 + 3.2).

Approach: table-driven over a stubbed `gh` — the module is loaded by path and its one gh
entry point replaced with a fake that serves a scenario's PR JSON and records every call, so
nothing touches the network. Everything else is real: a temp git repo (origin URL set, never
contacted), a temp scope with a review log, door.py on the real diff, and packet.py writing the
refusal packet / merged event into the temp repo's outbox. verdict-gate.py's subprocess is
stubbed to a (exit, JSON) answer — `pass` unless a case says otherwise (its own suite covers
it) — so run_gate's own reading of that answer is what the table exercises.
"""
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from _helpers import dispatch_env, load

dm = load("driver-merge.py")
dm.UNKNOWN_SLEEP = 0


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout.strip()


def readj(path):
    with open(path) as f:
        return json.load(f)


def commit(repo, path, text, msg):
    full = os.path.join(repo, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(text)
    git(repo, "add", path)
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


GREEN = [{"__typename": "CheckRun", "name": "ci", "status": "COMPLETED", "conclusion": "SUCCESS"}]
APP = 15368


def run(name, app, conclusion="success"):
    return {"name": name, "status": "completed", "conclusion": conclusion, "app": {"id": app, "slug": "a"}}


BOUND_CI = {"contexts": ["ci"], "checks": [{"context": "ci", "app_id": APP}]}
BOUND_E2E = {"contexts": ["ci", "e2e"], "checks": [{"context": "ci", "app_id": None}, {"context": "e2e", "app_id": APP}]}
RULE_CI_BOUND = {"type": "required_status_checks",
                 "parameters": {"required_status_checks": [{"context": "ci", "integration_id": APP}]}}
RULE_LINT = {"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": "lint"}]}}
# the classic protection document as GitHub serves it for wellmed-backbone `develop` (2026-10-28)
LIVE_CLASSIC = {"url": "u", "required_pull_request_reviews": {"required_approving_review_count": 1},
                "required_signatures": {"url": "u", "enabled": False}, "enforce_admins": {"enabled": False},
                "required_linear_history": {"enabled": False}, "allow_force_pushes": {"enabled": False},
                "allow_deletions": {"enabled": False}, "block_creations": {"enabled": False},
                "required_conversation_resolution": {"enabled": False}, "lock_branch": {"enabled": False},
                "allow_fork_syncing": {"enabled": False}}
NOT_PROTECTED = (1, "Branch not protected (HTTP 404)")
SKIPPED = [{"__typename": "CheckRun", "name": "ci", "status": "COMPLETED", "conclusion": "SKIPPED"},
           {"__typename": "StatusContext", "context": "x", "state": "NEUTRAL"}]

# name, overrides — defaults: code repo, develop base, green, CLEAN, codex SHIP, driver, app change
CASES = [
    ("eligible clean merge", {}, 0, {"merged": True, "admin": False}),
    ("vacuous green: no checks", {"checks": []}, 1, {"merged": False, "says": "vacuous green — no checks"}),
    ("skipped/neutral only", {"checks": SKIPPED}, 1, {"merged": False, "says": "all skipped/neutral"}),
    ("pending check", {"checks": [{"__typename": "CheckRun", "name": "ci", "status": "IN_PROGRESS"}]}, 1,
     {"merged": False, "says": "ci: IN_PROGRESS"}),
    ("failed status context", {"checks": GREEN + [{"__typename": "StatusContext", "context": "d", "state": "FAILURE"}]},
     1, {"merged": False, "says": "d: FAILURE"}),
    ("unknown check type", {"checks": [{"__typename": "Mystery", "name": "m"}]}, 1, {"merged": False}),
    ("prod base on code repo", {"base": "main"}, 1, {"merged": False, "says": "is prod"}),
    ("odd base on code repo", {"base": "release"}, 1, {"merged": False, "says": "not this repo's merge target"}),
    ("docs repo merges to main", {"name": "kalpa-docs", "base": "main"}, 0, {"merged": True}),
    ("docs repo refuses develop", {"name": "kalpa-docs", "base": "develop"}, 1, {"merged": False}),
    ("floor hit -> one-way packet", {"floor": True}, 1, {"merged": False, "packet": "one-way", "says": "proto"}),
    # CI definitions never auto-merge, but a CI edit is reversible: a two-way "CI change" packet,
    # not the one-way floor (10.3-r2-04; the floor rows moved here from test_door)
    *[(f"PR edits CI {p} -> two-way", {"path": p}, 1, {"merged": False, "packet": "two-way", "says": pat})
      for p, pat in [(".github/workflows/ci.yml", ".github/workflows/"),
                     (".github/actions/setup/action.yml", ".github/actions/"),
                     (".github/CODEOWNERS", "CODEOWNERS"), (".circleci/config.yml", ".circleci/"),
                     (".gitlab-ci.yml", ".gitlab-ci.yml"), ("Jenkinsfile", "Jenkinsfile"),
                     ("buildspec-dev.yml", "buildspec*.yml")]],
    ("degraded review merges, flagged", {"reviewer": "claude-lean subscription"}, 0,
     {"merged": True, "event": "degraded review: claude-lean"}),
    ("no reviewer is no review", {"reviewer": "none codex down"}, 1, {"merged": False}),
    ("DO NOT SHIP not accepted", {"verdict": "DO NOT SHIP"}, 1, {"merged": False, "packet": "two-way"}),
    ("non-SHIP accepted merges", {"verdict": "SHIP AFTER BLOCKING", "accepted": True}, 0, {"merged": True}),
    ("gate blocked", {"gate": (1, {"verdict": "blocked"})}, 1, {"merged": False, "says": "blocked (exit 1)"}),
    # advisory exits 0 on every block: "reported" is not "passed" (10.3-r1-01)
    ("gate advisory refused", {"gate": (0, {"verdict": "advisory", "marker": "⚠ verify advisory: 1 blocked"})}, 1,
     {"merged": False, "says": "advisory (exit 0)"}),
    ("gate predates refused", {"gate": (0, {"verdict": "predates-gate"})}, 1, {"merged": False}),
    ("gate unknown verdict refused", {"gate": (0, {"verdict": "mystery"})}, 1, {"merged": False}),
    ("gate output unreadable", {"gate": (0, "not json")}, 1, {"merged": False, "says": "unreadable"}),
    ("gate pass marker flagged", {"gate": (0, {"verdict": "pass", "marker": "⚠ judge: claude"})}, 0,
     {"merged": True, "event": "⚠ judge: claude"}),
    ("code commit after review", {"after_review": "app/late.go"}, 1, {"merged": False, "says": "past review"}),
    ("plans-only commit after review", {"after_review": "plans/progress.md"}, 0, {"merged": True}),
    # every PR commit must sit in some review range of this repo in THIS unit (10.3-r1-04)
    ("code commit before review base", {"pre_base": "app/early.go"}, 1, {"merged": False, "says": "unreviewed commits: 1"}),
    ("stacked branch: other unit's commit", {"pre_base": "app/other.go", "stacked": True}, 1,
     {"merged": False, "says": "unreviewed commits: 1"}),
    ("plans-only commit before review base", {"pre_base": "plans/notes.md"}, 0, {"merged": True}),
    ("two reviews cover the range", {"split_review": True}, 0, {"merged": True}),
    # --admin only when GitHub says a review approval is what is missing (Alex 83, 10.3-r3-01)
    ("admin: only review missing, checks green", {"state": "BLOCKED"}, 0, {"merged": True, "admin": True}),
    ("BLOCKED but approved: something else blocks", {"state": "BLOCKED", "review": "APPROVED"}, 1,
     {"merged": False, "packet": "two-way", "says": "reviewDecision APPROVED"}),
    ("BLOCKED, no review required", {"state": "BLOCKED", "review": None}, 1,
     {"merged": False, "says": "reviewDecision none"}),
    # every entry of a required name must be satisfied: GitHub requires a same-named status AND run
    ("BLOCKED: green run + failing status, same context", {"state": "BLOCKED", "checks": GREEN + [
        {"__typename": "StatusContext", "context": "ci", "state": "FAILURE"}]}, 1,
     {"merged": False, "says": "not satisfied on the head: ci"}),
    ("BLOCKED: two same-app runs, one failing", {"state": "BLOCKED", "protection": (0, BOUND_CI),
                                                 "check_runs": (0, [run("ci", APP), run("ci", APP, "failure")])}, 1,
     {"merged": False, "says": f"not satisfied on the head: ci (app {APP})"}),
    ("BLOCKED: bound run pending beside a green one", {"state": "BLOCKED", "protection": (0, BOUND_CI),
                                                       "check_runs": (0, [run("ci", APP), dict(run("ci", APP), status="in_progress", conclusion=None)])}, 1,
     {"merged": False, "says": f"ci (app {APP})"}),
    # --admin bypasses required checks too: each one must be SUCCESS on the head (10.3-r1-03)
    ("BLOCKED: required check never reported", {"state": "BLOCKED", "protection": (0, {"contexts": ["ci", "e2e"]})},
     1, {"merged": False, "says": "e2e"}),
    ("BLOCKED: protection unreadable", {"state": "BLOCKED", "protection": (1, "HTTP 403: Forbidden")}, 1,
     {"merged": False, "says": "branch protection unreadable"}),
    ("BLOCKED: ruleset check missing", {"state": "BLOCKED", "protection": (1, "Branch not protected (HTTP 404)"),
                                        "rulesets": (0, [RULE_LINT])}, 1, {"merged": False, "says": "lint"}),
    ("BLOCKED: rulesets unreadable", {"state": "BLOCKED", "rulesets": (1, "HTTP 500")}, 1,
     {"merged": False, "says": "rulesets unreadable"}),
    # a required check on a later rulesets page is still required; an unreadable page refuses (10.3-r2-06)
    ("BLOCKED: ruleset check on page 2", {"state": "BLOCKED", "protection": (1, "Branch not protected (HTTP 404)"),
                                          "rulesets": (0, [[], [RULE_LINT]]), "paged": True}, 1,
     {"merged": False, "says": "lint"}),
    ("BLOCKED: rulesets page unreadable", {"state": "BLOCKED", "rulesets": (0, [[], {"message": "x"}]), "paged": True},
     1, {"merged": False, "says": "read incomplete"}),
    # GitHub counts a required check skipped by `if:` (SKIPPED/NEUTRAL) as passing; absent still refuses (10.3-r2-05)
    ("BLOCKED: required check skipped, admin", {"state": "BLOCKED", "protection": (0, {"contexts": ["ci", "e2e"]}),
                                                "checks": GREEN + [{"__typename": "CheckRun", "name": "e2e",
                                                                    "status": "COMPLETED", "conclusion": "SKIPPED"}]},
     0, {"merged": True, "admin": True}),
    # a required check bound to an app (classic app_id, ruleset integration_id) is satisfied only by a
    # check run from THAT app — a same-named commit status anyone can post is not it (10.3-r2-03)
    ("BLOCKED: bound check from its app, admin", {"state": "BLOCKED", "protection": (0, BOUND_CI),
                                                  "check_runs": (0, [run("ci", APP)])},
     0, {"merged": True, "admin": True}),
    ("BLOCKED: bound check posted as a status", {"state": "BLOCKED", "protection": (0, BOUND_E2E),
                                                 "checks": GREEN + [{"__typename": "StatusContext", "context": "e2e",
                                                                     "state": "SUCCESS"}],
                                                 "check_runs": (0, [run("ci", APP)])},
     1, {"merged": False, "says": f"e2e (app {APP})"}),
    ("BLOCKED: bound check from another app", {"state": "BLOCKED", "protection": (0, BOUND_CI),
                                               "check_runs": (0, [run("ci", 999)])},
     1, {"merged": False, "says": f"ci (app {APP})"}),
    ("BLOCKED: ruleset integration_id bound", {"state": "BLOCKED", "protection": (1, "Branch not protected (HTTP 404)"),
                                               "rulesets": (0, [RULE_CI_BOUND]), "check_runs": (0, [run("ci", 999)])},
     1, {"merged": False, "says": f"ci (app {APP})"}),
    ("BLOCKED: check runs unreadable, bound", {"state": "BLOCKED", "protection": (0, BOUND_CI),
                                               "check_runs": (1, "HTTP 502")},
     1, {"merged": False, "says": "binding cannot be verified"}),
    ("BLOCKED: app_id -1 is any source, admin", {"state": "BLOCKED",
                                                 "protection": (0, {"checks": [{"context": "ci", "app_id": -1}]})},
     0, {"merged": True, "admin": True}),
    # --admin bypasses EVERY protection requirement, not just reviews and checks: any other one,
    # or one this script does not model, refuses it (10.3-r4-01, Alex 83)
    *[(f"BLOCKED: classic {k} enabled", {"state": "BLOCKED", "classic": {k: {"enabled": True}}}, 1,
       {"merged": False, "says": f"more than checks and a review: {k}"})
      for k in ("required_signatures", "required_conversation_resolution", "lock_branch", "required_linear_history")],
    ("BLOCKED: classic required_deployments", {"state": "BLOCKED", "classic": {"required_deployments":
                                                                              {"required_deployment_environments": ["staging"]}}},
     1, {"merged": False, "says": "required_deployments"}),
    ("BLOCKED: classic field not modelled", {"state": "BLOCKED", "classic": {"required_merge_queue": {"enabled": False}}},
     1, {"merged": False, "says": "required_merge_queue (not modelled)"}),
    ("BLOCKED: classic flag unreadable", {"state": "BLOCKED", "classic": {"lock_branch": {"enabled": "yes"}}},
     1, {"merged": False, "says": "lock_branch unreadable"}),
    *[(f"BLOCKED: ruleset {t}", {"state": "BLOCKED", "protection": NOT_PROTECTED, "rulesets": (0, [{"type": t}])}, 1,
       {"merged": False, "says": f"ruleset {t}"})
      for t in ("required_signatures", "code_scanning", "workflows", "merge_queue", "required_deployments", "deletion")],
    ("BLOCKED: ruleset thread resolution", {"state": "BLOCKED", "protection": NOT_PROTECTED, "rulesets": (0, [
        {"type": "pull_request", "parameters": {"required_approving_review_count": 1,
                                                "required_review_thread_resolution": True}}])},
     1, {"merged": False, "says": "ruleset required_review_thread_resolution"}),
    ("BLOCKED: ruleset review + checks only, admin", {"state": "BLOCKED", "protection": NOT_PROTECTED, "rulesets": (0, [
        {"type": "pull_request", "parameters": {"required_approving_review_count": 1,
                                                "required_review_thread_resolution": False}},
        {"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": "ci"}]}}])},
     0, {"merged": True, "admin": True}),
    ("BLOCKED: nothing required, admin", {"state": "BLOCKED", "protection": (1, "Branch not protected (HTTP 404)")},
     0, {"merged": True, "admin": True}),
    ("dirty refused", {"state": "DIRTY"}, 1, {"merged": False}),
    ("unknown state after retries", {"state": "UNKNOWN"}, 1, {"merged": False}),
    ("draft refused", {"draft": True}, 1, {"merged": False}),
    ("non-driver refused before gh", {"driver": False}, 1, {"merged": False, "no_gh": True, "packet": None}),
    # inside herdr only a pane registered as the driver on this host merges; every other pane is a
    # lane, refused before any gh call; an unreadable log refuses (Alex 86, 10.3-r4-03)
    ("registered driver pane merges", {"herdr": "driver"}, 0, {"merged": True}),
    *[(f"herdr pane {m} refused", {"herdr": m}, 1,
       {"merged": False, "no_gh": True, "packet": None, "says": "no driver registration on this host"})
      for m in ("lane", "unregistered", "reused", "none", "alias", "blank-host", "other-host")],
    ("dispatch log unreadable refused", {"herdr": "unreadable"}, 1,
     {"merged": False, "no_gh": True, "packet": None, "says": "fail closed"}),
    ("herdr pane without --driver refused", {"herdr": "none", "driver": False}, 1,
     {"merged": False, "no_gh": True, "packet": None, "says": "no --driver"}),
    ("gh error -> no merge", {"gh_view_rc": 1}, 1, {"merged": False, "says": "could not evaluate"}),
    ("merge call fails", {"merge_rc": 1, "readback": "OPEN"}, 1, {"merged": False, "packet": "two-way",
                                                                  "says": "gh pr merge failed"}),
    # gh can exit non-zero after GitHub merged: the read-back decides (10.3-r1-06)
    ("merge rc!=0 but landed", {"merge_rc": 1}, 0, {"merged": True, "event": "gh pr merge failed"}),
    ("merge not read back", {"readback": "OPEN"}, 1, {"merged": False, "says": "reads back OPEN"}),
    # only a read-back AT the checked head is this run's merge: a failed gh may mean the head moved
    # and someone merged it there — no `merged` event for commits no condition checked (10.3-r2-02)
    ("merge rc!=0, landed at another head", {"merge_rc": 1, "readback_head": "e" * 40}, 1,
     {"merged": False, "packet": "two-way", "says": "MERGED-ELSEWHERE"}),
    ("merge rc=0, read back at another head", {"readback_head": "e" * 40}, 1,
     {"merged": False, "packet": "two-way", "says": "not the checked head"}),
    ("read-back head unreadable", {"merge_rc": 1, "readback_head": None}, 1,
     {"merged": False, "packet": "two-way", "says": "an unreadable head"}),
]


class DriverMergeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def build(self, o):
        name = o.get("name", "wellmed-demo")
        root = tempfile.mkdtemp(dir=self.tmp.name)
        repo = os.path.join(root, name)
        os.makedirs(repo)
        git(repo, "init", "-q", "-b", "develop")
        git(repo, "config", "user.email", "t@example.invalid")
        git(repo, "config", "user.name", "t")
        git(repo, "remote", "add", "origin", f"git@github-alias:Owner/{name}.git")
        base = commit(repo, "README.md", "x\n", "base")
        git(repo, "checkout", "-q", "-b", "feature/x")
        rbase = commit(repo, o["pre_base"], "p\n", "before the review base") if o.get("pre_base") else base
        head = commit(repo, o.get("path") or ("proto/a.proto" if o.get("floor") else "app/a.go"), "y\n", "change")
        mid = head
        if o.get("split_review"):
            head = commit(repo, "app/b.go", "b\n", "fix round")
        reviewed = head
        if o.get("after_review"):
            head = commit(repo, o["after_review"], "z\n", "later")
        scope = os.path.join(root, "scope")
        os.makedirs(os.path.join(scope, "artifacts"))
        rv = {"record": "review", "reviewer": o.get("reviewer", "codex sol"), "verdict": o.get("verdict", "SHIP")}
        recs = ([dict(rv, review_id="10.3-r1", verdict="SHIP AFTER BLOCKING", range={name: f"{rbase}..{mid}"},
                      shas={"base": rbase, "head": mid})] if o.get("split_review") else []) + \
            [dict(rv, review_id="10.3-r" + ("2" if o.get("split_review") else "1"),
                  range={name: f"{mid if o.get('split_review') else rbase}..{reviewed}"},
                  shas={"base": mid if o.get("split_review") else rbase, "head": reviewed})]
        if o.get("stacked"):  # the pre-base commit was reviewed — in ANOTHER unit's log
            with open(os.path.join(scope, "artifacts", "review-10.2.jsonl"), "w") as f:
                f.write(json.dumps(dict(rv, review_id="10.2-r1", range={name: f"{base}..{rbase}"})) + "\n")
        if o.get("accepted"):
            recs.append({"record": "acceptance", "by": "Alex (standing policy)"})
        with open(os.path.join(scope, "artifacts", "review-10.3.jsonl"), "w") as f:
            f.write("".join(json.dumps(r) + "\n" for r in recs))
        return repo, scope, base, head

    def fake_gh(self, o, base, head, calls):
        pr = {"number": 7, "state": "OPEN", "isDraft": o.get("draft", False), "baseRefName": o.get("base", "develop"),
              "headRefName": "feature/x", "baseRefOid": base, "headRefOid": head,
              "mergeStateStatus": o.get("state", "CLEAN"), "reviewDecision": o.get("review", "REVIEW_REQUIRED"), "url": "u", "statusCheckRollup": o.get("checks", GREEN)}

        def gh(*args):
            calls.append(args)
            if args[:2] == ("pr", "view"):
                if o.get("gh_view_rc"):
                    return 1, "", "HTTP 502: bad gateway"
                if "state,mergeCommit,headRefOid" in args:
                    st = o.get("readback", "MERGED")
                    return 0, json.dumps({"state": st, "mergeCommit": {"oid": "f" * 40} if st == "MERGED" else None,
                                          "headRefOid": o.get("readback_head", head)}), ""
                return 0, json.dumps(pr), ""
            if args[0] == "api":
                path = args[-1]
                if "/check-runs" in path:  # one page, as --paginate --slurp serves it
                    crc, runs = o.get("check_runs", (0, []))
                    if crc:
                        return crc, "", runs
                    return 0, json.dumps([{"total_count": len(runs), "check_runs": runs}]), ""
                key = "protection" if path.endswith("/protection") else "rulesets"
                arc, body = o.get(key, (0, {"contexts": ["ci"], "checks": [{"context": "ci"}]} if key == "protection" else []))
                if arc:
                    return arc, "", body
                if key == "protection":  # the full classic document: o["protection"] is its checks part
                    body = dict(LIVE_CLASSIC, required_status_checks=body, **o.get("classic", {}))
                if key == "rulesets":  # served as pages: o["rulesets"] is one page unless "paged"
                    pages = body if o.get("paged") else [body]
                    if "--paginate" not in args:
                        return 0, json.dumps(pages[0]), ""
                    return 0, json.dumps(pages if "--slurp" in args else pages[0]), ""
                return 0, json.dumps(body), ""
            if args[:2] == ("pr", "merge"):
                return o.get("merge_rc", 0), "", "merge failed" if o.get("merge_rc") else ""
            return 1, "", "unexpected gh call"
        return gh

    def run_case(self, cmd, o):
        repo, scope, base, head = self.build(o)
        calls = []
        env = {k: v for k, v in os.environ.items() if k != "DECISION_QUEUE_URL" and not k.startswith("HERDR_")}
        env["CLAUDE_CODE_SESSION_ID"] = "test-session"
        if o.get("herdr"):
            env.update(dispatch_env(self.tmp.name, o["herdr"]))
        argv = [cmd, "--repo", repo, "--pr", "7", "--scope", scope, "--unit", "10.3"]
        if o.get("driver", True):
            argv.append("--driver")
        out = io.StringIO()
        real_sh, gates = dm.sh, []

        def fake_sh(cmd, cwd=None, timeout=120):
            if dm.VERDICT_GATE not in cmd:
                return real_sh(cmd, cwd=cwd, timeout=timeout)
            gates.append(cmd)
            grc, gdoc = o.get("gate", (0, {"verdict": "pass", "marker": ""}))
            return grc, gdoc if isinstance(gdoc, str) else json.dumps(gdoc) + "\n", ""
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(dm, "gh", self.fake_gh(o, base, head, calls)), \
                mock.patch.object(dm, "sh", fake_sh), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = dm.main(argv)
        self.assertTrue(all("--blocking" in g for g in gates), gates)
        outbox = os.path.join(repo, ".decision-queue", "outbox")
        files = sorted(os.listdir(outbox)) if os.path.isdir(outbox) else []
        packets = [readj(os.path.join(outbox, f)) for f in files
                   if f.startswith("pk") and f.endswith(".json") and not f.endswith(".state.json")]
        events = [readj(os.path.join(outbox, f)) for f in files if f.startswith("evt-")]
        return rc, out.getvalue(), calls, packets, events

    def test_merge_table(self):
        for name, o, want_rc, want in CASES:
            with self.subTest(name):
                rc, out, calls, packets, events = self.run_case("merge", o)
                merges = [c for c in calls if c[:2] == ("pr", "merge")]
                self.assertEqual(rc, want_rc, out)
                self.assertTrue(all("--auto" not in c for c in calls), "auto-merge must never be set")
                if want.get("says"):
                    self.assertIn(want["says"], out)
                if want.get("no_gh"):
                    self.assertEqual(calls, [])
                if want["merged"]:
                    self.assertEqual(len(merges), 1, out)
                    self.assertIn("--match-head-commit", merges[0])
                    self.assertEqual("--admin" in merges[0], bool(want.get("admin")), merges[0])
                    self.assertIn("MERGED Owner/", out)
                    self.assertEqual([e["kind"] for e in events], ["merged"], out)
                    self.assertIn("pr=7", events[0]["body"])
                    self.assertIn("sha=" + "f" * 40, events[0]["body"])
                    self.assertEqual(packets, [])
                    if want.get("event"):
                        self.assertIn(want["event"], events[0]["body"])
                else:
                    self.assertIn("refused" if want.get("no_gh") else
                                  "MERGED-ELSEWHERE" if "readback_head" in o else "NOT MERGED", out)
                    self.assertEqual(events, [])
                    if not o.get("merge_rc") and not o.get("readback") and "readback_head" not in o:
                        self.assertEqual(merges, [], "a refused PR must never reach gh pr merge")
                    door = want.get("packet", "two-way") if "packet" in want else "two-way"
                    if door is None:
                        self.assertEqual(packets, [])
                    else:
                        self.assertEqual([p["door"] for p in packets], [door], out)
                        if door == "one-way":
                            self.assertIn(o.get("path") or "proto/a.proto", packets[0]["evidence"])
                        if o.get("path"):  # a CI change: Alex reviews and merges by hand
                            self.assertIn(o["path"], packets[0]["evidence"])
                            self.assertIn("CI change", json.dumps(packets[0]))

    def test_check_never_merges_or_writes(self):
        for name, o, want_rc, _ in CASES:
            if o.get("merge_rc") or o.get("readback") or "readback_head" in o:
                continue  # merge-only failures: check is eligible there
            with self.subTest(name):
                rc, out, calls, packets, events = self.run_case("check", o)
                want = 1 if want_rc else 0
                self.assertEqual(rc, want, out)
                self.assertEqual([c for c in calls if c[:2] == ("pr", "merge")], [])
                self.assertEqual((packets, events), ([], []))

    def test_refusal_then_merged_elsewhere_is_a_second_packet(self):  # 10.3-r3-03
        # a re-run after a two-way refusal on head H finds the PR merged past H: the old card
        # must not be re-sent in place of "Merged past the checked head"
        built = self.build({})
        with mock.patch.object(self, "build", lambda o: built):
            rc1, out1, _, p1, _ = self.run_case("merge", {"checks": []})
            rc2, out2, _, p2, _ = self.run_case("merge", {"merge_rc": 1, "readback_head": "e" * 40})
        self.assertEqual((rc1, rc2), (1, 1), out2)
        self.assertIn("MERGED-ELSEWHERE", out2)
        self.assertEqual(len(p1), 1)
        self.assertEqual(len(p2), 2, out2)
        new = [p for p in p2 if p["id"] != p1[0]["id"]][0]
        self.assertIn("Merged past the checked head", new["title"])
        self.assertIn("f" * 12, new["id"])  # keyed on the merge commit that landed

    def test_refusal_id_tracks_the_case(self):  # 10.3-r3-03 siblings: what differs must reach the id
        repo = self.build({})[0]
        label = "Some-Long-Organisation/a-rather-long-repository-name#1234"
        cases = [([("checks", "pending")], "a" * 40), ([("checks", "x")], "a" * 40),
                 ([("mergeable", "UNSTABLE")], "a" * 40), ([("checks", "pending")], "b" * 40)]
        with contextlib.redirect_stdout(io.StringIO()):
            ids = [dm.emit_packet(repo, "10.3", label, failed, [], None, head) for failed, head in cases]
        self.assertTrue(all(ids), ids)
        self.assertEqual(ids[0], ids[1], "same failed conditions, same head: idempotent")
        self.assertEqual(len({ids[0], ids[2], ids[3]}), 3, ids)  # another condition / head: a new card
        # 10.3-r4-06: the new card for the same head supersedes the open one; another head's stays open
        outbox = os.path.join(repo, ".decision-queue", "outbox")
        status = lambda pid: readj(os.path.join(outbox, f"{pid}.state.json"))["status"]
        self.assertEqual([status(i) for i in (ids[0], ids[2], ids[3])], ["stale", "open", "open"])
        stale_ev = [readj(os.path.join(outbox, f)) for f in os.listdir(outbox) if f.startswith("evt-")]
        self.assertIn(f"superseded by {ids[2]}", [e["body"] for e in stale_ev if e.get("packet_id") == ids[0]])
        with contextlib.redirect_stdout(io.StringIO()):  # another PR on the same head is not superseded
            other = dm.emit_packet(repo, "10.3", label + "5", [("checks", "y")], [], None, "b" * 40)
        self.assertEqual((status(ids[3]), status(other)), ("open", "open"))
        with contextlib.redirect_stdout(io.StringIO()):  # the first case comes back: a fresh open card
            back = dm.emit_packet(repo, "10.3", label, [("checks", "pending")], [], None, "a" * 40)
        self.assertNotIn(back, ids)
        self.assertEqual((status(back), status(ids[2])), ("open", "stale"))

    def test_event_failure_exits_4(self):
        o = {}
        with mock.patch.object(dm, "post_event", lambda repo, body: False):
            rc, out, calls, _, _ = self.run_case("merge", o)
        self.assertEqual(rc, 4, out)
        self.assertIn("MERGED", out)


if __name__ == "__main__":
    unittest.main()
