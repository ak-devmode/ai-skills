"""resolve-plans-dir.sh — the one owner of path → plans-dir.

Approach: point HOME at a throwaway tree holding every docs repo the script knows, then
resolve real paths inside it. The IRIS cases are the reason this file exists: kalpa-iris
sits under ~/Projects/wellmed/ but is a standalone graph, so the wellmed catch-all must
never claim it (kalpa-iris CLAUDE.md §3.2).
"""

import os
import tempfile
import unittest

from _helpers import run

PLANS = {
    "pmg": "Projects/pmg/pmg-docs/plans",
    "wellmed": "Projects/wellmed/kalpa-docs/plans",
    "iris": "Projects/wellmed/kalpa-iris/iris-docs/plans",
    "ai-skills": "Projects/ai-skills/plans",
}


class ResolvePlansDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.realpath(self.tmp.name)
        for rel in PLANS.values():
            os.makedirs(os.path.join(self.home, rel))
        for rel in ("Projects/wellmed/wellmed-backbone", "Projects/wellmed/kalpa-iris/services/spine",
                    ".herdr/worktrees/kalpa-iris/feature-x", "elsewhere"):
            os.makedirs(os.path.join(self.home, rel), exist_ok=True)
        self.env = {**os.environ, "HOME": self.home}

    def tearDown(self):
        self.tmp.cleanup()

    def resolve(self, rel):
        return run("resolve-plans-dir.sh", os.path.join(self.home, rel), env=self.env)

    def test_each_path_maps_to_its_graph(self):
        cases = [
            ("Projects/wellmed/wellmed-backbone", "wellmed"),
            ("Projects/wellmed/kalpa-iris", "iris"),
            ("Projects/wellmed/kalpa-iris/services/spine", "iris"),
            (".herdr/worktrees/kalpa-iris/feature-x", "iris"),
            ("Projects/pmg/pmg-docs", "pmg"),
            ("Projects/ai-skills", "ai-skills"),
        ]
        for rel, graph in cases:
            with self.subTest(rel=rel):
                p = self.resolve(rel)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(p.stdout.strip(), os.path.join(self.home, PLANS[graph]))

    def test_unknown_project_exits_3(self):
        self.assertEqual(self.resolve("elsewhere").returncode, 3)

    def test_missing_docs_repo_exits_4_and_creates_nothing(self):
        os.rmdir(os.path.join(self.home, PLANS["iris"]))
        p = self.resolve("Projects/wellmed/kalpa-iris/services/spine")
        self.assertEqual(p.returncode, 4)
        self.assertFalse(os.path.exists(os.path.join(self.home, PLANS["iris"])))


if __name__ == "__main__":
    unittest.main()
