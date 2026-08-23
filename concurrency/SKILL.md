---
name: concurrency
version: 0.2.0
description: |
  ONE responsibility: map what can run in parallel and what cannot, against a
  clear set of rules — re-derived from repo ground truth on every run, never
  from a scope's dependency claims. Then dispatch each parallel unit to a
  visible, named herdr pane running the right model seat (Opus / codex / GLM)
  and supervise by agent state plus a Claude-to-Claude gate-broadcast bus. The single
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

## 4. Partition procedure — ONE responsibility

This skill maps what can run in parallel and what cannot, against the rules
below. It does not plan, review, or execute the tasks themselves.

Input: a scope folder (plan stubs + PLANS-INDEX row) or an explicit task list
— treated as HYPOTHESES only.

**4.0 Evidence rules — never take the scope's word for it.** Every
classification is re-derived from ground truth on every run: no cached DAG,
no trust in a prior run, no trust in stub prose.
- Claimed "done" / "already exists" ⇒ content-grep `origin/<trunk>` after a
  fetch (done means written). Claimed "missing" ⇒ same grep (landed ≠ absent).
- Claimed touch-set ⇒ derive the real one by grepping the code the task names
  (files, tables, protos, routing keys). The derived set wins on conflict.
- Claimed blocker ⇒ verify it still blocks — a gate may have been passed
  since the stub was written. Claimed independence ⇒ verify nothing landed
  since that couples it.
- External gates (vendor sandboxes, credentials, prod state) that cannot be
  verified read-only from here: classify on recorded evidence (progress
  files, git log since the claim date) and stamp the verdict
  `UNVERIFIED-EXTERNAL` — visible in the output, never silently trusted.
- All checks read-only and bounded; estimate a sweep's cost before running it
  wide.

**4.1 Classify every task** into exactly one of:
- `HUMAN-GATED` — needs an action only Alex can take (credential/sandbox
  renewal, prod decision, sign-off), with the gate CONFIRMED still unmet per
  4.0. Surfaced in the plan; NEVER dispatched, never attempted.
- `BLOCKED` — a verified edge to an incomplete task (see 4.2).
- `READY` — all edges verified satisfied, no human gate.

**4.2 Build the dependency DAG.** Edges come from, in order of authority:
1. Repo-derived touch-set overlap (per 4.0): any overlap ⇒ same partition
   (serialized), never parallel branches over shared files.
2. Domain ordering rules (always edges, even when every document is silent):
   emitter before consumer; schema leads code; gRPC implementer leads caller.
3. Stub/index dependency claims — only those that SURVIVED 4.0 verification.
4. **Uncertain ⇒ serialize.** Refuse-to-parallelize is the default verdict;
   a pair joins the parallel set only when disjointness is SHOWN.

Every entry in the output carries its evidence (`evidence: <grep/commit/
check, or UNVERIFIED-EXTERNAL>`) so the verdict is auditable.

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
   Claude seats additionally get the §7.2 gate-bus reporting instruction
   (`GATE-PASSED` / `GATE-BLOCKED` via SendMessage to the supervisor).
4. Append one JSON line to `~/.config/herdr/concurrency-log.jsonl`:
   `{ts, scope, task, seat, branch, worktree, pane_id, status:"dispatched"}`.

## 7. Supervision & coordination

**7.1 herdr state layer (all seats)**
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

**7.2 Claude-to-Claude gate bus (claude + glm seats)**
Dispatched claude/glm panes are full local Claude Code sessions, so they
appear in the supervisor's `ListAgents` and are reachable via `SendMessage`
(native cross-session messaging over the local socket).
- Every dispatched Claude brief includes: "When your gate criteria are met,
  SendMessage the supervising session exactly: `GATE-PASSED <task> —
  <one-line evidence>`. If you hit a human-only blocker, send
  `GATE-BLOCKED <task> — <what Alex must do>`, then stop."
- A `GATE-PASSED` is a SIGNAL, never proof: the supervisor re-verifies from
  the consumer's vantage point (read the branch, run the gate check itself)
  BEFORE recomputing the frontier and releasing downstream partitions.
- On releasing new frontier tasks, the supervisor broadcasts a plain-text
  note to each affected running peer so it knows its upstream landed.
- The codex seat has no bus: herdr state + the `PARTITION-DONE` marker only.
- Messages are plain text and carry pointers, not payloads — evidence lives
  in the repo and the dispatch log.

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
