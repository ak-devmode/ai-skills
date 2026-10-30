"""phase-report.py (scope 10.5): one report per phase, composed from the records it already wrote.

Approach: build a throwaway scope with a finish table (written by finish-table.py init), a
verify report, a review log, a progress Decisions Log and a merge log; render it and check
each section reads its own source — rows from the table parser, the verify report and
verdict-gate.py's output embedded whole — and that a missing or damaged record says so,
never reads as zero (reframes 10.5-r1, 10.5-r2).
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
        self.projects = os.path.realpath(self.tmp.name)
        docs = os.path.join(self.projects, "team", "team-docs")
        self.scope = os.path.join(docs, "plans", "9-thing")
        os.makedirs(self.scope)
        subprocess.run(["git", "-C", docs, "init", "-q"], check=True)
        rows = os.path.join(self.tmp.name, "rows.jsonl")
        put(rows, json.dumps({"check_id": "p1-pipe", "deliverable": "accept A | B for every tenant",
                              "owner": "9.1", "check": "judge", "repo": "team/svc"}) + "\n")
        p = run("finish-table.py", "init", "--phase", "9.1=team/svc", "--rows", rows, "--scope", self.scope,
                "--projects", self.projects, "--by", "T")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.art = os.path.join(self.scope, "artifacts")

    def tearDown(self):
        self.tmp.cleanup()

    def report(self):
        p = run("phase-report.py", "--scope", self.scope, "--unit", "9.1", timeout=300)
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(os.path.join(self.art, "phase-report-9.1.md"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), p.stdout)  # printed and kept are the same text
        return p.stdout

    def test_missing_records_say_so(self):
        out = self.report()
        self.assertIn("| p1-names-resolve |", out)
        self.assertIn("approved rev 1", out)  # standing policy, nobody asked (§3.1.1)
        for line in ("No review log.", "No verify report.", "None recorded by driver-merge.py.",
                     "No progress file"):
            self.assertIn(line, out)

    def test_rows_are_whole_and_pipes_escaped(self):  # 10.5-r1-06, r1-11
        out = self.report()
        row = next(l for l in out.splitlines() if l.startswith("| p1-pipe |"))
        self.assertIn("accept A \\| B for every tenant", row)
        self.assertEqual(row.replace("\\|", "").count("|"), 5)  # four cells, no shifted columns
        self.assertIn("`judge` (rung 2)", row)
        self.assertIn("team/svc/.", row)

    def test_damaged_log_is_reported_not_read_as_zero(self):  # 10.5-r1-04
        put(os.path.join(self.art, "review-9.1.jsonl"),
            jl({"record": "review", "review_id": "9.1-r1", "reviewer": "codex x", "verdict": "SHIP"}) + "{torn\n")
        out = self.report()
        self.assertIn("Review log damaged", out)
        self.assertNotIn("Findings: 0", out)
        gate = out.split("## 2. Gate", 1)[1].split("## 3.", 1)[0]
        self.assertIn("exit 3", gate)  # the gate's own error, never "accepted"  (10.5-r2-01)
        self.assertIn("review-9.1.jsonl", gate)

    def test_every_section_reads_its_record(self):
        put(os.path.join(self.art, "verify-9.1-report.md"),
            "# Verify 9.1\n\n**Run:** run-3 · table rev 1\n\n## 1. Checks\n\n| Check | Result |\n|---|---|\n| p1-names-resolve | pass |\n\n"
            "## 2. Findings\n\n- **medium** · weak-row · `p1-pipe` · t — existence only; call the route\n"
            "- **misfiled** `9.1-r1-02` — a missing tenant filter dismissed as a nit\n\n## 3. Lever candidates\n\nnone\n")
        put(os.path.join(self.art, "review-9.1.jsonl"), jl(
            {"record": "review", "review_id": "9.1-r1", "reviewer": "codex gpt-x", "verdict": "SHIP AFTER BLOCKING"},
            {"record": "finding", "finding_id": "9.1-r1-01", "severity": "blocking"},
            {"record": "finding", "finding_id": "9.1-r1-02", "severity": "note"},
            {"record": "finding", "finding_id": "9.1-r1-03", "severity": "should-fix"},
            {"record": "disposition", "finding_id": "9.1-r1-01", "disposition": "fixed", "sha": "abc"},
            {"record": "disposition", "finding_id": "9.1-r1-02", "disposition": "accepted", "reason": "wording"},
            {"record": "review", "review_id": "9.1-r2", "reviewer": "claude-fallback out", "verdict": "SHIP"}))
        put(os.path.join(self.scope, "progress.md"),
            "# P\n\n## Decisions Log\n- (2026-10-29) 9.1 uses a queue\n"
            "- (2026-10-29) 44 answered: drop the cache\n- (2026-10-29) 86 (Alex) invert it\n"
            "- (2026-10-29) 19.1 unrelated\n\n## Plan 9.1: x\n- built per Alex 44 and 86 (Alex)\n")
        put(os.path.join(self.art, "merges-9.1.jsonl"), jl(
            {"ts": "2026-10-29T01:00:00+00:00", "slug": "team/svc", "pr": 7, "base": "develop",
             "sha": "f" * 40, "flags": ["degraded review: lean"]}))
        out = self.report()
        self.assertIn("## 2. Gate", out)
        self.assertIn("verdict: ", out)  # the gate's own text, whole (10.5-r2-03)
        self.assertIn("p1-pipe", out.split("## 2. Gate", 1)[1].split("## 3.", 1)[0])
        self.assertIn("weak-row · `p1-pipe`", out)  # the verify report, whole
        self.assertIn("**misfiled** `9.1-r1-02`", out)
        self.assertIn("**Run:** run-3 · table rev 1", out)  # its header names the run (10.5-r2-02)
        self.assertIn("#### 1. Checks", out)  # headings sit below the section's
        self.assertIn("Lever candidates", out)
        self.assertIn("as of its own run; §2 is current", out)  # an older report never reads as current (10.5-r3-02)
        self.assertIn("- Rounds: 2 reviews (claude-fallback ×1, codex ×1)", out)
        self.assertIn("- Last: 9.1-r2 — SHIP", out)
        self.assertIn("- Findings: 3 (blocking 1, note 1, should-fix 1)", out)
        self.assertIn("1 without a disposition", out)
        self.assertIn("- nit `9.1-r1-02` — wording", out)
        self.assertIn("9.1 uses a queue", out)
        self.assertIn("44 answered: drop the cache", out)  # cited by number in the unit's section
        self.assertIn("86 (Alex) invert it", out)
        self.assertNotIn("19.1 unrelated", out)
        self.assertIn("- team/svc#7 → develop @ ffffffffffff", out)
        self.assertIn("degraded review: lean", out)

    def test_standalone_progress_file_is_found(self):  # 10.5-r1-10
        put(os.path.join(self.scope, "thing-PROGRESS.md"), "# P\n\n## Decisions Log\n- (2026-10-29) 9.1 keeps it\n")
        self.assertIn("9.1 keeps it", self.report())


if __name__ == "__main__":
    unittest.main()
