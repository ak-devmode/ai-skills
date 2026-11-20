"""lane-brief.py put — a brief that did not land fails the launch gate.
Approach: fake `ssh` and `scp` on PATH. The fake scp copies into a temp "remote home" unless
FAKE_SCP=fail (the WellMed 231 `scp: Connection closed`); the fake ssh runs the command there.
"""
import os
import stat
import tempfile
import unittest

from _helpers import run

SSH = '#!/bin/bash\ncd "$FAKE_HOME" && HOME="$FAKE_HOME" bash -c "${@: -1}"\n'  # the last arg is the script
SCP = ('#!/bin/bash\n[ "$FAKE_SCP" = fail ] && { echo "scp: Connection closed" >&2; exit 255; }\n'
       '# bash 3.2 (macOS): no negative indices. Files are the non-option args before the last.\n'
       'files=""; last=""; skip=""\n'
       'for a in "$@"; do case "$a" in -q) ;; -o) skip=1 ;; *) if [ -n "$skip" ]; then skip=""; '
       'else [ -n "$last" ] && files="$files $last"; last="$a"; fi ;; esac; done\n'
       'cp $files "$FAKE_HOME/${last#*:}"\n')


class TestPut(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.bin, self.home = os.path.join(t, "bin"), os.path.join(t, "home")
        os.makedirs(self.bin)
        os.makedirs(self.home)
        for name, body in (("ssh", SSH), ("scp", SCP)):
            p = os.path.join(self.bin, name)
            with open(p, "w") as fh:
                fh.write(body)
            os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
        self.brief = os.path.join(t, "bb7.md")
        with open(self.brief, "w") as fh:
            fh.write("# bb7\n")

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, **env):
        e = dict(os.environ, PATH=self.bin + ":" + os.environ["PATH"], FAKE_HOME=self.home, **env)
        return run("lane-brief.py", "put", "--machine", "box", "--dir", "~/.cache/briefs", self.brief, env=e)

    def test_landed_brief_passes(self):
        p = self.put()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("ok bb7.md", p.stdout)

    def test_failed_copy_fails_the_gate(self):
        p = self.put(FAKE_SCP="fail")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FAIL bb7.md: missing", p.stdout)

    def test_local_copy(self):
        d = os.path.join(self.tmp.name, "local")
        p = run("lane-brief.py", "put", "--dir", d, self.brief)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
