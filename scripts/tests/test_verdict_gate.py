"""verdict-gate.py, ledger-init.sh --repo, plans-index.py status/validate — end to end.

Approach: every verdict here is produced by the real runner (verify-run.py run → judged
→ finalize) against a throwaway repo, never hand-written, so the gate is tested against
exactly what it will read in use. Each test builds a plans dir with a PLANS-INDEX row,
a scope folder, a finish table and a ledger, under a fake projects root passed through
VERIFY_PROJECTS.
"""

import json
import os
import subprocess
import tempfile
import unittest

from _helpers import run, script

HEADER = ("| check_id | deliverable | owner | class | check | repo | dir | env | timeout | rung "
          "| unreachable_ok | evidence |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n")
INDEX = ("# Plans\n\n## Active Plans\n\n| # | Status | Folder | Description | Created by |\n"
         "|---|---|---|---|---|\n| 5 | 🔄 In progress | `5-x/` | scope | t |\n"
         "| 5.1 | 🔄 In progress | `5-x/` | phase one | t |\n\n## Completed / Archived\n\n"
         "| # | Status | Folder | Description | Created by |\n|---|---|---|---|---|\n")
FIELDS = ("expected ·", "found    ·", "where    ·", "cause    ·", "next     ·", "docs     ·")


def git(path, *args):
    return subprocess.run(["git", "-C", path, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          check=True, capture_output=True, text=True).stdout.strip()


def row(cid, check, owner="5.1", rung="4", ok="no"):
    return f"| {cid} | d | {owner} | B | `{check}` | svc | . | - | - | {rung} | {ok} | ev |\n"


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.projects = os.path.join(root, "projects")
        self.svc = os.path.join(self.projects, "svc")
        os.makedirs(self.svc)
        git(self.svc, "init", "-q", "-b", "main")
        git(self.svc, "commit", "-q", "--allow-empty", "-m", "a")
        self.plans = os.path.join(self.projects, "plans")  # private: no origin → not public
        self.scope = os.path.join(self.plans, "5-x")
        os.makedirs(os.path.join(self.scope, "artifacts"))
        git(self.projects, "init", "-q", "-b", "main")  # the log's destination is a git repo
        self.index = os.path.join(self.plans, "PLANS-INDEX.md")
        with open(self.index, "w") as fh:
            fh.write(INDEX)
        self.plan = os.path.join(self.scope, "5.1-x-PLAN.md")
        open(self.plan, "w").close()
        self.env = dict(os.environ, VERIFY_PROJECTS=self.projects)
        self.log = os.path.join(self.scope, "artifacts", "verify-5.1.jsonl")
        self.set_table([row("ok", "true")])

    def tearDown(self):
        self.tmp.cleanup()

    # ---- helpers
    def set_table(self, rows, rev=1):
        self.table = os.path.join(self.scope, "finish-conditions.md")
        with open(self.table, "w") as fh:
            fh.write(f"# t\n\n**Schema version:** verify/1\n**Revision:** {rev}\n\n{HEADER}{''.join(rows)}\n")

    def ledger(self, *extra):
        p = subprocess.run(["bash", script("ledger-init.sh"), self.scope, "--plan", self.plan,
                            "--phase", "1: x", "--repo", self.svc, *extra],
                           capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p

    def verify(self, judge=None, items=None):
        """run → (judged) → finalize; returns run_id."""
        p = run("verify-run.py", "run", "--table", self.table, "--log", self.log, "--owner", "5.1", env=self.env)
        rid = p.stdout.split("run_id: ")[1].split()[0]
        if items is not None:
            path = os.path.join(self.tmp.name, "j.json")
            with open(path, "w") as fh:
                json.dump(items, fh)
            j = run("verify-run.py", "judged", "--log", self.log, "--run-id", rid, "--judge", judge,
                    "--input", path, env=self.env)
            self.assertEqual(j.returncode, 0, j.stderr)
            run("verify-run.py", "finalize", "--log", self.log, "--run-id", rid, env=self.env)
        else:
            run("verify-run.py", "finalize", "--log", self.log, "--run-id", rid, "--judge",
                judge or "none not configured", env=self.env)
        return rid

    def gate(self, *extra):
        return run("verdict-gate.py", "--scope", self.scope, "--unit", "5.1", *extra, env=self.env)

    def gate_json(self, *extra):
        p = self.gate("--json", *extra)
        return p.returncode, json.loads(p.stdout)

    def v(self, cid, verdict, rung=4):
        return {"check_id": cid, "verdict": verdict, "rung_reached": rung, "reason": f"judge: {verdict}"}


class TestGate(Fixture):
    def test_pass(self):
        self.ledger()
        self.verify("codex gpt-test", [self.v("ok", "pass")])
        code, doc = self.gate_json("--blocking")
        self.assertEqual((code, doc["verdict"], doc["marker"]), (0, "pass", ""))

    def test_missing_verdict_blocks(self):
        p = self.gate("--blocking")
        self.assertEqual(p.returncode, 1)
        self.assertIn("no final verdict", p.stdout)
        for f in FIELDS:
            self.assertIn(f, p.stdout)

    def test_under_rung_blocks(self):
        self.set_table([row("ok", "true", rung="5")])
        self.ledger()
        self.verify("codex gpt-test", [self.v("ok", "pass")])
        code, doc = self.gate_json("--blocking")
        self.assertEqual(code, 1)
        self.assertIn("under the required rung", doc["report"][0])

    def test_fail_then_fixed_clears(self):
        self.set_table([row("flag", "test -f ok.flag")])
        self.ledger()
        self.verify()
        self.assertEqual(self.gate("--blocking").returncode, 1)
        open(os.path.join(self.svc, "ok.flag"), "w").close()
        self.verify()
        self.assertEqual(self.gate("--blocking").returncode, 0)

    def test_runner_row_downgraded_by_judge_blocks(self):
        self.ledger()
        self.verify("codex gpt-test", [self.v("ok", "fail")])
        code, doc = self.gate_json("--blocking")
        self.assertEqual(code, 1)
        self.assertIn("verdict is fail", doc["report"][0])

    def test_judge_row_passes_on_judge_verdict(self):
        self.set_table([row("jr", "judge", rung="2")])
        self.ledger()
        self.verify("codex gpt-test", [self.v("jr", "pass", 2)])
        self.assertEqual(self.gate("--blocking").returncode, 0)

    def test_pending_run_blocks(self):
        self.ledger()
        self.verify("codex gpt-test", [self.v("ok", "pass")])
        run("verify-run.py", "run", "--table", self.table, "--log", self.log, "--owner", "5.1", env=self.env)
        code, doc = self.gate_json("--blocking")
        self.assertEqual(code, 1)
        self.assertIn("unfinished run", doc["report"][0])

    def test_unreachable(self):
        for ok, code in (("no", 1), ("yes: dev VPN flaps", 0)):
            with self.subTest(unreachable_ok=ok):
                self.set_table([row("away", "exit 3", ok=ok)])
                self.ledger()
                self.verify()
                self.assertEqual(self.gate("--blocking").returncode, code)

    def test_stale_sha_rejected(self):
        self.verify()                                   # evidence at commit a
        git(self.svc, "commit", "-q", "--allow-empty", "-m", "b")
        no_base = self.gate_json("--blocking")          # no base: evidence must be at HEAD
        self.assertEqual(no_base[0], 1)
        self.assertIn("stale", no_base[1]["report"][0])
        self.ledger()                                   # base = b: evidence at a is outside b..HEAD
        code, doc = self.gate_json("--blocking")
        self.assertEqual(code, 1)
        self.assertIn("outside the unit's range", doc["report"][0])

    def test_table_revision_change_blocks(self):
        self.ledger()
        self.verify()
        self.set_table([row("ok", "true")], rev=2)
        code, doc = self.gate_json("--blocking")
        self.assertEqual(code, 1)
        self.assertIn("predates the current finish table", doc["report"][0])

    def test_fallback_marker_set_then_cleared(self):
        self.ledger()
        self.verify("claude-fallback codex not authed", [self.v("ok", "pass")])
        code, doc = self.gate_json("--blocking")
        self.assertEqual((code, doc["marker"]), (0, "⚠ judge: claude-fallback codex not authed"))
        self.verify("codex gpt-test", [self.v("ok", "pass")])
        self.assertEqual(self.gate_json("--blocking")[1]["marker"], "")

    def test_advisory_warns_without_blocking(self):
        self.set_table([row("bad", "exit 1")])
        self.ledger()
        self.verify()
        p = self.gate("--advisory")
        self.assertEqual(p.returncode, 0)
        self.assertIn("[WARN]", p.stdout)
        self.assertIn("ADVISORY", p.stdout)
        self.assertIn("marker: ⚠ judge: none not configured ⚠ verify advisory: 1 blocked (bad)", p.stdout)

    def test_skip_verify_needs_a_reason(self):
        self.assertEqual(self.gate("--skip-verify", "  ").returncode, 2)
        code, doc = self.gate_json("--skip-verify", "codex down for the day")
        self.assertEqual((code, doc["verdict"], doc["marker"]), (0, "skipped", "⚠ verify skipped: codex down for the day"))

    def test_disposition_coverage(self):
        self.ledger()
        self.verify("codex gpt-test", [self.v("ok", "pass")])
        review = os.path.join(self.scope, "artifacts", "review-5.1.jsonl")
        f = {"schema": "verify/1", "record": "finding", "review_id": "5.1-r1", "file": "a.py", "line": 1}
        with open(review, "w") as fh:
            fh.write(json.dumps(dict(f, finding_id="5.1-r1-01")) + "\n")
            fh.write(json.dumps(dict(f, finding_id="5.1-r1-02")) + "\n")
            fh.write(json.dumps({"schema": "verify/1", "record": "disposition", "finding_id": "5.1-r1-01",
                                 "disposition": "rejected", "sha": None, "reason": ""}) + "\n")
        code, doc = self.gate_json("--blocking")
        self.assertEqual(code, 1)
        self.assertEqual({b["id"] for b in doc["blocks"]}, {"5.1-r1-01", "5.1-r1-02"})
        with open(review, "a") as fh:
            for fid, extra in (("5.1-r1-01", {"disposition": "rejected", "reason": "misread"}),
                               ("5.1-r1-02", {"disposition": "fixed", "sha": "abc1234"})):
                fh.write(json.dumps(dict({"schema": "verify/1", "record": "disposition", "finding_id": fid}, **extra)) + "\n")
        self.assertEqual(self.gate("--blocking").returncode, 0)

    def test_malformed_table_is_exit_3(self):
        with open(self.table, "a") as fh:
            fh.write("| broken |\n")
        self.set_table([row("ok", "true").replace("| B |", "| Z |")])
        p = self.gate()
        self.assertEqual(p.returncode, 3)


class TestLedgerBase(Fixture):
    def test_base_recorded_once(self):
        first = self.ledger()
        self.assertEqual(first.returncode, 0, first.stderr)
        sha_a = git(self.svc, "rev-parse", "HEAD")
        self.assertIn(f"base: 5.1 svc {sha_a}", first.stdout)
        git(self.svc, "commit", "-q", "--allow-empty", "-m", "b")
        again = self.ledger("--resumed")
        self.assertIn(f"base: kept 5.1 svc {sha_a}", again.stdout)
        with open(os.path.join(self.scope, "closeout-prep.md")) as fh:
            self.assertEqual(fh.read().count("- base: 5.1 svc "), 1)

    def test_non_repo_fails_loud(self):
        p = subprocess.run(["bash", script("ledger-init.sh"), self.scope, "--plan", self.plan,
                            "--phase", "1: x", "--repo", self.tmp.name], capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 1)
        self.assertIn("cannot record base SHA", p.stderr)


class TestIndexEnforcement(Fixture):
    def status(self, *extra):
        return run("plans-index.py", "status", self.index, "--num", "5.1", "--status", "✅ Done (2026-09-26)",
                   *extra, env=self.env)

    def validate(self):
        return run("plans-index.py", "validate", self.index, env=self.env)

    def row51(self):
        with open(self.index) as fh:
            return next(line for line in fh if line.startswith("| 5.1 "))

    def test_blocking_refuses_done(self):
        self.set_table([row("bad", "exit 1")])
        self.ledger()
        self.verify()
        before = self.row51()
        p = self.status("--blocking")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("[BLOCK] refusing Done for 5.1", p.stderr)
        refusal = p.stderr[p.stderr.index("[BLOCK] refusing Done"):]
        for f in FIELDS:
            self.assertIn(f, refusal)
        self.assertEqual(self.row51(), before)

    def test_pass_writes_done_clean(self):
        self.ledger()
        self.verify("codex gpt-test", [self.v("ok", "pass")])
        p = self.status("--blocking")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("| ✅ Done (2026-09-26) |", self.row51())
        self.assertEqual(self.validate().returncode, 0)

    def test_advisory_marks_and_validate_accepts(self):
        self.set_table([row("bad", "exit 1")])
        self.ledger()
        self.verify()
        p = self.status("--advisory")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("⚠ verify advisory: 1 blocked (bad)", self.row51())
        self.assertEqual(self.validate().returncode, 0)

    def test_hand_edited_done_caught_by_validate(self):
        self.set_table([row("bad", "exit 1")])
        self.ledger()
        self.verify()
        with open(self.index) as fh:
            text = fh.read()
        with open(self.index, "w") as fh:
            fh.write(text.replace("| 5.1 | 🔄 In progress |", "| 5.1 | ✅ Done (by hand) |"))
        p = self.validate()
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("phase 5.1", p.stdout)
        self.assertIn("written by hand", p.stdout)

    def test_skip_is_loud_in_the_index(self):
        self.set_table([row("bad", "exit 1")])
        p = self.status("--blocking", "--skip-verify", "env down")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("⚠ verify skipped: env down", self.row51())
        self.assertEqual(self.validate().returncode, 0)

    def test_scope_without_table_is_exempt(self):
        os.remove(self.table)
        p = self.status()
        self.assertEqual(p.returncode, 0)
        self.assertIn("gate not run", p.stderr)


if __name__ == "__main__":
    unittest.main()
