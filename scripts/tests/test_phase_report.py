"""phase-report.py (scope 10.5): one report per phase from the records it already wrote.

Approach: build a throwaway scope with a finish table (written by finish-table.py init), a
verify log, a judge answer with a weak-row finding, a review log, a progress Decisions Log
and a merge log; render it and check each section reads the right record. A missing record
must say so, never read as zero.
"""
import json
import os
import subprocess
import tempfile
import unittest

from _helpers import run


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def jl(*recs):
    return "".join(json.dumps(r) + "\n" for r in recs)


class PhaseReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        projects = os.path.realpath(self.tmp.name)
        docs = os.path.join(projects, "team", "team-docs")
        self.scope = os.path.join(docs, "plans", "9-thing")
        os.makedirs(self.scope)
        subprocess.run(["git", "-C", docs, "init", "-q"], check=True)
        p = run("finish-table.py", "init", "--phase", "9.1=team/svc", "--scope", self.scope,
                "--projects", projects, "--by", "T")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.art = os.path.join(self.scope, "artifacts")

    def tearDown(self):
        self.tmp.cleanup()

    def report(self):
        p = run("phase-report.py", "--scope", self.scope, "--unit", "9.1")
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(os.path.join(self.art, "phase-report-9.1.md"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), p.stdout)  # printed and kept are the same text
        return p.stdout

    def test_missing_records_say_so(self):
        out = self.report()
        self.assertIn("| p1-names-resolve |", out)
        self.assertIn("| not run |", out)
        for line in ("No review log.", "No verify log.", "None recorded by driver-merge.py.", "No progress file"):
            self.assertIn(line, out)

    def test_every_section_reads_its_record(self):
        rid = "9.1-20261029T000000-aaaa"
        put(os.path.join(self.art, "verify-9.1.jsonl"), jl(
            {"run_id": rid, "run_state": "pending", "check_id": "p1-names-resolve"},
            {"run_id": rid, "run_state": "final", "judge": "codex gpt-x",
             "results": {"p1-names-resolve": {"result": "pass", "rung_reached": 4, "reason": "runner: exit 0"},
                         "p1-no-overbuild": {"result": "fail", "rung_reached": 2, "reason": "judge: registry"}}}))
        put(os.path.join(self.art, f"verify-9.1-judge-{rid}.json"), json.dumps({"findings": [
            {"check_id": "p1-scope-deliverables", "lens": "weak-row", "severity": "medium", "where": "x",
             "text": "existence only; call the route"},
            {"check_id": "p1-no-overbuild", "lens": "over-build", "severity": "low", "where": "y", "text": "z"}]}))
        put(os.path.join(self.art, "review-9.1.jsonl"), jl(
            {"record": "review", "review_id": "9.1-r1", "reviewer": "codex gpt-x", "verdict": "SHIP AFTER BLOCKING"},
            {"record": "finding", "finding_id": "9.1-r1-01", "severity": "blocking"},
            {"record": "finding", "finding_id": "9.1-r1-02", "severity": "note"},
            {"record": "finding", "finding_id": "9.1-r1-03", "severity": "should-fix"},
            {"record": "disposition", "finding_id": "9.1-r1-01", "disposition": "fixed", "sha": "abc"},
            {"record": "disposition", "finding_id": "9.1-r1-02", "disposition": "accepted", "reason": "wording"},
            {"record": "review", "review_id": "9.1-r2", "reviewer": "claude-fallback out", "verdict": "SHIP"},
            {"record": "acceptance", "by": "T (standing policy)", "ts": "2026-10-29T00:00:00Z"}))
        put(os.path.join(self.scope, "progress.md"),
            "# P\n\n## Decisions Log\n- (2026-10-29) 9.1 uses a queue (Alex 12)\n"
            "- (2026-10-29) 44 answered: drop the cache\n- (2026-10-29) 19.1 unrelated\n"
            "\n## Plan 9.1: x\n- built per Alex 44\n")
        put(os.path.join(self.art, "merges-9.1.jsonl"), jl(
            {"ts": "2026-10-29T01:00:00+00:00", "slug": "team/svc", "pr": 7, "base": "develop",
             "sha": "f" * 40, "flags": ["degraded review: lean"]}))
        out = self.report()
        self.assertIn("| p1-names-resolve | Every identifier", out)
        self.assertIn("| pass | 4/4 | runner: exit 0 |", out)
        self.assertIn("- Runs: 1 (1 finalized)", out)
        self.assertIn("- Latest: fail 1, pass 1 — judge codex gpt-x", out)
        self.assertIn("- Weak rows (judge, advisory): 1", out)
        self.assertIn("`p1-scope-deliverables` — existence only; call the route", out)
        self.assertNotIn("registry` —", out)  # only the weak-row lens is listed as a weak row
        self.assertIn("- Rounds: 2 reviews (claude-fallback ×1, codex ×1)", out)
        self.assertIn("- Last: 9.1-r2 — SHIP", out)
        self.assertIn("- Findings: 3 (blocking 1, note 1, should-fix 1)", out)
        self.assertIn("1 without a disposition", out)
        self.assertIn("- Accepted: T (standing policy)", out)
        self.assertIn("- nit `9.1-r1-02` — wording", out)
        self.assertIn("9.1 uses a queue", out)
        self.assertIn("44 answered: drop the cache", out)  # cited by number in the unit's section
        self.assertNotIn("19.1 unrelated", out)
        self.assertIn("- team/svc#7 → develop @ ffffffffffff", out)
        self.assertIn("degraded review: lean", out)


if __name__ == "__main__":
    unittest.main()
