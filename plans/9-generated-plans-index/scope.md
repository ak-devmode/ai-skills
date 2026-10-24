# Generated PLANS-INDEX + index cleanup
**Project:** ai-skills (tooling for all four plans graphs)  **Branch:** main → `feature/9-generated-plans-index`  **Date:** 2026-10-24
**Created by:** Alex
**Scope folder:** ~/Projects/ai-skills/plans/9-generated-plans-index/
**Source repo(s):** ~/Projects/ai-skills · ~/Projects/wellmed/kalpa-docs · ~/Projects/pmg/pmg-docs · ~/Projects/wellmed/kalpa-iris (iris-docs) · ~/Projects/wellmed/kalpa-orchestra (read-only: backlogs)
**Primary repo (worktree):** ai-skills, `feature/9-generated-plans-index` (9.1). 9.2 and 9.3 are docs-repo work on each trunk.
**Backlog:** none

## 1. Context

Every concurrent session edits one shared `plans/PLANS-INDEX.md` in place, so rebases conflict on it and sessions abandon half-rebased scratch worktrees (the kalpa-docs `kd` orphan, stuck since 2026-10-22, removed 2026-10-24). `TO-DO.md`'s half of the problem was fixed the same day with `plans/TO-DO.md merge=union` (kalpa-docs `7be4ccff`). This scope fixes the index half: each scope's row lives with the scope, the shared file becomes generated output, and on kalpa-docs a bot is its only writer. It also clears the backlog of closed work out of the Active tables before the cutover.

## 2. Repo Graph

Single-repo task for code (ai-skills has no CROSS-REPO.md); the docs repos are data the script operates on.

