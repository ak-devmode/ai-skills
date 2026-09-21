#!/usr/bin/env python3
# Offline tests for the alarm-remediation workflow (scope 146, Phase 2).
#
# Approach: table-driven where the shape allows, fully offline. Agent stages are driven
# by a fake runner keyed off each prompt's unique opening line, so the whole state
# machine — including the PIPELINE code-defect path — is exercised without a token, a
# real worktree, or a single LLM call. The two load-bearing safety properties get their
# own explicit tests: the HPACK honesty gate (a PIPELINE incident whose root-cause
# annotation is "upstream-unavailable" MUST degrade to a proposal, never a PR) and the
# fail-closed repro gate.

import json
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
WF = HERE.parent
sys.path.insert(0, str(WF))

import agent
import dedup
import gates
import email_ses
import heartbeat
import remediate
import worktree as wt


# ---- fake agent runner: dispatch on each prompt's unique opening phrase ----
def make_runner(root_cause=None, repro=None, fix=None, verify=None, email=None):
    defaults = {
        "root_cause": {"annotation_found": True, "annotation_says": "mechanical",
                       "root_cause": "nil-deref in handler", "fix_available": True,
                       "fix_class": "mechanical-diff", "recommended_lever": "guard the nil",
                       "short_circuit": False},
        "repro": {"repro_available": True, "repro_cmd": "go test ./... -run Panic",
                  "signal_assertion": "panic string absent from output", "notes": "ok"},
        "fix": {"diff": "--- a/x.go\n+++ b/x.go\n@@\n-bad\n+good\n",
                "files_touched": ["x.go"], "explanation": "guard nil"},
        "verify": {"fails_pre_fix": True, "passes_post_fix": True,
                   "signal_tied": True, "verdict": "pass"},
        "email": {"problem": "Gateway panics on nil header.",
                  "solution": "Guard the nil deref in the handler.",
                  "body": "Root cause: ... Recommended: ..."},
    }
    over = {"root_cause": root_cause, "repro": repro, "fix": fix,
            "verify": verify, "email": email}
    table = {k: (over[k] if over[k] is not None else defaults[k]) for k in defaults}
    markers = {"You are the root-cause stage": "root_cause",
               "You are the repro stage": "repro",
               "You are the fix stage": "fix",
               "You are the verify stage": "verify",
               "You are the email-composition stage": "email"}

    def runner(prompt):
        for marker, stage in markers.items():
            if marker in prompt:
                return "```json\n" + json.dumps(table[stage]) + "\n```"
        raise AssertionError("prompt matched no known stage")
    return runner


# ---- fake worktree: no git, records apply/run behaviour ----
class FakeTree:
    def __init__(self, pre_rc=1, post_rc=0, apply_ok=True):
        self.pre_rc, self.post_rc, self.apply_ok = pre_rc, post_rc, apply_ok
        self.keep = False
        self.path = Path("/tmp/fake-wt-does-not-exist")
        self._applied = False
        self.pruned = False

    def run(self, cmd, timeout=900):
        return (self.post_rc if self._applied else self.pre_rc,
                "panic: nil" if (not self._applied) else "ok")

    def apply_diff(self, diff):
        self._applied = self.apply_ok
        return self.apply_ok, "" if self.apply_ok else "patch failed"

    def prune(self):
        self.pruned = True


def gw_incident(route="PIPELINE"):
    return {"alertName": "Gateway restart storm", "firings": 12,
            "labels": {"env": "dev", "tier": "page", "instance": "gw-1"},
            "class": "code-defect", "route": route, "why": "crash", "repo": "wellmed-gateway-go",
            "annotation": "grpc-go HPACK panic"}


class TestAgentContract(unittest.TestCase):
    def test_missing_key_fails_loud(self):
        bad = lambda p: "```json\n{}\n```"
        with self.assertRaises(agent.AgentError):
            agent.run_agent("root_cause", _ctx(), runner=bad)

    def test_unfilled_placeholder_fails_loud(self):
        with self.assertRaises(agent.AgentError):
            agent.run_agent("root_cause", {"alertName": "x"}, runner=make_runner())

    def test_valid_roundtrip(self):
        r = agent.run_agent("root_cause", _ctx(), runner=make_runner())
        self.assertEqual(r["fix_class"], "mechanical-diff")


