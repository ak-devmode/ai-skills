"""packet.py (10.1 task 1.2).

Approach: each test runs packet.py as a subprocess inside a throwaway git repo, with
HERDR_* identity pinned by env, against either no queue, a dead port, or a local
http.server stub on 127.0.0.1 that records POSTs and can be told to fail. Covers the
offline `Blocked` path, idempotent retry, driver-only POST, lane-tag refusals, and
touch/stale/close state transitions.
"""
import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from _helpers import run

LANE = {"PACKET_MACHINE": "mba", "PACKET_WORKSPACE": "ws1", "PACKET_AGENT": "laneA"}


def put(path, text, mode="w"):
    with open(path, mode) as f:
        f.write(text)


def load(path):
    with open(path) as f:
        return json.load(f)


class Stub:
    """Local queue: records (path, body); fail=True answers 500; seen ids answer 409."""

    def __init__(self):
        self.posts, self.fail, ids = [], False, set()
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if outer.fail:
                    code = 500
                elif body["id"] in ids:
                    code = 409
                else:
                    ids.add(body["id"]); code = 201
                    outer.posts.append((self.path, body))
                self.send_response(code); self.end_headers()

            def log_message(self, *a):
                pass

        self.srv = HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_port}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def stop(self):
        self.srv.shutdown(); self.srv.server_close()


class PacketBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = self._tmp.name
        self.g("init", "-q", "-b", "main")
        put(os.path.join(self.repo, "a.txt"), "a\n")
        self.commit("base")
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("HERDR_", "DECISION_QUEUE", "PACKET_"))}
        self.env.update(LANE)

    def g(self, *a):
        subprocess.run(["git", "-C", self.repo, "-c", "user.email=t@t", "-c", "user.name=t", *a],
                       check=True, capture_output=True)

    def commit(self, msg):
        put(os.path.join(self.repo, "a.txt"), msg + "\n", "a")
        self.g("add", "-A"); self.g("commit", "-q", "-m", msg)

    def pk(self, *args, env=None, stdin=None):
        e = dict(self.env, **(env or {}))
        return run("packet.py", *args, cwd=self.repo, env=e)

    def new(self, *extra, env=None, door="two-way"):
        p = self.pk("new", "--door", door, "--title", "Pick one", "--unit", "10/1.2",
                    "--option", "alpha", "--option", "beta", "--body", "why", *extra, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        pid = next(l.split()[1] for l in p.stdout.splitlines() if l.startswith("PACKET "))
        return pid, p.stdout

    def outbox(self):
        return os.path.join(self.repo, ".decision-queue", "outbox")

    def tag(self, pid, who="mba/ws1/laneA"):
        return f"[lane {who} {pid}] Option 1: alpha."


class TestNew(PacketBase):
    def test_writes_outbox_prints_packet_and_self_ignores(self):
        pid, out = self.new()
        self.assertTrue(os.path.exists(os.path.join(self.outbox(), f"{pid}.json")))
        self.assertIn("(recommended)", out)
        self.assertIn(f"[lane mba/ws1/laneA {pid}]", out)
        st = subprocess.run(["git", "-C", self.repo, "status", "--porcelain"], capture_output=True, text=True)
        self.assertEqual(st.stdout.strip(), "")  # outbox never dirties the worktree

    def test_invalid_packet_refused_and_nothing_written(self):
        p = self.pk("new", "--door", "two-way", "--title", "t", "--unit", "u", "--option", "a",
                    "--recommended", "5", "--body", "b")
        self.assertEqual(p.returncode, 1)
        self.assertFalse(os.path.exists(self.outbox()))

    def test_one_way_info_needs_options_rule(self):
        p = self.pk("new", "--door", "one-way", "--title", "t", "--unit", "u", "--body", "b")
        self.assertEqual(p.returncode, 2)

    def test_range_promotes_door(self):
        os.makedirs(os.path.join(self.repo, "db", "migrations"))
        put(os.path.join(self.repo, "db", "migrations", "1.sql"), "x")
        self.g("add", "-A"); self.g("commit", "-q", "-m", "mig")
        pid, out = self.new("--range", "HEAD~1..HEAD")
        doc = load(os.path.join(self.outbox(), f"{pid}.json"))
        self.assertEqual(doc["door"], "one-way")
        self.assertIn("promoted", out)


class TestQueue(PacketBase):
    def test_offline_prints_blocked_and_exits_zero(self):
        # nothing listens on this port: connection refused
        pid, out = self.new("--driver", env={"DECISION_QUEUE_URL": "http://127.0.0.1:9"})
        self.assertIn("Blocked", out)
        self.assertIn(f"PACKET {pid}", out)
        state = load(os.path.join(self.outbox(), f"{pid}.state.json"))
        self.assertFalse(state["sent"])

    def test_server_error_is_blocked_not_fatal(self):
        s = Stub(); self.addCleanup(s.stop); s.fail = True
        _, out = self.new("--driver", env={"DECISION_QUEUE_URL": s.url})
        self.assertIn("Blocked", out)
        self.assertIn("HTTP 500", out)

    def test_lane_never_posts_driver_does(self):
        s = Stub(); self.addCleanup(s.stop)
        env = {"DECISION_QUEUE_URL": s.url}
        pid, out = self.new(env=env)
        self.assertEqual(s.posts, [])
        self.assertIn("driver POSTs", out)
        _, out = self.new("--driver", env=env)
        self.assertEqual([p for p, _ in s.posts], ["/packets"])

    def test_herdr_driver_name_posts(self):
        s = Stub(); self.addCleanup(s.stop)
        self.new(env={"DECISION_QUEUE_URL": s.url, "HERDR_AGENT_NAME": "driver", "PACKET_AGENT": "driver"})
        self.assertEqual(len(s.posts), 1)

    def test_flush_resends_after_outage_and_is_idempotent(self):
        s = Stub(); self.addCleanup(s.stop)
        s.fail = True
        env = {"DECISION_QUEUE_URL": s.url}
        pid, _ = self.new("--driver", env=env)
        s.fail = False
        out = self.pk("flush", "--driver", env=env).stdout
        self.assertIn("FLUSHED 1 packets", out)
        self.assertEqual([b["id"] for _, b in s.posts], [pid])
        out = self.pk("flush", "--driver", env=env).stdout
        self.assertIn("FLUSHED 0 packets", out)
        # retrying `new --id` for the same id re-sends but the queue still holds one row
        self.new("--driver", "--id", pid, env=env)
        self.assertEqual(len(s.posts), 1)

    def test_driver_flushes_a_lane_outbox(self):
        s = Stub(); self.addCleanup(s.stop)
        pid, _ = self.new()  # lane writes, no POST
        out = self.pk("flush", "--driver", "--outbox", self.outbox(),
                      env={"DECISION_QUEUE_URL": s.url}).stdout
        self.assertIn("FLUSHED 1 packets", out)

    def test_lane_flush_sends_nothing(self):
        s = Stub(); self.addCleanup(s.stop)
        self.new()
        self.pk("flush", env={"DECISION_QUEUE_URL": s.url})
        self.assertEqual(s.posts, [])

    def test_close_event_posts_via_driver(self):
        s = Stub(); self.addCleanup(s.stop)
        env = {"DECISION_QUEUE_URL": s.url}
        pid, _ = self.new("--driver", env=env)
        self.assertEqual(self.pk("close", pid, "--driver", env=env).returncode, 0)
        kinds = [(p, b.get("kind")) for p, b in s.posts]
        self.assertIn(("/events", "closed"), kinds)


class TestCheckReply(PacketBase):
    def check(self, text, *extra):
        return self.pk("check-reply", "--reply", text, *extra)

    def test_good_reply_accepted(self):
        pid, _ = self.new()
        p = self.check(self.tag(pid))
        self.assertEqual((p.returncode, p.stdout.strip()), (0, f"OK {pid}"))

    def test_refusals(self):
        pid, _ = self.new()
        other, _ = self.new()
        cases = {
            "no tag": "just do alpha",
            "tag not at start": f"ok so {self.tag(pid)}",
            "wrong lane": self.tag(pid, "mba/ws1/laneB"),
            "wrong machine": self.tag(pid, "homelab/ws1/laneA"),
            "unknown packet": self.tag("pkdeadbeef00"),
            "two tags": f"{self.tag(pid)} also {self.tag(other)}",
        }
        for name, text in cases.items():
            with self.subTest(name):
                p = self.check(text)
                self.assertEqual(p.returncode, 1, p.stdout)
                self.assertIn("refused", p.stderr)

    def test_closed_and_stale_refused(self):
        pid, _ = self.new()
        self.assertEqual(self.pk("close", pid).returncode, 0)
        p = self.check(self.tag(pid))
        self.assertEqual(p.returncode, 1)
        self.assertIn("closed", p.stderr)
        pid2, _ = self.new()
        self.assertEqual(self.pk("stale", pid2, "--force").returncode, 0)
        p = self.check(self.tag(pid2))
        self.assertEqual(p.returncode, 1)
        self.assertIn("stale", p.stderr)

    def test_other_lanes_packet_refused_even_with_forged_tag(self):
        pid, _ = self.new(env={"PACKET_AGENT": "laneB"})  # emitted by laneB, same outbox
        p = self.check(self.tag(pid))  # laneA presents a tag naming itself
        self.assertEqual(p.returncode, 1)
        self.assertIn("another lane", p.stderr)

    def test_genuine_packet_of_another_lane_refused(self):
        pid, _ = self.new(env={"PACKET_AGENT": "laneB"})
        p = self.check(self.tag(pid, "mba/ws1/laneB"))  # honest tag, but laneA is asking
        self.assertEqual(p.returncode, 1)
        self.assertIn("this lane is", p.stderr)

    def test_corrupt_state_fails_closed(self):
        pid, _ = self.new()
        put(os.path.join(self.outbox(), f"{pid}.state.json"), "{nope")
        self.assertEqual(self.check(self.tag(pid)).returncode, 1)

    def test_driver_checks_on_behalf_of_a_lane(self):
        pid, _ = self.new()
        p = self.pk("check-reply", "--reply", self.tag(pid), "--lane", "mba/ws1/laneA",
                    env={"PACKET_AGENT": "driver"})
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_identity_outside_herdr_uses_machine_cwd_session(self):
        env = {k: v for k, v in self.env.items() if not k.startswith("PACKET_")}
        env.update(PACKET_MACHINE="mba", CLAUDE_SESSION_ID="sess1234abcd")
        p = run("packet.py", "new", "--door", "two-way", "--title", "t", "--unit", "u",
                "--option", "a", "--body", "b", cwd=self.repo, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertRegex(p.stdout, r"\[lane mba/cwd-[^/]+-[0-9a-f]{6}/session-sess1234abcd pk")


class TestStateTransitions(PacketBase):
    def test_touch_counts_stacked_commits(self):
        pid, _ = self.new()
        self.commit("one"); self.commit("two")
        p = self.pk("touch", pid)
        self.assertIn("commits_stacked=2", p.stdout)
        doc = load(os.path.join(self.outbox(), f"{pid}.json"))
        self.assertEqual(doc["reversal_cost"]["commits_stacked"], 2)

    def test_touch_refuses_one_way_and_closed(self):
        ow, _ = self.new(door="one-way")
        self.assertEqual(self.pk("touch", ow).returncode, 1)
        tw, _ = self.new()
        self.pk("close", tw)
        self.assertEqual(self.pk("touch", tw).returncode, 1)

    def test_stale_only_when_head_moved(self):
        pid, _ = self.new()
        self.assertIn("current", self.pk("stale", pid).stdout)
        self.commit("moved")
        self.assertIn("STALE", self.pk("stale", pid).stdout)
        self.assertEqual(self.pk("check-reply", "--reply", self.tag(pid)).returncode, 1)

    def test_close_is_idempotent_and_unknown_id_refused(self):
        pid, _ = self.new()
        self.assertEqual(self.pk("close", pid).returncode, 0)
        self.assertIn("already closed", self.pk("close", pid).stdout)
        self.assertEqual(self.pk("close", "pkdeadbeef00").returncode, 1)

    def test_event_done_validates(self):
        p = self.pk("event", "--kind", "done", "--body", "task 1.2 done")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.pk("event", "--kind", "closed").returncode, 1)  # needs --packet-id


if __name__ == "__main__":
    unittest.main()
