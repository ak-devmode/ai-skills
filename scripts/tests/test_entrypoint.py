"""The test entrypoint itself: every shared Python script compiles, and the harness runs.

Approach: byte-compile each scripts/*.py in memory. It is the floor under every other
test here — a syntax error in a script a skill shells out to is otherwise found by the
skill at run time, mid-task. It also means `python3 -m unittest discover scripts/tests`
never reports "NO TESTS RAN", which exits 5 on Python >= 3.12 and would read as a failure.
"""

import glob
import os
import unittest

from _helpers import SCRIPTS


class TestScriptsCompile(unittest.TestCase):
    def test_every_script_compiles(self):
        paths = sorted(glob.glob(os.path.join(SCRIPTS, "*.py")))
        self.assertTrue(paths, f"no scripts found under {SCRIPTS}")
        for path in paths:
            with self.subTest(script=os.path.basename(path)):
                with open(path, encoding="utf-8") as fh:
                    compile(fh.read(), path, "exec")


if __name__ == "__main__":
    unittest.main()
