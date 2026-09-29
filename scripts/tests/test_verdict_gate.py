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

    def test_block_message_carries_the_output_line(self):
        self.set_table([row("bad", "echo '  [FAIL] env `X` does not resolve'; exit 1")])
        self.ledger()
        self.verify()
        p = self.gate("--blocking")
        self.assertIn("output: [FAIL] env `X` does not resolve", p.stdout)

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

    def test_hand_edited_final_record_blocks(self):
        self.set_table([row("bad", "exit 1")])
        self.ledger()
        self.verify()
        with open(self.log) as fh:
            recs = [json.loads(x) for x in fh]
        recs[-1]["results"]["bad"].update(result="pass", rung_reached=4)  # forge the verdict
        with open(self.log, "w") as fh:
            fh.write("".join(json.dumps(r) + "\n" for r in recs))
        code, doc = self.gate_json("--blocking")
        self.assertEqual(code, 1)
        self.assertIn("contradicts its own evidence", doc["report"][0])

    def test_none_judged_record_is_not_evidence(self):
        # A judged record smuggled in under a `none` judge line (5.2-r1-03) must not pass a
        # judge row: the gate's authority re-check treats it as absent → inconclusive.
        self.set_table([row("jr", "judge", rung="2")])
        self.ledger()
        self.verify()
        with open(self.log) as fh:
            recs = [json.loads(x) for x in fh]
        final = recs[-1]
        judged = dict(final, run_state="judged", check_id="jr", judge="none unavailable",
                      verdict="pass", rung_reached=2, reason="forged")
        judged.pop("results")
        final.update(judge="none unavailable")
        final["results"]["jr"] = {"result": "pass", "rung_reached": 2, "reason": "judge: forged"}
        with open(self.log, "w") as fh:
            fh.write("".join(json.dumps(r) + "\n" for r in recs[:-1] + [judged, final]))
        code, doc = self.gate_json("--blocking")
        self.assertEqual(code, 1)
        self.assertIn("contradicts its own evidence", doc["report"][0])

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

    def test_index_gate_mode_line_makes_the_default_blocking(self):
        self.set_table([row("bad", "exit 1")])
        self.ledger()
        self.verify()
        self.assertEqual(self.gate().returncode, 0)  # fleet default: advisory
        with open(self.index, "a") as fh:
            fh.write("\n**Gate mode:** blocking\n")
        p = self.gate()
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("BLOCKED", p.stdout)
        self.assertEqual(self.gate("--advisory").returncode, 0)  # an explicit flag still wins

    def test_unapproved_table_blocks_and_legacy_table_is_exempt(self):
        self.ledger()
        self.verify("codex gpt-test", [self.v("ok", "pass")])
        self.assertEqual(self.gate("--blocking").returncode, 0)  # no **Approved:** line: predates §3.5
        with open(self.table) as fh:
            text = fh.read()
        with open(self.table, "w") as fh:
            fh.write(text.replace("**Revision:** 1\n", "**Revision:** 1\n**Approved:** pending\n"))
        code, doc = self.gate_json("--blocking")
        self.assertEqual(code, 1)
        self.assertEqual([b["id"] for b in doc["blocks"]], ["table-approval"])
        with open(self.table, "w") as fh:
            fh.write(text.replace("**Revision:** 1\n", "**Revision:** 1\n**Approved:** rev 1 — Alex, 2026-09-29\n"))
        self.assertEqual(self.gate("--blocking").returncode, 0)

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


