"""Tests for scripts/dispatch-log.py.

Approach: run the script as /concurrency does, against a temp log, and read the log back.
--pane is required: a record with no pane, or a blank one, must be a usage error that writes
nothing. --status driver is the driver registering its own pane (Alex 86): always this host's
normalized name, never another machine's (10.3-r4-03).
"""

import json
import os
import tempfile
import unittest

from _helpers import load, run


class DispatchLogTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.log = os.path.join(self._tmp.name, "log.jsonl")

    def test_pane_is_required(self):
        base = ["--scope", "10", "--task", "t", "--log", self.log]
        cases = [  # (name, extra args, exit, records written)
            ("pane given", ["--status", "dispatched", "--pane", "w1:p2"], 0, 1),
            ("no pane", ["--status", "dispatched"], 2, 0),
            ("blank pane", ["--status", "dispatched", "--pane", "  "], 2, 0),
            ("terminal record without pane", ["--status", "done"], 2, 0),
        ]
        for name, extra, rc, n in cases:
            with self.subTest(name):
                if os.path.exists(self.log):
                    os.remove(self.log)
                p = run("dispatch-log.py", *base, *extra)
                self.assertEqual(p.returncode, rc, p.stderr)
                lines = open(self.log).read().splitlines() if os.path.exists(self.log) else []
                self.assertEqual(len(lines), n)
                if n:
                    self.assertEqual(json.loads(lines[0])["pane_id"], "w1:p2")

    def test_driver_registers_its_own_pane_on_this_host(self):  # Alex 86, 10.3-r4-03
        me = load("placement.py").this_host()
        base = ["--scope", "10", "--pane", "w1:p2", "--log", self.log]
        cases = [  # (name, extra args, exit, records written)
            ("registration", ["--status", "driver"], 0, 1),
            ("this host named", ["--status", "driver", "--machine", me.upper()], 0, 1),
            ("another host", ["--status", "driver", "--machine", "elsewhere-box"], 2, 0),
            ("lane record still needs a task", ["--status", "dispatched"], 2, 0),
        ]
        for name, extra, rc, n in cases:
            with self.subTest(name):
                if os.path.exists(self.log):
                    os.remove(self.log)
                p = run("dispatch-log.py", *base, *extra)
                self.assertEqual(p.returncode, rc, p.stderr)
                lines = open(self.log).read().splitlines() if os.path.exists(self.log) else []
                self.assertEqual(len(lines), n)
                if n:
                    rec = json.loads(lines[0])
                    self.assertEqual((rec["kind"], rec["status"], rec["task"], rec["machine"]),
                                     ("driver", "driver", "driver", me))


if __name__ == "__main__":
    unittest.main()
