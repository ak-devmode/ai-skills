"""plans-publish.sh — a /plan write to a plans trunk reaches origin now, or halts.

Approach: a throwaway bare `origin` plus two clones, A and B, stand in for two machines
sharing one plans trunk (homelab2026 and the MBA on kalpa-docs `main`). Each case
arranges what B has already pushed, has A publish, then reads the result back from
origin rather than trusting the exit code. HOME and git config are isolated so the
developer's hooks, signing and identity never leak in.
"""

import os
import subprocess
import tempfile
import unittest

from _helpers import run


class PlansPublish(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = os.path.realpath(self.tmp.name)
        self.env = {**os.environ, "HOME": root, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        self.origin = os.path.join(root, "origin.git")
        self.git(root, "init", "-q", "--bare", "-b", "main", self.origin)
        seed = os.path.join(root, "seed")
        self.git(root, "clone", "-q", self.origin, seed)
        self.write(seed, "plans/progress.md", "line one\nline two\n")
        self.write(seed, "plans/PLANS-INDEX.md", "index\n")
        self.git(seed, "add", ".")
        self.git(seed, "commit", "-q", "-m", "seed")
        self.git(seed, "push", "-q", "origin", "main")
        self.a = self.clone(root, "a")
        self.b = self.clone(root, "b")

    def tearDown(self):
        self.tmp.cleanup()

    # --- helpers ---------------------------------------------------------------

    def git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, env=self.env, check=True,
                              capture_output=True, text=True).stdout.rstrip("\n")

    def clone(self, root, name):
        path = os.path.join(root, name)
        self.git(root, "clone", "-q", self.origin, path)
        return path

    def write(self, repo, rel, text):
        path = os.path.join(repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def b_pushes(self, rel, text, msg="b"):
        self.git(self.b, "pull", "-q", "--rebase", "origin", "main")
        self.write(self.b, rel, text)
        self.git(self.b, "add", rel)
        self.git(self.b, "commit", "-q", "-m", msg)
        self.git(self.b, "push", "-q", "origin", "main")

    def publish(self, *paths, msg="plan: [Task 1.1] test", repo=None):
        plans = os.path.join(repo or self.a, "plans")
        return run("plans-publish.sh", plans, "-m", msg, "--", *paths, env=self.env)

    def origin_main(self):
        return self.git(self.origin, "rev-parse", "main")

    def on_origin(self, repo, rev="HEAD"):
        sha = self.git(repo, "rev-parse", rev)
        return subprocess.run(["git", "merge-base", "--is-ancestor", sha, "main"],
                              cwd=self.origin, env=self.env).returncode == 0

    # --- cases -----------------------------------------------------------------

    def test_a_clean_publish_lands_on_origin(self):
        self.write(self.a, "plans/progress.md", "line one\nline two\ntask 1.1 done\n")
        r = self.publish("progress.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("published", r.stdout)
        self.assertTrue(self.on_origin(self.a))
        self.assertEqual(self.git(self.a, "log", "-1", "--format=%s"), "plan: [Task 1.1] test")

    def test_b_origin_moved_without_overlap_rebases_and_publishes(self):
        self.b_pushes("plans/PLANS-INDEX.md", "index\nrow from b\n")
        self.write(self.a, "plans/progress.md", "line one\nline two\ntask 1.1 done\n")
        r = self.publish("progress.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.on_origin(self.a))
        self.git(self.b, "pull", "-q", "origin", "main")
        with open(os.path.join(self.b, "plans/progress.md"), encoding="utf-8") as fh:
            self.assertIn("task 1.1 done", fh.read())

    def test_c_conflict_halts_with_commit_kept_and_nothing_pushed(self):
        self.b_pushes("plans/progress.md", "line one EDITED BY B\nline two\n")
        before = self.origin_main()
        self.write(self.a, "plans/progress.md", "line one EDITED BY A\nline two\n")
        r = self.publish("progress.md")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("progress.md", r.stderr)
        self.assertEqual(self.origin_main(), before)
        self.assertFalse(os.path.exists(os.path.join(self.a, ".git", "rebase-merge")))
        self.assertEqual(self.git(self.a, "log", "-1", "--format=%s"), "plan: [Task 1.1] test")
        self.assertEqual(self.git(self.a, "status", "--porcelain"), "")

    def test_d_feature_branch_commits_only(self):
        self.git(self.a, "checkout", "-q", "-b", "feature/x")
        before = self.origin_main()
        self.write(self.a, "plans/progress.md", "line one\nline two\nbranch work\n")
        r = self.publish("progress.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("not trunk", r.stdout)
        self.assertEqual(self.origin_main(), before)
        self.assertEqual(self.git(self.origin, "branch", "--list", "feature/x"), "")

    def test_e_sibling_files_never_ride_along(self):
        self.write(self.a, "plans/untracked-sibling.md", "other session\n")
        self.write(self.a, "plans/PLANS-INDEX.md", "index\nstaged by a sibling\n")
        self.git(self.a, "add", "plans/PLANS-INDEX.md")
        self.write(self.a, "plans/progress.md", "line one\nline two\nmine\n")
        r = self.publish("progress.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        committed = self.git(self.a, "show", "--name-only", "--format=", "HEAD").split()
        self.assertEqual(committed, ["plans/progress.md"])
        status = self.git(self.a, "status", "--porcelain")
        self.assertIn("?? plans/untracked-sibling.md", status)
        self.assertIn("M  plans/PLANS-INDEX.md", status)

    def test_f_push_race_is_retried_once(self):
        hook = os.path.join(self.a, ".git", "hooks", "pre-push")
        marker = os.path.join(self.a, ".git", "raced")
        with open(hook, "w", encoding="utf-8") as fh:
            fh.write("#!/usr/bin/env bash\n"
                     f"[ -e '{marker}' ] && exit 0\n"
                     f"touch '{marker}'\n"
                     f"cd '{self.b}' && git pull -q --rebase origin main && "
                     "echo race >> plans/PLANS-INDEX.md && git commit -qam race && "
                     "git push -q --no-verify origin main\n")
        os.chmod(hook, 0o755)
        self.write(self.a, "plans/progress.md", "line one\nline two\nafter the race\n")
        r = self.publish("progress.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.exists(marker))
        self.assertTrue(self.on_origin(self.a))
        self.assertEqual(self.git(self.origin, "log", "-2", "--format=%s", "main").splitlines(),
                         ["plan: [Task 1.1] test", "race"])

    def test_g_unreachable_origin_keeps_commit(self):
        self.git(self.a, "remote", "set-url", "origin", os.path.join(self.a, "nowhere.git"))
        self.write(self.a, "plans/progress.md", "line one\nline two\noffline\n")
        r = self.publish("progress.md")
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertEqual(self.git(self.a, "log", "-1", "--format=%s"), "plan: [Task 1.1] test")

    def test_h_usage_errors(self):
        plans = os.path.join(self.a, "plans")
        self.assertEqual(run("plans-publish.sh", plans, "-m", "x", "--", env=self.env).returncode, 2)
        self.assertEqual(run("plans-publish.sh", plans, "--", "progress.md", env=self.env).returncode, 2)
        self.assertEqual(run("plans-publish.sh", os.path.join(self.a, "nope"), "-m", "x", "--",
                             "p.md", env=self.env).returncode, 2)

    def test_i_next_publish_carries_an_earlier_unpushed_commit(self):
        self.write(self.a, "plans/progress.md", "line one\nline two\nleft behind\n")
        self.git(self.a, "commit", "-qam", "earlier, unpushed")
        r = self.publish("progress.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("nothing new", r.stderr)
        self.assertTrue(self.on_origin(self.a))

    def test_j_sibling_uncommitted_edit_survives_the_rebase(self):
        self.b_pushes("plans/new-from-b.md", "b\n")
        self.write(self.a, "plans/PLANS-INDEX.md", "index\nsibling is mid-edit\n")
        self.write(self.a, "plans/progress.md", "line one\nline two\nmine\n")
        r = self.publish("progress.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.on_origin(self.a))
        with open(os.path.join(self.a, "plans/PLANS-INDEX.md"), encoding="utf-8") as fh:
            self.assertIn("sibling is mid-edit", fh.read())
        self.assertEqual(self.git(self.a, "stash", "list"), "")

    def test_k_busy_repo_halts(self):
        open(os.path.join(self.a, ".git", "MERGE_HEAD"), "w").close()
        r = self.publish("progress.md")
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn("busy", r.stderr)

    def test_l_unset_origin_head_is_not_a_silent_success(self):
        self.git(self.a, "remote", "set-head", "origin", "-d")
        before = self.origin_main()
        self.write(self.a, "plans/progress.md", "line one\nline two\nno trunk known\n")
        r = self.publish("progress.md")
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertIn("set-head", r.stderr)
        self.assertEqual(self.origin_main(), before)
        self.assertEqual(self.git(self.a, "log", "-1", "--format=%s"), "plan: [Task 1.1] test")

    def test_m_failed_add_halts_inside_the_contract(self):
        r = self.publish("no-such-file.md")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("git add failed", r.stderr)
        self.assertIn("did not match", r.stderr)

    def test_n_rejected_push_says_why(self):
        hook = os.path.join(self.origin, "hooks", "pre-receive")
        with open(hook, "w", encoding="utf-8") as fh:
            fh.write("#!/usr/bin/env bash\necho 'protected branch says no' >&2\nexit 1\n")
        os.chmod(hook, 0o755)
        self.write(self.a, "plans/progress.md", "line one\nline two\nrefused\n")
        r = self.publish("progress.md")
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        self.assertIn("git:", r.stderr)
        self.assertEqual(self.git(self.a, "log", "-1", "--format=%s"), "plan: [Task 1.1] test")


if __name__ == "__main__":
    unittest.main()
