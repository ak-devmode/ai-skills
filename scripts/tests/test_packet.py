"""packet.py (10.1 task 1.2).

Approach: each test runs packet.py as a subprocess inside a throwaway git repo, with
HERDR_* identity pinned by env, against either no queue, a dead port, or a local
http.server stub on 127.0.0.1 that records POSTs and can be told to fail. Covers the
offline `Blocked` path, idempotent retry, driver-only POST, lane-tag refusals, and
touch/stale/close state transitions.
"""
import json
import os
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from _helpers import run, script, load as load_script

SESSION_VARS = ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID", "CODEX_SESSION_ID")
LANE = {"PACKET_MACHINE": "mba", "PACKET_WORKSPACE": "ws1", "PACKET_AGENT": "laneA"}


def put(path, text, mode="w"):
    with open(path, mode) as f:
        f.write(text)


def load(path):
    with open(path) as f:
        return json.load(f)


class Stub:
    """Local queue: records (path, body); fail=True answers 500; a seen id answers 200 when the
    body is identical and 409 when it differs; an event for an unknown packet answers 404;
    `force` (a status code) overrides everything."""

    def __init__(self):
        self.posts, self.fail, self.redirect, self.delay, ids = [], False, False, 0, {}
        self.force = None
        outer = self

        class H(BaseHTTPRequestHandler):
            def do_GET(self):  # where a redirected POST lands: 200, but nothing is stored
                self.send_response(200); self.end_headers()

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                time.sleep(outer.delay)
                if outer.redirect:
                    self.send_response(302)
                    self.send_header("Location", outer.url + "/elsewhere"); self.end_headers()
                    return
                if outer.force:
                    code = outer.force
                elif outer.fail:
                    code = 500
                elif body["id"] in ids:
                    code = 200 if ids[body["id"]] == body else 409
                elif self.path == "/events" and body.get("packet_id") and body["packet_id"] not in ids:
                    code = 404
                else:
                    ids[body["id"]] = body; code = 201
                    outer.posts.append((self.path, body))
                self.send_response(code); self.end_headers()

            def log_message(self, *a):
                pass

        self.srv = HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_port}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def stop(self):
        self.srv.shutdown(); self.srv.server_close()


DEMO = {"DQ_UI_DEMO_TENANT": "demo-tenant"}


class PacketBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = self._tmp.name
        self.g("init", "-q", "-b", "main")
        put(os.path.join(self.repo, "a.txt"), "a\n")
        self.commit("base")
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("HERDR_", "DECISION_QUEUE", "PACKET_"))
                    and k not in SESSION_VARS}
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
                    "--option", "alpha::first", "--option", "beta::second", "--context", "why", *extra, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        pid = next(l.split()[1] for l in p.stdout.splitlines() if l.startswith("PACKET "))
        return pid, p.stdout

    def outbox(self):
        return os.path.join(self.repo, ".decision-queue", "outbox")

    def sent(self, pid):
        return os.path.exists(os.path.join(self.outbox(), f"{pid}.sent"))

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

    def test_ui_packet_from_payload_file_and_non_png_refused(self):
        fx = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "packets", "valid", "ui-two-way.json")
        payload = load(fx)["payload"]
        pf = os.path.join(self.repo, "ui-payload.json")
        put(pf, json.dumps(payload))
        args = ("new", "--door", "two-way", "--type", "ui", "--title", "t", "--unit", "u",
                "--option", "a::x", "--option", "b::y", "--context", "c", "--payload-file", pf)
        p = self.pk(*args, env=DEMO)
        self.assertEqual(p.returncode, 0, p.stderr)
        payload["new"]["image"] = "data:image/jpeg;base64,AAAA"
        put(pf, json.dumps(payload))
        p = self.pk(*args, env=DEMO)
        self.assertEqual(p.returncode, 1, p.stdout)  # refused: not a PNG data URI, nothing queued
        self.assertIn("/payload/new/image", p.stderr + p.stdout)

    def _ui(self, mutate=None, env=DEMO):
        fx = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "packets", "valid", "ui-two-way.json")
        payload = load(fx)["payload"]
        if mutate:
            mutate(payload)
        pf = os.path.join(self.repo, "ui-payload.json")
        put(pf, json.dumps(payload))
        return self.pk("new", "--door", "two-way", "--type", "ui", "--title", "t", "--unit", "u",
                       "--option", "a::x", "--option", "b::y", "--context", "c", "--payload-file", pf, env=env)

    def test_ui_image_content_checks(self):  # 10.4-r3-05
        import base64
        def setimg(raw=None, b64=None):
            def f(p):
                p["old"]["image"] = "data:image/png;base64," + (b64 if b64 is not None else base64.b64encode(raw).decode())
            return f
        cases = [("bad base64", setimg(b64="AAA*AAAA"), "invalid base64"),
                 ("svg bytes labelled png", setimg(raw=b"<svg xmlns='x'></svg>"), "not a PNG"),
                 ("oversize", setimg(raw=b"\x89PNG\r\n\x1a\n" + b"0" * 1_500_001), "cap")]
        for name, mut, want in cases:
            with self.subTest(name):
                p = self._ui(mut)
                self.assertEqual(p.returncode, 1, p.stdout)
                self.assertIn(want, p.stderr)
                self.assertFalse(os.path.exists(self.outbox()))

    def test_ui_demo_tenant_guard(self):  # driver call: fail closed on real-patient tenants
        p = self._ui(env={"DQ_UI_DEMO_TENANT": ""})
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("DQ_UI_DEMO_TENANT is not set", p.stderr)
        p = self._ui(env={"DQ_UI_DEMO_TENANT": "some-other-tenant"})
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("does not equal", p.stderr)
        self.assertFalse(os.path.exists(self.outbox()))

    def test_invalid_packet_refused_and_nothing_written(self):
        p = self.pk("new", "--door", "two-way", "--title", "t", "--unit", "u", "--option", "a::x",
                    "--recommended", "5", "--context", "b")
        self.assertEqual(p.returncode, 1)
        self.assertFalse(os.path.exists(self.outbox()))

    # --- schema v2 (10.4 cards lane): the card is capped, the refusal says what to cut ---
    def v2(self, *extra, title="Who pays?", context="A visit can owe nothing.", options=("a::x", "b::y")):
        args = ["new", "--door", "two-way", "--title", title, "--unit", "u", "--context", context]
        for o in options:
            args += ["--option", o]
        return self.pk(*args, *extra)

    def test_v2_writes_context_evidence_why_and_no_body(self):
        p = self.v2("--evidence", "`a.go:12`", options=("Signal from backbone::one path", "Read bill::ties schemas"))
        self.assertEqual(p.returncode, 0, p.stderr)
        pid = p.stdout.split()[1]
        doc = load(os.path.join(self.outbox(), f"{pid}.json"))
        self.assertEqual((doc["schema_version"], doc["context"], doc["evidence"], doc["payload"]),
                         (2, "A visit can owe nothing.", "`a.go:12`", {}))
        self.assertEqual(doc["options"][0], {"id": "1", "label": "Signal from backbone", "why": "one path",
                                             "recommended": True})
        self.assertIn("     one path", p.stdout)  # the why prints under its option

    def test_v2_caps_refused_with_the_cut_message(self):
        cases = [("title", dict(title="q" * 101), "cut title to 100 chars (now 101)"),
                 ("context", dict(context="c" * 401), "cut context to 400 chars (now 401)"),
                 ("label", dict(options=("l" * 61 + "::w",)), "cut option 1 label to 60 chars (now 61)"),
                 ("why", dict(options=("a::x", "b::" + "w" * 141)), "cut option 2 why to 140 chars (now 141)")]
        for name, kw, want in cases:
            with self.subTest(name):
                p = self.v2(**kw)
                self.assertEqual(p.returncode, 1, p.stdout)
                self.assertIn(want, p.stderr)
                self.assertFalse(os.path.exists(self.outbox()))
        p = self.v2("--evidence", "e" * 4001)
        self.assertIn("cut evidence to 4000 chars (now 4001)", p.stderr)
        p = self.v2(title="q" * 100, context="c" * 400, options=("l" * 60 + "::" + "w" * 140,))
        self.assertEqual(p.returncode, 0, p.stderr)  # at the cap is fine

    def test_v2_refusals_name_the_fix(self):
        cases = [("body", ("--body", "long prose"), {}, "v2 has no body"),
                 ("no why", (), dict(options=("a",)), "option 1 needs a why"),
                 ("recommended text", (), dict(options=("a (Recommended)::x",)), 'drop "(recommended)"'),
                 ("two-line title", (), dict(title="a\nb"), "title must be one line"),
                 ("no context", (), dict(context=""), "--context is required")]
        for name, extra, kw, want in cases:
            with self.subTest(name):
                p = self.v2(*extra, **kw)
                self.assertEqual(p.returncode, 1, p.stdout)
                self.assertIn(want, p.stderr)
        self.assertFalse(os.path.exists(self.outbox()))

    def test_recommended_marker_refused_in_any_case_on_any_option(self):
        # 10.4-r14-05: the flag is the only marker; a mixed-case one on either option is refused
        for marker in ("(RECOMMENDED)", "(ReCoMmEnDeD)", "(recommended)"):
            for which, opts in (("recommended", (f"a {marker}::x", "b::y")), ("other", ("a::x", f"b {marker}::y"))):
                with self.subTest(marker=marker, option=which):
                    p = self.v2(options=opts)
                    self.assertEqual(p.returncode, 1, p.stdout)
                    self.assertIn('drop "(recommended)"', p.stderr)
        self.assertFalse(os.path.exists(self.outbox()))

    def test_v1_non_recommended_label_marker_is_not_shown_as_a_second_recommendation(self):
        p = self.pk("new", "--schema-version", "1", "--door", "two-way", "--title", "t", "--unit", "u",
                    "--option", "alpha", "--option", "beta (RECOMMENDED)", "--body", "b")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.lower().count("(recommended)"), 1, p.stdout)
        self.assertIn("1. alpha  (recommended)", p.stdout)

    def test_v1_still_written_on_request_and_refuses_v2_fields(self):
        base = ("new", "--schema-version", "1", "--door", "two-way", "--title", "t", "--unit", "u",
                "--option", "alpha (recommended)", "--option", "beta", "--body", "b")
        p = self.pk(*base)
        self.assertEqual(p.returncode, 0, p.stderr)
        doc = load(os.path.join(self.outbox(), f"{p.stdout.split()[1]}.json"))
        self.assertEqual((doc["schema_version"], doc["payload"]), (1, {"body": "b"}))
        self.assertEqual(p.stdout.count("(recommended)"), 1, p.stdout)  # a v1 label saying it is not doubled
        p = self.pk(*base, "--context", "c")
        self.assertEqual(p.returncode, 1)
        self.assertIn("v1 has no --context/--evidence", p.stderr)

    def test_v2_caps_match_the_schema(self):
        import re as _re
        schema = load(os.path.join(os.path.dirname(script("packet.py")), "..", "schemas", "packet.schema.json"))
        v2 = next(b["then"] for b in schema["allOf"]
                  if b["if"]["properties"].get("schema_version", {}).get("const") == 2 and "required" in b["then"])
        opt = schema["$defs"]["option_v2"]["properties"]
        pats = {"title": v2["properties"]["title"], "context": v2["properties"]["context"],
                "evidence": v2["properties"]["evidence"], "label": opt["label"], "why": opt["why"]}
        packet = load_script("packet.py")
        for field, sch in pats.items():
            self.assertEqual(int(_re.search(r"\{1,(\d+)\}", sch["pattern"]).group(1)), packet.V2_CAPS[field], field)

    def test_one_way_info_needs_options_rule(self):
        p = self.pk("new", "--door", "one-way", "--title", "t", "--unit", "u", "--context", "b")
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
        self.assertFalse(self.sent(pid))

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
        self.assertTrue(self.sent(pid))
        out = self.pk("flush", "--driver", env=env).stdout
        self.assertIn("FLUSHED 0 packets", out)
        # retrying `new --id` for the same id re-sends but the queue still holds one row
        out = self.new("--driver", "--id", pid, env=env)[1]
        self.assertEqual(len(s.posts), 1)
        # the 200 duplicate from the second POST counts as sent: no Blocked note, still marked sent
        self.assertNotIn("Blocked", out)
        self.assertTrue(self.sent(pid))

    def _marker(self, name):
        return os.path.exists(os.path.join(self.outbox(), name))

    def test_409_is_a_conflict_not_a_send(self):  # driver finding: 409 used to count as sent
        s = Stub(); self.addCleanup(s.stop)
        env = {"DECISION_QUEUE_URL": s.url}
        pid, _ = self.new("--driver", env=env)
        path = os.path.join(self.outbox(), f"{pid}.json")
        doc = load(path); doc["title"] = "changed"; put(path, json.dumps(doc))
        os.remove(os.path.join(self.outbox(), f"{pid}.sent"))
        p = self.pk("new", "--driver", "--id", pid, "--door", "two-way", "--title", "Other",
                    "--unit", "10/1.2", "--option", "a::x", "--option", "b::y", "--context", "x", env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("Conflict:", p.stdout)
        self.assertFalse(self.sent(pid))
        self.assertTrue(self._marker(f"{pid}.conflict"))
        out = self.pk("flush", "--driver", env=env).stdout
        self.assertIn("FLUSHED 0 packets", out)
        self.assertIn(".conflict", out)
        self.assertEqual(len(s.posts), 1)  # flush did not retry the conflicted id

    def test_400_is_rejected_once_never_retried(self):
        s = Stub(); self.addCleanup(s.stop); s.force = 400
        env = {"DECISION_QUEUE_URL": s.url}
        pid, out = self.new("--driver", env=env)
        self.assertIn("Rejected:", out)
        self.assertIn("HTTP 400", out)
        self.assertNotIn("Blocked", out)
        self.assertFalse(self.sent(pid))
        self.assertTrue(self._marker(f"{pid}.rejected"))
        s.force = None
        out = self.pk("flush", "--driver", env=env).stdout
        self.assertIn("FLUSHED 0 packets", out)
        self.assertIn(".rejected", out)
        self.assertEqual(s.posts, [])

    def test_other_4xx_stay_blocked_and_retry(self):  # 10.1-r7-01
        s = Stub(); self.addCleanup(s.stop)
        env = {"DECISION_QUEUE_URL": s.url}
        for code in (401, 403, 404, 408, 429):
            s.force = code
            pid, out = self.new("--driver", env=env)
            self.assertIn("Blocked", out, code)
            self.assertFalse(self._marker(f"{pid}.rejected") or self._marker(f"{pid}.conflict"), code)
            s.force = None
            out = self.pk("flush", "--driver", env=env).stdout
            self.assertIn("FLUSHED 1 packets", out, code)
        for code in (413, 415, 422):
            s.force = code
            pid, out = self.new("--driver", env=env)
            self.assertIn("Rejected:", out, code)
            self.assertTrue(self._marker(f"{pid}.rejected"), code)

    def _event_of_refused_packet(self, code):
        s = Stub(); self.addCleanup(s.stop); s.force = code
        env = {"DECISION_QUEUE_URL": s.url}
        pid, _ = self.new("--driver", env=env)
        marker = "conflict" if code == 409 else "rejected"
        self.assertTrue(self._marker(f"{pid}.{marker}"))
        s.force = None
        n = len(s.posts)
        self.assertEqual(self.pk("close", pid, "--driver", env=env).returncode, 0)
        for _ in range(2):
            out = self.pk("flush", "--driver", env=env).stdout
        self.assertEqual(len(s.posts), n)  # nothing POSTed: neither packet nor close event
        evs = [f for f in os.listdir(self.outbox()) if f.startswith("evt-") and f.endswith(".json")]
        self.assertTrue(evs)
        for f in evs:
            self.assertTrue(self._marker(f[:-5] + ".rejected"))
        self.assertIn("FLUSHED 0 packets, 0 events", out)

    def test_event_of_400_packet_is_marked_not_posted(self):  # 10.1-r7-02
        self._event_of_refused_packet(400)

    def test_event_of_409_packet_is_marked_not_posted(self):  # 10.1-r7-03
        self._event_of_refused_packet(409)

    def test_resend_after_400_clears_marker_and_close_is_posted(self):  # 10.1-r10-01
        s = Stub(); self.addCleanup(s.stop); s.force = 400
        env = {"DECISION_QUEUE_URL": s.url}
        pid, _ = self.new("--driver", env=env)
        self.assertTrue(self._marker(f"{pid}.rejected"))
        s.force = None
        p = self.pk("new", "--id", pid, "--driver", "--door", "two-way", "--title", "Pick one",
                    "--unit", "10/1.2", "--option", "alpha::first", "--option", "beta::second", "--context", "why", env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(self.sent(pid))
        self.assertFalse(self._marker(f"{pid}.rejected"))
        self.assertEqual(self.pk("close", pid, "--driver", env=env).returncode, 0)
        self.pk("flush", "--driver", env=env)  # close --driver POSTs at once; flush must not undo it
        self.assertEqual([path for path, _ in s.posts], ["/packets", "/events"])
        self.assertFalse([f for f in os.listdir(self.outbox()) if f.startswith("evt-") and f.endswith(".rejected")])

    def test_marker_unlink_failure_is_reported_and_flush_recovers(self):  # 10.1-r12-01
        s = Stub(); self.addCleanup(s.stop); s.force = 400
        env = {"DECISION_QUEUE_URL": s.url}
        pid, _ = self.new("--driver", env=env)
        s.force = None
        self.assertEqual(self.pk("close", pid, "--driver", env=env).returncode, 0)  # event marked refused
        # sitecustomize makes unlink of evt-*.rejected raise PermissionError until the flag file is gone
        inj = tempfile.mkdtemp(); self.addCleanup(lambda: __import__("shutil").rmtree(inj, True))
        flag = os.path.join(inj, "fail")
        put(flag, "")
        put(os.path.join(inj, "sitecustomize.py"),
            "import os, pathlib\n_u = pathlib.Path.unlink\n"
            "def unlink(self, *a, **k):\n"
            f"    if self.name.startswith('evt-') and self.name.endswith('.rejected') and os.path.exists({flag!r}):\n"
            "        raise PermissionError(13, 'injected')\n"
            "    return _u(self, *a, **k)\n"
            "pathlib.Path.unlink = unlink\n")
        bad = dict(env, PYTHONPATH=inj)
        p = self.pk("new", "--id", pid, "--driver", "--door", "two-way", "--title", "Pick one",
                    "--unit", "10/1.2", "--option", "alpha::first", "--option", "beta::second", "--context", "why", env=bad)
        self.assertEqual(p.returncode, 0, p.stderr)  # harness error never stops the caller
        self.assertIn("refusal markers not cleared", p.stderr)
        self.assertTrue(self.sent(pid))
        n = len(s.posts)
        self.pk("flush", "--driver", env=bad)  # still failing: reported again, no event POSTed
        self.assertEqual(len(s.posts), n)
        os.remove(flag)  # permissions recover
        out = self.pk("flush", "--driver", env=bad).stdout
        self.assertIn("FLUSHED 0 packets, 1 events", out)
        self.assertEqual([path for path, _ in s.posts][n:], ["/events"])
        self.assertFalse([f for f in os.listdir(self.outbox()) if f.endswith(".rejected")])

    def test_flush_warns_on_missing_outbox(self):  # driver todo
        s = Stub(); self.addCleanup(s.stop)
        gone = os.path.join(self.repo, "nope")
        p = self.pk("flush", "--driver", "--outbox", gone, env={"DECISION_QUEUE_URL": s.url})
        self.assertEqual(p.returncode, 0)
        self.assertIn(f"Skipped: outbox {gone} does not exist", p.stdout)

    def test_5xx_stays_blocked_and_retries(self):
        s = Stub(); self.addCleanup(s.stop); s.force = 503
        env = {"DECISION_QUEUE_URL": s.url}
        pid, out = self.new("--driver", env=env)
        self.assertIn("Blocked", out)
        self.assertFalse(self._marker(f"{pid}.rejected") or self._marker(f"{pid}.conflict"))

    def test_event_404_is_kept_and_sent_after_the_packet(self):
        s = Stub(); self.addCleanup(s.stop)
        env = {"DECISION_QUEUE_URL": s.url}
        pid, _ = self.new()  # lane outbox only: the packet is not on the queue
        p = self.pk("event", "--driver", "--kind", "done", "--body", "hi", "--packet-id", pid, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("not on the queue yet", p.stdout + p.stderr)
        evs = [f for f in os.listdir(self.outbox()) if f.startswith("evt-") and f.endswith(".json")]
        self.assertEqual(len(evs), 1)
        self.assertFalse(any(f.endswith((".conflict", ".rejected", ".sent")) for f in os.listdir(self.outbox()) if f.startswith("evt-")))
        out = self.pk("flush", "--driver", env=env).stdout  # packets go first, then the event
        self.assertIn("FLUSHED 1 packets, 1 events", out)
        self.assertEqual([p_ for p_, _ in s.posts], ["/packets", "/events"])

    def test_driver_flushes_a_lane_outbox(self):
        s = Stub(); self.addCleanup(s.stop)
        pid, _ = self.new()  # lane writes, no POST
        out = self.pk("flush", "--driver", "--outbox", self.outbox(),
                      env={"DECISION_QUEUE_URL": s.url}).stdout
        self.assertIn("FLUSHED 1 packets", out)
        self.assertEqual([(p, b["id"]) for p, b in s.posts], [("/packets", pid)])
        self.assertTrue(self.sent(pid))

    def test_lane_flush_sends_nothing(self):
        s = Stub(); self.addCleanup(s.stop)
        self.new()
        self.pk("flush", env={"DECISION_QUEUE_URL": s.url})
        self.assertEqual(s.posts, [])
        self.assertEqual([f for f in os.listdir(self.outbox()) if f.endswith(".sent")], [])

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
                "--option", "a::x", "--context", "b", cwd=self.repo, env=env)
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


class Drip:
    """Raw socket server that answers with one header byte every 0.3 s for `secs` seconds:
    each socket read succeeds, so only a wall-clock deadline can stop the caller."""

    def __init__(self, secs=6):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0)); self.sock.listen(5)
        self.url = f"http://127.0.0.1:{self.sock.getsockname()[1]}"
        threading.Thread(target=self.loop, args=(secs,), daemon=True).start()

    def loop(self, secs):
        try:
            conn, _ = self.sock.accept()
            conn.settimeout(1)
            try:
                conn.recv(65536)
            except OSError:
                pass
            for ch in b"HTTP/1.1 200 OK\r\n" + b"X-Pad: " + b"a" * 200:
                conn.sendall(bytes([ch])); time.sleep(secs / 220)
            conn.close()
        except OSError:
            pass

    def stop(self):
        self.sock.close()


