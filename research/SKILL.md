---
name: research
description: >-
  Cost-tuned deep research. Runs the deep-research-lean workflow (Scope→Search→
  Fetch→Verify→Synthesize) with each phase on a right-sized model — grunt work on
  Haiku/Sonnet, synthesis on Opus (~70% cheaper than the built-in deep-research,
  which runs every subagent on the session model). Use when asked to "research",
  "deep research", "research report", "deeply research X", or "/research <topic>".
allowed-tools: Workflow, AskUserQuestion
---

# Deep research (cost-tuned)

The user wants a multi-source, fact-checked research report. Do NOT answer from
memory and do NOT fan out a bare Agent swarm — route through the tuned workflow.

## 1. Scope before spending

1. Restate the research question in one sentence as you understood it.
2. If it is underspecified (missing budget / region / timeframe / use-case /
   comparison set), ask 2–3 clarifying questions **inline as plain text** (Alex
   prefers text over the structured selector). Fold the answers into the question.
3. Deep research fans out across many agents and web calls and costs real money —
   **confirm the scoped question with the user before running.** One line: the
   final scoped question + "run it?".

## 2. Run the tuned workflow

Once confirmed, invoke:

```
Workflow({
  name: "deep-research-lean",
  args: "<the final scoped question, with clarifications woven in>"
})
```

Invoke **by `name`**, not `scriptPath`. The tool does not expand `~`, and it
rejects an absolute `scriptPath` outside the working directory unless that file
was read first this session. The name resolves via the
`~/.claude/workflows/deep-research-lean.js` symlink.

The workflow runs in the background and returns a task notification when done —
do not re-invoke or poll it; relay the report when it lands. It returns
**structured output only and writes no file** — if the user wants the report on
disk, write it yourself from the result, and keep file-path/format instructions
out of `args` (they reach only the agents, which can't honour them).

## 3. Architecture (for reference)

`Scope (Sonnet) → Search (Haiku, 5 angles) → Fetch (Sonnet, ≤15 sources) →
Verify (Haiku, 3-vote adversarial, 2/3 refutes to kill a claim) →
Synthesize (Opus, merge dupes, rank by confidence, cite sources)`.

## 4. Tuning the cost/quality dial

Edit the `MODEL_*` constants at the top of
`~/.claude/workflows/deep-research-lean.js`:
`MODEL_SCOPE`, `MODEL_SEARCH`, `MODEL_FETCH`, `MODEL_VERIFY`, `MODEL_SYNTH`
(plus `VOTES_PER_CLAIM`, `MAX_FETCH`, `MAX_VERIFY_CLAIMS`). Only Synthesize
genuinely benefits from Opus; push the rest cheaper for faster/cheaper runs.
