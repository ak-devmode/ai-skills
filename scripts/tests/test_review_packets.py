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
        os.makedirs(os.path.join(self.repo, "migrations"))
        with open(os.path.join(self.repo, "migrations", "001.sql"), "w") as fh:
            fh.write("select 1;\n")
        tr.git(self.repo, "add", "-A")
        tr.git(self.repo, "commit", "-q", "-m", "migration")
        door = {"file": "migrations/001.sql", "line": 1, "severity": "blocking", "category": "domain",
                "group": "3.5", "text": "bad migration", "fix": "redo"}
        self.assertEqual(self.record(findings=[door], reframe=dict(self.REFRAME, removes=["#1"])).returncode, 0)
        p = self.judged("9.1-r1")   # accepted, overturns nothing: the floor hit alone makes it Alex's
        self.assertEqual(p.returncode, 0, p.stderr)
        (doc,) = self.packets()
        self.assertValid(doc)
        self.assertIn("migrations/001.sql", doc["payload"]["body"])

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

    def test_case3_a_different_reframe_is_no_packet(self):
        self.run_env()
        self.record(reframe=self.REFRAME)
        self.judged("9.1-r1", "reject", reason="it moves the scanner")
        self.record(reframe=dict(self.REFRAME, proposal="drop the retry loop and fail fast on the first error"))
        self.assertEqual(self.packets(), [])

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
