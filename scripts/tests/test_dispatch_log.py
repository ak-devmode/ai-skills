"""Tests for scripts/dispatch-log.py.

Approach: run the script as /concurrency does, against a temp log, and read the log back.
--pane is required because packet.py tells a lane from the driver by this record (Alex 84):
a record with no pane, or a blank one, must be a usage error that writes nothing.
"""

import json
import os
import tempfile
import unittest

from _helpers import run


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


if __name__ == "__main__":
    unittest.main()
