"""Tests for scripts/dispatch-log.py.

Approach: run the script as /concurrency does, against a temp log, and read the log back.
--pane is required: a record with no pane, or a blank one, must be a usage error that writes
nothing. --status driver is the driver registering its own pane (Alex 86): always this host's
normalized name, never another machine's (10.3-r4-03), bound to the session that registered
(Alex 97), and refused for a pane whose latest record is an open lane record, with no session
id, or with an unreadable log — a refusal writes nothing and names no way through.
"""

import json
import os
import tempfile
import unittest

from _helpers import load, run

SESSION_VARS = ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID", "CODEX_SESSION_ID")


def session_env(sid="sess-a"):
    """This environment with exactly one session id (or none when sid is None)."""
    env = {k: v for k, v in os.environ.items() if k not in SESSION_VARS}
    return dict(env, CLAUDE_CODE_SESSION_ID=sid) if sid is not None else env


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
                if n:  # every record names its machine, so a later one closes a registration
                    rec = json.loads(lines[0])
                    self.assertEqual((rec["pane_id"], rec["machine"]), ("w1:p2", load("placement.py").this_host()))

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
                p = run("dispatch-log.py", *base, *extra, env=session_env())
                self.assertEqual(p.returncode, rc, p.stderr)
                lines = open(self.log).read().splitlines() if os.path.exists(self.log) else []
                self.assertEqual(len(lines), n)
                if n:
                    rec = json.loads(lines[0])
                    self.assertEqual((rec["kind"], rec["status"], rec["task"], rec["machine"], rec["session"]),
                                     ("driver", "driver", "driver", me, "sess-a"))

    def test_registration_refusals(self):  # Alex 97, 10.3-r6-02 / r6-05
        me = load("placement.py").this_host()
        lane = lambda status, machine=me, pane="w1:p2": json.dumps(
            {"scope": "10", "task": "10.3", "pane_id": pane, "status": status,
             **({"machine": machine} if machine else {})})
        cases = [  # (name, log lines before, session, exit)
            ("open lane: dispatched", [lane("dispatched")], "sess-a", 3),
            ("open lane: blocked, no machine", [lane("blocked", None)], "sess-a", 3),
            ("lane done, then the driver", [lane("dispatched"), lane("done")], "sess-a", 0),
            ("lane failed, then the driver", [lane("failed")], "sess-a", 0),
            ("open lane on another host", [lane("dispatched", "elsewhere-box")], "sess-a", 0),
            ("open lane in another pane", [lane("dispatched", pane="w1:p9")], "sess-a", 0),
            ("no session id", [], None, 3),
            ("unreadable log", ["{not json"], "sess-a", 3),
        ]
        for name, before, sid, rc in cases:
            with self.subTest(name):
                with open(self.log, "w") as f:
                    f.write("".join(l + "\n" for l in before))
                p = run("dispatch-log.py", "--scope", "10", "--status", "driver", "--pane", "w1:p2",
                        "--log", self.log, env=session_env(sid))
                self.assertEqual(p.returncode, rc, p.stderr)
                lines = open(self.log).read().splitlines()
                self.assertEqual(len(lines), len(before) + (rc == 0))
                if rc:  # the refusal a lane reads never hands it the registration (10.3-r6-05)
                    self.assertNotIn("--status", p.stderr)
                    self.assertIn("refused", p.stderr)
                if name.startswith("open lane: "):
                    self.assertIn("A lane never registers, merges or posts: stop.", p.stderr)


if __name__ == "__main__":
    unittest.main()
