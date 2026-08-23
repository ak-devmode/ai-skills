---
name: concurrency
version: 0.1.0
description: |
  Partition a scope's plan surface into non-overlapping, dependency-ordered
  units and dispatch each to a visible, named herdr pane running the right
  model seat (Opus / codex / GLM), then supervise by agent state. The single
  controlled home for no-human-in-the-loop agent trains. Use when asked to
  "/concurrency", "dispatch this scope concurrently", "run these phases in
  parallel", "start an agent train", or "herd this scope". Dry-run is the
  default — nothing is dispatched without --dispatch. Do NOT use for
  single-task work or as a substitute for /plan; this skill consumes /scope
  and /plan output, it does not replace them.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Agent
---

# /concurrency — herdr-backed multi-agent dispatch

Design record: `plans/concurrency/scope.md` (ai-skills). Status lives in
`plans/concurrency/progress.md`, never here and never in scope.md.

## 1. Operating tiers

- **Active tier** — the invoking session (one of Alex's 2–4 primaries)
  dispatches 1–N small panes it supervises. Default tier.
- **Overnight tier** (`--overnight`, phase 6.4 — NOT YET IMPLEMENTED; refuse
  with that statement) — a named persistent session (`herdr --session
  overnight`) running one long task in auto mode.

## 2. Preconditions — check ALL before anything else

- [ ] herdr server answers: `herdr workspace list` exits 0. If not: report and
      stop — never `brew services start` on Alex's behalf mid-skill.
- [ ] Running inside a herdr pane: `test "${HERDR_ENV:-}" = 1`. If outside,
      say so and ask before proceeding — the socket works from outside, but
      pane-context is absent and herdr's own guidance is to control only from
      within.
- [ ] Load herdr's control-surface instructions: run `herdr --skill` and
      follow it for ALL pane/workspace/worktree mechanics. This skill defines
      WHAT to dispatch; `herdr --skill` defines HOW to drive herdr.
- [ ] Target repo identified, trunk known (`develop` for wellmed/pmg, `main`
      otherwise), `git fetch` run. Never dispatch from a dirty primary tree
      without surfacing it first.
- [ ] For the GLM seat only: `OPENROUTER_API_KEY` present in the environment.
      Absent ⇒ GLM rows in the plan are marked `seat-unavailable`, never
      silently rerouted.

## 3. Model routing table

THE single source of routing truth. New seats are new rows. Verified on this
machine 2026-08-23.

| Seat | Launch inside pane | Verified | Route to it |
|------|-------------------|----------|-------------|
| `opus` | `claude` (global default model: opus) | Opus 4.8 default | judgment, design-adjacent implementation, anything touching prod-shaped decisions |
| `codex` | `codex -m gpt-5.6-sol` (headless: `codex exec -m gpt-5.6-sol`) | codex-cli ≥0.149.0, id live-probed OK | secondary implementation, independent review passes |
| `glm` | `claude --model z-ai/glm-5.2` with per-pane env `ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1`, `ANTHROPIC_API_KEY=$OPENROUTER_API_KEY` | id confirmed on OpenRouter (1M ctx; `:free` variant exists for trials) | mechanical/bulk: migrations-by-pattern, test scaffolds, sweeps |

Env-leak rule: provider overrides are injected ONLY via herdr `--env` at
workspace/worktree creation for that seat's pane. Never `export` them in the
invoking session; never write them to any settings file. Provider swap
(OpenRouter → Z.ai coding plan) edits this table's one row and nothing else.

## 4. Partition procedure

Input: a scope folder (plan stubs + PLANS-INDEX row) or an explicit task list.

**4.1 Classify every task** into exactly one of:
- `HUMAN-GATED` — needs an action only Alex can take (credential/sandbox
  renewal, prod decision, sign-off, Gate A "human" language in the stub).
  Surfaced in the plan; NEVER dispatched, never attempted.
- `BLOCKED` — depends on an incomplete task (see 4.2 edges).
- `READY` — all edges satisfied, no human gate.

**4.2 Build the dependency DAG.** Edges come from, in order of authority:
1. Explicit dependency/blocked/precondition language in the stubs.
2. File/service touch-set overlap: derive each task's expected touch-set
   (repos, dirs, tables, proto files) from its stub; any overlap ⇒ same
   partition (serialized), never parallel branches over shared files.
3. Domain ordering rules (always edges, even if the stub is silent):
   emitter before consumer; schema leads code; gRPC implementer leads caller.
4. **Uncertain ⇒ serialize.** Refuse-to-parallelize is the default verdict;
   a pair joins the parallel set only when disjointness is SHOWN.

**4.3 The dispatch set** is the DAG's ready frontier, capped (§6). Everything
else is listed with the edge or gate that excludes it — exclusions are part
of the output, not silent.

## 5. Dry-run output (the DEFAULT — no flag dispatches anything)

Print exactly this shape and stop:

```
CONCURRENCY PLAN — <scope> @ <repo>          [DRY RUN — nothing dispatched]
ready frontier (cap N):
  <task>  seat=<seat>  branch=concurrency/<scope>-<task>
          worktree=<path>  freeze=<paths>
          pane label: <scope>#<task>@<seat>
excluded:
  <task>  HUMAN-GATED: <what Alex must do>
  <task>  BLOCKED by <task>: <edge reason>
  <task>  SERIALIZED with <task>: <shared touch-set>
Run again with --dispatch to execute.
```

## 6. --dispatch (phase 6.2+; claude-only and pane cap 2 until the 6.3 gate)

Per partition, in this order (syntax authority: `herdr --skill`):
1. `herdr worktree create --cwd <repo> --base origin/<trunk>
   --branch concurrency/<scope>-<task> --label "<scope>#<task>@<seat>"
   [--env KEY=VAL ...]` — env vars ONLY for the glm seat.
2. Launch the seat's command (table §3) in the created pane via `pane run`.
3. First instruction in every dispatched prompt: run `/freeze <paths>` for its
   partition, then the task brief, then: commit locally when done; NEVER push,
   NEVER open a PR, NEVER merge; end by printing `PARTITION-DONE <task>`.
4. Append one JSON line to `~/.config/herdr/concurrency-log.jsonl`:
   `{ts, scope, task, seat, branch, worktree, pane_id, status:"dispatched"}`.

## 7. Supervision

- Wait on state, not scrollback: `herdr agent wait <pane> --until done` (and
  `--until blocked` in parallel where the CLI allows one waiter per pane;
  otherwise poll `herdr agent list`).
- On `blocked`: `herdr notification show` naming pane label + last visible
  lines; do not answer another agent's permission prompts on its behalf.
- Read output with `pane read --source detection` (or `visible`).
  **NEVER `--source recent`** — it returns empty when no UI client is
  attached, which is exactly this skill's headless condition.
- Record every terminal state in the dispatch log (`status: done|blocked|
  failed`, plus the tail that proves it).

## 8. Collection & teardown

- Report per partition: branch, commit shas, `PARTITION-DONE` seen or not,
  test evidence from the pane tail. Split fixed vs NOT-fixed explicitly.
- Landing is MANUAL and Alex's: hand him per-branch merge commands, bare.
- `herdr worktree remove` only after Alex confirms the branch is landed or
  abandoned — worktrees with unmerged commits are never removed automatically.

## 9. Hard rails (restated so they can be quoted back)

1. Dry-run default; `--dispatch` is the only path to execution.
2. Refuse-to-parallelize default; uncertainty serializes.
3. Pane cap 2 until the 6.3 gate raises it.
4. Dispatched agents never push, never open PRs, never merge.
5. HUMAN-GATED tasks are surfaced, never attempted.
6. Every dispatch and every outcome lands in the JSONL log.
7. Provider env overrides are per-pane only (§3 env-leak rule).

## 10. Known traps

- `pane read --source recent` empty headless (§7).
- One git index per checkout: partitions get worktrees, ALWAYS — two agents
  in one tree is the failure this skill exists to prevent.
- `agent wait` on a pane whose process died may hang: guard waits with a
  timeout and re-check `herdr agent list`.
- codex model cache staleness: a 400 "requires a newer version of Codex"
  means upgrade the CLI (`npm install -g @openai/codex@latest`), not that the
  model id is wrong.
- GLM seat is Claude Code with a foreign model: tool-use reliability varies;
  keep its briefs mechanical and explicit.
