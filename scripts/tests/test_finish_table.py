"""finish-table.py — the one writer of finish-conditions.md.

Approach: build a throwaway docs repo (the scope folder lives in it) under a fake projects
root, drive the real script, and read every result back through verify_lib.parse_table —
the parser the runner and the gate use — so a table this script writes is by construction
one they accept. Refusals are checked to leave the file byte-for-byte unchanged.
"""

import json
import os
import subprocess
import tempfile
import unittest

from _helpers import load, run

vl = load("verify_lib.py")


class FinishTable(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.projects = os.path.realpath(self.tmp.name)
        docs = os.path.join(self.projects, "team", "team-docs")
        self.scope = os.path.join(docs, "plans", "9-thing")
        os.makedirs(self.scope)
        subprocess.run(["git", "-C", docs, "init", "-q"], check=True)
        self.table = os.path.join(self.scope, "finish-conditions.md")

    def tearDown(self):
        self.tmp.cleanup()

    def ft(self, *args):
        return run("finish-table.py", *args, "--scope", self.scope, "--projects", self.projects, "--by", "T / Claude")

    def rows_file(self, *rows):
        path = os.path.join(self.tmp.name, "rows.jsonl")
        with open(path, "w") as fh:
            fh.writelines(json.dumps(r) + "\n" for r in rows)
        return path

    def text(self):
        with open(self.table, encoding="utf-8") as fh:
            return fh.read()

    def ids(self):
        return {r["check_id"]: r for r in vl.parse_table(self.table)["rows"]}

    def test_init_emits_standard_rows_per_phase(self):
        p = self.ft("init", "--phase", "9.1=team/svc", "--phase", "9.2", "--phase", "9.3=team/a,team/b",
                    "--test-plan-owner", "9.3")
        self.assertEqual(p.returncode, 0, p.stderr)
        rows = self.ids()
        # commit-producing phase: names-resolve + scope-deliverables + no-overbuild + rejections
        self.assertEqual({k for k in rows if k.startswith("p1-")},
                         {"p1-names-resolve", "p1-scope-deliverables", "p1-no-overbuild", "p1-rejections-justified"})
        self.assertEqual(rows["p1-names-resolve"]["repo"], "team/svc")
        self.assertEqual(rows["p1-names-resolve"]["rung"], 4)
        self.assertIn("$VERIFY_BASE..HEAD", rows["p1-names-resolve"]["check"])
        # commit-less phase: verify only, judged against the docs repo
        self.assertEqual({k for k in rows if k.startswith("p2-")}, {"p2-scope-deliverables"})
        self.assertEqual(rows["p2-scope-deliverables"]["repo"], "team/team-docs")
        # two repos: one names-resolve row each
        self.assertIn("p3-names-resolve-a", rows)
        self.assertIn("p3-names-resolve-b", rows)
        self.assertEqual(rows["test-plan-followed"]["owner"], "9.3")
        self.assertTrue(all(r["owner"] in ("9.1", "9.2", "9.3") for r in rows.values()))
        text = self.text()
        self.assertIn("**Revision:** 1", text)
        self.assertRegex(text, r"\| 1 \| \d{4}-\d\d-\d\d \| Created \| T / Claude \|")

    def test_extra_rows_get_defaults_and_escaping(self):
        rows = self.rows_file({"check_id": "p1-evals", "deliverable": "evals pass", "owner": "9.1",
                               "check": "make eval | tee out", "repo": "team/svc", "env": "VERIFY_EVAL=1",
                               "timeout": 300})
        p = self.ft("init", "--phase", "9.1=team/svc", "--rows", rows)
        self.assertEqual(p.returncode, 0, p.stderr)
        r = self.ids()["p1-evals"]
        self.assertEqual((r["check"], r["env"], r["timeout"], r["rung"], r["unreachable_ok"]),
                         ("make eval | tee out", {"VERIFY_EVAL": "1"}, 300, 4, False))

    def test_predates_is_written_and_parsed(self):
        p = self.ft("init", "--phase", "9.3=team/svc", "--predates", "9.1,9.2")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(vl.parse_table(self.table)["predates"], ["9.1", "9.2"])
        self.assertIn("9.1, 9.2 predate the gate", self.text())

    def test_predates_cannot_also_be_a_phase(self):
        p = self.ft("init", "--phase", "9.1=team/svc", "--predates", "9.1")
        self.assertEqual(p.returncode, 2)
        self.assertFalse(os.path.exists(self.table))

    def test_init_refuses_an_existing_table(self):
        self.ft("init", "--phase", "9.1=team/svc")
        before = self.text()
        p = self.ft("init", "--phase", "9.2")
        self.assertEqual(p.returncode, 3)
        self.assertIn("already exists", p.stderr)
        self.assertEqual(self.text(), before)

    def test_add_bumps_revision_and_logs_the_change(self):
        self.ft("init", "--phase", "9.1=team/svc")
        rows = self.rows_file({"check_id": "p1-tests", "deliverable": "suite green", "owner": "9.1",
                               "check": "make test", "repo": "team/svc"})
        p = self.ft("add", "--rows", rows, "--change", "suite row")
        self.assertEqual(p.returncode, 0, p.stderr)
        t = vl.parse_table(self.table)
        self.assertEqual(t["revision"], 2)
        self.assertIn("p1-tests", {r["check_id"] for r in t["rows"]})
        self.assertRegex(self.text(), r"\| 2 \| \d{4}-\d\d-\d\d \| suite row \| T / Claude \|")

    def test_add_that_would_not_parse_changes_nothing(self):
        self.ft("init", "--phase", "9.1=team/svc")
        before = self.text()
        dup = self.rows_file({"check_id": "p1-no-overbuild", "deliverable": "x", "owner": "9.1",
                              "check": "judge", "repo": "team/svc"})
        p = self.ft("add", "--rows", dup, "--change", "dup")
        self.assertEqual(p.returncode, 3)
        self.assertIn("unique check_id", p.stderr)
        for f in ("expected ·", "found    ·", "where    ·", "cause    ·", "next     ·", "docs     ·"):
            self.assertIn(f, p.stderr)
        self.assertEqual(self.text(), before)

    def test_dry_run_writes_nothing(self):
        p = self.ft("init", "--phase", "9.1=team/svc", "--dry-run")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("| p1-names-resolve |", p.stdout)
        self.assertFalse(os.path.exists(self.table))

    def test_all_started_scope_gets_a_rowless_table(self):
        # 5.3-r1-01: /plan §5.6.2a writes every phase under --predates, no --phase
        p = self.ft("init", "--predates", "9.1,9.2")
        self.assertEqual(p.returncode, 0, p.stderr)
        t = vl.parse_table(self.table)
        self.assertEqual((t["rows"], t["predates"]), ([], ["9.1", "9.2"]))

    def test_init_with_nothing_is_usage(self):
        self.assertEqual(self.ft("init").returncode, 2)
        self.assertEqual(self.ft("init", "--predates", " , ").returncode, 2)  # 5.3-r2-05
        self.assertFalse(os.path.exists(self.table))

    def test_bad_phase_is_usage(self):
        self.assertEqual(self.ft("init", "--phase", "one").returncode, 2)


if __name__ == "__main__":
    unittest.main()
