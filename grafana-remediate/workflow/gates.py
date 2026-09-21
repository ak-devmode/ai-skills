#!/usr/bin/env python3
# The logic gates (scope 146, Phase 2, Tasks 2.1 / 2.3 / 2.3b).
#
# Approach: each gate is a discrete, independently-testable function with an explicit
# fail-closed default. The safety properties the scope demands are STRUCTURAL here, not
# a prompt's good intentions:
#   - phi_gate: nothing egresses if PHI/tenant data is present (delegates to the
#     deterministic phi_scrub — detection is not an LLM's job).
#   - repro_gate: fail-closed. No runnable repro tied to the ORIGINAL signal => the
#     defect can never reach a PR. Returns available=False and the caller degrades to
#     a proposal email. This is where "repro-or-nothing" lives.
#   - verify_gate: the independent acceptance oracle. The fix is accepted only if the
#     repro reproduced the original signal pre-fix AND stopped reproducing it post-fix,
#     judged against the alarm's own signal — guarding circular confirmation.
#
# Execution (running the repro command, applying the diff) is delegated to worktree.py
# so these functions stay pure decision logic that tests can drive with fakes.
#
# Stdlib only.

import phi_scrub
from agent import run_agent, NON_MECHANICAL_FIX


def phi_gate(payload):
    """Egress hard stop. (ok, findings, redacted). ok True only when nothing sensitive.
    Caller policy: ok False => HOLD, surface only the redacted form to a human."""
    return phi_scrub.gate(payload)


def root_cause_allows_pipeline(rc_result):
    """The agent-layer honesty gate (HPACK negative test). Even if the deterministic
    classifier routed to PIPELINE, root-cause reading the firing rule's annotation can
    flip it to propose-only. True only for a genuine mechanical-diff with a fix."""
    if rc_result.get("short_circuit"):
        return False
    if not rc_result.get("fix_available"):
        return False
    return rc_result.get("fix_class") == "mechanical-diff" \
        and rc_result.get("fix_class") not in NON_MECHANICAL_FIX


def repro_gate(incident, ctx, worktree, runner=None):
    """Ask the agent for a repro tied to the original signal, then RUN it pre-fix.
    Fail-closed: any of {agent says unavailable, command errors out, does not exercise
    the signal} => available=False (degrade to proposal, never a PR)."""
    r = run_agent("repro", ctx, runner=runner)
    out = {"available": False, "repro_cmd": r.get("repro_cmd", ""),
           "signal_assertion": r.get("signal_assertion", ""),
           "pre_output": "", "pre_rc": None, "notes": r.get("notes", "")}
    if not r.get("repro_available"):
        out["notes"] = f"agent: repro not available. {out['notes']}"
        return out
    if not out["repro_cmd"].strip():
        out["notes"] = "agent claimed repro_available but gave no command"
        return out
    rc, output = worktree.run(out["repro_cmd"])
    out["pre_rc"], out["pre_output"] = rc, output
    # A repro must FAIL pre-fix (reproduce the defect). rc==0 pre-fix means it did not
    # reproduce the signal -> not a usable repro -> fail-closed.
    out["available"] = (rc != 0)
    if rc == 0:
        out["notes"] = "repro command passed pre-fix -> did not reproduce the signal; fail-closed"
    return out


def verify_gate(repro, post_rc, post_output, ctx, runner=None):
    """Independent acceptance oracle. The fix is accepted only on a pass verdict tied to
    the original signal. post_rc/post_output are from re-running repro['repro_cmd']
    AFTER the diff was applied in the worktree."""
    v = run_agent("verify", {**ctx,
                             "signal_assertion": repro["signal_assertion"],
                             "pre_output": repro["pre_output"],
                             "post_output": post_output}, runner=runner)
    mechanical_pass = (repro["pre_rc"] != 0 and post_rc == 0)
    accepted = bool(mechanical_pass
                    and v.get("fails_pre_fix") and v.get("passes_post_fix")
                    and v.get("signal_tied") and v.get("verdict") == "pass")
    return {"accepted": accepted, "verdict": v.get("verdict"),
            "mechanical_pass": mechanical_pass, "detail": v}
