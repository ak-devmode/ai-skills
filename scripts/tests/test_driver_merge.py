"""Tests for scripts/driver-merge.py (scope 10 §4.3, plan 10.3 tasks 3.1 + 3.2).

Approach: table-driven over a stubbed `gh` — the module is loaded by path and its one gh
entry point replaced with a fake that serves a scenario's PR JSON and records every call, so
nothing touches the network. Everything else is real: a temp git repo (origin URL set, never
contacted), a temp scope with a review log, door.py on the real diff, and packet.py writing the
refusal packet / merged event into the temp repo's outbox. verdict-gate.py is stubbed to its
exit-0 answer except where a case says otherwise (its own suite covers it).
"""
import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from _helpers import load

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
    ("gate blocked", {"gate": (False, "verdict-gate.py blocked (exit 1)", "")}, 1, {"merged": False}),
    ("gate advisory flagged", {"gate": (True, "gate advisory", "⚠ verify advisory: 1 blocked")}, 0,
     {"merged": True, "event": "verify advisory"}),
    ("code commit after review", {"after_review": "app/late.go"}, 1, {"merged": False, "says": "past review"}),
    ("plans-only commit after review", {"after_review": "plans/progress.md"}, 0, {"merged": True}),
    ("admin only when protection blocks", {"state": "BLOCKED"}, 0, {"merged": True, "admin": True}),
    ("dirty refused", {"state": "DIRTY"}, 1, {"merged": False}),
    ("unknown state after retries", {"state": "UNKNOWN"}, 1, {"merged": False}),
    ("draft refused", {"draft": True}, 1, {"merged": False}),
    ("non-driver refused before gh", {"driver": False}, 1, {"merged": False, "no_gh": True, "packet": None}),
    ("gh error -> no merge", {"gh_view_rc": 1}, 1, {"merged": False, "says": "could not evaluate"}),
    ("merge call fails", {"merge_rc": 1}, 1, {"merged": False, "packet": "two-way"}),
    ("merge not read back", {"readback": "OPEN"}, 1, {"merged": False, "says": "reads back OPEN"}),
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
        head = commit(repo, o.get("path") or ("proto/a.proto" if o.get("floor") else "app/a.go"), "y\n", "change")
        reviewed = head
        if o.get("after_review"):
            head = commit(repo, o["after_review"], "z\n", "later")
        scope = os.path.join(root, "scope")
        os.makedirs(os.path.join(scope, "artifacts"))
        recs = [{"record": "review", "review_id": "10.3-r1", "reviewer": o.get("reviewer", "codex sol"),
                 "verdict": o.get("verdict", "SHIP"), "range": {name: f"{base}..{reviewed}"},
                 "shas": {"base": base, "head": reviewed}}]
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
                if "state,mergeCommit" in args:
                    st = o.get("readback", "MERGED")
                    return 0, json.dumps({"state": st, "mergeCommit": {"oid": "f" * 40} if st == "MERGED" else None}), ""
                return 0, json.dumps(pr), ""
            if args[:2] == ("pr", "merge"):
                return o.get("merge_rc", 0), "", "merge failed" if o.get("merge_rc") else ""
            return 1, "", "unexpected gh call"
        return gh

    def run_case(self, cmd, o):
        repo, scope, base, head = self.build(o)
        calls = []
        env = {k: v for k, v in os.environ.items() if k not in ("DECISION_QUEUE_URL", "HERDR_AGENT_NAME")}
        env["CLAUDE_CODE_SESSION_ID"] = "test-session"
        argv = [cmd, "--repo", repo, "--pr", "7", "--scope", scope, "--unit", "10.3"]
        if o.get("driver", True):
            argv.append("--driver")
        out = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(dm, "gh", self.fake_gh(o, base, head, calls)), \
                mock.patch.object(dm, "run_gate", lambda s, u: o.get("gate", (True, "gate pass", ""))), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = dm.main(argv)
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
                    self.assertIn("NOT MERGED" if not want.get("no_gh") else "refused", out)
                    self.assertEqual(events, [])
                    if not o.get("merge_rc") and not o.get("readback"):
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
            if o.get("merge_rc") or o.get("readback"):
                continue  # merge-only failures: check is eligible there
            with self.subTest(name):
                rc, out, calls, packets, events = self.run_case("check", o)
                want = 1 if (want_rc or o.get("driver") is False) else 0
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