| Repo | Role | Trunk | Branch at scoping | Notes |
|---|---|---|---|---|
| ai-skills | primary (code) | main | main, clean, in sync | 9.1 lands here |
| kalpa-docs | data + bot | main | main | 207 Active rows; existing `plans-index-guard.yml` (PR-only) |
| pmg-docs | data | main | main, **ahead 3** (another session's unpushed commits) | different GitHub org — local render, no bot |
| kalpa-iris (iris-docs) | data | develop | develop | its index holds load-bearing prose (gate mode, member list) |
| kalpa-orchestra | read-only | main | — | `projects/*/BACKLOG.md` for the archive guard; ensemble skills read the kalpa-docs index |

**Drift flagged:** pmg-docs ahead 3. **Snapshot taken:** 2026-10-24.

## 3. ADR Alignment

ai-skills has no ADRs. kalpa-docs ADR-029 (programs): members archive into their program's own `archive/` — **conforms**; the generator derives that placement from disk.

## 4. Phases

### 4.1 Phase 1 — Records + generator (ai-skills) · gate C

`plans-index.py` stops editing the shared file in place:

- **Record:** each scope's rows (its scope row plus its `N.P` phase rows, canonical 5 columns) live in a machine-written block inside the scope's own `progress.md`, between `<!-- plans-index:begin -->` / `<!-- plans-index:end -->`. Like Resume Context, it is the overwritable exception to append-only; only the script writes it. A folder with no `progress.md` gets a minimal one. Rows with no folder (loose PRDs, `_(not created)_`) go in one `plans/index-loose.md`.
- **Membership follows disk:** a record under `archive/` or `*-program/archive/` renders in Completed / Archived; a live folder renders in Active. No row is ever "moved" again — `move` becomes a folder move plus a status write.
- **New commands:** `render <plans-dir>` (rebuild PLANS-INDEX.md: generated-file banner + pointer to `plans/README.md` + the two tables), `migrate <plans-dir>` (one-shot, idempotent: old index rows → records; prints every row it cannot place), `check <plans-dir>` (committed index == fresh render; never invokes `verdict-gate.py`).
- **Render mode per graph,** declared in `plans/README.md` as `**Index render:** bot | local`. `bot`: local commands write records only and never touch PLANS-INDEX.md (a dirty tracked render would reintroduce the conflict). `local`: commands re-render and commit it, as today.
- **Archive guard:** archiving a kalpa-docs scope that an open kalpa-orchestra backlog row still points at (`scoped(N)`, not done) is refused and flagged; `--force "<reason>"` overrides.
- **Readers moved to records:** `next-number`, `validate`, `gate-count`, `status`'s verify gate (unchanged semantics), `claim-scope-number.sh`, `verify_lib.py` gate-mode lookup (reads `plans/README.md`, falls back to the index), `closeout/scripts/scan-archive-drift.py` + `verify-archive.sh`, `todo-sweep/scripts/sweep.py`, `context-gather.sh`, `plans-publish.sh` (in `bot` mode commits records, never the index). Skill prose updated where it names the index write: `/scope` §5.8–5.9, `/plan` §12.4, `/closeout` §13, `/repo-cleanup` §6, `/prd` §3.4.

### 4.2 Phase 2 — Close out finished work (kalpa-docs, pmg-docs) · gate B, concurrent with 9.1

Dispatched with `/concurrency`, one lane per scope:
- **168** (financial document templates, ✅ Done 2026-10-14) — full `/closeout`.
- **pmg-docs candidate(s)** — confirm complete against disk, then full `/closeout`.
- **155, 161** (LIS, superseded by 196 on 2026-10-24) — archive by hand, no closeout: folder to `archive/`, row moved, status names 196.
- Each archive passes the backlog check by hand (9.1's guard is not live yet).

Runs on the current script against the old index. Only one lane per repo writes an index, so the lanes cannot conflict with each other.

### 4.3 Phase 3 — Cutover · gate A (bot credential), then D (observe)

- Migrate all four graphs with `migrate`; diff the render against the old index row-for-row. Expected differences only: the 52 kalpa-docs phase rows whose scope is already archived move to Completed, and the moved prose.
- Move prose out of the indexes into `plans/README.md`: kalpa-docs header conventions (rewritten for the new model) and the `pending/` Cleanup table (to an archive note); IRIS's Programs table, `**Gate mode:** blocking` line, Program members table and Graph layout, and repoint kalpa-iris `CLAUDE.md` §1.2.
- kalpa-docs `.github/workflows/plans-index-render.yml`: on push to `main` touching `plans/**`, render and commit if changed. If the pushed index was hand-edited, it re-renders anyway and leaves a commit comment: "PLANS-INDEX.md is generated — update ai-skills and write through `plans-index.py`; hand-editing is being phased out." Replaces `plans-index-guard.yml` + `.github/scripts/check-plans-index.py`; the size and headerless-row checks move into `check`.
- **Human (Alex):** the bot's push credential and its bypass on `main`'s PR rule.
- Observe on the real trunk: a record-only push renders within ~1 min; a deliberate hand edit is overwritten and the comment appears.

## 5. Architecture

```
  session (any repo, any machine)                  GitHub (kalpa-docs)
  -------------------------------                  -------------------
  plans-index.py add/status/move
        |
        v
  plans/<N>-slug/progress.md        plans-publish.sh      push to main
  [plans-index:begin..end block] ------------------------> |
  (folder location = Active/Archived)                      v
                                              plans-index-render.yml
                                                render -> PLANS-INDEX.md
                                                hand edit? -> overwrite + comment
                                                     |
  git pull  <---------- bot commit ------------------+
        |
        v
  PLANS-INDEX.md (read in TextMate / grep; ~1 min lag)

  pmg-docs / iris-docs / ai-skills: same records, mode `local` -> script renders + commits
```

## 6. What Already Exists

- `ai-skills/scripts/plans-index.py` — the single writer (add / move / status / next-number / validate / gate-count), canonical 5-column shape, verify gate on Done phase rows.
- `ai-skills/scripts/plans-publish.sh` (scope 8) — commits named paths, rebases, pushes, halts on conflict.
- `ai-skills/scripts/claim-scope-number.sh` — max over four sources.
- `kalpa-docs/.github/workflows/plans-index-guard.yml` + `.github/scripts/check-plans-index.py` — PR-only guard (size ≤150KB, headerless rows, Active rows for archived scopes).
- `ai-skills/scripts/verify_lib.py:28-101` — reads `**Gate mode:**` from the index.
- `ai-skills/repo-cleanup/SKILL.md` §6 — plans-hygiene precedent for archiving.

## 7. Table Identity Map

No DB write/DDL surface — Step 4.5 N/A.

## 8. Inherited TO-DOs

| TO-DO item | Origin section | In / Out | Phase | Why |
|---|---|---|---|---|
| `/prd` §3.4 hand-appends a 6-column index row | found at scoping (not in TO-DO) | In (auto) | 1 | The last writer that bypasses the script; same file set |
| `claim-scope-number.sh` counts other graphs' scope numbers from ai-skills branch names (`docs/171-tooling-todos` → claimed 172 for ai-skills scope 9) | found at scoping | In (auto) | 1 | A reader this phase rewrites anyway |
| verdict-gate.py memory blowup (`plans-index.py validate` on a kalpa-docs worktree, 7.5 GB) | ai-skills TO-DO, 2026-10-06 | Out | — | Separate defect; constraint taken instead: `render` and `check` never call the gate. Stays in `TO-DO.md` |

## 9. NOT in Scope

- Ensemble `update-backlog` / `backlog-verify` keep reading the rendered kalpa-docs index; ~1 min lag accepted (Alex). Pointing them at records is a later change.
- A bot for pmg-docs, iris-docs or ai-skills — they run `local` mode until conflicts there justify one.
- Rewriting Description cells; the cleanup moves rows, it does not edit them.

## 10. Skill Sequence

### 10.1 Plan Reviews

| # | Skill | Apply? | When | Notes |
|---|---|---|---|---|
| 1 | /plan-ceo-review | YES | 1st | Mandatory; keep it short — finishes today |
| 2 | /plan-eng-review | YES | 2nd | Record format, bot-mode read path, migration diff |
| 3–4 | design / devex reviews | N/A | — | No UI; the CLI surface is internal |

### 10.2 Implementation Support

N/A x4 — not a bug fix, no UI.

### 10.3 Review & QA

| # | Skill | Apply? | When | Notes |
|---|---|---|---|---|
| 9 | /review | YES | end of 9.1, 9.3 | ai-skills range; kalpa-docs workflow |
| 12 | /qa-only | YES | 9.1 | `python3 -m unittest discover scripts/tests` |
| 10 | /health | OPTIONAL | 9.1 | |
| 11, 13–15 | browser QA / devex-review | N/A x5 | — | No UI |

### 10.4 Ship & Post-ship

| # | Skill | Apply? | When | Notes |
|---|---|---|---|---|
| 16 | /ship | N/A | — | Not in use; promotion is /review → PR → merge → /closeout |
| 17 | /document-release | OPTIONAL | after 9.3 | ai-skills README / ARCHITECTURE mention the index |
| 18 | /retro | OPTIONAL | — | |

`/concurrency` runs 9.1 and 9.2 side by side.

## 11. Key Decisions Captured

- (2026-10-24) Bot on kalpa-docs only; script change everywhere (Alex, Q3).
- Alex reads the index in TextMate, so the rendered file stays committed (Q4).
- The bot may bypass `main`'s PR rule, as engineers do (Q5).
- Everyone writes the kalpa-docs index, so a hand edit must be caught, fixed and explained, not silently dropped (Q6, Q14).
- 168 and pmg candidates get full `/closeout` via `/concurrency`; 155 and 161 are archived by hand as superseded by 196 (Q7, Q13).
- Program members follow their program's archive (Q8).
- Per-scope records over a static archive file: membership follows disk, so drift cannot occur (Q9).
- Records live inside `progress.md`, not a new file (Q16).
- Index prose leaves the index; IRIS's gate-mode line and member list must move, not drop, or IRIS's gate silently turns advisory (Q10).
- Archive guard against open kalpa-orchestra backlog rows (Q11).
- Today's deadline: 9.1 and 9.2 run concurrently (Q12, Q15).

## GSTACK REVIEW REPORT

**Review:** /plan-ceo-review, 2026-10-24 · **Mode:** HOLD SCOPE (Alex: keep it short, finish today) · **Depth:** compressed run, premise + failure modes only; Review Sections 1–10 not walked individually (Alex's instruction overrides the skill's full pass).

| Run | Status | Findings |
|---|---|---|
| Premise challenge (0A) | PASS | kalpa-docs index: 84 commits in 7 days by 8 authors (busiest day 22), 42 conflict/rebase/renumber commits in 30 days. The pain is real and the fix targets it directly. |
| Existing-code leverage (0B) | PASS | Single writer `plans-index.py` already exists; PR guard `plans-index-guard.yml` exists. Extend, don't rebuild. |
| Hold-scope hardening | 3 in-scope repairs | see below |
| Decisions | 4 pending | see below |

**In-scope repairs (needed to meet the scope's own acceptance, no question):**
- R1 · `render`/`check` fail loud when a row that rendered before has lost its record (an agent `Write` over `progress.md` can clobber the block). Silent row loss is the failure mode this design would otherwise add. → 9.1 Task 1.2.
- R2 · Scope 168 has an unmerged branch, `origin/plan/168-financial-document-templates` (+13 commits). Its closeout lands or reconciles that branch first. → 9.2 Task 2.1.
- R3 · Teammates mostly reach `main` through PRs (9 open: #164 #166 #171 #173 #178 #179 #181 #182 #183), so the PR path needs the hand-edit check, not just the post-push bot. → 9.3 Task 3.3.

**Decisions (Alex, 2026-10-24):**
- D1 · PR #173 closed as superseded by this scope; Oktonius told why. → done at review.
- D2 · PR check fails a PR that edits the rendered index; post-push bot covers direct pushes. → 9.3 Task 3.3.
- D3 · `migrate --branch <ref>` for open branches + channel post before cutover. → 9.1 Task 1.2, 9.3 Task 3.1.
- D4 · Import hand edits back into records — deferred to ai-skills `plans/TO-DO.md`.

NO UNRESOLVED DECISIONS
