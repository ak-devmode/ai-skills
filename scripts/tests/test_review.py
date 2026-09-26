"""review/scripts/review.py — explicit ranges, stable IDs, dispositions that can't lie.

Approach: throwaway repos under a fake projects root (VERIFY_PROJECTS) — one generic, one
under `wellmed/` so project detection selects the domain groups — and a fixture answer
standing in for the reviewer. The executor is not under test; the plumbing both executors
share is. Coverage is checked with verdict-gate.py's own function, so the test proves what
the gate will see.
"""

import json
import os
import subprocess
import tempfile
import unittest

from _helpers import load, run

REVIEW = "review/scripts/review.py"


def git(path, *args):
    return subprocess.run(["git", "-C", path, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          check=True, capture_output=True, text=True).stdout.strip()


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class TestReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.projects = os.path.join(self.tmp.name, "projects")
        self.repo = self.mkrepo("wellmed/svc")
        self.generic = self.mkrepo("other/tool")
        self.scope = os.path.join(self.projects, "plans", "9-x")
        os.makedirs(os.path.join(self.scope, "artifacts"))
        self.env = dict(os.environ, VERIFY_PROJECTS=self.projects)
        self.log = os.path.join(self.scope, "artifacts", "review-9.1.jsonl")

    def tearDown(self):
        self.tmp.cleanup()

    def mkrepo(self, rel):
        path = os.path.join(self.projects, rel)
        os.makedirs(path)
        git(path, "init", "-q", "-b", "main")
        git(path, "commit", "-q", "--allow-empty", "-m", "base")
        with open(os.path.join(path, "a.sh"), "w") as fh:
            fh.write("#!/bin/sh\ncurl x || true\n")
        git(path, "add", "-A")
        git(path, "commit", "-q", "-m", "work")
        return path

    def rng(self, repo):
        return f"{git(repo, 'rev-list', '--max-parents=0', 'HEAD')}..HEAD"

    def answer(self, **over):
        doc = {"findings": [
            {"file": "a.sh", "line": 2, "severity": "note", "category": "dirty-comment", "group": "",
             "text": "n", "fix": ""},
            {"file": "a.sh", "line": 2, "severity": "blocking", "category": "silent-failure", "group": "",
             "text": "`|| true` swallows the curl failure", "fix": "drop it"},
            {"file": "b.go", "line": 9, "severity": "should-fix", "category": "domain", "group": "3.5",
             "text": "no tenant filter", "fix": "filter"}],
            "checked_clear": ["3.1"], "not_applicable": ["3.2 — no FHIR"], "cannot_do": ["no network"],
            "verdict": "SHIP AFTER BLOCKING"}
        doc.update(over)
        path = os.path.join(self.tmp.name, "answer.json")
        with open(path, "w") as fh:
            json.dump(doc, fh)
        return path

    def record(self, reviewer="codex gpt-test", **over):
        return run(REVIEW, "record", "--repo", self.repo, "--range", self.rng(self.repo), "--reviewer", reviewer,
                   "--input", self.answer(**over), "--scope", self.scope, "--unit", "9.1", "--passes", "p",
                   env=self.env)

    def findings(self):
        with open(self.log) as fh:
            return [r for r in map(json.loads, fh) if r["record"] == "finding"]

    # ---- prepare
    def test_prepare_selects_rules_by_project(self):
        cases = [(self.repo, (), "domain ✓ (wellmed)", "apply all groups"),
                 (self.generic, (), "domain n/a — generic repo", None),
                 (self.repo, ("--engine-only",), "domain SKIPPED (--engine-only)", None),
                 (self.repo, ("--kalpa-only",), "engine SKIPPED (--kalpa-only)", "apply all groups")]
        for repo, flags, passes, rule in cases:
            with self.subTest(repo=repo, flags=flags):
                p = run(REVIEW, "prepare", "--repo", repo, "--range", self.rng(repo), *flags, env=self.env)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertIn(passes, p.stdout)
                prompt = read(p.stdout.split("prompt: ")[1].split()[0])
                self.assertNotIn("{{", prompt)
                self.assertIn("(1 commits)", prompt)
                self.assertIn("rules/lenses.md", prompt)
                if rule:
                    self.assertIn(rule, prompt)
                else:
                    self.assertNotIn("rules/domain.md", prompt)

    def test_prepare_refuses_empty_and_bad_ranges(self):
        head = git(self.repo, "rev-parse", "HEAD")
        empty = run(REVIEW, "prepare", "--repo", self.repo, "--range", f"{head}..HEAD", env=self.env)
        self.assertEqual(empty.returncode, 3)
        self.assertIn("range is empty", empty.stderr)
        self.assertEqual(run(REVIEW, "prepare", "--repo", self.repo, "--range", "HEAD", env=self.env).returncode, 2)

    # ---- record
    def test_record_assigns_stable_ids_in_severity_order(self):
        p = self.record()
        self.assertEqual(p.returncode, 0, p.stderr)
        got = [(f["finding_id"], f["severity"]) for f in self.findings()]
        self.assertEqual(got, [("9.1-r1-01", "blocking"), ("9.1-r1-02", "should-fix"), ("9.1-r1-03", "note")])
        self.assertEqual(self.findings()[0]["range"], {"wellmed/svc": self.rng(self.repo)})
        self.record()
        self.assertEqual(self.findings()[-1]["finding_id"], "9.1-r2-03")
        report = read(os.path.join(self.scope, "artifacts", "review-9.1-r1.md"))
        for needle in ("## BLOCKING (1)", "**9.1-r1-01** `a.sh:2`", "## Not applicable", "3.2 — no FHIR",
                       "## What this review did not cover", "- no network", "**Verdict:** SHIP AFTER BLOCKING"):
            self.assertIn(needle, report)
        self.assertNotIn("DEGRADED", report)

    def test_fallback_reviewer_is_degraded_in_the_header(self):
        self.record(reviewer="claude-fallback codex not authed")
        report = read(os.path.join(self.scope, "artifacts", "review-9.1-r1.md"))
        self.assertIn("**DEGRADED:** reviewer is `claude-fallback codex not authed`", report.split("## BLOCKING")[0])

    def test_record_rejects_malformed_answers(self):
        bad = [dict(findings=[{"file": "a.sh", "line": "two", "severity": "note", "category": "engine",
                               "group": "", "text": "x", "fix": ""}]),
               dict(findings=[{"file": "a.sh", "line": 1, "severity": "meh", "category": "engine",
                               "group": "", "text": "x", "fix": ""}]),
               dict(verdict="LGTM")]
        for over in bad:
            with self.subTest(over=over):
                p = self.record(**over)
                self.assertEqual(p.returncode, 3, p.stdout)
                self.assertIn("nothing recorded", p.stderr)
        self.assertFalse(os.path.exists(self.log))

    def test_record_without_scope_prints_and_logs_nothing(self):
        p = run(REVIEW, "record", "--repo", self.repo, "--range", self.rng(self.repo), "--reviewer",
                "codex gpt-test", "--input", self.answer(), env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("## BLOCKING (1)", p.stdout)
        self.assertIn("nothing logged", p.stderr)

    # ---- dispose
    def dispose(self, fid, *how):
        return run(REVIEW, "dispose", "--scope", self.scope, "--unit", "9.1", "--finding", fid, *how,
                   "--by", "t", env=self.env)

    def test_dispositions_and_gate_coverage(self):
        self.record()
        gate = load("verdict-gate.py")
        blocks, n = gate.coverage_blocks(self.log)
        self.assertEqual((len(blocks), n), (3, 3))
        self.assertEqual(self.dispose("9.1-r9-99", "--rejected", "x").returncode, 2)
        # a fix commit that does not touch a.sh is refused
        with open(os.path.join(self.repo, "other.txt"), "w") as fh:
            fh.write("x")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "unrelated")
        wrong = self.dispose("9.1-r1-01", "--fixed", git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(wrong.returncode, 1)
        self.assertIn("does not touch the finding's file", wrong.stderr)
        # a real fix touching a.sh is accepted
        with open(os.path.join(self.repo, "a.sh"), "w") as fh:
            fh.write("#!/bin/sh\nset -e\ncurl x\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "fix")
        self.assertEqual(self.dispose("9.1-r1-01", "--fixed", git(self.repo, "rev-parse", "HEAD")).returncode, 0)
        self.assertEqual(self.dispose("9.1-r1-02", "--rejected", "   ").returncode, 1)
        self.assertEqual(self.dispose("9.1-r1-02", "--rejected", "tenant filter is in the repo layer").returncode, 0)
        self.assertEqual(len(gate.coverage_blocks(self.log)[0]), 1)
        self.assertEqual(self.dispose("9.1-r1-03", "--rejected", "comment is accurate").returncode, 0)
        self.assertEqual(gate.coverage_blocks(self.log), ([], 3))


if __name__ == "__main__":
    unittest.main()
