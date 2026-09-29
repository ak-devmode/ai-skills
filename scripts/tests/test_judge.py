"""verify/scripts/judge.py — the judge only sees disk, and only well-formed answers land.

Approach: a real runner run over a throwaway repo with a runner row, a judge row and a
declared-unreachable row, then prepare / record / report exactly as /verify calls them.
The judge's answer is a fixture file — the executor (codex or the Claude fallback) is
not what is under test here; the plumbing both of them share is.
"""

import json
import os
import subprocess
import tempfile
import unittest

from _helpers import run

JUDGE = "verify/scripts/judge.py"
HEADER = ("| check_id | deliverable | owner | class | check | repo | dir | env | timeout | rung "
          "| unreachable_ok | evidence |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n")
ROWS = ("| ok | builds | 9.1 | B | `true` | svc | . | - | - | 4 | no | ev |\n"
        "| jr | scope deliverables landed | 9.1 | B | judge | svc | . | - | - | 2 | no | ev |\n"
        "| away | live check | 9.1 | B | `exit 3` | svc | . | - | - | 4 | yes: env flaps | ev |\n")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def git(path, *args):
    return subprocess.run(["git", "-C", path, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          check=True, capture_output=True, text=True).stdout.strip()


class TestJudge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.projects = os.path.join(self.tmp.name, "projects")
        self.svc = os.path.join(self.projects, "svc")
        os.makedirs(self.svc)
        git(self.projects, "init", "-q", "-b", "main")
        git(self.svc, "init", "-q", "-b", "main")
        git(self.svc, "commit", "-q", "--allow-empty", "-m", "base")
        self.base = git(self.svc, "rev-parse", "HEAD")
        git(self.svc, "commit", "-q", "--allow-empty", "-m", "work")
        self.scope = os.path.join(self.projects, "plans", "9-x")
        os.makedirs(os.path.join(self.scope, "artifacts"))
        with open(os.path.join(self.scope, "finish-conditions.md"), "w") as fh:
            fh.write(f"**Schema version:** verify/1\n**Revision:** 1\n\n{HEADER}{ROWS}")
        with open(os.path.join(self.scope, "scope.md"), "w") as fh:
            fh.write("# scope\n")
        self.env = dict(os.environ, VERIFY_PROJECTS=self.projects)
        self.log = os.path.join(self.scope, "artifacts", "verify-9.1.jsonl")
        p = run("verify-run.py", "run", "--table", os.path.join(self.scope, "finish-conditions.md"),
                "--log", self.log, "--owner", "9.1", env=self.env)
        self.rid = p.stdout.split("run_id: ")[1].split()[0]

    def tearDown(self):
        self.tmp.cleanup()

    def ledger(self, sha):
        with open(os.path.join(self.scope, "closeout-prep.md"), "w") as fh:
            fh.write(f"## Phase 1: x\n\n- base: 9.1 svc {sha}\n")

    def judge(self, cmd, *extra):
        return run(JUDGE, cmd, "--scope", self.scope, "--unit", "9.1", "--run-id", self.rid, *extra, env=self.env)

    def answer(self, **over):
        doc = {"verdicts": [{"check_id": c, "verdict": "pass", "rung_reached": r, "reason": f"checked {c}"}
                            for c, r in (("ok", 4), ("jr", 2), ("away", 4))],
               "findings": [{"check_id": "jr", "lens": "over-build", "severity": "low", "where": "a.py:1",
                             "text": "registry for one caller"}],
               "lever_candidates": [], "feature_map": "n/a"}
        doc.update(over)
        path = os.path.join(self.tmp.name, "answer.json")
        with open(path, "w") as fh:
            json.dump(doc, fh)
        return path

    def records(self, state):
        with open(self.log) as fh:
            return [r for r in map(json.loads, fh) if r["run_state"] == state]

    # ---- prepare
    def test_prepare_renders_from_disk(self):
        self.ledger(self.base)
        out = os.path.join(self.tmp.name, "work")
        p = self.judge("prepare", "--out-dir", out)
        self.assertEqual(p.returncode, 0, p.stderr)
        prompt = read(p.stdout.split("prompt: ")[1].split()[0])
        self.assertNotIn("{{", prompt)
        for cid in ("| ok | runner | 4 |", "| jr | judge | 2 |", "| away | runner | 4 |"):
            self.assertIn(cid, prompt)
        self.assertIn(f"`{self.base}..", prompt)
        self.assertIn("(1 commits)", prompt)
        self.assertIn(self.rid, prompt)

    def test_prepare_refuses_empty_range(self):
        self.ledger(git(self.svc, "rev-parse", "HEAD"))
        p = self.judge("prepare")
        self.assertEqual(p.returncode, 3)
        self.assertIn("range is empty", p.stderr)
        self.assertIn("cause    · code", p.stderr)

    def test_prepare_needs_a_range(self):
        p = self.judge("prepare")
        self.assertEqual(p.returncode, 3)
        self.assertIn("no revision range for svc", p.stderr)
        ok = self.judge("prepare", "--range", f"svc={self.base}..HEAD")
        self.assertEqual(ok.returncode, 0, ok.stderr)

    # ---- record
    def test_record_lands_verdicts_and_raw_output(self):
        p = self.judge("record", "--judge", "codex gpt-test", "--input", self.answer())
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual({r["check_id"] for r in self.records("judged")}, {"ok", "jr", "away"})
        raw = os.path.join(self.scope, "artifacts", f"verify-9.1-judge-{self.rid}.json")
        self.assertEqual(json.loads(read(raw))["judge"], "codex gpt-test")

    def test_record_rejects_malformed_answers(self):
        cases = {
            "missing check": dict(verdicts=[{"check_id": "ok", "verdict": "pass", "rung_reached": 4, "reason": "x"}]),
            "unknown check": dict(verdicts=[{"check_id": c, "verdict": "pass", "rung_reached": 4, "reason": "x"}
                                            for c in ("ok", "jr", "away", "zzz")]),
            "bad lens": dict(findings=[{"check_id": "ok", "lens": "vibes", "severity": "low", "where": "x", "text": "y"}]),
            "finding on unknown check": dict(findings=[{"check_id": "nope", "lens": "evidence", "severity": "low",
                                                        "where": "x", "text": "y"}]),
            "bad feature_map": dict(feature_map="fine"),
            # 5.2-r1-06: shape is enforced from the schema file, before anything lands
            "finding missing where/text": dict(findings=[{"check_id": "jr", "lens": "evidence", "severity": "low"}]),
            "malformed lever candidate": dict(lever_candidates=[{"check_id": "away"}]),
            "findings is null": dict(findings=None),
            "verdicts is an object": dict(verdicts={}),
        }
        for name, over in cases.items():
            with self.subTest(case=name):
                p = self.judge("record", "--judge", "codex gpt-test", "--input", self.answer(**over))
                self.assertEqual(p.returncode, 3, p.stdout)
                self.assertIn("nothing recorded", p.stderr)
                self.assertIn("none malformed judge output", p.stderr)
        self.assertEqual(self.records("judged"), [])

    # ---- report
    def test_report(self):
        self.ledger(self.base)
        self.judge("record", "--judge", "claude-fallback codex not authed", "--input", self.answer())
        run("verify-run.py", "finalize", "--log", self.log, "--run-id", self.rid, env=self.env)
        p = self.judge("report")
        self.assertEqual(p.returncode, 0, p.stderr)
        text = read(os.path.join(self.scope, "artifacts", "verify-9.1-report.md"))
        self.assertIn("**Judge:** claude-fallback codex not authed", text)
        self.assertIn("| jr | pass | 2/2 |", text)
        self.assertIn("**low** · over-build · `jr`", text)
        self.assertIn("- `away` — gap:", text)  # unreachable row is always a lever candidate
        self.assertIn("⚠ judge: claude-fallback codex not authed", text)

    def test_report_propagates_a_gate_error(self):
        # 5.2-r1-05: a gate that errors must not become a successful report.
        self.ledger(self.base)
        self.judge("record", "--judge", "codex gpt-test", "--input", self.answer())
        run("verify-run.py", "finalize", "--log", self.log, "--run-id", self.rid, env=self.env)
        with open(os.path.join(self.scope, "finish-conditions.md"), "w") as fh:
            fh.write(f"**Schema version:** verify/1\n**Revision:** 1\n\n{HEADER}"
                     "| ok | builds | 9.1 | B |  | svc | . | - | - | 4 | no | ev |\n")  # blank check cell
        p = self.judge("report")
        self.assertEqual(p.returncode, 3, p.stdout)
        self.assertIn("[ERROR]", p.stderr)
        text = read(os.path.join(self.scope, "artifacts", "verify-9.1-report.md"))
        self.assertIn("GATE ERROR (exit 3)", text)


if __name__ == "__main__":
    unittest.main()