class TestHonestyGate(unittest.TestCase):
    """HPACK negative test: root-cause annotation must be able to abort PIPELINE."""
    CASES = [
        ({"fix_class": "mechanical-diff", "fix_available": True, "short_circuit": False}, True),
        ({"fix_class": "upstream-unavailable", "fix_available": False, "short_circuit": True}, False),
        ({"fix_class": "infra", "fix_available": False, "short_circuit": True}, False),
        ({"fix_class": "auth-semantics", "fix_available": False, "short_circuit": True}, False),
        ({"fix_class": "mechanical-diff", "fix_available": False, "short_circuit": False}, False),
    ]

    def test_gate(self):
        for partial, expect in self.CASES:
            rc = {"annotation_found": True, "annotation_says": "x", "root_cause": "y",
                  "recommended_lever": "z", **partial}
            self.assertEqual(gates.root_cause_allows_pipeline(rc), expect, partial)

    def test_hpack_pipeline_degrades_to_propose(self):
        runner = make_runner(root_cause={
            "annotation_found": True, "annotation_says": "unfixable upstream",
            "root_cause": "x/net hpack bug golang/go#72940", "fix_available": False,
            "fix_class": "upstream-unavailable", "recommended_lever": "HeaderTableSize(0)+nginx L4",
            "short_circuit": True})
        out, kept = remediate._pipeline(gw_incident(), runner=runner, send=False,
                                        tree_factory=lambda *a: self.fail("worktree created on abort!"))
        self.assertTrue(out["route"].startswith("PROPOSE(degraded:root-cause)"))
        self.assertFalse(kept)


class TestReproGateFailClosed(unittest.TestCase):
    def test_agent_says_no_repro(self):
        runner = make_runner(repro={"repro_available": False, "repro_cmd": "",
                                    "signal_assertion": "", "notes": "cannot build in sandbox"})
        out, kept = remediate._pipeline(gw_incident(), runner=runner,
                                        tree_factory=lambda *a: FakeTree())
        self.assertEqual(out["route"], "PROPOSE(degraded:no-repro)")

    def test_repro_passes_pre_fix_is_rejected(self):
        # rc==0 pre-fix means the repro did not reproduce the signal -> unusable.
        tree = FakeTree(pre_rc=0)
        runner = make_runner()
        out, kept = remediate._pipeline(gw_incident(), runner=runner,
                                        tree_factory=lambda *a: tree)
        self.assertEqual(out["route"], "PROPOSE(degraded:no-repro)")


class TestVerifyOracle(unittest.TestCase):
    def test_pass_opens_pr(self):
        out, kept = remediate._pipeline(gw_incident(), runner=make_runner(),
                                        tree_factory=lambda *a: FakeTree(pre_rc=1, post_rc=0))
        self.assertEqual(out["route"], "PR")
        self.assertFalse(out["pr"]["opened"])  # Phase 2: never actually opens

    def test_mechanical_fail_post_rc_nonzero_keeps_worktree(self):
        tree = FakeTree(pre_rc=1, post_rc=1)  # fix didn't kill the signal
        out, kept = remediate._pipeline(gw_incident(), runner=make_runner(),
                                        tree_factory=lambda *a: tree)
        self.assertEqual(out["route"], "PROPOSE(degraded:verify-failed)")
        self.assertTrue(kept)
        self.assertTrue(tree.keep)

    def test_agent_says_untied_signal_fails(self):
        # Mechanical rc looks fine but the oracle says the signal wasn't tied.
        runner = make_runner(verify={"fails_pre_fix": True, "passes_post_fix": True,
                                     "signal_tied": False, "verdict": "pass"})
        out, kept = remediate._pipeline(gw_incident(), runner=runner,
                                        tree_factory=lambda *a: FakeTree(pre_rc=1, post_rc=0))
        self.assertEqual(out["route"], "PROPOSE(degraded:verify-failed)")


