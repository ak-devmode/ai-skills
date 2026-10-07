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
        for f in doc["findings"] if isinstance(doc["findings"], list) else []:
            if isinstance(f, dict):
                f.setdefault("target", "shipped")   # required since plan 7.1 (lenses §7)
        path = os.path.join(self.tmp.name, "answer.json")
        with open(path, "w") as fh:
            json.dump(doc, fh)
        return path

    def record(self, reviewer="codex gpt-test", repo=None, extra=(), **over):
        repo = repo or self.repo
        return run(REVIEW, "record", "--repo", repo, "--range", self.rng(repo), "--reviewer", reviewer,
                   "--input", self.answer(**over), "--scope", self.scope, "--unit", "9.1", "--passes", "p",
                   *extra, env=self.env)

    def findings(self):
        with open(self.log) as fh:
            return [r for r in map(json.loads, fh) if r["record"] == "finding"]

    # ---- prepare --lean (plan 7)
    def lean(self, repo, *flags):
        p = run(REVIEW, "prepare", "--repo", repo, "--range", self.rng(repo), "--lean",
                "--out-dir", os.path.join(self.tmp.name, "lean"), *flags, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        bundle = read(p.stdout.split("prompt: ")[1].split()[0])
        uncovered = bundle.split("## Not in this bundle")[1].split("## The diff")[0]
        self.assertNotRegex(bundle, r"\{\{[A-Z_]+\}\}")
        self.assertIn("Read no other file", bundle)
        self.assertIn("`verdict`", bundle)   # the Output contract came along
        return p.stdout, bundle, uncovered

    def test_lean_bundle_inlines_this_projects_sections_only(self):
        iris = self.mkrepo("wellmed/kalpa-iris")
        for repo, present, absent in ((self.repo, ["### 3.3", "### 3.8"], ["### 3.9"]),
                                      (iris, ["### 3.2", "### 3.9"], ["### 3.3", "### 3.4"]),
                                      (self.generic, [], ["### 3.1"])):
            with self.subTest(repo=repo):
                out, bundle, uncovered = self.lean(repo)
                self.assertIn("lean: 1 of 1 file(s) inlined", out)
                self.assertIn("+curl x || true", bundle)
                items = [x for x in uncovered.splitlines() if x.startswith("- ")]
                self.assertEqual(items, ["- the repo's `CLAUDE.md` (not present at the range's head) — not read",
                                         "- the repo's `ARCHITECTURE.md` (not present at the range's head) — not read",
                                         "- " + load(REVIEW).LEAN_NO_ADJACENT])   # always declared, by the script
                for s in present:
                    self.assertIn(s, bundle)
                for s in absent:
                    self.assertNotIn(s, bundle)
        _, bundle, _ = self.lean(self.repo, "--engine-only")
        self.assertNotIn("### 3.1", bundle)

    def test_lean_bundle_past_the_cap_lists_never_cuts(self):
        with open(os.path.join(self.repo, "big.txt"), "w") as fh:
            fh.write("".join(f"line {i}\n" for i in range(1600)))
        with open(os.path.join(self.repo, "small.sh"), "w") as fh:
            fh.write("echo small\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "big")
        out, bundle, uncovered = self.lean(self.repo)
        self.assertIn("lean: 2 of 3 file(s) inlined", out)       # a.sh + small.sh fit; big.txt does not
        self.assertIn("+echo small", bundle)
        self.assertNotIn("line 1599", bundle)                     # never partially inlined
        self.assertIn("`big.txt` — 1,600 changed lines", uncovered)
        self.assertIn("`big.txt` — 1,600 changed lines", bundle)  # and the reviewer is told

    def test_lean_bundle_inlines_a_name_git_would_quote(self):
        # review 7.1-r1-06: a quoted --numstat name used as a pathspec gave an empty patch
        for name in ("with space.sh", "ünï.sh", "star*.sh"):
            with open(os.path.join(self.repo, name), "w") as fh:
                fh.write(f"echo {name}-marker\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "odd names")
        out, bundle, _ = self.lean(self.repo)
        self.assertIn("lean: 4 of 4 file(s) inlined", out)
        for name in ("with space.sh", "ünï.sh", "star*.sh"):
            self.assertIn(f"+echo {name}-marker", bundle)

    def test_lean_bundle_lists_an_oversized_claude_md(self):
        with open(os.path.join(self.repo, "CLAUDE.md"), "w") as fh:
            fh.write("x" * 30_000)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "big claude.md")     # read at the range's head, not the tree
        _, bundle, uncovered = self.lean(self.repo)
        self.assertIn("`CLAUDE.md` (30,000 bytes", uncovered)
        self.assertNotIn("## The repo's CLAUDE.md", bundle)    # listed, never inlined as rules

    def test_lean_sections_match_groups_and_domain_md(self):
        rv = load(REVIEW)
        self.assertEqual(set(rv.LEAN_SECTIONS), set(rv.GROUPS))
        for proj, numbers in rv.LEAN_SECTIONS.items():
            self.assertEqual(len(rv.domain_sections(numbers)), len(numbers), proj)

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

    def test_prepare_runs_the_repos_declared_checks_as_evidence(self):
        """The reviewer cannot build or test in its sandbox, so the runner does and hands
        over each check's command, exit status and output — only at the range's own head."""
        def prepare(*flags):
            p = run(REVIEW, "prepare", "--repo", self.repo, "--range", self.rng(self.repo), *flags, env=self.env)
            self.assertEqual(p.returncode, 0, p.stderr)
            return p.stdout, read(p.stdout.split("prompt: ")[1].split()[0])

        out, prompt = prepare()
        self.assertIn("checks: none declared", out)
        self.assertIn("declares none in `.review-checks`", prompt)
        self.assertNotIn("{{", prompt)

        with open(os.path.join(self.repo, ".review-checks"), "w") as fh:
            fh.write("# name | command, from the repo root\nbuild | echo built-ok\n"
                     "tests | sh -c 'echo two failed; exit 3'\nnot a check line\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "declare checks")
        out, prompt = prepare()
        self.assertRegex(out, r"checks: build ✓ \(\d+s\) · tests ✗ exit 3 \(\d+s\)")
        for want in ("### build — exit 0", "$ echo built-ok", "built-ok", "### tests — exit 3", "two failed",
                     "Do not list one of them under `cannot_do`"):
            self.assertIn(want, prompt)
        self.assertNotIn("not a check line", prompt)

        out, prompt = prepare("--no-checks")
        self.assertIn("checks: skipped (--no-checks)", out)
        self.assertNotIn("built-ok", prompt)

        # Evidence of another tree is not evidence of the range: a dirty tree, or a range
        # whose head is not checked out, runs nothing and says so.
        with open(os.path.join(self.repo, "a.sh"), "a") as fh:
            fh.write("# edited, not committed\n")
        out, prompt = prepare()
        self.assertIn("checks: not run — the working tree has uncommitted changes", out)
        self.assertNotIn("built-ok", prompt)
        git(self.repo, "checkout", "-q", "--", "a.sh")
        base = git(self.repo, "rev-list", "--max-parents=0", "HEAD")
        p = run(REVIEW, "prepare", "--repo", self.repo, "--range", f"{base}..HEAD~1", env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertRegex(p.stdout, r"checks: not run — the working tree is at \w{9}, not the range's head \w{9}")

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

    def test_lean_reviewer_is_never_codex_coverage(self):
        # plan 7: a lean review needs a covering codex review to clear, exactly like a fallback
        gate = load("verdict-gate.py")
        p = self.record(reviewer="claude-lean mode lean (default)", findings=[], verdict="SHIP")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(gate.fallback_markers(self.log, self.projects), ["review claude-lean mode lean (default)"])
        report = read(os.path.join(self.scope, "artifacts", "review-9.1-r1.md"))
        self.assertIn("**DEGRADED (lean: single Sonnet pass over one bundle, no specialists, diff capped at "
                      "1,500 lines):** reviewer is `claude-lean mode lean (default)`", report.split("## BLOCKING")[0])
        self.record(findings=[], verdict="SHIP")
        self.assertEqual(gate.fallback_markers(self.log, self.projects), [])

    def test_lean_record_recomputes_what_the_range_leaves_out(self):
        # review 7.1-r2-01: the not-covered list comes from the range itself, never from the caller
        with open(os.path.join(self.repo, "big.txt"), "w") as fh:
            fh.write("".join(f"line {i}\n" for i in range(1600)))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "big")
        p = self.record(reviewer="claude-lean mode lean (default)", extra=("--mode", "mode: lean (default)"),
                        cannot_do=[])                            # a reviewer that listed nothing
        self.assertEqual(p.returncode, 0, p.stderr)
        report = read(os.path.join(self.scope, "artifacts", "review-9.1-r1.md"))
        head, tail = report.split("## BLOCKING")[0], report.split("## What this review did not cover")[1]
        self.assertIn("**mode: lean (default)**", head)
        self.assertIn("- `big.txt` — 1,600 changed lines", tail)
        self.assertIn("- " + load(REVIEW).LEAN_NO_ADJACENT, tail)
        self.record(cannot_do=[])                                # a codex review gets no lean list
        codex = read(os.path.join(self.scope, "artifacts", "review-9.1-r2.md"))
        self.assertNotIn(load(REVIEW).LEAN_NO_ADJACENT, codex)

    def test_lean_bundle_inlines_architecture_md(self):
        # review 7.1-r1-03: the full prompt reads CLAUDE.md and ARCHITECTURE.md first
        for doc, text in (("CLAUDE.md", "claude-rule-marker"), ("ARCHITECTURE.md", "arch-rule-marker")):
            with open(os.path.join(self.repo, doc), "w") as fh:
                fh.write(text + "\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "docs")
        _, bundle, _ = self.lean(self.repo)
        self.assertIn("claude-rule-marker", bundle)
        self.assertIn("arch-rule-marker", bundle)

    def test_lean_bundle_lists_a_symlinked_doc_never_reads_the_link(self):
        # review 7.1-r3-02: `git show` of a symlink returns its target path, not the document
        with open(os.path.join(self.repo, "real.md"), "w") as fh:
            fh.write("real-doc-marker\n")
        os.symlink("real.md", os.path.join(self.repo, "CLAUDE.md"))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "linked doc")
        _, bundle, uncovered = self.lean(self.repo)
        self.assertIn("`CLAUDE.md` (not a regular file at the range's head (mode 120000))", uncovered)
        self.assertNotIn("## The repo's CLAUDE.md", bundle)

    def test_lean_rounds_stop_at_three_like_codex(self):
        for rnd in (1, 2, 3):
            p = self.record(reviewer="claude-lean mode lean (default)", findings=[], verdict="SHIP")
            self.assertEqual("round 3 of 3: STOP" in p.stdout, rnd == 3, p.stdout)

    def test_scaffolding_findings_are_capped_and_force_no_rereview(self):
        # lenses §7 (Alex, 2026-10-02): block only when shipped work is wrong
        mk = lambda file, target: {"file": file, "line": 1, "severity": "blocking", "category": "fail-open",
                                   "group": "", "text": "t", "fix": "", "target": target}
        p = self.record(findings=[mk("a.sh", "shipped"), mk("check.sh", "scaffolding"),
                                  mk("plans/9-x/finish-conditions.md", "shipped")], verdict="SHIP AFTER BLOCKING")
        self.assertEqual(p.returncode, 0, p.stderr)
        by = {f["file"]: f for f in self.findings()}
        self.assertEqual((by["a.sh"]["severity"], by["a.sh"]["target"]), ("blocking", "shipped"))
        for name in ("check.sh", "plans/9-x/finish-conditions.md"):     # declared, or a scaffolding file
            self.assertEqual((by[name]["severity"], by[name]["target"], by[name]["capped"]),
                             ("should-fix", "scaffolding", True))
        report = read(os.path.join(self.scope, "artifacts", "review-9.1-r1.md"))
        self.assertIn("scaffolding, capped from blocking", report.split("## SHOULD FIX")[1])
        # a scaffolding finding fixed off-anchor needs no later review; a shipped one still does
        fix = self.commit(self.repo, "other.txt")
        gate = load("verdict-gate.py")
        for fid in (by["check.sh"]["finding_id"], by["a.sh"]["finding_id"]):
            run(REVIEW, "dispose", "--scope", self.scope, "--unit", "9.1", "--finding", fid, "--fixed", fix,
                "--off-anchor", "test", env=self.env)
        base = {"wellmed/svc": git(self.repo, "rev-list", "--max-parents=0", "HEAD")}
        blocks = [b[0] for b in gate.review_presence_blocks(self.log, base, self.projects, self.scope)]
        self.assertIn(f"rereview:{by['a.sh']['finding_id']}", blocks)
        self.assertNotIn(f"rereview:{by['check.sh']['finding_id']}", blocks)

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
        self.assertIn("does not reach the finding: a.sh is not touched", wrong.stderr)
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

    def commit(self, repo, *files):
        for rel in files:
            os.makedirs(os.path.join(repo, os.path.dirname(rel)), exist_ok=True)
            with open(os.path.join(repo, rel), "a") as fh:
                fh.write("x\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "c")
        return git(repo, "rev-parse", "HEAD")

    def test_fixed_accepts_the_anchor_else_an_off_anchor_reason(self):
        # 149.2-r11-02: a missing-coverage finding on pkg/res.go is fixed by a test-only commit —
        # off the anchor, with a reason, like every commit that does not touch the file (r2-02).
        gate = load("verdict-gate.py")
        self.record(findings=[{"file": "pkg/res.go", "line": 3, "severity": "should-fix", "category": "domain",
                               "group": "3.8", "text": "no test for the failure path", "fix": "add one"}])
        cases = [  # (files the commit changes, extra flags, exit, via)
            (["pkg/res.go"], (), 0, "anchor"),
            (["pkg/res_test.go"], (), 1, None),          # its own test is still off the anchor
            (["pkg/res_test.go"], ("--off-anchor", "adds the failure-path test"), 0, "off-anchor"),
            (["pkg/validation_test.go"], (), 1, None),
            (["other/res_test.go"], (), 1, None),
            (["pkg/sub/res_test.go"], (), 1, None),
            (["pkg/notes.md"], (), 1, None),
            (["pkg/notes.md"], ("--off-anchor", "   "), 1, None),
            (["internal/saga/continuator.go"], ("--off-anchor", "the go.mod pin was the symptom; the fix "
                                                "removes the call"), 0, "off-anchor"),
            (["pkg/res.go"], ("--off-anchor", "also explained"), 0, "anchor"),
        ]
        for files, flags, code, via in cases:
            with self.subTest(files=files, flags=flags):
                before = len(read(self.log).splitlines())
                sha = self.commit(self.repo, *files)
                p = self.dispose("9.1-r1-01", "--fixed", sha[:9], *flags)
                self.assertEqual(p.returncode, code, p.stderr)
                recs = [json.loads(x) for x in read(self.log).splitlines()]
                if code:
                    self.assertEqual(len(recs), before)
                    continue
                self.assertEqual((recs[-1]["sha"], recs[-1]["via"]), (sha, via))
                self.assertEqual(gate.coverage_blocks(self.log), ([], 1))
        self.assertEqual(self.dispose("9.1-r1-01", "--rejected", "x", "--off-anchor", "y").returncode, 2)
        # a hand-written off-anchor fix with no reason still blocks
        with open(self.log, "a") as fh:
            fh.write(json.dumps({"schema": "verify/1", "ts": "t", "record": "disposition", "finding_id": "9.1-r1-01",
                                 "disposition": "fixed", "sha": sha, "via": "off-anchor", "reason": " ",
                                 "by": "t"}) + "\n")
        self.assertEqual(gate.coverage_blocks(self.log)[0][0][1], "`fixed` off the anchor without a reason")

    def test_off_anchor_fix_needs_a_later_review_at_any_severity(self):
        # review adhoc-03: only a reason ties an off-anchor commit to the finding, so the gate
        # wants it reviewed again — a note as much as a blocking finding. An anchor fix does not.
        gate = load("verdict-gate.py")
        rng = self.rng(self.repo)
        self.record(findings=[{"file": "pkg/res.go", "line": 3, "severity": sev, "category": "engine",
                               "group": "", "text": "t", "fix": ""} for sev in ("should-fix", "note")])
        off = self.commit(self.repo, "internal/other.go")
        self.assertEqual(self.dispose("9.1-r1-01", "--fixed", off, "--off-anchor", "the caller moved").returncode, 0)
        self.assertEqual(self.dispose("9.1-r1-02", "--fixed", self.commit(self.repo, "pkg/res.go")).returncode, 0)
        presence = lambda: [b[:2] for b in gate.review_presence_blocks(self.log, {}, self.projects)]
        self.assertEqual(presence(), [("rereview:9.1-r1-01", "an off-anchor fix was never reviewed")])
        p = run(REVIEW, "record", "--repo", self.repo, "--range", f"{rng.split('..')[1]}..{git(self.repo, 'rev-parse', 'HEAD')}",
                "--reviewer", "codex gpt-test", "--input", self.answer(findings=[], verdict="SHIP"),
                "--scope", self.scope, "--unit", "9.1", env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(presence(), [])

    def test_round_cap_stop_lets_the_users_accept_stand_in_for_the_rereview(self):
        # review/SKILL.md §5.1 hard stop (kalpa-iris 1.1: five rounds re-reviewing its own
        # checkers). Before the cap a fix is re-reviewed whatever the user says; from round 3,
        # the user's `accept` after the disposition ends the loop instead of another round.
        gate = load("verdict-gate.py")
        one = [{"file": "pkg/res.go", "line": 3, "severity": "blocking", "category": "engine", "group": "",
                "text": "t", "fix": ""}]
        blocks = lambda: gate.review_presence_blocks(self.log, {}, self.projects)
        for n, waived in ((1, False), (2, False), (3, True)):
            with self.subTest(round=n):
                self.assertEqual(self.record(findings=one).returncode, 0)
                fix = self.commit(self.repo, "internal/other.go")
                self.assertEqual(self.dispose(f"9.1-r{n}-01", "--fixed", fix, "--off-anchor", "moved").returncode, 0)
                self.assertEqual([b[0] for b in blocks()], [f"rereview:9.1-r{n}-01"])
                self.assertEqual("review.py accept" in blocks()[0][2], waived)
                p = run(REVIEW, "accept", "--scope", self.scope, "--unit", "9.1", "--by", "Alex", env=self.env)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual([b[0] for b in blocks()], [] if waived else [f"rereview:9.1-r{n}-01"])

    def test_a_fix_off_the_current_branch_blocks(self):
        # review r2-04: a fix on a side branch passes dispose (it is after the review) but is
        # not in what ships until merged
        gate = load("verdict-gate.py")
        self.record(findings=[{"file": "a.sh", "line": 2, "severity": "note", "category": "engine", "group": "",
                               "text": "t", "fix": ""}])
        git(self.repo, "checkout", "-q", "-b", "side")
        side = self.commit(self.repo, "a.sh")
        self.assertEqual(self.dispose("9.1-r1-01", "--fixed", side).returncode, 0)
        git(self.repo, "checkout", "-q", "main")
        ids = lambda: [b[0] for b in gate.review_presence_blocks(self.log, {}, self.projects)]
        self.assertEqual(ids(), ["unmerged:9.1-r1-01"])
        git(self.repo, "merge", "-q", "--ff-only", "side")
        self.assertEqual(ids(), [])

    def test_a_test_alone_never_fixes_a_blocking_finding(self):
        # review adhoc-02: its own test, but the defect is in the code
        self.record(findings=[{"file": "pkg/res.go", "line": 3, "severity": "blocking", "category": "fail-open",
                               "group": "", "text": "err swallowed", "fix": "return it"}])
        sha = self.commit(self.repo, "pkg/res_test.go")
        p = self.dispose("9.1-r1-01", "--fixed", sha)
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertIn("a commit in wellmed/svc changing pkg/res.go\n", p.stderr)
        p = self.dispose("9.1-r1-01", "--fixed", sha, "--off-anchor", "the test pins the contract the caller relies on")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("(via off-anchor)", p.stdout)

    def test_fixed_in_another_repo(self):
        # 149.2-r5-01: a bpjs finding fixed at its source in gateway-go; 149.2-r2-03/-r18-03:
        # findings on a docs-repo hand-back file. The sha must exist where --fixed-in says, and a
        # fix in another repo is always off the anchor: no directory-name matching (r2-06).
        gw, docs = self.mkrepo("wellmed/gw"), self.mkrepo("wellmed/kalpa-docs")
        gw_wt = os.path.join(self.tmp.name, "gw-wt")
        git(gw, "worktree", "add", "-q", gw_wt)
        mk = lambda file, sev="note": {"file": file, "line": 1, "severity": sev, "category": "domain",
                                       "group": "3.1", "text": "t", "fix": ""}
        self.record(findings=[mk("go.mod", "blocking"), mk("kalpa-docs/plans/x.md"),
                              mk(os.path.join(docs, "plans", "y.md"))])
        gw_fix = self.commit(gw, "go.mod", "internal/egress/errors.go")   # touches a go.mod — not svc's
        docs_fix = self.commit(docs, "plans/x.md", "plans/y.md")
        svc_sha = git(self.repo, "rev-parse", "HEAD")
        cases = [  # (finding, flags, exit, recorded repo, via)
            ("9.1-r1-01", ("--fixed", gw_fix), 1, None, None),                              # not in svc
            ("9.1-r1-01", ("--fixed", gw_fix, "--fixed-in", gw), 1, None, None),            # go.mod is svc's
            ("9.1-r1-01", ("--fixed", svc_sha, "--fixed-in", gw), 1, None, None),           # sha not in gw
            ("9.1-r1-01", ("--fixed", gw_fix, "--fixed-in", "/no/such/repo"), 2, None, None),
            ("9.1-r1-01", ("--fixed-in", gw, "--rejected", "x"), 2, None, None),
            ("9.1-r1-01", ("--fixed", gw_fix, "--fixed-in", gw_wt, "--off-anchor", "egress errors carry no URL"),
             0, "wellmed/gw", "off-anchor"),
            ("9.1-r1-02", ("--fixed", docs_fix, "--fixed-in", docs), 1, None, None),        # touched, but elsewhere
            ("9.1-r1-02", ("--fixed", docs_fix, "--fixed-in", docs, "--off-anchor", "hand-back corrected"), 0,
             "wellmed/kalpa-docs", "off-anchor"),
            ("9.1-r1-03", ("--fixed", docs_fix[:8], "--fixed-in", os.path.join(docs, "plans"), "--off-anchor",
                           "hand-back corrected"), 0, "wellmed/kalpa-docs", "off-anchor"),   # a subdir resolves up
            ("9.1-r1-02", ("--fixed", docs_fix, "--fixed-in", self.repo), 1, None, None),   # own repo: not there
        ]
        for fid, flags, code, repo, via in cases:
            with self.subTest(fid=fid, flags=flags):
                before = len(read(self.log).splitlines())
                p = self.dispose(fid, *flags)
                self.assertEqual(p.returncode, code, p.stderr)
                recs = [json.loads(x) for x in read(self.log).splitlines()]
                if code:
                    self.assertEqual(len(recs), before)
                else:
                    self.assertEqual((recs[-1]["finding_id"], recs[-1]["repo"], recs[-1]["via"]), (fid, repo, via))
        gate = load("verdict-gate.py")
        self.assertEqual(gate.coverage_blocks(self.log), ([], 3))
        # the blocking fix is re-reviewed in the repo that holds it, not the finding's
        rereview = lambda: [b[0] for b in gate.review_presence_blocks(self.log, {}, self.projects)]
        self.assertEqual(rereview(), ["rereview:9.1-r1-01", "rereview:9.1-r1-02", "rereview:9.1-r1-03"])
        for repo, left in ((gw, ["rereview:9.1-r1-02", "rereview:9.1-r1-03"]), (docs, [])):
            p = run(REVIEW, "record", "--repo", repo, "--range", self.rng(repo), "--reviewer", "codex gpt-test",
                    "--input", self.answer(findings=[], verdict="SHIP"), "--scope", self.scope, "--unit", "9.1",
                    env=self.env)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(rereview(), left)

    def test_fixed_refuses_the_reviewed_code(self):
        # review adhoc-01: the commit that introduced a finding touches its file, so the reviewed
        # code itself was accepted as its own fix — and the original review's range satisfied
        # the gate's re-review check. In the finding's repo by ancestry; elsewhere by date.
        gate = load("verdict-gate.py")
        intro = self.commit(self.repo, "pkg/res.go")
        gw = self.mkrepo("wellmed/gw")
        with open(os.path.join(gw, "old.go"), "w") as fh:
            fh.write("x\n")
        git(gw, "add", "-A")
        subprocess.run(["git", "-C", gw, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "old"],
                       check=True, env=dict(os.environ, GIT_COMMITTER_DATE="2000-01-01T00:00:00Z"))
        old = git(gw, "rev-parse", "HEAD")
        self.record(findings=[{"file": "pkg/res.go", "line": 3, "severity": "blocking", "category": "fail-open",
                               "group": "", "text": "err swallowed", "fix": "return it"}])
        cases = [  # (flags, exit, stderr needle)
            (("--fixed", intro), 1, "predates the finding: it is in the code that review reviewed"),
            (("--fixed", intro, "--off-anchor", "explained"), 1, "predates the finding"),
            (("--fixed", old, "--fixed-in", gw, "--off-anchor", "explained"), 1, "committed before the review"),
        ]
        for flags, code, needle in cases:
            with self.subTest(flags=flags):
                p = self.dispose("9.1-r1-01", *flags)
                self.assertEqual(p.returncode, code, p.stderr)
                self.assertIn(needle, p.stderr)
        self.assertEqual(self.dispose("9.1-r1-01", "--fixed", self.commit(self.repo, "pkg/res.go")).returncode, 0)
        # r2-05: in another repo the date decides, and an unknown review time fails closed
        rr, new = load(REVIEW), self.commit(gw, "new.go")
        f = {"range": {"wellmed/svc": "a.." + git(self.repo, "rev-parse", "HEAD")}}
        cases = [("2000-06-01T00:00:00Z", None), (None, "time is unknown"), ("garbage", "time is unknown"),
                 ("2099-01-01T00:00:00Z", "committed before the review")]
        for ts, needle in cases:
            with self.subTest(ts=ts):
                why = rr.predates(dict(f, ts=ts), new, gw, [])
                (self.assertIsNone(why) if needle is None else self.assertIn(needle, why or ""))
        # misfiled names the old commit as not a fix instead of printing its dispose line
        self.dispose("9.1-r1-01", "--rejected", f"FIXED by {intro[:8]}")
        self.dispose("9.1-r1-01", "--rejected", f"by design since {intro[:8]}; NOT FIXED, out of scope")
        p = run(REVIEW, "misfiled", "--scope", self.scope, "--unit", "9.1", env=self.env)
        self.assertIn("no affirmative `FIXED` claim", p.stdout)
        self.assertNotIn("--fixed ", p.stdout)
        self.dispose("9.1-r1-01", "--rejected", f"FIXED by {intro[:8]}")
        p = run(REVIEW, "misfiled", "--scope", self.scope, "--unit", "9.1", env=self.env)
        self.assertIn(f"{intro[:8]}: not a fix", p.stdout)
        self.assertNotIn(f"--fixed {intro[:8]}", p.stdout)
        # a hand-written record of the reviewed code as the fix blocks at the gate
        with open(self.log, "a") as fh:
            fh.write(json.dumps({"schema": "verify/1", "ts": "t", "record": "disposition", "finding_id": "9.1-r1-01",
                                 "disposition": "fixed", "sha": intro, "repo": "wellmed/svc", "via": "anchor",
                                 "reason": None, "by": "t"}) + "\n")
        self.assertIn("predates:9.1-r1-01", [b[0] for b in gate.review_presence_blocks(self.log, {}, self.projects)])

    def test_fixed_in_is_the_same_repo_only_by_git_identity(self):
        # review adhoc-04: a repo outside the projects root keys by basename, so a stranger named
        # like the finding's repo matched by key and its same-named file counted as the anchor.
        own = self.mkrepo("svc2")
        p = run(REVIEW, "record", "--repo", own, "--range", self.rng(own), "--reviewer", "codex gpt-test",
                "--input", self.answer(), "--scope", self.scope, "--unit", "9.1", env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        stranger = os.path.join(self.tmp.name, "elsewhere", "svc2")
        os.makedirs(stranger)
        git(stranger, "init", "-q", "-b", "main")
        sha = self.commit(stranger, "a.sh")
        p = self.dispose("9.1-r1-01", "--fixed", sha, "--fixed-in", stranger)
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertIn("is outside", p.stderr)
        rr = load(REVIEW)
        f = {"range": {"svc2": "a..b"}, "file": "a.sh"}
        cases = [(own, True), (stranger, False), (self.repo, False)]
        self.addCleanup(setattr, rr.vl, "PROJECTS", rr.vl.PROJECTS)  # verify_lib is shared in-process
        rr.vl.PROJECTS = self.projects
        for path, want in cases:
            with self.subTest(path=path):
                self.assertEqual(rr.same_repo(f, path, "svc2"), want)

    def test_misfiled_rejections_redispose_as_fixed(self):
        # 149.2 logged real fixes as "rejected — not rejected on merit — FIXED by <sha>". The
        # latest disposition decides (§6.3), so a new `fixed` record supersedes each one.
        gate = load("verdict-gate.py")
        self.record()
        fix = self.commit(self.repo, "a.sh")
        self.dispose("9.1-r1-01", "--rejected", f"not rejected on merit — FIXED by {fix[:7]} (tooling gap)")
        self.dispose("9.1-r1-02", "--rejected", "FIXED in kalpa-docs, committed with the progress notes")
        self.dispose("9.1-r1-03", "--rejected", "the comment is accurate as of 20260929")
        # review adhoc-07: a negated claim, and a SHA cited outside the FIXED clause, print no dispose line
        rr = load(REVIEW)
        cases = [(f"NOT FIXED by {fix[:8]}: by design", (False, [])),
                 (f"was never FIXED; see {fix[:8]}", (False, [])),
                 (f"FIXED by {fix[:8]}; the bug came from abcdef12", (True, [fix[:8]])),
                 ("not rejected on merit — FIXED in kalpa-docs decd35d", (True, ["decd35d"])),
                 ("not rejected on merit", (False, [])),
                 (f"FIXED upstream\nNOT FIXED by {fix[:8]}", (True, [])),          # r2-07
                 (f"FIXED upstream! NOT FIXED by {fix[:8]}", (True, [])),
                 (f"FIXED by {fix[:8]}? no", (True, [fix[:8]])),
                 # kalpa-iris 1.1 worded its four misfiled fixes in lower case
                 (f"Fixed in the rows, not the generator ({fix[:8]}, rows.py → v.md). Declined: x",
                  (True, [fix[:8]])),
                 (f"Bookkeeping, resolved without an edit: committed in {fix[:8]}.", (True, [fix[:8]])),
                 (f"left unresolved; see {fix[:8]}", (False, [])),
                 (f"not fixed by {fix[:8]}", (False, []))]
        for reason, want in cases:
            with self.subTest(reason=reason):
                self.assertEqual(rr.fix_claims(reason), want)
        ls = lambda: run(REVIEW, "misfiled", "--scope", self.scope, "--unit", "9.1", env=self.env)
        p = ls()
        self.assertEqual(p.returncode, 0, p.stderr)
        cases = [  # (needle, present)
            (f"--finding 9.1-r1-01 --fixed {fix[:7]}    # wellmed/svc, via anchor", True),
            ("9.1-r1-02 should-fix", True), ("no SHA in the reason resolves", True),
            ("9.1-r1-03", False),               # a rejection on merit is not misfiled
            ("20260929", False),                # a digit-only token resolving nowhere is not a SHA
            ("2 misfiled rejection(s) in 9.1", True)]
        for needle, present in cases:
            with self.subTest(needle=needle):
                (self.assertIn if present else self.assertNotIn)(needle, p.stdout)
        cmd = next(x for x in p.stdout.splitlines() if "--finding 9.1-r1-01" in x).split("#")[0].split()
        redo = subprocess.run([sys.executable] + cmd + ["--by", "t"], env=self.env, capture_output=True, text=True)
        self.assertEqual(redo.returncode, 0, redo.stderr)
        latest = {r["finding_id"]: r for r in map(json.loads, read(self.log).splitlines())
                  if r["record"] == "disposition"}
        self.assertEqual((latest["9.1-r1-01"]["disposition"], latest["9.1-r1-01"]["sha"]), ("fixed", fix))
        self.assertIn("1 misfiled rejection(s) in 9.1", ls().stdout)
        self.assertEqual(gate.coverage_blocks(self.log), ([], 3))
        p = run(REVIEW, "accept", "--scope", self.scope, "--unit", "9.1", "--by", "Alex", env=self.env)
        self.assertIn("1 fixed, 2 rejected", p.stdout)

    def test_worktree_review_is_keyed_by_the_primary_checkout(self):
        wt = os.path.join(self.tmp.name, "herdr-wt-rec")
        git(self.repo, "worktree", "add", "-q", wt)
        p = run(REVIEW, "record", "--repo", wt, "--range", self.rng(wt), "--reviewer", "codex gpt-test",
                "--input", self.answer(), "--scope", self.scope, "--unit", "9.1", "--passes", "p", env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(list(self.findings()[0]["range"]), ["wellmed/svc"])
        with open(os.path.join(wt, "a.sh"), "w") as fh:
            fh.write("#!/bin/sh\nset -e\ncurl x\n")
        git(wt, "add", "-A")
        git(wt, "commit", "-q", "-m", "fix in the worktree")
        self.assertEqual(self.dispose("9.1-r1-01", "--fixed", git(wt, "rev-parse", "HEAD")).returncode, 0)

    def test_deferred_only_past_the_round_cap_with_a_written_todo(self):
        gate = load("verdict-gate.py")
        self.record()
        self.assertEqual(self.dispose("9.1-r1-02", "--deferred", "TO-DO: early").returncode, 1)  # round 1
        for _ in range(3):
            self.record()
        todo = os.path.join(os.path.dirname(self.scope), "TO-DO.md")
        self.assertEqual(self.dispose("9.1-r4-02", "--deferred", "tenant filter").returncode, 1)  # no file
        with open(todo, "w") as fh:
            fh.write("Prose naming 9.1-r4-02 outside an item.\n- [x] [review 9.1-r4-03] closed already\n"
                     "- [ ] [review 9.1-r4-020] a different finding\n- [ ] tenant filter, unlinked\n"
                     "- [ ] unrelated task, see 9.1-r4-02 for context\n- [ ] [review 9.1-r4-02]\n")
        for why in ("prose", "closed", "longer ID", "unlinked", "mentioned, not marked", "bare marker"):
            with self.subTest(why=why):
                self.assertEqual(self.dispose("9.1-r4-02", "--deferred", "tenant filter").returncode, 1)
        self.assertEqual(self.dispose("9.1-r4-03", "--deferred", "comment").returncode, 1)  # only a closed item
        with open(todo, "a") as fh:
            fh.write("- [ ] [review 9.1-r4-02] tenant filter\n- [ ] [review 9.1-r4-03] comment\n"
                     "- [ ] [review 9.1-r4-01] blocking one\n")
        self.assertEqual(self.dispose("9.1-r4-01", "--deferred", "x").returncode, 1)  # blocking
        self.assertEqual(self.dispose("9.1-r4-02", "--deferred", "  ").returncode, 1)
        self.assertEqual(self.dispose("9.1-r4-02", "--deferred", "tenant filter").returncode, 0)
        self.assertEqual(self.dispose("9.1-r4-03", "--deferred", "comment").returncode, 0)
        r4 = [b[0] for b in gate.coverage_blocks(self.log)[0] if b[0].startswith("9.1-r4-")]
        self.assertEqual(r4, ["9.1-r4-01"])
        # closing an item into the archive keeps the deferral valid; deleting it does not
        os.makedirs(os.path.join(os.path.dirname(self.scope), "archive"), exist_ok=True)
        with open(os.path.join(os.path.dirname(self.scope), "archive", "TO-DO-archive.md"), "w") as fh:
            fh.write("- [x] [review 9.1-r4-03] comment — done\n")
        with open(todo, "w") as fh:
            fh.write("- [ ] [review 9.1-r4-02] tenant filter\n")
        r4 = [b[0] for b in gate.coverage_blocks(self.log)[0] if b[0].startswith("9.1-r4-")]
        self.assertEqual(r4, ["9.1-r4-01"])
        with open(todo, "w") as fh:
            fh.write("")
        r4 = [b[0] for b in gate.coverage_blocks(self.log)[0] if b[0].startswith("9.1-r4-")]
        self.assertEqual(r4, ["9.1-r4-01", "9.1-r4-02"])
        # a hand-written deferral of the blocking finding still blocks
        with open(self.log, "a") as fh:
            fh.write(json.dumps({"schema": "verify/1", "ts": "t", "record": "disposition", "finding_id": "9.1-r4-01",
                                 "disposition": "deferred", "sha": None, "reason": "later", "by": "t"}) + "\n")
        self.assertTrue(any(b[0] == "9.1-r4-01" and "deferred" in b[1] for b in gate.coverage_blocks(self.log)[0]))

    def test_accept_needs_every_disposition_and_a_new_finding_reopens(self):
        self.record()
        accept = lambda: run(REVIEW, "accept", "--scope", self.scope, "--unit", "9.1", "--by", "Alex", env=self.env)
        gate = load("verdict-gate.py")
        self.assertEqual(accept().returncode, 1)  # open findings
        self.dispose("9.1-r1-01", "--rejected", "x")
        self.dispose("9.1-r1-02", "--rejected", "y")
        self.dispose("9.1-r1-03", "--rejected", "z")
        self.assertFalse(gate.accepted(self.log))
        p = accept()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("0 fixed, 3 rejected, 0 deferred", p.stdout)
        self.assertTrue(gate.accepted(self.log))
        self.record()
        self.assertFalse(gate.accepted(self.log))

    def test_gate_requires_acceptance_only_under_an_approved_table(self):
        gate = load("verdict-gate.py")
        table = os.path.join(self.scope, "finish-conditions.md")
        body = ("\n\n| check_id | deliverable | owner | class | check | repo | dir | env | timeout | rung | "
                "unreachable_ok | evidence |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n"
                "| ok | x | 9.1 | B | `true` | wellmed/svc | . | - | - | 4 | no | ev |\n")
        self.record()
        for fid in ("9.1-r1-01", "9.1-r1-02", "9.1-r1-03"):
            self.dispose(fid, "--rejected", "x")
        ids = lambda: [b[0] for b in gate.evaluate(self.scope, "9.1", self.projects)[1]]
        with open(table, "w") as fh:
            fh.write("**Schema version:** verify/1\n**Revision:** 1" + body)  # legacy: exempt
        self.assertNotIn("review-acceptance", ids())
        with open(table, "w") as fh:
            fh.write("**Schema version:** verify/1\n**Revision:** 1\n**Approved:** rev 1 — Alex, 2026-09-29" + body)
        self.assertIn("review-acceptance", ids())
        run(REVIEW, "accept", "--scope", self.scope, "--unit", "9.1", "--by", "Alex", env=self.env)
        self.assertNotIn("review-acceptance", ids())

    def test_accept_waits_for_the_log_lock(self):
        import fcntl
        import time
        self.record()
        for fid in ("9.1-r1-01", "9.1-r1-02", "9.1-r1-03"):
            self.dispose(fid, "--rejected", "x")
        cmd = [sys.executable, script(REVIEW), "accept", "--scope", self.scope, "--unit", "9.1", "--by", "Alex"]
        with open(self.log, "a") as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            proc = subprocess.Popen(cmd, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            time.sleep(1.0)
            self.assertIsNone(proc.poll(), "accept wrote while another writer held the log")
        out, errs = proc.communicate(timeout=30)
        self.assertEqual(proc.returncode, 0, errs)

    def test_convergence_signals(self):
        for _ in range(3):
            p = self.record()
            self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("[CONVERGENCE] a.sh drew findings in each of the last 3 wellmed/svc rounds", p.stdout)
        self.assertIn("[CONVERGENCE] b.go", p.stdout)
        self.assertNotIn("round 3 >", p.stdout)
        self.assertIn("[CONVERGENCE] wellmed/svc round 3 of 3: STOP", p.stdout)
        p = self.record(findings=[])
        self.assertIn("[CONVERGENCE] wellmed/svc round 4 > 3", p.stdout)
        self.assertNotIn("drew findings", p.stdout)  # a clean round breaks the streak

    def test_a_file_outside_the_repos_converges_across_lanes(self):
        # review adhoc-08: a hand-back doc cited by three lanes' reviews in a row, three spellings
        docs, gw = self.mkrepo("wellmed/kalpa-docs"), self.mkrepo("wellmed/gw")
        mk = lambda file: [{"file": file, "line": 1, "severity": "note", "category": "doc-claim", "group": "",
                            "text": "t", "fix": ""}]
        steps = [(self.generic, "other.md"), (self.repo, "kalpa-docs/plans/x.md"),
                 (gw, os.path.join(docs, "plans", "x.md")), (self.repo, "../kalpa-docs/plans/x.md")]
        out = [self.record(repo=repo, findings=mk(file)).stdout for repo, file in steps]
        self.assertNotIn("outside the reviewed repos", "".join(out[:3]))   # r1 is inside the window
        self.assertIn("x.md (outside the reviewed repos) drew findings in each of the unit's last 3", out[3])
        self.assertNotIn("other.md", out[3])

    def test_rounds_count_per_repo_within_the_unit(self):
        # 149.2: one unit, 13 repos — bpjs's first review was r5 and the round cap fired on
        # it. IDs stay unit-wide; every round rule counts the reviews of that review's repo.
        steps = [  # (repo, unit-wide id, repo round, must print, must not print)
            (self.repo, "9.1-r1", 1, [], ["[CONVERGENCE]"]),
            (self.generic, "9.1-r2", 1, [], ["[CONVERGENCE]"]),
            (self.generic, "9.1-r3", 2, [], ["[CONVERGENCE]"]),
            (self.repo, "9.1-r4", 2, [], ["[CONVERGENCE]"]),  # unit round 4, svc round 2
            (self.generic, "9.1-r5", 3, ["a.sh drew findings in each of the last 3 other/tool rounds"],
             ["round 5 >", "> 3:"]),
            (self.repo, "9.1-r6", 3, ["last 3 wellmed/svc rounds"], ["> 3:"]),
            (self.generic, "9.1-r7", 4, ["[CONVERGENCE] other/tool round 4 > 3"], ["wellmed/svc round"]),
        ]
        for repo, rid, rnd, has, hasnt in steps:
            with self.subTest(rid=rid):
                p = self.record(repo=repo)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertIn(f"review {rid}:", p.stdout)
                self.assertIn(f"round: {rnd} of ", p.stdout)
                for needle in has:
                    self.assertIn(needle, p.stdout)
                for needle in hasnt:
                    self.assertNotIn(needle, p.stdout)
        todo = os.path.join(os.path.dirname(self.scope), "TO-DO.md")
        with open(todo, "w") as fh:
            fh.write("".join(f"- [ ] [review 9.1-r{n}-02] tenant filter\n" for n in range(1, 8)))
        # deferral: past round 3 of the finding's repo, whatever its unit-wide number
        for fid, code in (("9.1-r4-02", 1), ("9.1-r5-02", 1), ("9.1-r6-02", 1), ("9.1-r7-02", 0)):
            with self.subTest(defer=fid):
                p = self.dispose(fid, "--deferred", "tenant filter")
                self.assertEqual(p.returncode, code, p.stderr)
                if code:
                    self.assertIn("round 3 ≤ 3" if fid != "9.1-r4-02" else "round 2 ≤ 3", p.stderr)

    def test_repo_round_reads_logs_without_review_records(self):
        rr = load(REVIEW)
        f = lambda rid, repo: {"record": "finding", "review_id": rid, "range": {repo: "a..b"}, "file": "x"}
        recs = [f("9.1-r1", "a"), f("9.1-r2", "b"), f("9.1-r3", "a"), f("9.1-r10", "a")]
        cases = [("9.1-r1", ("a", 1)), ("9.1-r2", ("b", 1)), ("9.1-r3", ("a", 2)), ("9.1-r10", ("a", 3)),
                 ("9.1-r9", (None, 0))]
        for rid, want in cases:
            with self.subTest(rid=rid):
                self.assertEqual(rr.repo_round(recs, "9.1", rid), want)


    def test_rounds_of_one_repo_count_together_across_worktree_keys(self):
        # review adhoc-06: 149.2 logged four supply-chain rounds under its worktree's path; a
        # review keyed by the primary checkout restarted at round 1 and never converged.
        wt = os.path.join(self.projects, "wellmed", "svc.worktrees", "live")
        git(self.repo, "worktree", "add", "-q", wt)
        f = lambda rid, repo: {"record": "finding", "review_id": rid, "range": {repo: "a..b"}, "file": "x"}
        recs = [f("9.1-r1", "wellmed/svc.worktrees/gone-149"), f("9.1-r2", "wellmed/svc.worktrees/live"),
                f("9.1-r3", "wellmed/other"), f("9.1-r4", "wellmed/svc")]
        # in a subprocess: verify_lib reads VERIFY_PROJECTS at import, and is shared in-process
        out = subprocess.run([sys.executable, "-c", "import json,sys; sys.path.insert(0, sys.argv[1]); "
                              "from _helpers import load; rr = load('review/scripts/review.py'); "
                              "print(json.dumps([rr.repo_round(json.loads(sys.argv[2]), '9.1', i) "
                              "for i in ('9.1-r1', '9.1-r2', '9.1-r3', '9.1-r4')]))",
                              os.path.dirname(os.path.abspath(__file__)), json.dumps(recs)],
                             env=self.env, capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out), [["wellmed/svc", 1], ["wellmed/svc", 2], ["wellmed/other", 1],
                                           ["wellmed/svc", 3]])


if __name__ == "__main__":
    unittest.main()
