#!/usr/bin/env python3
# Substrate-agnostic LLM stage runner (scope 146, Phase 2, Task 2.1).
#
# Approach: every agentic stage (root-cause, repro, fix, verify, email) is invoked
# through ONE function, run_agent(stage, ctx), so the orchestrator never embeds a
# provider. Dev-time and the 5a-WITA cloud routine call the identical code path — the
# only thing that changes is who schedules remediate.py. This is the "same gate logic
# for both substrates" decision made real: there is no second, re-expressed form.
#
# Each stage is a versioned prompt file in prompts/<stage>.md with {{placeholders}}.
# The prompt instructs the model to return a single fenced ```json block; run_agent
# renders the template, calls `claude -p`, and parses that block into a dict against a
# per-stage required-key contract (STAGE_CONTRACT). A missing key is a hard failure,
# not a silent {} — an agent stage that returns garbage must fail loud, never pass.
#
# Alarm text is UNTRUSTED (injection surface, Operating Contract #5): it is rendered
# into a fenced <alarm_evidence> region and the prompt tells the model that region is
# data, never instructions. run_agent does not act on the model's text beyond parsing
# the declared JSON contract.
#
# Testability: pass runner=<callable> to inject a fake (see tests/); the default
# runner shells to the claude CLI. No network in --dry-run — the orchestrator simply
# never calls run_agent there.
#
# Stdlib only.

import json
import re
import subprocess
from pathlib import Path

PROMPTS = Path(__file__).parent / "prompts"

# Per-stage required keys. run_agent rejects a result missing any of these.
STAGE_CONTRACT = {
    "root_cause": ["annotation_found", "annotation_says", "root_cause",
                   "fix_available", "fix_class", "recommended_lever", "short_circuit"],
    "repro":      ["repro_available", "repro_cmd", "signal_assertion", "notes"],
    "fix":        ["diff", "files_touched", "explanation"],
    "verify":     ["fails_pre_fix", "passes_post_fix", "signal_tied", "verdict"],
    "email":      ["problem", "solution", "body"],
}

# fix_class values that mean "not a mechanical diff" -> the PIPELINE route must abort
# to PROPOSE. This is the agent-layer honesty gate (the HPACK negative test): even if
# the deterministic classifier routed an incident to PIPELINE, root-cause reading the
# firing rule's annotation can and must flip it back to propose-only.
NON_MECHANICAL_FIX = {"infra", "auth-semantics", "business-semantics",
                      "upstream-unavailable", "live-host-probe", "none"}


class AgentError(RuntimeError):
    pass


def _render(stage, ctx):
    tpl = (PROMPTS / f"{stage}.md").read_text()
    out = tpl
    for k, v in ctx.items():
        out = out.replace("{{" + k + "}}", str(v))
    leftover = re.findall(r"\{\{(\w+)\}\}", out)
    if leftover:
        raise AgentError(f"stage {stage}: unfilled placeholders {leftover}")
    return out


def _extract_json(text):
    # Prefer a fenced ```json block; fall back to the last {...} span.
    m = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    blob = m[-1] if m else None
    if blob is None:
        start = text.rfind("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise AgentError("no JSON object in agent output")
        blob = text[start:end + 1]
    try:
        return json.loads(blob)
    except json.JSONDecodeError as e:
        raise AgentError(f"agent output not valid JSON: {e}")


def _claude_runner(prompt, cwd=None):
    # Headless invocation. Identical in a dev shell and a cloud routine. `cwd` lets a
    # stage (the fix stage) run INSIDE the per-alarm worktree so Claude Code can read
    # the repo and produce a grounded diff rather than guessing from the prompt alone.
    proc = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True, text=True, timeout=900, cwd=cwd,
    )
    if proc.returncode != 0:
        raise AgentError(f"claude -p exited {proc.returncode}: {proc.stderr[:400]}")
    try:
        env = json.loads(proc.stdout)
        return env.get("result", proc.stdout)
    except json.JSONDecodeError:
        return proc.stdout


def run_agent(stage, ctx, runner=None, cwd=None):
    """Render prompts/<stage>.md with ctx, invoke the model, parse + validate JSON.

    runner(prompt)->str lets tests inject a deterministic fake. `cwd` (default runner
    only) runs the model inside a directory — used for the fix stage so it operates in
    the worktree. Returns the parsed stage dict; raises AgentError on any contract
    violation (fail-loud floor).
    """
    if stage not in STAGE_CONTRACT:
        raise AgentError(f"unknown stage {stage!r}")
    prompt = _render(stage, ctx)
    if runner is None:
        raw = _claude_runner(prompt, cwd=cwd)
    else:
        raw = runner(prompt)
    result = _extract_json(raw)
    missing = [k for k in STAGE_CONTRACT[stage] if k not in result]
    if missing:
        raise AgentError(f"stage {stage}: missing keys {missing} in {sorted(result)}")
    return result