class TestReviewRequired(Fixture):
    """5.3-r1-03: a unit with commits in range cannot pass without a /review covering it."""

    def review_record(self, base, head):
        rec = {"schema": "verify/1", "ts": "t", "record": "review", "review_id": "5.1-r1",
               "reviewer": "codex gpt-test", "range": {"svc": f"{base}..{head}"},
               "shas": {"base": base, "head": head}, "passes": "p", "findings": 0, "verdict": "SHIP"}
        with open(os.path.join(self.scope, "artifacts", "review-5.1.jsonl"), "a") as fh:
            fh.write(json.dumps(rec) + "\n")

    def setUp(self):
        super().setUp()
        self.ledger()
        self.b = git(self.svc, "rev-parse", "HEAD")
        git(self.svc, "commit", "-q", "--allow-empty", "-m", "unit work")
        self.h = git(self.svc, "rev-parse", "HEAD")

    def test_unreviewed_commits_block(self):
        self.verify("codex gpt-test", [self.v("ok", "pass")])
        code, doc = self.gate_json("--blocking")
        self.assertEqual(code, 1)
        self.assertIn("review:svc", [b["id"] for b in doc["blocks"]])

    def test_covering_review_passes_even_after_later_commits(self):
        self.review_record(self.b, self.h)
        git(self.svc, "commit", "-q", "--allow-empty", "-m", "progress note")
        self.verify("codex gpt-test", [self.v("ok", "pass")])
        code, doc = self.gate_json("--blocking")
        self.assertEqual((code, doc["verdict"]), (0, "pass"), doc)

    def test_legacy_log_with_findings_only_still_counts(self):
        rec = {"schema": "verify/1", "ts": "t", "record": "finding", "review_id": "5.1-r1", "finding_id": "5.1-r1-01",
               "reviewer": "codex gpt-test", "range": {"svc": f"{self.b}..{self.h}"}, "file": "a", "line": 1}
        disp = {"schema": "verify/1", "ts": "t", "record": "disposition", "finding_id": "5.1-r1-01",
                "disposition": "rejected", "reason": "fine", "by": "t"}
        with open(os.path.join(self.scope, "artifacts", "review-5.1.jsonl"), "w") as fh:
            fh.write(json.dumps(rec) + "\n" + json.dumps(disp) + "\n")
        self.verify("codex gpt-test", [self.v("ok", "pass")])
        code, doc = self.gate_json("--blocking")
        self.assertEqual(code, 0, doc)

    def test_review_of_a_discarded_branch_does_not_cover(self):
        # 5.3-r2-03: the reviewed head must be on the current branch
        git(self.svc, "checkout", "-q", "-b", "side")
        git(self.svc, "commit", "-q", "--allow-empty", "-m", "side work")
        side = git(self.svc, "rev-parse", "HEAD")
        git(self.svc, "checkout", "-q", "main")
        self.review_record(self.b, side)
        self.verify("codex gpt-test", [self.v("ok", "pass")])
        code, doc = self.gate_json("--blocking")
        self.assertIn("review:svc", [b["id"] for b in doc["blocks"]])

    def blocking_finding_fixed(self):
        self.review_record(self.b, self.h)
        git(self.svc, "commit", "-q", "--allow-empty", "-m", "fix r1-01")
        fix = git(self.svc, "rev-parse", "HEAD")
        recs = [{"schema": "verify/1", "ts": "t", "record": "finding", "review_id": "5.1-r1", "finding_id": "5.1-r1-01",
                 "reviewer": "codex gpt-test", "range": {"svc": f"{self.b}..{self.h}"}, "file": "a", "line": 1,
                 "severity": "blocking"},
                {"schema": "verify/1", "ts": "t", "record": "disposition", "finding_id": "5.1-r1-01",
                 "disposition": "fixed", "sha": fix, "by": "t"}]
        with open(os.path.join(self.scope, "artifacts", "review-5.1.jsonl"), "a") as fh:
            fh.writelines(json.dumps(r) + "\n" for r in recs)
        return fix

    def test_blocking_fix_needs_a_later_review(self):
        # 5.3-r2-03: /plan §6.8 "review the fixes again", enforced
        fix = self.blocking_finding_fixed()
        self.verify("codex gpt-test", [self.v("ok", "pass")])
        code, doc = self.gate_json("--blocking")
        self.assertIn("rereview:5.1-r1-01", [b["id"] for b in doc["blocks"]])
        self.review_record(self.h, fix)            # r2 covers the fix
        code, doc = self.gate_json("--blocking")
        self.assertEqual((code, doc["verdict"]), (0, "pass"), doc)

    def test_unreadable_repo_blocks_instead_of_counting_zero(self):
        # 5.3-r2-02: a git failure is never "no commits"
        with open(os.path.join(self.scope, "closeout-prep.md"), "a") as fh:
            fh.write("\n- base: 5.1 gone 0123456789abcdef0123456789abcdef01234567\n")
        self.review_record(self.b, self.h)
        self.verify("codex gpt-test", [self.v("ok", "pass")])
        code, doc = self.gate_json("--blocking")
        self.assertIn("review:gone", [b["id"] for b in doc["blocks"]])

    def test_review_that_starts_after_the_base_does_not_cover(self):
        git(self.svc, "commit", "-q", "--allow-empty", "-m", "more")
        self.review_record(self.h, git(self.svc, "rev-parse", "HEAD"))
        self.verify("codex gpt-test", [self.v("ok", "pass")])
        code, doc = self.gate_json("--blocking")
        self.assertIn("review:svc", [b["id"] for b in doc["blocks"]])


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

    def test_malformed_gate_mode_refuses_done_instead_of_going_advisory(self):
        self.set_table([row("bad", "exit 1")])
        self.ledger()
        self.verify()
        with open(self.index, "a") as fh:
            fh.write("\n**Gate mode:** blockng\n")
        before = self.row51()
        p = self.status()
        self.assertNotEqual(p.returncode, 0, p.stdout)
        self.assertIn("unknown gate mode", p.stderr)
        self.assertEqual(self.row51(), before)

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

    def test_move_with_plans_brings_the_phase_rows(self):
        # 5.3 closeout: child rows follow the scope row and are repointed
        os.makedirs(os.path.join(self.plans, "archive", "5-x"))
        p = run("plans-index.py", "move", self.index, "--num", "5", "--to", "archived",
                "--folder", "archive/5-x/", "--with-plans", env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(self.index) as fh:
            text = fh.read()
        archived = text.split("## Completed / Archived")[1]
        self.assertIn("| 5 |", archived)
        self.assertIn("| 5.1 | 🔄 In progress | archive/5-x/ |", archived)
        self.assertNotIn("| 5.1 ", text.split("## Completed / Archived")[0])

    def test_scope_without_table_is_exempt(self):
        os.remove(self.table)
        p = self.status()
        self.assertEqual(p.returncode, 0)
        self.assertIn("gate not run", p.stderr)


class TestPredatesAndCloseout(Fixture):
    """Scope 5.3: running scopes never reconcile verify (Predates gate), /closeout's --all
    view, and the clean-scope count toward the blocking flip."""

    def table_with(self, rows, predates=None):
        head = f"**Predates gate:** {predates}\n" if predates else ""
        with open(self.table, "w") as fh:
            fh.write(f"# t\n\n**Schema version:** verify/1\n**Revision:** 1\n{head}\n{HEADER}{''.join(rows)}\n")

    def verify_unit(self, unit, judge_items):
        log = os.path.join(self.scope, "artifacts", f"verify-{unit}.jsonl")
        p = run("verify-run.py", "run", "--table", self.table, "--log", log, "--owner", unit, env=self.env)
        rid = p.stdout.split("run_id: ")[1].split()[0]
        path = os.path.join(self.tmp.name, f"j-{unit}.json")
        with open(path, "w") as fh:
            json.dump(judge_items, fh)
        run("verify-run.py", "judged", "--log", log, "--run-id", rid, "--judge", "codex gpt-test",
            "--input", path, env=self.env)
        run("verify-run.py", "finalize", "--log", log, "--run-id", rid, env=self.env)

    def test_predating_phase_is_exempt_and_validate_accepts_its_done(self):
        self.table_with([row("later", "true", owner="5.2")], predates="5.1")
        code, doc = self.gate_json("--blocking")
        self.assertEqual((code, doc["verdict"]), (0, "predates-gate"))
        with open(self.index) as fh:
            text = fh.read()
        with open(self.index, "w") as fh:
            fh.write(text.replace("| 5.1 | 🔄 In progress |", "| 5.1 | ✅ Done (before the gate) |"))
        self.assertEqual(run("plans-index.py", "validate", self.index, env=self.env).returncode, 0)

    def test_predating_phase_that_owns_rows_is_malformed(self):
        self.table_with([row("ok", "true")], predates="5.1")
        p = self.gate()
        self.assertEqual(p.returncode, 3)
        self.assertIn("predates the gate owns rows", p.stderr)

    def closeout(self, *extra):
        return run("verdict-gate.py", "--scope", self.scope, "--all", *extra, env=self.env)

    def test_all_fails_on_any_block_even_in_advisory(self):
        self.table_with([row("ok", "true"), row("bad", "exit 1", owner="5.2")], predates="5.0")
        self.ledger()
        self.verify_unit("5.1", [self.v("ok", "pass")])
        self.verify_unit("5.2", [self.v("bad", "fail")])
        p = self.closeout("--advisory")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("marker: ⚠ verify failed bad", p.stdout)
        self.assertIn("n/a   5.0  predates the gate", p.stdout)

    def test_all_json_says_which_units_need_verify(self):
        # 5.3-r1-04: closeout must be able to tell "missing verdict" from "failed verdict"
        self.table_with([row("ok", "true"), row("bad", "exit 1", owner="5.2")])
        self.ledger()
        self.verify_unit("5.2", [self.v("bad", "fail")])
        doc = json.loads(self.closeout("--json").stdout)
        units = {u["unit"]: u for u in doc["units"]}
        self.assertTrue(units["5.1"]["needs_verify"])
        self.assertEqual(units["5.1"]["blocks"][0]["what"], "no final verdict")
        self.assertFalse(units["5.2"]["needs_verify"])
        self.assertEqual(units["5.2"]["blocks"][0]["id"], "bad")

    def test_all_passes_clean_with_codex(self):
        self.table_with([row("ok", "true")])
        self.ledger()
        self.verify_unit("5.1", [self.v("ok", "pass")])
        p = self.closeout("--json")
        doc = json.loads(p.stdout)
        self.assertEqual((p.returncode, doc["verdict"], doc["marker"]), (0, "pass", ""))

    def archived_scope(self, n, passing=True):
        folder = os.path.join(self.plans, "archive", f"{n}-s")
        os.makedirs(os.path.join(folder, "artifacts"))
        unit = f"{n}.1"
        with open(os.path.join(folder, "finish-conditions.md"), "w") as fh:
            fh.write(f"# t\n\n**Schema version:** verify/1\n**Revision:** 1\n\n{HEADER}"
                     + row("ok", "true" if passing else "exit 1", owner=unit))
        log = os.path.join(folder, "artifacts", f"verify-{unit}.jsonl")
        p = run("verify-run.py", "run", "--table", os.path.join(folder, "finish-conditions.md"), "--log", log,
                "--owner", unit, env=self.env)
        rid = p.stdout.split("run_id: ")[1].split()[0]
        path = os.path.join(self.tmp.name, f"j{n}.json")
        with open(path, "w") as fh:
            json.dump([self.v("ok", "pass")], fh)
        run("verify-run.py", "judged", "--log", log, "--run-id", rid, "--judge", "codex gpt-test", "--input", path,
            env=self.env)
        run("verify-run.py", "finalize", "--log", log, "--run-id", rid, env=self.env)

    def test_gate_count_needs_a_passing_gated_scope(self):
        # 5.3-r1-05: no ⚠ is not enough — an ungated or failing table never counts
        ungated = os.path.join(self.plans, "archive", "7-s")
        os.makedirs(ungated)
        with open(os.path.join(ungated, "finish-conditions.md"), "w") as fh:
            fh.write(f"# t\n\n**Schema version:** verify/1\n**Revision:** 1\n**Predates gate:** 7.1\n\n{HEADER}")
        self.archived_scope(8, passing=False)
        with open(self.index, "a") as fh:
            fh.write("| 7 | ✅ Done | `archive/7-s/` | s | t |\n| 8 | ✅ Done | `archive/8-s/` | s | t |\n")
        p = run("plans-index.py", "gate-count", self.index, "--discover", env=self.env)
        self.assertIn("clean gated scopes: 0/5", p.stdout)
        self.assertIn("with ⚠: projects 8", p.stdout)
        self.assertEqual(p.stdout.count("projects 8"), 1)  # explicit + --discover counted once

    def test_gate_count_and_reminder_at_five(self):
        rows = ""
        for n in range(1, 7):
            self.archived_scope(n)
            mark = " ⚠ verify advisory: 1 blocked (x)" if n == 6 else ""
            rows += (f"| {n} | ✅ Done | `archive/{n}-s/` | s | t |\n"
                     f"| {n}.1 | ✅ Done{mark} | `archive/{n}-s/` | p | t |\n")
        with open(self.index, "a") as fh:
            fh.write(rows)
        p = run("plans-index.py", "gate-count", self.index, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("clean gated scopes: 5/5", p.stdout)
        self.assertIn("with ⚠: projects 6", p.stdout)
        self.assertIn("REMINDER", p.stdout)
        with open(self.index, "w") as fh:
            fh.write(INDEX + rows.replace("| 2.1 | ✅ Done |", "| 2.1 | ✅ Done ⚠ judge: none x |"))
        p = run("plans-index.py", "gate-count", self.index, env=self.env)
        self.assertIn("clean gated scopes: 4/5", p.stdout)
        self.assertNotIn("REMINDER", p.stdout)
        # --discover finds the index under VERIFY_PROJECTS by itself
        p = run("plans-index.py", "gate-count", "--discover", env=self.env)
        self.assertIn("clean gated scopes: 4/5", p.stdout)


if __name__ == "__main__":
    unittest.main()
