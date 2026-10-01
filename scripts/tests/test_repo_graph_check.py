"""repo-graph-check.py — heading forms, the empty-section false pass, and git classification.

Approach: table-driven. Each case writes a scope.md into a temp dir next to a throwaway
git repo under a fake --projects root, runs the script as /plan does, and asserts the
exit code and the line that explains it.
"""

import os
import subprocess
import tempfile
import unittest

from _helpers import run

TABLE = """| Repo | Current branch | HEAD SHA | Dirty |
|---|---|---|---|
| demo | main | {sha} | no |
"""


def git(path, *args):
    return subprocess.run(["git", "-C", path, *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class TestRepoGraphCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.projects = os.path.join(self.tmp.name, "projects")
        self.repo = os.path.join(self.projects, "demo")
        os.makedirs(self.repo)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
            "--allow-empty", "-m", "base")
        self.sha = git(self.repo, "rev-parse", "--short", "HEAD")

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, body):
        scope = os.path.join(self.tmp.name, "scope.md")
        with open(scope, "w", encoding="utf-8") as fh:
            fh.write("# Scope\n\n" + body + "\n## Next\n")
        return run("repo-graph-check.py", scope, "--projects", self.projects)

    def test_cases(self):
        table = TABLE.format(sha=self.sha)
        cases = [
            ("unnumbered heading + table", "## Repo Graph\n\n" + table, 0, "unchanged"),
            ("numbered heading + table", "## 2. Repo Graph\n\n" + table, 0, "unchanged"),
            ("sub-numbered heading", "## 4.5 Repo Graph (snapshot)\n\n" + table, 0, "unchanged"),
            ("no section", "## Context\n\nnothing here\n", 4, "no Repo Graph section"),
            ("prose-only section is not a pass", "## 2. Repo Graph\n\nSingle-repo task.\n",
             4, "no snapshot table"),
        ]
        for name, body, code, needle in cases:
            with self.subTest(case=name):
                p = self.check(body)
                self.assertEqual(p.returncode, code, p.stdout + p.stderr)
                self.assertIn(needle, p.stdout)

    def test_advanced_repo(self):
        table = TABLE.format(sha=self.sha)
        git(self.repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
            "--allow-empty", "-m", "next")
        p = self.check("## Repo Graph\n\n" + table)
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("advanced", p.stdout)

    def test_skipped_rows_excluded_from_verdict(self):
        table = ("| Repo | Current branch | HEAD SHA | In Scope? |\n|---|---|---|---|\n"
                 f"| demo | main | {self.sha} | YES |\n"
                 "| gone-oos | — | deadbee | **NO** |\n"
                 "| no-sha | — | — | YES |\n")
        p = self.check("## Repo Graph\n\n" + table)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("skipped    gone-oos", p.stdout)
        self.assertIn("skipped    no-sha", p.stdout)

    def test_all_rows_skipped_is_not_a_pass(self):
        table = "| Repo | HEAD SHA | In Scope? |\n|---|---|---|\n| demo | — | NO |\n"
        p = self.check("## Repo Graph\n\n" + table)
        self.assertEqual(p.returncode, 4, p.stdout)
        self.assertIn("nothing was checked", p.stdout)


class TestRemoteRefColumn(unittest.TestCase):
    """`HEAD SHA (origin/main)`: compare against the fetched remote ref, not local HEAD."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.projects = os.path.join(self.tmp.name, "projects")
        self.origin = os.path.join(self.tmp.name, "origin.git")
        self.repo = os.path.join(self.projects, "demo")
        self.pusher = os.path.join(self.tmp.name, "pusher")
        os.makedirs(self.projects)
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", self.origin], check=True)
        subprocess.run(["git", "clone", "-q", self.origin, self.pusher], check=True,
                       capture_output=True)
        self.commit(self.pusher, "base")
        git(self.pusher, "push", "-q", "origin", "HEAD:main")
        subprocess.run(["git", "clone", "-q", self.origin, self.repo], check=True,
                       capture_output=True)

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, path, msg):
        git(path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
            "--allow-empty", "-m", msg)
        return git(path, "rev-parse", "--short", "HEAD")

    def check(self, sha, branch="main (local 3 behind)"):
        table = ("| Repo | Current Branch | HEAD SHA (origin/main) |\n|---|---|---|\n"
                 f"| demo | {branch} | {sha} |\n")
        scope = os.path.join(self.tmp.name, "scope.md")
        with open(scope, "w", encoding="utf-8") as fh:
            fh.write("# Scope\n\n## 2. Repo Graph\n\n" + table + "\n## Next\n")
        return run("repo-graph-check.py", scope, "--projects", self.projects)

    def test_behind_origin_local_is_unchanged(self):
        recorded = self.commit(self.pusher, "remote only")
        git(self.pusher, "push", "-q", "origin", "HEAD:main")
        p = self.check(recorded)  # local clone never saw `recorded`; the fetch must
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("unchanged  demo", p.stdout)
        self.assertIn("origin/main", p.stdout)

    def test_behind_origin_local_remote_advanced(self):
        recorded = self.commit(self.pusher, "snapshot")
        git(self.pusher, "push", "-q", "origin", "HEAD:main")
        self.commit(self.pusher, "after snapshot")
        git(self.pusher, "push", "-q", "origin", "HEAD:main")
        p = self.check(recorded)
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("advanced   demo", p.stdout)
        self.assertIn("(1 commits)", p.stdout)

    def test_fetch_failure_is_said_not_silent(self):
        recorded = git(self.repo, "rev-parse", "--short", "HEAD")
        git(self.repo, "remote", "set-url", "origin", os.path.join(self.tmp.name, "nope.git"))
        p = self.check(recorded)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("fetch origin main failed", p.stdout)


if __name__ == "__main__":
    unittest.main()
