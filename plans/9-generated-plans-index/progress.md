# Progress: Generated PLANS-INDEX + index cleanup

## Index record

Script-owned (`plans-index.py`); PLANS-INDEX.md is rendered from it.

<!-- plans-index:begin -->
| # | Status | Folder | Description | Created by |
|---|---|---|---|---|
| 9 | 📝 Draft (2026-10-24) | `9-generated-plans-index/` | Each scope's index row moves into a script-owned block in its own progress.md and PLANS-INDEX.md becomes generated output, so concurrent sessions stop conflicting on one shared file. On kalpa-docs a GitHub Action is the only writer of the rendered index (about 1 min lag) and overwrites hand edits with a note to update ai-skills; pmg-docs, IRIS and ai-skills render locally. Also clears closed work: /closeout on 168 and pmg candidates, 155/161 archived as superseded by 196, and the 52 orphaned phase rows fixed by the migration. | Alex |
| 9.1 | 📝 Draft (2026-10-24) | `9-generated-plans-index/` | Phase 1 — records in progress.md, render/migrate/check, render mode per graph, backlog archive guard, readers + skill prose moved off the shared file. | Alex |
| 9.2 | 📝 Draft (2026-10-24) | `9-generated-plans-index/` | Phase 2 — /closeout 168 and pmg candidates, archive LIS 155/161 by hand; concurrent with 9.1. | Alex |
| 9.3 | 📝 Draft (2026-10-24) | `9-generated-plans-index/` | Phase 3 — migrate four graphs, move index prose to plans/README.md (IRIS gate mode), kalpa-docs render bot + hand-edit note, observe on trunk. | Alex |
<!-- plans-index:end -->

## Operating Contract (pinned — survives compaction; re-read on every resume)
1. Scope↔code mismatch = STOP, investigate in-context, report before proceeding.
2. Re-validate each phase's surface against live code before entering it; raise gaps in batched blocks, not per-step.
3. Wrap + commit + check in at every phase boundary; progress updates land more often than boundaries. This file alone must be enough for a cold context to resume.
4. Finish today (2026-10-24): 9.1 and 9.2 run concurrently via `/concurrency`; reviews stay short.
5. `render` and `check` never invoke `verdict-gate.py` (memory blowup, ai-skills TO-DO 2026-10-06).

## Resume Context
**Scope:** ~/Projects/ai-skills/plans/9-generated-plans-index/scope.md
**Last action:** /concurrency dispatched 9.1 (pane w14:p18, opus/alex, `feature/9-generated-plans-index`) and 9.2 (pane w14:p19, sonnet/int, kalpa-docs `plan/9.2-closeouts`) in tab "9 lanes"; kalpa-docs PR #183 merged (c7fe5e33) to unblock the 161 archive (2026-10-24)
**Next action:** land 9.1 (PR to ai-skills main), then 9.3 cutover; 9.3 needs Alex's GitHub App + bypass
**Open blockers:** bot GitHub App + `main` bypass (9.3 Task 3.4)
**Key files changed:** None yet

---

## Decisions Log
- (2026-10-24) Records in a script-owned block inside each scope's `progress.md`; membership follows disk; kalpa-docs bot is the sole writer of the rendered index; other graphs render locally. Full list: scope.md §11.
- (2026-10-24) pmg-docs closeouts dropped from 9.2 (Alex: focus is kalpa; possibly 46 later, not required). The 11 pmg scopes already under `archive/` but still in Active are fixed by the 9.3 migration, no closeout.
- (2026-10-24) Scope 168's leftover branch is already landed by content (PRs #139, #143); CEO R2 needs no reconcile, branch delete goes in teardown.
- (2026-10-24) Scope number 9, not the 172 `claim-scope-number.sh` offered — it counted the WellMed branch `docs/171-tooling-todos` in ai-skills. Fix folded into 9.1.

---

## Progress Log

| Date | Skill/Action | Status | Notes |
|------|--------------|--------|-------|
| 2026-10-24 | /scope | Done | Scope created — generated index, kalpa-docs bot, closeouts + LIS archive, cutover |
| 2026-10-24 | /plan-ceo-review | Done | HOLD SCOPE; 3 repairs, D1–D4 decided (D4 → TO-DO); PR #173 closed by Alex |
| 2026-10-24 | /plan-eng-review | Done | 6 findings mapped; D23 smaller arrangement, D24 archive index split |
| 2026-10-24 | 9.2 (lane) | Done | 155/161 archived as superseded by 196, 168 closed out; landed on kalpa-docs main (711631a9) |
| 2026-10-24 | 168 residual docs (lane) | Done | backbone CLAUDE.md §15 (#643), kalpa-docs api/export.md (ef5eb982) |
| 2026-10-24 | 9.1 (lane) | Built | 4 commits (7608e10..193a692); /review r1 Claude fallback (codex out of credits): 16 findings, all fixed in 11 commits (fd7267a..5404af5); suite 326 OK (driver rerun). Alex: cleanup scope, no round-2 review |

---

## Human Steps

| Step | Status | Notes |
|------|--------|-------|
| Approve finish-conditions table | [x] Done | rev 1, Alex, 2026-10-24 |
| Bot push credential + `main` bypass on kalpa-docs | [ ] Pending | 9.3 gate A |

---

## Plans

| # | Plan File | Phase | Status | Notes |
|---|-----------|-------|--------|-------|
| 9.1 | 9.1-generated-plans-index-PLAN.md | Phase 1 — Records + generator | Draft | ai-skills worktree |
| 9.2 | 9.2-generated-plans-index-PLAN.md | Phase 2 — Close out finished work | Draft | concurrent with 9.1 |
| 9.3 | 9.3-generated-plans-index-PLAN.md | Phase 3 — Cutover | Draft | after 9.1 merged + 9.2 done |

---

## Artifacts
(none yet)
