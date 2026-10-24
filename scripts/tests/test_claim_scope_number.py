"""claim-scope-number.sh — the branch source counts only this graph's scope numbers.

Approach: a temp repo with an origin, a plans/ dir, and branches named like real ones.
`docs/171-tooling-todos` (kalpa-docs scope 171's branch, living in ai-skills) has no
plans/171-* folder, so it must not be claimed against; `feature/9-x` has plans/9-x on
its tip, so it must. Records mode adds a fresh-render read of the local records.
"""

import os
import subprocess
import tempfile
import unittest

from _helpers import run


class ClaimScopeNumber(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = os.path.realpath(self.tmp.name)
        self.env = {**os.environ, "HOME": root, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        origin = os.path.join(root, "origin.git")
        self.git(root, "init", "-q", "--bare", "-b", "main", origin)
        self.repo = os.path.join(root, "repo")
        self.git(root, "clone", "-q", origin, self.repo)
        self.plans = os.path.join(self.repo, "plans")
        self.write("plans/3-alpha/progress.md", "# p\n")
        self.write("plans/PLANS-INDEX.md", "| # | Status |\n|---|---|\n| 3 | x |\n")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-q", "-m", "seed")
        self.git(self.repo, "push", "-q", "origin", "main")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, rel, text):
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def branch(self, name, folder=None):
        self.git(self.repo, "checkout", "-q", "-b", name)
        self.write(f"plans/{folder or 'other'}/progress.md" if folder else "notes.md", name)
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-q", "-m", name)
        self.git(self.repo, "checkout", "-q", "main")
        if folder:  # the folder is on the branch only, not on main's disk
            self.assertFalse(os.path.exists(os.path.join(self.plans, folder)))

    def claim(self):
        p = run("claim-scope-number.sh", self.plans, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)
        return int(p.stdout.strip())

    def test_another_graphs_branch_number_is_ignored(self):
        self.branch("docs/171-tooling-todos")
        self.assertEqual(self.claim(), 4)

    def test_this_graphs_branch_number_counts(self):
        self.branch("docs/171-tooling-todos")
        self.branch("feature/9-x", folder="9-x")
        self.assertEqual(self.claim(), 10)

    def test_archived_folder_on_a_branch_counts(self):
        self.branch("fix/12-y", folder="archive/12-y")
        self.assertEqual(self.claim(), 13)

    def test_records_mode_reads_a_fresh_render(self):
        self.write("plans/README.md", "**Index render:** bot\n")
        self.write("plans/index-loose.md",
                   "<!-- plans-index:begin active -->\n| # | Status | Folder | Description | Created by |\n"
                   "|---|---|---|---|---|\n| 20 | 📝 PRD | _(not created)_ | d | t |\n"
                   "<!-- plans-index:end active -->\n")
        self.assertEqual(self.claim(), 21)

    def test_records_that_do_not_render_stop_the_claim(self):
        # 9.1-r1-03: a failed render read as local_max=0 and re-claimed the loose number
        self.write("plans/README.md", "**Index render:** bot\n")
        self.write("plans/index-loose.md",
                   "<!-- plans-index:begin active -->\n| 20 | 📝 PRD | _(not created)_ | d | t |\n")
        p = run("claim-scope-number.sh", self.plans, env=self.env)
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertEqual(p.stdout, "")

    def test_a_date_prefixed_file_is_not_a_scope(self):
        # 9.1-r1-04: plans/2026-10-24-notes.md counted as scope 2026
        self.write("plans/2026-10-24-notes.md", "notes\n")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-q", "-m", "notes")
        self.git(self.repo, "push", "-q", "origin", "main")
        self.git(self.repo, "checkout", "-q", "-b", "docs/2027-more")
        self.write("plans/2027-10-24-more.md", "more\n")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-q", "-m", "more")
        self.git(self.repo, "checkout", "-q", "main")
        self.assertEqual(self.claim(), 4)

    def test_a_branch_row_without_a_folder_counts(self):
        # 9.1-r1-05: a branch that registered its number before making the folder
        self.git(self.repo, "checkout", "-q", "-b", "feature/15-z")
        self.write("plans/PLANS-INDEX.md", "| # | Status |\n|---|---|\n| 3 | x |\n| 15 | y |\n")
        self.git(self.repo, "commit", "-q", "-am", "row 15")
        self.git(self.repo, "checkout", "-q", "main")
        self.assertEqual(self.claim(), 16)
        self.git(self.repo, "checkout", "-q", "-b", "feature/16-w")
        self.write("plans/index-loose.md", "| 16 | 📝 PRD | _(not created)_ | d | t |\n")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-q", "-m", "loose 16")
        self.git(self.repo, "checkout", "-q", "main")
        self.assertEqual(self.claim(), 17)


if __name__ == "__main__":
    unittest.main()