class TestDedup(unittest.TestCase):
    def test_signature_stable_across_firings(self):
        a, b = gw_incident(), gw_incident()
        b["firings"] = 99
        self.assertEqual(dedup.signature_key(a), dedup.signature_key(b))

    def test_reopen_rules(self):
        prior = {"severity": "warning", "deploy_sha": "abc", "firings": 2}
        self.assertEqual(dedup.should_reopen({"labels": {"severity": "critical"}, "firings": 2}, prior)[0], True)
        self.assertEqual(dedup.should_reopen({"labels": {"deploy_sha": "def"}, "firings": 2}, prior)[0], True)
        self.assertEqual(dedup.should_reopen({"labels": {}, "firings": 10}, prior)[0], True)
        self.assertEqual(dedup.should_reopen({"labels": {"severity": "warning", "deploy_sha": "abc"}, "firings": 2}, prior)[0], False)

    def test_handled_store_dedups_then_reopens(self):
        store = {}
        inc = gw_incident()
        dedup.record_handled(inc, store, "PROPOSE")
        self.assertTrue(dedup.is_duplicate(inc, store, gh_enabled=False)[0])
        worse = gw_incident()
        worse["firings"] = inc["firings"] + 5
        self.assertFalse(dedup.is_duplicate(worse, store, gh_enabled=False)[0])


class TestEmailES(unittest.TestCase):
    def test_two_sentence_lead_order(self):
        subject, body = email_ses.compose(
            gw_incident("PROPOSE"),
            agent_email={"problem": "It panics.", "solution": "Guard the nil.",
                         "body": "detail here"})
        self.assertTrue(body.startswith("It panics. Guard the nil."))
        self.assertIn("[alarm-resolver]", subject)

    def test_pr_summary_reused_verbatim(self):
        subject, body = email_ses.compose(gw_incident("PIPELINE"), pr_summary="## PR SUMMARY BODY")
        self.assertEqual(body, "## PR SUMMARY BODY")

    def test_redaction_footer(self):
        _, body = email_ses.compose(gw_incident(), pr_summary="x", redacted_count=3)
        self.assertIn("redacted 3 sensitive", body)

    def test_send_refuses_phi(self):
        with self.assertRaises(RuntimeError):
            email_ses.send("subj", "patient NIK 3204012509900001 leaked", dry_run=True)

    def test_send_dry_run_ok(self):
        self.assertFalse(email_ses.send("subj", "all clean", dry_run=True)["sent"])


class TestPHIEgressInPipeline(unittest.TestCase):
    def test_proposal_with_phi_is_held_and_redacted(self):
        runner = make_runner(
            root_cause={"annotation_found": True, "annotation_says": "leak",
                        "root_cause": "err for clinic_5 patient", "fix_available": False,
                        "fix_class": "infra", "recommended_lever": "x", "short_circuit": True},
            email={"problem": "Error on clinic_5.", "solution": "Do x.",
                   "body": "patient NIK 3204012509900001 involved"})
        out, _ = remediate._pipeline(gw_incident(), runner=runner, send=False)
        self.assertTrue(out.get("phi_held"))
        self.assertIn("nik", out.get("redacted", []))


class TestWorktreeLifecycle(unittest.TestCase):
    def test_age_sweep_reaps_old(self):
        import tempfile, os
        root = Path(tempfile.mkdtemp())
        old = root / "old-wt"; old.mkdir()
        new = root / "new-wt"; new.mkdir()
        os.utime(old, (time.time() - 999999, time.time() - 999999))
        orig = wt.SCRATCH
        try:
            wt.SCRATCH = root
            reaped = wt.age_sweep()
            self.assertIn("old-wt", reaped)
            self.assertNotIn("new-wt", reaped)
        finally:
            wt.SCRATCH = orig


class TestDryRunCalibration(unittest.TestCase):
    """The Task 2.5 read-only pass must reproduce the signed-off routing with NO LLM."""
    def test_september_corpus_routes_no_egress(self):
        corpus = WF.parent / "september-alarms.json"
        if not corpus.exists():
            self.skipTest("september corpus not present")
        incidents = remediate.load_incidents(str(corpus))
        # No PIPELINE survives (today's corpus has 0 auto-PR-eligible defects; HPACK is
        # deduped to PROPOSE by known_issues). This is the Phase-1 key conclusion.
        results, counts = remediate.process(incidents, dry_run=True, gh_enabled=False)
        routes = {r["route"] for r in results}
        self.assertNotIn("PIPELINE", routes, f"unexpected PIPELINE in dry-run: {routes}")
        self.assertEqual(counts["emails"] + counts["prs"] + counts["held"], 0,
                         "dry-run must not egress")


def _ctx():
    return {"alertName": "x", "class": "c", "route": "PIPELINE", "env": "dev",
            "tier": "page", "firings": 1, "repo": "wellmed-gateway-go",
            "annotation": "a", "evidence": "{}"}


if __name__ == "__main__":
    unittest.main(verbosity=2)
