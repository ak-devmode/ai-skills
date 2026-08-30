# Progress: Herdr Agent Workflow — one-flow dispatch, agent naming, worktree lifecycle

## Operating Contract (pinned — survives compaction; re-read on every resume)
1. Scope↔skill mismatch = STOP, investigate in-context, report before proceeding.
2. Re-validate each skill's current text against disk before editing it; scope #3 (`concurrency/`) is being amended, so read its live state first — raise gaps in batched blocks.
3. Wrap + commit + check in at every phase boundary; progress updates land more frequently than boundaries. This file alone must let a cold context resume.
4. This is a de-cluttering scope: prefer removing ceremony over adding it. Do not add flags/steps the user must remember.

## Resume Context
**Scope:** ~/Projects/ai-skills/plans/4-herdr-agent-workflow/scope.md
**Last action:** Phase 2 Task 2.0 done — created shared `herdr/SKILL.md` (registered), pointed `/concurrency` at it (precondition/naming/layout/worker-bypass), captured the new pane layout + `--dangerously-skip-permissions` worker launch. §3 routing-table dedup classifier-blocked (table left in both — cleanup pending).
**Next action:** Phase 2 remaining — 2.1 /scope primary-repo field · 2.2 /plan worktree+driver naming · 2.3 /closeout teardown · 2.4 CLAUDE.md rule · 2.5 seams note.
**Open blockers:** Gate A (Phase 1 dogfood) still open. §3 dedup needs classifier approval.
**Key files changed:** `herdr/SKILL.md` (new, registered); `concurrency/SKILL.md` (§2/§3/§6 reference the herdr skill; tab-per-scope layout removed; worker bypass)

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
| 2026-08-30 | /plan 4.2 (Task 2.0) | Done | Created shared `herdr/SKILL.md` (registered); `/concurrency` references it; tab-per-scope layout removed; new pane layout + `--dangerously-skip-permissions` workers. §3 dedup classifier-blocked. |

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
| 4.2 | 4.2-herdr-agent-workflow-PLAN.md | Phase 2 — shared herdr skill + worktree lifecycle + naming + CLAUDE.md | In progress (2.0 done) | Gate C; friend's tool = follow-up |

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

## Plan 4.2: Shared herdr skill + worktree lifecycle + driver naming + CLAUDE.md

### Resume Context (Plan 4.2)
Task 2.0 (shared herdr skill) done + registered. Remaining: 2.1 `/scope` primary-repo field · 2.2 `/plan` (worktree create + driver naming, optional-for-solo) · 2.3 `/closeout` (worktree remove + prune) · 2.4 CLAUDE.md execution-parallelism rule · 2.5 seams note. §3 routing dedup needs classifier approval.

### Session: 2026-08-30
- **Task 2.0 — shared `herdr` skill** ✅ Created `herdr/SKILL.md` v0.1.0: preconditions, naming, model-B worktree lifecycle, worker launch + trust/bypass, default pane layout (driver full-height LEFT, workers half-height rightward, no tabs), model routing, gotchas, supervision. Registered via `setup.sh` (symlink live, no collision). Pointed `/concurrency` at it — §2 precondition loads the herdr skill; §6 1b layout → reference (tab-per-scope removed); §6 step 1 naming → reference; §6 step 2 workers append `--dangerously-skip-permissions`. ⚠ §3 routing-table dedup **classifier-blocked** (secret-looking GLM launch line) — table duplicated in `/concurrency` §3 + `herdr` §6; cleanup pending approval.

---

## Artifacts
(none yet)
