"""lever-candidates.py — second sighting only from a different scope; re-runs are no-ops.

Approach: build two scope folders under one plans dir, each with a finish table and a
verdict log whose final run is produced by the real runner (an unreachable row, exit 3),
then drive the script against a shared TO-DO.md and read the section back.
"""

import os
import subprocess
import tempfile
import unittest

from _helpers import run

HEADER = ("| check_id | deliverable | owner | class | check | repo | dir | env | timeout | rung "
          "| unreachable_ok | evidence |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n")


class Levers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.projects = os.path.realpath(self.tmp.name)
        self.svc = os.path.join(self.projects, "svc")
        os.makedirs(self.svc)
        for path in (self.svc, self.projects):
            subprocess.run(["git", "-C", path, "init", "-q"], check=True)
        subprocess.run(["git", "-C", self.svc, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
                        "--allow-empty", "-m", "a"], check=True)
        self.plans = os.path.join(self.projects, "docs", "plans")
        self.todo = os.path.join(self.plans, "TO-DO.md")
        os.makedirs(self.plans)
        with open(self.todo, "w") as fh:
            fh.write("# TO-DO\n\n## Some scope (Plan 1)\n- [ ] unrelated item\n")
        self.env = dict(os.environ, VERIFY_PROJECTS=self.projects)

    def tearDown(self):
        self.tmp.cleanup()

    def scope(self, name, unit, cid="p1-env-up"):
        sc = os.path.join(self.plans, name)
        os.makedirs(os.path.join(sc, "artifacts"))
        table = os.path.join(sc, "finish-conditions.md")
        with open(table, "w") as fh:
            fh.write(f"# t\n\n**Schema version:** verify/1\n**Revision:** 1\n\n{HEADER}"
                     f"| {cid} | env reachable | {unit} | B | `exit 3` | svc | . | - | - | 4 | no | ev |\n")
        self.verify(sc, unit)
        return sc

    def verify(self, sc, unit):
        log = os.path.join(sc, "artifacts", f"verify-{unit}.jsonl")
        p = run("verify-run.py", "run", "--table", os.path.join(sc, "finish-conditions.md"), "--log", log,
                "--owner", unit, env=self.env)
        rid = p.stdout.split("run_id: ")[1].split()[0]
        run("verify-run.py", "finalize", "--log", log, "--run-id", rid, "--judge", "none t", env=self.env)
        return rid

    def lc(self, sc):
        return run("lever-candidates.py", "--scope", sc, "--todo", self.todo, env=self.env)

    def text(self):
        with open(self.todo) as fh:
            return fh.read()

    def test_first_sighting_is_recorded_not_built(self):
        p = self.lc(self.scope("1-a", "1.1"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("new               env-up-verified-unreachable", p.stdout)
        t = self.text()
        self.assertIn("## Lever candidates", t)
        self.assertIn("- [ ] **`env-up-verified-unreachable`** — ", t)
        self.assertIn("Touches: svc · p1-env-up", t)
        self.assertIn("- [ ] unrelated item", t)
        self.assertNotIn("BUILD NOW", t)

    def test_rerunning_closeout_changes_nothing(self):
        sc = self.scope("1-a", "1.1")
        self.lc(sc)
        before = self.text()
        p = self.lc(sc)
        self.assertIn("already recorded", p.stdout)
        self.assertEqual(self.text(), before)

    def test_reverifying_the_same_scope_never_counts(self):
        sc = self.scope("1-a", "1.1")
        self.lc(sc)
        self.verify(sc, "1.1")
        p = self.lc(sc)
        self.assertIn("sighting          env-up-verified-unreachable  (1 scope(s)", p.stdout)
        self.assertNotIn("SECOND SIGHTING", p.stdout)
        self.assertNotIn("BUILD NOW", self.text())

    def test_same_gap_in_another_scope_is_the_second_sighting(self):
        self.lc(self.scope("1-a", "1.1"))
        # a different phase number: the p<P>- prefix is not part of the key
        p = self.lc(self.scope("2-b", "2.3", cid="p3-env-up"))
        self.assertIn("SECOND SIGHTING: env-up-verified-unreachable — build the lever now", p.stdout)
        t = self.text()
        self.assertIn("BUILD NOW (second sighting)", t)
        self.assertEqual(t.count("- [ ] **`env-up-verified-unreachable`**"), 1)
        self.assertEqual(t.count("Sighting: docs/"), 2)
        again = self.lc(self.scope("3-c", "3.1"))
        self.assertNotIn("SECOND SIGHTING", again.stdout)  # flips once
        self.assertEqual(self.text().count("BUILD NOW"), 1)

    def test_nothing_to_record(self):
        sc = os.path.join(self.plans, "4-d")
        os.makedirs(os.path.join(sc, "artifacts"))
        with open(os.path.join(sc, "finish-conditions.md"), "w") as fh:
            fh.write(f"# t\n\n**Schema version:** verify/1\n**Revision:** 1\n\n{HEADER}"
                     "| ok | d | 4.1 | B | `true` | svc | . | - | - | 4 | no | ev |\n")
        self.verify(sc, "4.1")
        before = self.text()
        p = self.lc(sc)
        self.assertEqual(p.returncode, 0)
        self.assertIn("none", p.stdout)
        self.assertEqual(self.text(), before)


if __name__ == "__main__":
    unittest.main()