class TestSendPath(PacketBase):
    """10.1-r1-02 (send must not clobber concurrent state), -05 (bounded, no redirect), -06 (robust)."""

    def test_close_during_post_is_not_overwritten(self):
        s = Stub(); self.addCleanup(s.stop); s.delay = 1.5
        env = dict(self.env, DECISION_QUEUE_URL=s.url)
        proc = subprocess.Popen(
            ["python3", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "packet.py"),
             "new", "--driver", "--door", "two-way", "--title", "t", "--unit", "u",
             "--option", "a::x", "--context", "b"],
            cwd=self.repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(proc.kill)
        deadline = time.time() + 5
        while time.time() < deadline and not (
                os.path.isdir(self.outbox()) and any(f.endswith(".state.json") for f in os.listdir(self.outbox()))):
            time.sleep(0.05)
        pid = next(f for f in os.listdir(self.outbox()) if f.endswith(".state.json"))[: -len(".state.json")]
        time.sleep(0.3)  # the driver is now inside the POST
        self.assertEqual(self.pk("close", pid).returncode, 0)
        proc.communicate(timeout=10)
        self.assertEqual(load(os.path.join(self.outbox(), f"{pid}.state.json"))["status"], "closed")
        self.assertTrue(self.sent(pid))

    def test_redirect_is_a_failure_not_a_send(self):
        s = Stub(); self.addCleanup(s.stop); s.redirect = True
        pid, out = self.new("--driver", env={"DECISION_QUEUE_URL": s.url})
        self.assertIn("Blocked", out)
        self.assertIn("HTTP 302", out)
        self.assertFalse(self.sent(pid))

    def test_slow_drip_server_cannot_hold_the_caller_past_the_deadline(self):
        d = Drip(); self.addCleanup(d.stop)
        t0 = time.time()
        pid, out = self.new("--driver", env={"DECISION_QUEUE_URL": d.url, "PACKET_POST_TIMEOUT": "1"})
        self.assertLess(time.time() - t0, 3.5)
        self.assertIn("Blocked", out)
        self.assertIn("timed out", out)
        self.assertFalse(self.sent(pid))

    def test_flush_skips_a_corrupt_item_and_sends_the_rest(self):
        s = Stub(); self.addCleanup(s.stop)
        ids = [self.new()[0] for _ in range(3)]
        put(os.path.join(self.outbox(), f"{ids[1]}.json"), "{nope")
        p = self.pk("flush", "--driver", env={"DECISION_QUEUE_URL": s.url})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("Traceback", p.stderr)
        self.assertIn("FLUSHED 2 packets", p.stdout)
        self.assertIn(ids[1], p.stdout)  # reported, not silent
        self.assertEqual(sorted(b["id"] for _, b in s.posts), sorted(ids[:1] + ids[2:]))

    def test_flush_skips_a_missing_packet_file(self):
        s = Stub(); self.addCleanup(s.stop)
        ids = [self.new()[0] for _ in range(2)]
        os.remove(os.path.join(self.outbox(), f"{ids[0]}.json"))
        p = self.pk("flush", "--driver", env={"DECISION_QUEUE_URL": s.url})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("FLUSHED 1 packets", p.stdout)

    def test_unreadable_files_are_exit_one_not_a_traceback(self):
        p = self.pk("new", "--door", "two-way", "--title", "t", "--unit", "u", "--option", "a::x",
                    "--body-file", os.path.join(self.repo, "missing.txt"))
        self.assertEqual(p.returncode, 1)
        self.assertNotIn("Traceback", p.stderr)
        p = self.pk("check-reply", "--file", os.path.join(self.repo, "missing.txt"))
        self.assertEqual(p.returncode, 1)
        self.assertNotIn("Traceback", p.stderr)


