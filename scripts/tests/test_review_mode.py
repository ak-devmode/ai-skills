"""Tests for scripts/review-mode.py — precedence flag > env > default, and loud failure.

Approach: table-driven over every flag × env combination, run as a subprocess the way
the skills call it, with AI_SKILLS_REVIEW_MODE set or removed explicitly per case.
"""

import os
import unittest

from _helpers import run

# (name, args, env value or None for unset, exit, stdout)
CASES = [
    ("unset env, no flag is lean by default", [], None, 0, "mode: lean (default)"),
    ("empty env is the default", [], "", 0, "mode: lean (default)"),
    ("env full", [], "full", 0, "mode: full (env)"),
    ("env lean", [], "lean", 0, "mode: lean (env)"),
    ("env value is case- and space-insensitive", [], " FULL ", 0, "mode: full (env)"),
    ("--full beats env lean", ["--full"], "lean", 0, "mode: full (flag)"),
    ("--lean beats env full", ["--lean"], "full", 0, "mode: lean (flag)"),
    ("--full with no env", ["--full"], None, 0, "mode: full (flag)"),
    ("a flag repeated is still one flag", ["--lean", "--lean"], None, 0, "mode: lean (flag)"),
    ("a bad env value is an error, never a silent lean", [], "fulll", 2, ""),
    ("a flag wins over a bad env value, which is still warned about", ["--full"], "fulll", 0,
     "mode: full (flag)"),
    ("both flags is an error", ["--full", "--lean"], None, 2, ""),
    ("an unknown argument is usage", ["--max"], None, 2, ""),
]


class TestReviewMode(unittest.TestCase):
    def test_cases(self):
        for name, args, value, code, out in CASES:
            with self.subTest(case=name):
                env = {k: v for k, v in os.environ.items() if k != "AI_SKILLS_REVIEW_MODE"}
                if value is not None:
                    env["AI_SKILLS_REVIEW_MODE"] = value
                p = run("review-mode.py", *args, env=env)
                self.assertEqual(p.returncode, code, p.stdout + p.stderr)
                self.assertEqual(p.stdout.strip(), out)
                if code or (value or "").strip().lower() not in ("", "lean", "full"):
                    self.assertIn("AI_SKILLS_REVIEW_MODE" if value else "", p.stderr,
                                  "an error or a bad setting must say why")
                    self.assertTrue(p.stderr.strip())


if __name__ == "__main__":
    unittest.main()
