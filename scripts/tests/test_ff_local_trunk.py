"""ff-local-trunk.sh — after worktree work merges, the local trunk catches up, or says why not.

Approach: a throwaway bare `origin`, a primary clone, and a `pusher` clone that lands
commits on origin the way a GitHub merge would. Each case arranges where trunk is checked
out (primary, a linked worktree, nowhere), runs the script against the primary, and reads
the trunk ref back rather than trusting the exit code. HOME and git config are isolated.
"""

import os
import subprocess
import tempfile
import unittest

from _helpers import run


class FfLocalTrunk(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        self.env = {**os.environ, "HOME": self.root, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        self.origin = os.path.join(self.root, "origin.git")
        self.git(self.root, "init", "-q", "--bare", "-b", "main", self.origin)
        self.pusher = os.path.join(self.root, "pusher")
        self.git(self.root, "clone", "-q", self.origin, self.pusher)
        self.commit(self.pusher, "a.txt", "seed\n", "seed")
        self.git(self.pusher, "push", "-q", "origin", "main")
        self.primary = os.path.join(self.root, "primary")
        self.git(self.root, "clone", "-q", self.origin, self.primary)

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, env=self.env, check=True,
                              capture_output=True, text=True).stdout.rstrip("\n")

    def commit(self, repo, rel, text, msg):
        with open(os.path.join(repo, rel), "w", encoding="utf-8") as fh:
            fh.write(text)
        self.git(repo, "add", rel)
        self.git(repo, "commit", "-q", "-m", msg)

    def merge_lands(self, branch="main", n=2):
        """Origin's trunk moves on — what a merged PR looks like from this disk."""
        self.git(self.pusher, "checkout", "-q", branch)
        self.git(self.pusher, "pull", "-q", "origin", branch)
        for i in range(n):
            self.commit(self.pusher, f"merged-{i}.txt", f"{i}\n", f"merged {i}")
        self.git(self.pusher, "push", "-q", "origin", branch)
        return self.git(self.pusher, "rev-parse", "HEAD")

    def ff(self, *extra):
        return run("ff-local-trunk.sh", self.primary, *extra, env=self.env)

    def test_a_primary_on_trunk_behind_is_advanced(self):
        target = self.merge_lands()
        r = self.ff()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("advanced main", r.stdout)
        self.assertEqual(self.git(self.primary, "rev-parse", "main"), target)
        self.assertTrue(os.path.exists(os.path.join(self.primary, "merged-1.txt")))

    def test_b_primary_on_feature_branch_ref_advanced_checkout_untouched(self):
        self.git(self.primary, "checkout", "-q", "-b", "feature/x")
        self.commit(self.primary, "wip.txt", "wip\n", "wip")
        head = self.git(self.primary, "rev-parse", "HEAD")
        target = self.merge_lands()
        r = self.ff()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ref only", r.stdout)
        self.assertEqual(self.git(self.primary, "rev-parse", "main"), target)
        self.assertEqual(self.git(self.primary, "rev-parse", "HEAD"), head)
        self.assertEqual(self.git(self.primary, "symbolic-ref", "--short", "HEAD"), "feature/x")

    def test_c_already_current(self):
        r = self.ff()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("already current", r.stdout)

    def test_d_local_trunk_ahead_or_diverged_changes_nothing(self):
        self.commit(self.primary, "local.txt", "local only\n", "unpushed on trunk")
        before = self.git(self.primary, "rev-parse", "main")
        self.merge_lands()
        r = self.ff()
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("not a fast-forward", r.stderr)
        self.assertEqual(self.git(self.primary, "rev-parse", "main"), before)

    def test_e_dirty_file_in_the_way_changes_nothing(self):
        before = self.git(self.primary, "rev-parse", "main")
        self.merge_lands(n=1)
        with open(os.path.join(self.primary, "merged-0.txt"), "w", encoding="utf-8") as fh:
            fh.write("untracked local copy\n")
        r = self.ff()
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertEqual(self.git(self.primary, "rev-parse", "main"), before)
        with open(os.path.join(self.primary, "merged-0.txt"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "untracked local copy\n")

    def test_f_unreachable_origin(self):
        self.git(self.primary, "remote", "set-url", "origin", os.path.join(self.root, "nowhere.git"))
        r = self.ff()
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)

    def test_g_explicit_develop_trunk(self):
        self.git(self.pusher, "checkout", "-q", "-b", "develop")
        self.git(self.pusher, "push", "-q", "origin", "develop")
        self.git(self.primary, "fetch", "-q", "origin")
        self.git(self.primary, "checkout", "-q", "-b", "develop", "origin/develop")
        target = self.merge_lands(branch="develop")
        r = self.ff("develop")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.git(self.primary, "rev-parse", "develop"), target)

    def test_h_trunk_checked_out_in_a_linked_worktree(self):
        self.git(self.primary, "checkout", "-q", "-b", "feature/y")
        wt = os.path.join(self.root, "wt-main")
        self.git(self.primary, "worktree", "add", "-q", wt, "main")
        target = self.merge_lands()
        r = self.ff()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(wt, r.stdout)
        self.assertEqual(self.git(wt, "rev-parse", "HEAD"), target)
        self.assertTrue(os.path.exists(os.path.join(wt, "merged-1.txt")))

    def test_i_usage(self):
        self.assertEqual(run("ff-local-trunk.sh", env=self.env).returncode, 2)
        self.assertEqual(run("ff-local-trunk.sh", os.path.join(self.root, "nope"),
                             env=self.env).returncode, 2)


if __name__ == "__main__":
    unittest.main()
