# Progress: Herdr Agent Workflow — one-flow dispatch, agent naming, worktree lifecycle

## Operating Contract (pinned — survives compaction; re-read on every resume)
1. Scope↔skill mismatch = STOP, investigate in-context, report before proceeding.
2. Re-validate each skill's current text against disk before editing it; scope #3 (`concurrency/`) is being amended, so read its live state first — raise gaps in batched blocks.
3. Wrap + commit + check in at every phase boundary; progress updates land more frequently than boundaries. This file alone must let a cold context resume.
4. This is a de-cluttering scope: prefer removing ceremony over adding it. Do not add flags/steps the user must remember.

## Resume Context
**Scope:** ~/Projects/ai-skills/plans/4-herdr-agent-workflow/scope.md
**Last action:** Phase 1 (Plan 4.1) executed — `/concurrency` dispatch ceremony collapsed to one inline gate; worker naming confirmed already-correct; scope #3 amended (dispatch rail + green-prose trap).
**Next action:** Gate A — Alex dogfoods one `/concurrency` dispatch to confirm entry is clean. Then Phase 2 (Plan 4.2).
**Open blockers:** Phase 1 checkpoint is a human gate (dogfood). Friend's bars/diff tool is a Phase-2 follow-up, not a blocker.
**Key files changed:** `concurrency/SKILL.md` (dispatch flow §5/§6, rail §9, green-prose §10, v0.3.0); `plans/concurrency/scope.md` (dispatch rail amended)

---

## Decisions Log
- (2026-08-30) Kill `/concurrency`'s `--dispatch` two-step → single inline flow (evaluate-and-bail if not worth it, then one `[y/N]`). Keep refuse-to-parallelize + pane cap.
- (2026-08-30) Worktrees required for `/concurrency`, optional on solo `/plan`.
- (2026-08-30) Agent naming: `/plan` agent → `driver`; `/concurrency` workers → lane/task names.
- (2026-08-30) `_herdr_attach` (OSC 10 on host window) supersedes scope #3's `herd`-alias green-prose fix.
- (2026-08-30) One new scope (#4) owns this; it amends scope #3 rather than reopening it.
- (2026-08-30) Bars / model-token / space-level-limit deferred to the friend's tool or a fork — leave seams, don't pre-build.

---

## Progress Log

| Date | Skill/Action | Status | Notes |
|------|--------------|--------|-------|
| 2026-08-30 | /scope | Done | Scope #4 created — 2 phases (concurrency one-flow + naming; worktree lifecycle + CLAUDE.md) |
| 2026-08-30 | /plan 4.1 | Done (pending gate) | `/concurrency` dispatch → single inline gate (§5/§6/§9, v0.3.0); worker naming already correct; scope #3 amended. Awaiting gate-A dogfood. |

---

## Human Steps

| Step | Status | Notes |
|------|--------|-------|
| Dogfood the new `/concurrency` flow (Phase 1 gate A) | [ ] Pending | Confirm entering concurrency is clean after the `--dispatch` removal |
| Receive friend's herdr tool (bars + diff) | [ ] Pending | ~2026-08-30 night; informs Phase 2 seams |

---

## Plans

| # | Plan File | Phase | Status | Notes |
|---|-----------|-------|--------|-------|
| 4.1 | 4.1-herdr-agent-workflow-PLAN.md | Phase 1 — /concurrency one-flow + worker naming + amend #3 | Done (pending gate-A dogfood) | Skill edits landed |
| 4.2 | 4.2-herdr-agent-workflow-PLAN.md | Phase 2 — worktree lifecycle + driver naming + CLAUDE.md | Draft | Gate C; soft wait on friend's tool |

---

## Plan 4.1: /concurrency one-flow + worker naming + amend #3

### Resume Context (Plan 4.1)
Skill edits complete; awaiting the gate-A dogfood (Alex runs one `/concurrency` dispatch and confirms entry is clean). No code blockers.

### Session: 2026-08-30
- **Task 1.1 — collapse the dispatch ceremony** ✅ `concurrency/SKILL.md`: frontmatter description; §5 reworked to "Evaluate, present, ask once" (5.0 bail-to-`/plan` when parallelism isn't worth it + 5.1 inline `[y/N]`); §6 header → "Dispatch — on `y`"; §9 rail 1; version 0.2.0→0.3.0. Removed dry-run-default + `--dispatch` re-run; kept refuse-to-parallelize, pane cap, and the human veto.
- **Task 1.2 — worker naming** ✅ No change needed — #3 already names workers at the pane level (`pane report-metadata --display-agent "<task> @<seat>"`, §6). Confirmed correct.
- **Task 1.3 — amend scope #3** ✅ `plans/concurrency/scope.md` §5 dispatch rail rewritten to the inline-gate flow (notes scope #4 supersession); `concurrency/SKILL.md` §10 green-prose trap updated — `_herdr_attach` (OSC 10 on host window) supersedes the removed `herd()` alias.

🔲 **CHECKPOINT (Gate A — human):** Alex dogfoods one `/concurrency` dispatch and confirms entry is finally clean (one inline confirm; a sequential scope gets told to use `/plan`; workers named by lane). Not yet done.

---

## Artifacts
(none yet)
