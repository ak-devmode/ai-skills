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


if __name__ == "__main__":
    unittest.main()
