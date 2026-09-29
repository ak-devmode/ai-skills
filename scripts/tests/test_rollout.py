"""verify-prereqs.sh and clone-behind.py — the two onboarding checks (scope 5.3 rollout).

Approach: prereqs run against fake codex binaries on a controlled PATH (installed and
logged in / logged out / absent), asserting a warning with its fix and exit 0 every time
— setup must never fail over these. clone-behind runs against a local bare "origin" so
behind / current / unreachable are all real git states, no network.
"""

import os
import stat
import subprocess
import sys
import tempfile
import unittest

from _helpers import run, script


def fake(path, body):
    with open(path, "w") as fh:
        fh.write("#!/bin/sh\n" + body)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


class Prereqs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bin = self.tmp.name
        os.symlink(sys.executable, os.path.join(self.bin, "python3"))
        for tool in ("head", "sh", "env"):
            src = subprocess.run(["which", tool], capture_output=True, text=True).stdout.strip()
            os.symlink(src, os.path.join(self.bin, tool))

    def tearDown(self):
        self.tmp.cleanup()

    def prereqs(self):
        env = {"PATH": self.bin, "HOME": self.tmp.name}
        return subprocess.run(["/bin/bash", script("verify-prereqs.sh")], env=env, capture_output=True, text=True)

    def test_all_present(self):
        fake(os.path.join(self.bin, "codex"),
             'case "$1" in --version) echo "codex-cli 9.9";; login) echo "Logged in using ChatGPT";; esac\n')
        p = self.prereqs()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("ok python3", p.stdout)
        self.assertIn("ok codex (codex-cli 9.9; Logged in using ChatGPT)", p.stdout)
        self.assertIn("try: /verify --demo", p.stdout)

    def test_no_codex_warns_with_the_fix_and_exits_0(self):
        p = self.prereqs()
        self.assertEqual(p.returncode, 0)
        self.assertIn("!! codex not installed", p.stdout)
        self.assertIn("fix: npm i -g @openai/codex && codex login", p.stdout)
        self.assertIn("⚠ judge: claude-fallback", p.stdout)

    def test_logged_out_codex_warns(self):
        fake(os.path.join(self.bin, "codex"),
             'case "$1" in --version) echo "codex-cli 9.9";; login) echo "Not logged in"; exit 1;; esac\n')
        p = self.prereqs()
        self.assertEqual(p.returncode, 0)
        self.assertIn("not logged in (Not logged in)", p.stdout)
        self.assertIn("fix: codex login", p.stdout)


class CloneBehind(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.origin, self.clone, self.other = (os.path.join(t, x) for x in ("origin.git", "clone", "other"))
        self.git(t, "init", "-q", "--bare", "-b", "main", self.origin)
        self.git(t, "clone", "-q", self.origin, self.other)
        self.git(self.other, "commit", "-q", "--allow-empty", "-m", "a")
        self.git(self.other, "push", "-q", "origin", "HEAD:main")
        self.git(t, "clone", "-q", self.origin, self.clone)

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, cwd, *args):
        subprocess.run(["git", "-C", cwd, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                       check=True, capture_output=True)

    def behind(self, *extra):
        return run("clone-behind.py", "--repo", self.clone, "--max-age", "0", *extra)

    def test_current_is_silent(self):
        p = self.behind()
        self.assertEqual((p.returncode, p.stdout), (0, ""))

    def test_behind_prints_one_line_with_the_fix(self):
        self.git(self.other, "commit", "-q", "--allow-empty", "-m", "b")
        self.git(self.other, "push", "-q", "origin", "HEAD:main")
        p = self.behind()
        self.assertEqual(p.returncode, 0)
        self.assertEqual(len(p.stdout.splitlines()), 1)
        self.assertIn("is 1 commit(s) behind origin/main — run: git -C", p.stdout)

    def test_a_fetch_of_another_branch_does_not_count_as_fresh(self):
        # 5.3-r1-08: FETCH_HEAD is refreshed by any fetch; only a fetch of origin main counts
        self.git(self.other, "push", "-q", "origin", "HEAD:side")
        self.git(self.clone, "fetch", "-q", "origin", "side")
        self.git(self.other, "commit", "-q", "--allow-empty", "-m", "b")
        self.git(self.other, "push", "-q", "origin", "HEAD:main")
        p = run("clone-behind.py", "--repo", self.clone, "--max-age", "3600")
        self.assertIn("is 1 commit(s) behind origin/main", p.stdout)

    def test_unreachable_origin_says_unknown_not_nothing(self):
        self.git(self.clone, "remote", "set-url", "origin", os.path.join(self.tmp.name, "gone.git"))
        p = self.behind()
        self.assertEqual(p.returncode, 0)
        self.assertIn("freshness unknown — fetch failed", p.stdout)


if __name__ == "__main__":
    unittest.main()
