"""Packets from review (scope 10 §4.2, plan 10.2 Task 2.5): one fixture per case.

Approach: reuse test_review.TestReview's throwaway-repo fixture (borrowed method by method, so
none of its tests re-run here), drive review.py record / reframe-record, and read the packet
JSON back from the repo's outbox; each must validate against schemas/packet.schema.json. The
negative cases assert NO packet; the harness-error case asserts the review still succeeds.
"""
import glob
import json
import os
import subprocess
import tempfile
import unittest

from _helpers import load
import test_review as tr


schema_check = load("schema_check.py")
vl = load("verify_lib.py")
packet_emit = load("packet_emit.py")


class TestReviewPackets(unittest.TestCase):
    # borrowed fixture helpers
    setUp, tearDown, mkrepo, rng, answer, record, records, judged = (
        tr.TestReview.setUp, tr.TestReview.tearDown, tr.TestReview.mkrepo, tr.TestReview.rng, tr.TestReview.answer,
        tr.TestReview.record, tr.TestReview.records, tr.TestReview.judged)
    REFRAME = tr.TestReview.REFRAME

    def run_env(self):
        env = dict(self.env, CLAUDE_CODE_SESSION_ID="t-sess")
        env.pop("DECISION_QUEUE_URL", None)
        env.pop("HERDR_AGENT_NAME", None)
        self.env = env

    def packets(self, repo=None):
        out = []
        for f in sorted(glob.glob(os.path.join(repo or self.repo, ".decision-queue", "outbox", "pk-*.json"))):
            if f.endswith(".state.json"):
                continue
            with open(f) as fh:
                out.append(json.load(fh))
        return out

    def prepare(self, rid):
        return tr.run(tr.REVIEW, "reframe-prepare", "--scope", self.scope, "--unit", "9.1", "--review", rid,
                      "--objective", "every fix lands reviewed", "--out-dir", os.path.join(self.tmp.name, "rf"),
                      env=self.env)

    def assertValid(self, doc):
        self.assertEqual(schema_check.validate(doc), [])
        self.assertEqual(doc["door"], "one-way")
        self.assertEqual(doc["type"], "generic")
        self.assertIn("Lineage:", doc["payload"]["body"])
        self.assertEqual(sum(o["recommended"] for o in doc["options"]), 1)

    def test_case1_an_accepted_reframe_that_overturns_a_decision(self):
        self.run_env()
        self.assertEqual(self.record(reframe=self.REFRAME).returncode, 0)
        self.assertEqual(self.packets(), [])
        p = self.judged("9.1-r1", overturns="D7: one writer for the log")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertRegex(p.stdout, r"PACKET pk-rv-9-1-9-1-r1-overturn")
        (doc,) = self.packets()
        self.assertValid(doc)
        self.assertIn("D7: one writer", doc["payload"]["body"])
        self.assertIn("9.1-r1-", doc["payload"]["body"])     # names the finding ids it would replace
        self.judged("9.1-r1", overturns="D7: one writer for the log")   # again: idempotent on id
        self.assertEqual(len(self.packets()), 1)

    def test_case1_an_accepted_reframe_touching_a_one_way_door(self):
        self.run_env()
        self.door_reframe()
        p = self.judged("9.1-r1")   # accepted, overturns nothing: the floor hit alone makes it Alex's
        self.assertHeld(p)
        (doc,) = self.packets()
        self.assertValid(doc)
        self.assertIn("migrations/001.sql", doc["payload"]["body"])

    def door_reframe(self, file="migrations/001.sql", commit=True):
        if commit:
            os.makedirs(os.path.join(self.repo, "migrations"))
            with open(os.path.join(self.repo, "migrations", "001.sql"), "w") as fh:
                fh.write("select 1;\n")
            tr.git(self.repo, "add", "-A")
            tr.git(self.repo, "commit", "-q", "-m", "migration")
        door = {"file": file, "line": 1, "severity": "blocking", "category": "domain",
                "group": "3.5", "text": "bad migration", "fix": "redo"}
        self.assertEqual(self.record(findings=[door], reframe=dict(self.REFRAME, removes=["#1"])).returncode, 0)

    def assertHeld(self, p):
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("do not build until answered", p.stdout)
        self.assertNotIn("build it, then record", p.stdout)
        self.assertNotIn("dispose --reframed", p.stdout)

    def test_case1_the_hold_prints_even_when_the_packet_cannot_be_written(self):
        # review 10.2-r3-01: the door decision is made before any output; an emission failure
        # loses the packet, never the hold — stdout must not say "build it"
        self.run_env()
        self.door_reframe()
        with open(os.path.join(self.repo, ".decision-queue"), "w") as fh:
            fh.write("in the way\n")
        p = self.judged("9.1-r1")
        self.assertHeld(p)
        self.assertIn("touches migrations/001.sql", p.stdout)
        self.assertIn("packet not written", p.stderr)
        self.assertNotIn("PACKET pk-", p.stdout)
        self.assertEqual(self.records("reframe-verdict")[-1]["user_call"], "touches migrations/001.sql")

    def test_case1_an_unclassifiable_door_is_the_users_call(self):
        # no stamped checkout to classify (a review logged before repo_path): one-way, held
        self.run_env()
        self.record(reframe=self.REFRAME)
        with open(self.log) as fh:
            recs = [json.loads(x) for x in fh]
        with open(self.log, "w") as fh:
            for r in recs:
                r.pop("repo_path", None)
                fh.write(json.dumps(r) + "\n")
        p = self.judged("9.1-r1")
        self.assertHeld(p)
        self.assertIn("door unknown", p.stdout)   # door.py raising: TestReframeCall's table

    def test_case1_an_accepted_reframe_on_two_way_code_is_no_packet(self):
        self.run_env()
        self.record(reframe=self.REFRAME)
        self.assertEqual(self.judged("9.1-r1").returncode, 0)
        self.assertEqual(self.packets(), [])

    def test_case2_a_blocking_finding_surviving_two_rounds(self):
        self.run_env()
        for n in (1, 2):
            p = self.record()
            self.assertEqual((p.returncode, self.packets()), (0, []), p.stdout + p.stderr)
        p = self.record()   # round 3, no SHIP, blocking finding, no qualifying reframe
        self.assertIn("round: 3 of", p.stdout)
        self.assertRegex(p.stdout, r"PACKET pk-rv-9-1-9-1-r3-stuck")
        (doc,) = self.packets()
        self.assertValid(doc)
        self.assertIn("swallows the curl failure", doc["payload"]["body"])
        self.assertIn("9.1-r1 → 9.1-r2 → 9.1-r3", doc["payload"]["body"])

    def test_case2_a_blocking_finding_first_raised_in_round_3_survived_nothing(self):
        # review 10.2-r3-04: "survived two rounds" — its file or reopens chain carried a blocking
        # finding in an earlier round; a new defect in round 3 is the inline STOP's, not a packet
        self.run_env()
        self.record()
        self.record()
        new = {"file": "c.py", "line": 1, "severity": "blocking", "category": "silent-failure", "group": "",
               "text": "new defect", "fix": "f"}
        p = self.record(findings=[new])
        self.assertIn("round: 3 of", p.stdout)
        self.assertNotIn("PACKET pk-", p.stdout)
        self.assertEqual(self.packets(), [])
        p = self.record(findings=[dict(new, file="d.py", reopens="9.1-r2-01")])   # chain into a.sh's blocking finding
        self.assertRegex(p.stdout, r"PACKET pk-rv-9-1-9-1-r4-stuck")

    def test_a_packet_lands_in_the_reviewed_worktree_not_the_primary_checkout(self):
        # review 10.2-r3-02: a herdr lane reviews a linked worktree outside ~/Projects; its packet
        # belongs in that tree's outbox, on the lane's branch and head, never the primary checkout's
        self.run_env()
        wt = os.path.join(self.tmp.name, "lane")
        tr.git(self.repo, "worktree", "add", "-q", "-b", "lane", wt)
        with open(os.path.join(wt, "a.sh"), "a") as fh:
            fh.write("curl y || true\n")
        tr.git(wt, "commit", "-q", "-am", "lane work")
        for _ in range(3):
            p = self.record(repo=wt)
            self.assertEqual(p.returncode, 0, p.stderr)
        self.assertRegex(p.stdout, r"PACKET pk-rv-9-1-9-1-r3-stuck")
        self.assertEqual(self.packets(), [])
        (doc,) = self.packets(wt)
        self.assertValid(doc)
        self.assertEqual((doc["branch"], doc["head_sha"]), ("lane", tr.git(wt, "rev-parse", "HEAD")))
        self.assertIn(f"Reviewed range: {self.rng(wt)}", doc["payload"]["body"])

    def test_case2_a_qualifying_reframe_in_the_lineage_means_no_packet(self):
        self.run_env()
        self.record(reframe=self.REFRAME)
        self.judged("9.1-r1")   # accepted, two-way, no overturn: qualifies
        self.record()
        self.record()
        self.assertEqual(self.packets(), [])

    def test_case3_a_rejected_reframe_proposed_again(self):
        self.run_env()
        self.record(reframe=self.REFRAME)
        self.judged("9.1-r1", "reject", reason="it moves the scanner")
        p = self.record(reframe=dict(self.REFRAME, proposal="Replace the per-line scanner with one allowlist table."))
        self.assertRegex(p.stdout, r"PACKET pk-rv-9-1-9-1-r2-repeat")
        (doc,) = self.packets()
        self.assertValid(doc)
        self.assertIn("it moves the scanner", doc["payload"]["body"])
        # review 10.2-r3-03: the hold replaces the judge-it line, and reframe-prepare refuses a re-judge
        self.assertIn("do not re-judge it", p.stdout)
        self.assertNotIn("judge it before fixing", p.stdout)
        q = self.prepare("9.1-r2")
        self.assertEqual(q.returncode, 1, q.stdout + q.stderr)
        self.assertIn("repeats one this lineage rejected", q.stderr)
        self.assertIn("9.1-r1: it moves the scanner", q.stderr)

    def test_case3_a_different_reframe_is_no_packet(self):
        self.run_env()
        self.record(reframe=self.REFRAME)
        self.judged("9.1-r1", "reject", reason="it moves the scanner")
        p = self.record(reframe=dict(self.REFRAME, proposal="drop the retry loop and fail fast on the first error"))
        self.assertEqual(self.packets(), [])
        self.assertIn("judge it before fixing", p.stdout)
        self.assertEqual(self.prepare("9.1-r2").returncode, 0)

    def test_r4_01_an_accept_recorded_on_a_repeat_is_still_held(self):
        # review 10.2-r4-01: reframe-prepare refuses a repeat, but reframe-record could still accept
        # it, print "build it" and back `dispose --by judge` — the hold must survive any later verdict
        self.run_env()
        self.record(reframe=self.REFRAME)
        self.judged("9.1-r1", "reject", reason="it moves the scanner")
        self.record(reframe=dict(self.REFRAME, proposal="Replace the per-line scanner with one allowlist table."))
        p = self.judged("9.1-r2")   # the judge run anyway, accepting
        self.assertHeld(p)
        self.assertIn("repeats one this lineage rejected", p.stdout)
        self.assertIn("9.1-r1: it moves the scanner", self.records("reframe-verdict")[-1]["user_call"])
        rv = load("review/scripts/review.py")
        recs = vl.read_jsonl(self.log)
        why = vl.judge_took(recs, "9.1-r2-01", rv.rounds(recs, "9.1")[1])
        self.assertIn("repeats one this lineage rejected", why)
        d = tr.run(tr.REVIEW, "dispose", "--scope", self.scope, "--unit", "9.1", "--finding", "9.1-r2-01",
                   "--reframed", "one table", "--commit", "HEAD", "--by", "judge", env=self.env)
        self.assertEqual(d.returncode, 1, d.stdout + d.stderr)
        self.assertIn("repeats one this lineage rejected", d.stderr)

    def test_r4_02_an_absolute_finding_anchor_still_hits_the_door(self):
        # review 10.2-r4-02: door.py reports repo-relative paths; a finding anchored by an absolute
        # path into the reviewed checkout must match, and one that cannot be placed there holds
        self.run_env()
        self.door_reframe(file=os.path.join(self.repo, "migrations", "001.sql"))
        p = self.judged("9.1-r1")
        self.assertHeld(p)
        self.assertIn("touches migrations/001.sql", p.stdout)
        self.door_reframe(file="/elsewhere/migrations/001.sql", commit=False)
        p = self.judged("9.1-r2")
        self.assertHeld(p)
        self.assertIn("finding anchor not in the reviewed checkout", p.stdout)

    def test_r4_03_a_superseded_accept_never_qualifies_for_case_2(self):
        # review 10.2-r4-03: case 2 read every historical accept; an accept re-recorded as rejected
        # suppressed the stuck packet for good. Only each reframe's latest verdict counts.
        self.run_env()
        self.record(reframe=self.REFRAME)
        self.judged("9.1-r1")                      # accepted, the judge's...
        self.judged("9.1-r1", "reject", reason="second look: it drops the audit")   # ...then superseded
        self.record()
        p = self.record()
        self.assertRegex(p.stdout, r"PACKET pk-rv-9-1-9-1-r3-stuck")

    def test_an_emission_failure_never_stops_the_review(self):
        # the outbox cannot be created (`.decision-queue` is a file): packet.py fails, the review
        # still succeeds, warns, and the inline question stands
        self.run_env()
        with open(os.path.join(self.repo, ".decision-queue"), "w") as fh:
            fh.write("in the way\n")
        self.record()
        self.record()
        p = self.record()   # round 3: the stuck case fires
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("packet not written", p.stderr)
        self.assertNotIn("Traceback (most recent call last):\n", p.stderr)
        self.assertNotIn("PACKET pk-", p.stdout)
        self.assertIsNone(packet_emit.emit(os.path.join(self.tmp.name, "nowhere"), "9.1", "t", ["a"], "b"))