class TestInfoAndOneWayHead(PacketBase):
    def test_info_packet_with_range_stays_info(self):  # 10.1-r1-03
        self.commit("second")  # HEAD~1 must resolve, else the range fails closed
        p = self.pk("new", "--door", "info", "--title", "FYI", "--unit", "u", "--option", "ack::ok", "--context", "b",
                    "--range", "HEAD~1..HEAD")
        self.assertEqual(p.returncode, 0, p.stderr)
        pid = next(l.split()[1] for l in p.stdout.splitlines() if l.startswith("PACKET "))
        self.assertEqual(load(os.path.join(self.outbox(), f"{pid}.json"))["door"], "info")

    def test_one_way_reply_refused_after_head_moves(self):  # 10.1-r1-07
        pid, _ = self.new(door="one-way")
        self.assertEqual(self.pk("check-reply", "--reply", self.tag(pid)).returncode, 0)
        self.commit("moved")
        p = self.pk("check-reply", "--reply", self.tag(pid))
        self.assertEqual(p.returncode, 1)
        self.assertIn("stale", p.stderr)

    def test_one_way_reply_accepted_after_plans_only_commit(self):  # 10.1-r3-02
        pid, _ = self.new(door="one-way")
        os.makedirs(os.path.join(self.repo, "plans"), exist_ok=True)
        put(os.path.join(self.repo, "plans", "p.md"), "x\n", "a")
        self.g("add", "-A"); self.g("commit", "-q", "-m", "plans only")
        self.assertEqual(self.pk("check-reply", "--reply", self.tag(pid)).returncode, 0)

    def test_one_way_reply_refused_when_plans_and_code_move(self):  # 10.1-r3-02
        pid, _ = self.new(door="one-way")
        os.makedirs(os.path.join(self.repo, "plans"), exist_ok=True)
        put(os.path.join(self.repo, "plans", "p.md"), "x\n", "a")
        self.commit("code too")
        p = self.pk("check-reply", "--reply", self.tag(pid))
        self.assertEqual(p.returncode, 1)
        self.assertIn("a.txt", p.stderr)

    def test_one_way_reply_refused_after_history_rewrite(self):  # 10.1-r3-02
        pid, _ = self.new(door="one-way")
        self.g("commit", "-q", "--amend", "--allow-empty", "-m", "rewritten")
        p = self.pk("check-reply", "--reply", self.tag(pid))
        self.assertEqual(p.returncode, 1)
        self.assertIn("stale", p.stderr)

    def test_bad_post_timeout_does_not_break_the_caller(self):  # 10.1-r3-03
        pid, out = self.new(env={"PACKET_POST_TIMEOUT": "abc"})
        self.assertNotIn("Traceback", out)

    def test_new_state_has_no_dead_sent_field(self):  # 10.1-r3-01
        pid, _ = self.new()
        self.assertNotIn("sent", load(os.path.join(self.outbox(), f"{pid}.state.json")))

    def test_two_way_reply_still_accepted_after_head_moves(self):
        pid, _ = self.new()
        self.commit("moved")
        self.assertEqual(self.pk("check-reply", "--reply", self.tag(pid)).returncode, 0)

    def test_one_way_reply_refused_when_head_unreadable(self):
        pid, _ = self.new(door="one-way")
        with tempfile.TemporaryDirectory() as elsewhere:
            odd = os.path.join(elsewhere, "box")  # not <repo>/.decision-queue/outbox
            subprocess.run(["cp", "-R", self.outbox(), odd], check=True)
            p = run("packet.py", "check-reply", "--reply", self.tag(pid), "--outbox", odd,
                    cwd=elsewhere, env=self.env)
        self.assertEqual(p.returncode, 1)
        self.assertIn("cannot read HEAD", p.stderr)

    def test_driver_outside_the_repo_checks_the_lane_repos_head(self):
        pid, _ = self.new(door="one-way")
        with tempfile.TemporaryDirectory() as elsewhere:
            p = run("packet.py", "check-reply", "--reply", self.tag(pid), "--outbox", self.outbox(),
                    "--lane", "mba/ws1/laneA", cwd=elsewhere, env=self.env)
        self.assertEqual(p.returncode, 0, p.stderr)


