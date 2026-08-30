# Progress: Herdr Agent Workflow — one-flow dispatch, agent naming, worktree lifecycle

## Operating Contract (pinned — survives compaction; re-read on every resume)
1. Scope↔skill mismatch = STOP, investigate in-context, report before proceeding.
2. Re-validate each skill's current text against disk before editing it; scope #3 (`concurrency/`) is being amended, so read its live state first — raise gaps in batched blocks.
3. Wrap + commit + check in at every phase boundary; progress updates land more frequently than boundaries. This file alone must let a cold context resume.
4. This is a de-cluttering scope: prefer removing ceremony over adding it. Do not add flags/steps the user must remember.

## Resume Context
**Scope:** ~/Projects/ai-skills/plans/4-herdr-agent-workflow/scope.md
**Last action:** Scope created (2026-08-30)
**Next action:** `/plan-ceo-review` (or `/autoplan`) on `scope.md`, then execute Phase 1 (`4.1`)
**Open blockers:** Phase 2 has a soft wait on the friend's herdr tool (bars + diff), arriving ~2026-08-30 night.
**Key files changed:** None yet

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
| 4.1 | 4.1-herdr-agent-workflow-PLAN.md | Phase 1 — /concurrency one-flow + worker naming + amend #3 | Draft | Gate A (dogfood) |
| 4.2 | 4.2-herdr-agent-workflow-PLAN.md | Phase 2 — worktree lifecycle + driver naming + CLAUDE.md | Draft | Gate C; soft wait on friend's tool |

---

## Artifacts
(none yet)