class TestReframeCall(unittest.TestCase):
    """verify_lib.reframe_call, the one owner of "is this reframe the user's call?" (review 10.2-r4),
    table-driven over in-memory logs: each row is (name, extra records after r1's reframe and r2's
    repeat proposal, review asked about, classify_at, door.py's answer or an exception, call, kind,
    a fragment of why)."""
    LIN = {"9.1-r1": ("9.1-r1", 1), "9.1-r2": ("9.1-r1", 2), "9.1-r9": ("9.1-r9", 1)}
    BASE = [{"record": "finding", "review_id": "9.1-r1", "finding_id": "9.1-r1-01", "file": "migrations/001.sql"},
            {"record": "finding", "review_id": "9.1-r9", "finding_id": "9.1-r9-01", "file": "/abs/out/x.sql"},
            {"record": "reframe", "review_id": "9.1-r1", "proposal": "one allowlist table", "removes": ["9.1-r1-01"]},
            {"record": "reframe", "review_id": "9.1-r2", "proposal": "One allowlist table!", "removes": ["9.1-r1-01"]},
            {"record": "reframe", "review_id": "9.1-r9", "proposal": "x", "removes": ["9.1-r9-01"]}]

    @staticmethod
    def v(rid, verdict="accepted", **kw):
        return dict({"record": "reframe-verdict", "review_id": rid, "verdict": verdict, "overturns": None,
                     "reason": f"{verdict} reason"}, **kw)

    def test_table(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        tmp = os.path.realpath(td.name)
        hit = {"door": "one-way", "paths": [{"path": "migrations/001.sql"}], "reason": "1 floor path(s) touched"}
        two = {"door": "two-way", "paths": [], "reason": "no floor path touched"}
        closed = {"door": "one-way", "paths": [], "reason": "fail-closed: bad range"}
        here = (tmp, "a..b")
        absolute = [dict(self.BASE[0], file=os.path.join(tmp, "migrations", "001.sql"))] + self.BASE[1:]
        rows = [
            ("no verdict yet", [], "9.1-r1", None, two, "unjudged", "unjudged", "no judge verdict"),
            ("no reframe", [], "9.1-r5", None, two, "user", "unknown", "no reframe record"),
            ("accepted, stamped two-way", [self.v("9.1-r1", user_call=None)], "9.1-r1", None, two,
             "judge", "accepted", "accepted reason"),
            ("accepted, stamped door", [self.v("9.1-r1", user_call="touches m")], "9.1-r1", None, two,
             "user", "door", "touches m"),
            ("accepted, never stamped", [self.v("9.1-r1")], "9.1-r1", None, two, "user", "door",
             "no door classification"),
            ("overturns", [self.v("9.1-r1", overturns="D7", user_call=None)], "9.1-r1", None, two,
             "user", "overturn", "D7"),
            ("rejected", [self.v("9.1-r1", "rejected")], "9.1-r1", None, two, "rejected", "rejected", "rejected"),
            ("not judged", [self.v("9.1-r1", "not-judged")], "9.1-r1", None, two, "rejected", "not-judged", ""),
            ("unknown verdict value", [self.v("9.1-r1", "maybe")], "9.1-r1", None, two, "user", "unknown", "maybe"),
            # 10.2-r4-03: the latest verdict decides, both ways
            ("accept superseded by reject", [self.v("9.1-r1", user_call=None), self.v("9.1-r1", "rejected")],
             "9.1-r1", None, two, "rejected", "rejected", ""),
            ("reject superseded by accept", [self.v("9.1-r9", "rejected"), self.v("9.1-r9", user_call=None)],
             "9.1-r9", None, two, "judge", "accepted", ""),
            # 10.2-r4-01: a repeat of a rejection is held, whatever its own verdict says
            ("repeat, unjudged", [self.v("9.1-r1", "rejected")], "9.1-r2", None, two, "user", "repeat",
             "9.1-r1: rejected reason"),
            ("repeat, accepted and stamped clean", [self.v("9.1-r1", "rejected"), self.v("9.1-r2", user_call=None)],
             "9.1-r2", None, two, "user", "repeat", "repeats one this lineage rejected"),
            ("rejection superseded is no repeat", [self.v("9.1-r1", "rejected"), self.v("9.1-r1", user_call=None)],
             "9.1-r2", None, two, "unjudged", "unjudged", ""),
            # 10.2-r5-01: only an EARLIER rejection is a repeat; a later similar one leaves r1's accept alone
            ("later similar rejection leaves an earlier accept", [self.v("9.1-r1", user_call=None),
             self.v("9.1-r2", "rejected")], "9.1-r1", None, two, "judge", "accepted", "accepted reason"),
            ("another lineage's rejection is no repeat", [self.v("9.1-r9", "rejected")], "9.1-r2", None, two,
             "unjudged", "unjudged", ""),
            # classify_at: the door is decided in the reviewed checkout (10.2-r4-02)
            ("door hit, relative anchor", [self.v("9.1-r1")], "9.1-r1", here, hit, "user", "door",
             "touches migrations/001.sql"),
            ("door hit, absolute anchor", "absolute", "9.1-r1", here, hit, "user", "door",
             "touches migrations/001.sql"),
            ("two-way", [self.v("9.1-r1")], "9.1-r1", here, two, "judge", "accepted", ""),
            ("anchor outside the checkout", [self.v("9.1-r9")], "9.1-r9", here, two, "user", "door",
             "finding anchor not in the reviewed checkout"),
            ("door.py failed closed", [self.v("9.1-r1")], "9.1-r1", here, closed, "user", "door", "fail-closed"),
            ("no checkout", [self.v("9.1-r1")], "9.1-r1", (None, "a..b"), two, "user", "door", "door unknown"),
            ("no range", [self.v("9.1-r1")], "9.1-r1", (tmp, None), two, "user", "door", "door unknown"),
            ("door.py raises", [self.v("9.1-r1")], "9.1-r1", here, RuntimeError("git exploded"), "user", "unknown",
             "could not decide (git exploded)"),
        ]
        orig = vl.door_classify
        self.addCleanup(setattr, vl, "door_classify", orig)
        for name, extra, rid, at, door, call, kind, why in rows:
            with self.subTest(name):
                def fake(*_, door=door):
                    if isinstance(door, Exception):
                        raise door
                    return door
                vl.door_classify = fake
                recs = absolute + [self.v("9.1-r1")] if extra == "absolute" else self.BASE + extra
                got = vl.reframe_call(recs, rid, self.LIN, classify_at=at)
                self.assertEqual(got[:2], (call, kind), got)
                self.assertIn(why, got[2])
                self.assertIn(got[0], vl.REFRAME_CALLS)

    def test_any_failure_is_the_users_call(self):
        orig = vl.repeated_reframe
        self.addCleanup(setattr, vl, "repeated_reframe", orig)

        def boom(*_):
            raise RuntimeError("log unreadable")
        vl.repeated_reframe = boom
        self.assertEqual(vl.reframe_call(self.BASE, "9.1-r2", self.LIN),
                         ("user", "unknown", "could not decide (log unreadable): treated as the user's call"))
        vl.repeated_reframe = orig
        self.assertEqual(vl.reframe_call(None, "9.1-r1", self.LIN)[:2], ("user", "unknown"))


if __name__ == "__main__":
    unittest.main()
