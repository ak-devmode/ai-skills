# Progress: Generated PLANS-INDEX + index cleanup

## Index record

Script-owned (`plans-index.py`); PLANS-INDEX.md is rendered from it.

<!-- plans-index:begin -->
| # | Status | Folder | Description | Created by |
|---|---|---|---|---|
| 9 | ✅ Done (2026-10-24) — generated index live on all four graphs; kalpa-docs bot-rendered | `archive/9-generated-plans-index/` | Each scope's index row moves into a script-owned block in its own progress.md and PLANS-INDEX.md becomes generated output, so concurrent sessions stop conflicting on one shared file. On kalpa-docs a GitHub Action is the only writer of the rendered index (about 1 min lag) and overwrites hand edits with a note to update ai-skills; pmg-docs, IRIS and ai-skills render locally. Also clears closed work: /closeout on 168 and pmg candidates, 155/161 archived as superseded by 196, and the 52 orphaned phase rows fixed by the migration. | Alex |
| 9.1 | ✅ Done (2026-10-24) — PR #17 merged ⚠ verify skipped: cleanup scope (Alex): /review r1 + 16/16 fixed + suite 326 OK stand in for /verify | `archive/9-generated-plans-index/` | Phase 1 — records in progress.md, render/migrate/check, render mode per graph, backlog archive guard, readers + skill prose moved off the shared file. | Alex |
| 9.2 | ✅ Done (2026-10-24) — 155/161 archived (superseded by 196), 168 closed out; pmg dropped (Alex) ⚠ verify skipped: commit-less archive lane; driver verified on origin/main | `archive/9-generated-plans-index/` | Phase 2 — /closeout 168 and pmg candidates, archive LIS 155/161 by hand; concurrent with 9.1. | Alex |
| 9.3 | ✅ Done (2026-10-24) — ai-skills + pmg local, IRIS #52, kalpa-docs #185 bot live (ffa8144b overwrote test hand edit) ⚠ verify skipped: cleanup scope (Alex): observed live on origin/main instead of /verify | `archive/9-generated-plans-index/` | Phase 3 — migrate four graphs, move index prose to plans/README.md (IRIS gate mode), kalpa-docs render bot + hand-edit note, observe on trunk. | Alex |
<!-- plans-index:end -->

## Operating Contract (pinned — survives compaction; re-read on every resume)
1. Scope↔code mismatch = STOP, investigate in-context, report before proceeding.
2. Re-validate each phase's surface against live code before entering it; raise gaps in batched blocks, not per-step.
3. Wrap + commit + check in at every phase boundary; progress updates land more often than boundaries. This file alone must be enough for a cold context to resume.
4. Finish today (2026-10-24): 9.1 and 9.2 run concurrently via `/concurrency`; reviews stay short.
5. `render` and `check` never invoke `verdict-gate.py` (memory blowup, ai-skills TO-DO 2026-10-06).

## Resume Context
**Scope:** ~/Projects/ai-skills/plans/9-generated-plans-index/scope.md
**Last action:** Scope complete and archived (2026-10-24). kalpa-docs bot live (#185; fixes e9ac7dd9, 2bb5cc33, 2d6ca8b5; bot render ffa8144b overwrote the deliberate hand edit bf17753c).
**Next action:** None. Open follow-ups in ai-skills plans/TO-DO.md (scope 9 section).
**Open blockers:** None
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
| 2026-10-24 | 9.3 | Done | IRIS #52 merged (ff96c9ab); kalpa-docs #185 merged (rebuilt after #184 conflicted); bot fixed twice live (comment only on overwrite; overwrite 0-row refusals, fail on lost rows; dispatch); hand-edit test overwritten by bot ffa8144b; check on origin/main = render matches records |
| 2026-10-24 | 9.1 | Landed | ai-skills PR #17 merged 591a32e |
| 2026-10-24 | 9.3 cutover | Partial | ai-skills live (ef0fce3, local); pmg live (586b2d6, local); IRIS PR kalpa-iris #52 (develop protected; gate mode blocking verified); kalpa-docs draft PR #184 (bot mode; dup rows 48/65 dropped; 164→50 KB) waits on the GitHub App |
| 2026-10-24 | 9.1 (lane) | Built | 4 commits (7608e10..193a692); /review r1 Claude fallback (codex out of credits): 16 findings, all fixed in 11 commits (fd7267a..5404af5); suite 326 OK (driver rerun). Alex: cleanup scope, no round-2 review |

---

## Human Steps

| Step | Status | Notes |
|------|--------|-------|
| Approve finish-conditions table | [x] Done | rev 1, Alex, 2026-10-24 |
| Bot push credential + `main` bypass on kalpa-docs | [x] Done | App kalpa-plans-index-bot (5451966), secrets set, on main bypass list (Alex, 2026-10-24) |

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
