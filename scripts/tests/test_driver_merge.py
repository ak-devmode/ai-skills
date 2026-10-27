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

from _helpers import fake_herdr, load

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
RULE_LINT = {"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": "lint"}]}}
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
    ("PR edits its own CI -> one-way", {"path": ".github/workflows/ci.yml"}, 1,
     {"merged": False, "packet": "one-way", "says": ".github/workflows/"}),
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
    ("admin only when protection blocks", {"state": "BLOCKED"}, 0, {"merged": True, "admin": True}),
    # --admin bypasses required checks too: each one must be SUCCESS on the head (10.3-r1-03)
    ("BLOCKED: required check never reported", {"state": "BLOCKED", "protection": (0, {"contexts": ["ci", "e2e"]})},
     1, {"merged": False, "says": "e2e"}),
    ("BLOCKED: protection unreadable", {"state": "BLOCKED", "protection": (1, "HTTP 403: Forbidden")}, 1,
     {"merged": False, "says": "branch protection unreadable"}),
    ("BLOCKED: ruleset check missing", {"state": "BLOCKED", "protection": (1, "Branch not protected (HTTP 404)"),
                                        "rulesets": (0, [RULE_LINT])}, 1, {"merged": False, "says": "lint"}),
    ("BLOCKED: rulesets unreadable", {"state": "BLOCKED", "rulesets": (1, "HTTP 500")}, 1,
     {"merged": False, "says": "rulesets unreadable"}),
    ("BLOCKED: nothing required, admin", {"state": "BLOCKED", "protection": (1, "Branch not protected (HTTP 404)")},
     0, {"merged": True, "admin": True}),
    ("dirty refused", {"state": "DIRTY"}, 1, {"merged": False}),
    ("unknown state after retries", {"state": "UNKNOWN"}, 1, {"merged": False}),
    ("draft refused", {"draft": True}, 1, {"merged": False}),
    ("non-driver refused before gh", {"driver": False}, 1, {"merged": False, "no_gh": True, "packet": None}),
    # inside herdr only the pane herdr names `driver` merges; --driver is ignored there and a
    # failed lookup refuses (10.3-r2-01: nothing sets $HERDR_AGENT_NAME — herdr is asked)
    ("herdr lane pane with --driver refused", {"herdr": "lane"}, 1,
     {"merged": False, "no_gh": True, "packet": None, "says": "a lane"}),
    ("herdr unnamed pane with --driver refused", {"herdr": "unnamed"}, 1,
     {"merged": False, "no_gh": True, "packet": None, "says": "(unnamed)"}),
    ("herdr error with --driver refused", {"herdr": "error"}, 1,
     {"merged": False, "no_gh": True, "packet": None, "says": "fail closed"}),
    ("herdr pane not listed refused", {"herdr": "absent"}, 1,
     {"merged": False, "no_gh": True, "packet": None, "says": "0 agents for pane"}),
    ("herdr driver pane without flag merges", {"herdr": "driver", "driver": False}, 0, {"merged": True}),
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
              "mergeStateStatus": o.get("state", "CLEAN"), "url": "u", "statusCheckRollup": o.get("checks", GREEN)}

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
                key = "protection" if "/protection/" in args[1] else "rulesets"
                arc, body = o.get(key, (0, {"contexts": ["ci"], "checks": [{"context": "ci"}]} if key == "protection" else []))
                return (arc, "", body) if arc else (0, json.dumps(body), "")
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
            env.update(fake_herdr(self.tmp.name, o["herdr"], env["PATH"]))
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
                            self.assertIn(o.get("path") or "proto/a.proto", packets[0]["payload"]["body"])

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

    def test_event_failure_exits_4(self):
        o = {}
        with mock.patch.object(dm, "post_event", lambda repo, body: False):
            rc, out, calls, _, _ = self.run_case("merge", o)
        self.assertEqual(rc, 4, out)
        self.assertIn("MERGED", out)


if __name__ == "__main__":
    unittest.main()