class TestSessionIdentity(PacketBase):  # 10.1-r1-01
    def env_no_lane(self, **extra):
        env = {k: v for k, v in self.env.items() if not k.startswith("PACKET_")}
        env["PACKET_MACHINE"] = "mba"
        env.update(extra)
        return env

    def newp(self, env, cwd=None):
        return run("packet.py", "new", "--door", "two-way", "--title", "t", "--unit", "u",
                   "--option", "a::x", "--context", "b", cwd=cwd or self.repo, env=env)

    def test_claude_code_session_id_is_read(self):
        p = self.newp(self.env_no_lane(CLAUDE_CODE_SESSION_ID="abcd1234efgh"))
        self.assertIn("/session-abcd1234efgh ", p.stdout)

    def test_subdirectory_resolves_to_the_same_lane(self):
        env = self.env_no_lane(CLAUDE_CODE_SESSION_ID="abcd1234efgh")
        p = self.newp(env)
        pid = next(l.split()[1] for l in p.stdout.splitlines() if l.startswith("PACKET "))
        tag = next(l for l in p.stdout.splitlines() if "reply:" in l).split("reply: ")[1]
        sub = os.path.join(self.repo, "deep", "dir"); os.makedirs(sub)
        p = run("packet.py", "check-reply", "--reply", tag, cwd=sub, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(pid, p.stdout)

    def test_no_session_id_warns_and_check_reply_needs_an_explicit_lane(self):
        env = self.env_no_lane()
        p = self.newp(env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("warning", p.stderr)
        tag = next(l for l in p.stdout.splitlines() if "reply:" in l).split("reply: ")[1]
        p = run("packet.py", "check-reply", "--reply", tag, cwd=self.repo, env=env)
        self.assertEqual(p.returncode, 1)
        self.assertIn("--lane", p.stderr)
        lane = tag[len("[lane "):].split(" ")[0]
        p = run("packet.py", "check-reply", "--reply", tag, "--lane", lane, cwd=self.repo, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
