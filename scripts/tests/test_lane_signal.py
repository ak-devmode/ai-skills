"""lane-signal.py wait — the two failures WellMed 231 hit (2026-11-20).
Approach: load the script as a module, point its lane dir at a temp HOME, and fake the two
outside calls (`sh` lists done files, `pane_status` asks herdr) so each wait runs one poll.
"""
import os
import tempfile
import unittest
from unittest import mock

from _helpers import load


class TestWait(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = mock.patch.dict(os.environ, {"HOME": self.tmp.name})
        self.home.start()
        self.ls = load("lane-signal.py")
        self.done = {}      # lane -> done-file body
        self.status = {}    # pane -> herdr status
        self.ls.sh = lambda machine, script: "".join(f"{n}.done\t{b}\n" for n, b in self.done.items())
        self.ls.pane_status = lambda machine, pane: self.status.get(pane, "working")
        self.ls.time.sleep = lambda s: None

    def tearDown(self):
        self.home.stop()
        self.tmp.cleanup()

    def wait(self, *lanes, idle_min=10, clock=None):
        argv = ["wait", "run1", "--idle-min", str(idle_min), "--timeout-min", "0.1"]
        for spec in lanes:
            argv += ["--lane", spec]
        with mock.patch("sys.stdout") as out:
            if clock is not None:
                ticks = iter(range(10 ** 6))  # each call one second later, so the deadline passes
                with mock.patch.object(self.ls.time, "time", lambda: clock + next(ticks)):
                    self.ls.main(argv)
            else:
                self.ls.main(argv)
        return "".join(c.args[0] for c in out.write.call_args_list)

    def test_a_reused_lane_name_reports_its_new_signal(self):
        # cat-fix ran, was reported, then a fix round re-dispatched it: the old report must not
        # read the new lane as done (it printed ALL-DONE before the lane had started).
        self.done["cat"] = "exit=0 at=T1 note=first"
        self.assertIn("DONE cat", self.wait("cat=p1"))
        del self.done["cat"]                       # the driver removes the file and re-dispatches
        self.assertNotIn("ALL-DONE", self.wait("cat=p1"))
        self.done["cat"] = "exit=0 at=T2 note=second"
        self.assertIn("DONE cat exit=0 at=T2", self.wait("cat=p1"))

    def test_idle_clock_survives_a_rearmed_wait(self):
        # a lane idle on its own question across many short re-armed waits still surfaces
        self.status["p1"] = "idle"
        self.assertNotIn("IDLE-NO-SIGNAL", self.wait("lab=p1", clock=1000.0))
        self.assertNotIn("IDLE-NO-SIGNAL", self.wait("lab=p1", clock=1000.0 + 5 * 60))
        self.assertIn("IDLE-NO-SIGNAL lab p1", self.wait("lab=p1", clock=1000.0 + 11 * 60))


class TestWaitingOnShells(unittest.TestCase):
    def test_footer(self):
        ls = load("lane-signal.py")
        for screen, want in (
                ("work\n  ⏵⏵ bypass permissions on · 1 shell · ← 1 agent\n", True),
                ("done\n✻ Brewed for 6m · 2 shells still running\n", True),
                ("done\n❯\n  ⏵⏵ bypass permissions on · ← 1 agent\n", False),
                ("1 shell mentioned long ago\n" + "line\n" * 10, False)):
            with self.subTest(screen=screen[:30]):
                self.assertEqual(ls.waiting_on_shells(screen), want)


if __name__ == "__main__":
    unittest.main()
