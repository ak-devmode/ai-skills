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
import unittest

from _helpers import load
import test_review as tr


schema_check = load("schema_check.py")
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

    def door_reframe(self):
        os.makedirs(os.path.join(self.repo, "migrations"))
        with open(os.path.join(self.repo, "migrations", "001.sql"), "w") as fh:
            fh.write("select 1;\n")
        tr.git(self.repo, "add", "-A")
        tr.git(self.repo, "commit", "-q", "-m", "migration")
        door = {"file": "migrations/001.sql", "line": 1, "severity": "blocking", "category": "domain",
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
        self.assertIn("door unknown", p.stdout)
        # door.py raising is one-way too, never "build it"
        rv = load("review/scripts/review.py")

        def boom(*_):
            raise RuntimeError("git exploded")
        rv.reframe_door = boom
        self.assertIn("door.py failed: git exploded", rv.user_call([], "9.1", "9.1-r1", {"overturns": None}))

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

    def test_case3_a_repeat_check_that_fails_holds(self):
        rv = load("review/scripts/review.py")

        def boom(*_):
            raise RuntimeError("log unreadable")
        rv.repeated_reframe = boom
        self.assertEqual(rv.repeat_of([], "9.1", "9.1-r2"),
                         (None, "could not check for an earlier rejection (log unreadable)"))

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


if __name__ == "__main__":
    unittest.main()
