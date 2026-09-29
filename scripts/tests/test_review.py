"""review/scripts/review.py — explicit ranges, stable IDs, dispositions that can't lie.

Approach: throwaway repos under a fake projects root (VERIFY_PROJECTS) — one generic, one
under `wellmed/` so project detection selects the domain groups — and a fixture answer
standing in for the reviewer. The executor is not under test; the plumbing both executors
share is. Coverage is checked with verdict-gate.py's own function, so the test proves what
the gate will see.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from _helpers import load, run, script

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

    def rng(self, repo, base=None):
        """The immutable range `record` requires: full SHAs, never `HEAD`."""
        base = base or git(repo, "rev-list", "--max-parents=0", "HEAD")
        return f"{git(repo, 'rev-parse', base)}..{git(repo, 'rev-parse', 'HEAD')}"

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
        iris = self.mkrepo("wellmed/kalpa-iris")
        wt = os.path.join(self.tmp.name, "herdr-wt")
        git(iris, "worktree", "add", "-q", wt)
        cases = [(self.repo, (), "domain ✓ (wellmed)", "apply §3.1–§3.8"),
                 (iris, (), "domain ✓ (iris)", "never §3.3/§3.4"),
                 (wt, (), "domain ✓ (iris)", "never §3.3/§3.4"),
                 (self.generic, (), "domain n/a — generic repo", None),
                 (self.repo, ("--engine-only",), "domain SKIPPED (--engine-only)", None),
                 (self.repo, ("--kalpa-only",), "engine SKIPPED (--kalpa-only)", "apply §3.1–§3.8")]
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

    def test_range_is_immutable_from_prepare_to_record(self):
        # 5.2-r3-01/-02: prepare resolves the range; record refuses a symbolic one, and an
        # unresolvable side is an error, never an empty SHA.
        root = git(self.repo, "rev-list", "--max-parents=0", "HEAD")
        p = run(REVIEW, "prepare", "--repo", self.repo, "--range", f"{root}..HEAD", env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(f"range: {self.rng(self.repo)}", p.stdout)
        self.assertIn(self.rng(self.repo), read(p.stdout.split("prompt: ")[1].split()[0]))
        sym = run(REVIEW, "record", "--repo", self.repo, "--range", f"{root}..HEAD", "--reviewer", "codex gpt-test",
                  "--input", self.answer(), "--scope", self.scope, "--unit", "9.1", env=self.env)
        self.assertEqual(sym.returncode, 2, sym.stderr)
        self.assertIn("immutable range prepare printed", sym.stderr)
        self.assertFalse(os.path.exists(self.log))
        rr = load("review/scripts/review.py")
        self.assertEqual(rr.resolve_range(self.repo, f"{root}..nosuchref")[0], None)

    def test_clean_reviews_reserve_distinct_ids(self):
        # 5.2-r1-07: a zero-finding review still writes a `review` record, so the next one
        # doesn't reuse its ID; and a missing artifacts dir is created, not a crash.
        shutil.rmtree(os.path.join(self.scope, "artifacts"))
        for n in (1, 2):
            p = self.record(findings=[], verdict="SHIP")
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn(f"review 9.1-r{n}: 0 finding(s)", p.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.scope, "artifacts", "review-9.1-r2.md")))

    def test_concurrent_reviews_mint_distinct_ids(self):
        # 5.2-r1-04: allocation and append happen under one lock.
        answer, rng = self.answer(), self.rng(self.repo)
        procs = [subprocess.Popen([sys.executable, script(REVIEW), "record", "--repo", self.repo, "--range",
                                   rng, "--reviewer", "codex gpt-test", "--input", answer,
                                   "--scope", self.scope, "--unit", "9.1"], env=self.env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) for _ in range(6)]
        for p in procs:
            _, err = p.communicate()
            self.assertEqual(p.returncode, 0, err)
        ids = [f["finding_id"] for f in self.findings()]
        self.assertEqual(len(ids), 18)
        self.assertEqual(len(set(ids)), 18)

    def test_duplicate_finding_ids_block_coverage(self):
        self.record()
        with open(self.log) as fh:
            recs = [json.loads(x) for x in fh]
        dup = dict(next(r for r in recs if r.get("finding_id") == "9.1-r1-01"), text="a different finding")
        with open(self.log, "a") as fh:
            fh.write(json.dumps(dup) + "\n")
        for fid in ("9.1-r1-01", "9.1-r1-02", "9.1-r1-03"):
            self.assertEqual(self.dispose(fid, "--rejected", "x").returncode, 0)
        blocks, _ = load("verdict-gate.py").coverage_blocks(self.log)
        self.assertEqual([b[1] for b in blocks], ["duplicate finding ID"])

    def test_fallback_review_marks_the_index_until_a_codex_review(self):
        # 5.2-r1-08: the gate reads the latest review's reviewer, not only verify's judge.
        gate = load("verdict-gate.py")
        table = os.path.join(self.scope, "finish-conditions.md")
        with open(table, "w") as fh:
            fh.write("**Schema version:** verify/1\n**Revision:** 1\n\n"
                     "| check_id | deliverable | owner | class | check | repo | dir | env | timeout | rung | "
                     "unreachable_ok | evidence |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n"
                     "| ok | x | 9.1 | B | `true` | wellmed/svc | . | - | - | 4 | no | ev |\n")
        self.record(reviewer="claude-fallback codex not authed", findings=[], verdict="SHIP")
        judges = gate.evaluate(self.scope, "9.1", self.projects)[2]
        self.assertIn("review claude-fallback codex not authed", judges)
        self.record(findings=[], verdict="SHIP")
        self.assertEqual(gate.evaluate(self.scope, "9.1", self.projects)[2], [])

    def test_only_a_covering_codex_review_clears_a_fallback(self):
        # 5.2-r2-01: a codex review of a narrower range leaves the fallback-reviewed commits
        # without codex, so the marker stays; a covering one clears it.
        gate = load("verdict-gate.py")
        with open(os.path.join(self.repo, "c.sh"), "w") as fh:
            fh.write("echo c\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "more")
        wide, narrow = self.rng(self.repo), self.rng(self.repo, "HEAD~1")

        def review(reviewer, rng):
            p = run(REVIEW, "record", "--repo", self.repo, "--range", rng, "--reviewer", reviewer, "--input",
                    self.answer(findings=[], verdict="SHIP"), "--scope", self.scope, "--unit", "9.1", env=self.env)
            self.assertEqual(p.returncode, 0, p.stderr)

        review("claude-fallback codex out of credits", wide)
        review("codex gpt-test", narrow)
        marks = gate.fallback_markers(self.log, self.projects)
        self.assertEqual(marks, ["review claude-fallback codex out of credits"])
        review("codex gpt-test", wide)
        self.assertEqual(gate.fallback_markers(self.log, self.projects), [])

    def test_fallback_reviewer_is_degraded_in_the_header(self):
        self.record(reviewer="claude-fallback codex not authed")
        report = read(os.path.join(self.scope, "artifacts", "review-9.1-r1.md"))
        self.assertIn("**DEGRADED:** reviewer is `claude-fallback codex not authed`", report.split("## BLOCKING")[0])

    def test_record_rejects_malformed_answers(self):
        bad = [dict(findings=[{"file": "a.sh", "line": "two", "severity": "note", "category": "engine",
                               "group": "", "text": "x", "fix": ""}]),
               dict(findings=[{"file": "a.sh", "line": 1, "severity": "meh", "category": "engine",
                               "group": "", "text": "x", "fix": ""}]),
               dict(verdict="LGTM"),
               # 5.2-r1-06: containers and required fields come from the schema file
               dict(findings=None), dict(findings={}), dict(findings=["a.sh:2 bad"]),
               dict(findings=[{"file": "a.sh", "line": 1, "severity": "note", "category": "engine",
                               "text": "x"}]),
               dict(cannot_do="everything")]
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

    def test_deferred_only_for_non_blocking_with_a_todo(self):
        self.record()
        gate = load("verdict-gate.py")
        self.assertEqual(self.dispose("9.1-r1-01", "--deferred", "TO-DO: x").returncode, 1)  # blocking
        self.assertEqual(self.dispose("9.1-r1-02", "--deferred", "  ").returncode, 1)
        self.assertEqual(self.dispose("9.1-r1-02", "--deferred", "TO-DO: tenant filter").returncode, 0)
        self.assertEqual(self.dispose("9.1-r1-03", "--deferred", "TO-DO: comment").returncode, 0)
        self.assertEqual([b[0] for b in gate.coverage_blocks(self.log)[0]], ["9.1-r1-01"])
        # a hand-written deferral of the blocking finding still blocks
        with open(self.log, "a") as fh:
            fh.write(json.dumps({"schema": "verify/1", "ts": "t", "record": "disposition", "finding_id": "9.1-r1-01",
                                 "disposition": "deferred", "sha": None, "reason": "later", "by": "t"}) + "\n")
        self.assertIn("deferred", gate.coverage_blocks(self.log)[0][0][1])

    def test_convergence_signals(self):
        for _ in range(3):
            p = self.record()
            self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("[CONVERGENCE] a.sh drew findings in each of the last 3 rounds", p.stdout)
        self.assertIn("[CONVERGENCE] b.go", p.stdout)
        self.assertNotIn("round 3 >", p.stdout)
        p = self.record(findings=[])
        self.assertIn("[CONVERGENCE] round 4 > 3", p.stdout)
        self.assertNotIn("drew findings", p.stdout)  # a clean round breaks the streak


if __name__ == "__main__":
    unittest.main()
