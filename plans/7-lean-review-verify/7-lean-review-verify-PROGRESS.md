# Lean /review and /verify — PROGRESS

**Plan:** `plans/7-lean-review-verify/7-lean-review-verify-PLAN.md`
**Branch:** `feature/7-lean-review-verify`

---

## Resume Context

- **Last completed:** Task 1.8 (reviewed by Alex 2026-10-02: the numbers fit a seat). The 7.1
  finish table is written and approved (rev 1). 1.R round 1 is fixed and dispositioned.
- **Next action:** 1.R round 2 — `/review --full` on the fix commits; then Alex's `accept`;
  then 1.V `/verify 7.1 --full`.
- **Open blockers:** `AI_SKILLS_REVIEW_MODE` is not yet in `.env.example`, so `p1-names-resolve`
  fails until Alex runs `bash ~/cc/add-review-mode-env.sh` and the change is committed.

---

## Session: 2026-10-02

### Phase 0 — ✅ DONE
- Every Input path and Related Doc resolves; the dry-run range `eea708c..45fcd32` exists.
- Status: Ready to execute (Alex approved 2026-10-02). Branch `feature/7-lean-review-verify`
  was confirmed with the plan.
- Read: CLAUDE.md, ARCHITECTURE.md, CROSS-REPO.md (standalone leaf; no Pattern Sources).
- Ledger: created `closeout-prep.md`, base `ai-skills bff989a`.
- Executed by: stamped `Alex / Claude`.

### Task 1.1 — ✅ DONE — mode resolver script
- **Files:** `scripts/review-mode.py` (new), `scripts/tests/test_review_mode.py` (new),
  `scripts/README.md`, `CLAUDE.md` §4/§5
- **Result:** `mode: lean (default)` with nothing set. 13 table cases cover flag × env,
  case and whitespace, a repeated flag, a bad env value (exit 2), a flag over a bad env
  value (wins but warns on stderr), both flags (exit 2) and an unknown argument (exit 2).
- **Issues:** `.env.example` can't be read or edited (permission deny). Alex adds
  `AI_SKILLS_REVIEW_MODE=` there; collected for the Task 1.8 stop.

### Task 1.2 — ✅ DONE — `claude-lean` judge line in the contract
- **Files:** `scripts/verify_lib.py`, `scripts/verify-run.py`, `review/scripts/review.py`,
  `verify/scripts/judge.py`, `templates/verify-contracts.md` §4.6, three test files
- **Result:** `claude-lean <reason>` is accepted wherever `claude-fallback` is. Every
  codex check in the scripts is a `codex ` prefix match, so lean is non-codex by
  construction. Three new tests pin it: the gate marker, review coverage (a later codex
  review clears it) and the judge report. 150 tests pass.

### Task 1.3 — ✅ DONE — `review.py prepare --lean` bundle
- **Files:** `review/scripts/review.py`, `review/prompts/review-lean.md` (new), `scripts/tests/test_review.py`
- **Result:** one bundle with the commits, the repo's CLAUDE.md (≤ 24 KB, else listed),
  the gstack checklist, only this project's `domain.md` sections, the lenses, a
  not-covered list, the capped diff, and `review.md`'s own Output section (one contract
  for both modes). Smoke test on `eea708c..45fcd32`: 2/2 files, 54 KB (~14k tokens).
  37 review tests pass.
- **Deviations from the plan text:**
  - The cap fills greedily: a file that doesn't fit is listed and smaller later files
    can still go in, rather than "every file after that". More coverage, same cap, never
    partial.
  - `prompt:` is the bundle path, so there's no separate `bundle:` line.
  - CLAUDE.md is inlined (≤ 24 KB) because the full prompt tells the reviewer to read it.
- **Risk:** the inlined gstack checklist has its own "Instructions" section, written for
  an agent that can run commands. The bundle header forbids running anything; the dry
  run (1.8) will show whether Sonnet obeys the header.

### Task 1.4 — ✅ DONE — `review.py record` for lean
- **Files:** `review/scripts/review.py`, `scripts/tests/test_review.py`
- **Result:** `--uncovered FILE` puts the sidecar's lines first in "What this review did
  not cover", ahead of the model's own `cannot_do`. A `claude-lean` reviewer without
  `--uncovered` is refused (exit 2), so the list can't be dropped by forgetting a flag.
  `--mode LINE` shows in the header and is stored on the `review` record. The lean
  DEGRADED header names the cap. Rounds are unchanged: lean stops at 3 like codex
  (tested). 156 tests pass.

### Task 1.5 — ✅ DONE — `judge.py prepare --lean` bundle
- **Files:** `verify/scripts/judge.py`, `verify/prompts/judge-lean.md` (new),
  `scripts/verify_lib.py`, `review/scripts/review.py`, `scripts/tests/test_judge.py`
- **Result:** the bundle is the lean preamble, then today's full prompt verbatim (one set
  of rules, tested by substring), then the inlined inputs: scope.md, the table, this run's
  verdict-log records, the review log, the test plans, and per repo a `--stat` plus the
  diff. One 1,500-line cap is shared across repos. Inputs over 40 KB and files past the
  cap are listed in the preamble, and a check needing them is `inconclusive`.
  200 tests pass.
- **Pattern:** the capped diff moved from `review.py` into `verify_lib.capped_diff`, so
  `/review` and `/verify` cap the same way (CLAUDE.md §3.5).

### Task 1.5a — ✅ DONE — `/verify` run cap, 2 per unit
- **Files:** `verify/scripts/judge.py`, `scripts/verify_lib.py`, `templates/verify-contracts.md` §4.10,
  `scripts/tests/test_judge.py`
- **Result:** `judge.py report` counts the unit's `final` lines in the verdict log. From
  run 2 on, it prints `[CONVERGENCE] verify <unit> run <n> of 2: STOP` and writes it under
  the report's Gate line. Mixed codex and lean runs count together (tested: run 1 no
  line, runs 2 and 3 STOP). The cap never changes a verdict.

### Task 1.6 — ✅ DONE — `/review` SKILL.md
- **Files:** `review/SKILL.md` (3.5.0 → 3.6.0)
- **Result:** §1.4 runs `review-mode.py` first: `full` goes to §2/§3 (only `--mode` added
  to §2.4), `lean` goes to a new §7 (render, one Sonnet `Agent` with a no-narrative prompt,
  record with `claude-lean` + `--uncovered`, what lean doesn't do; §4/§5 unchanged).
  Appended as §7 rather than inserted, so nothing renumbers: `/plan` and the contract cite
  §3 and §5.1. Lint: 0 issues, 1 size note (280 body lines).

### Task 1.7 — ✅ DONE — `/verify` SKILL.md
- **Files:** `verify/SKILL.md` (0.5.0 → 0.6.0)
- **Result:** `MODE` is set with the other variables (§2.3); §2.4 branches; lean adds
  `--lean` to §3.2 and replaces the probe/codex/fallback steps with §3.5.1 (one Sonnet
  subagent, judge line `claude-lean $MODE`); §3.9 is the run-cap stop; §5.1 leads with
  the mode. Nothing renumbered. Lint: 0 issues. Notes: a size note on review, and
  cross-skill overlap (32–37%) between the two skills' parallel mode/subagent paragraphs —
  advisory, left as is, since each skill states its own procedure.

#### Unplanned: resolver read its own docstring as env refs (`ca44e9a`)
- **Files modified:** `scripts/resolve-identifiers.py`
- **Why:** found by the 1.8 dry run. The 309af3f `node_eval_given` docstring and a trailing
  comment spelled out `process.env.NAME` and `process.env.X`, and `names-resolve` reported
  both. Reworded them. The general issue (ENV_USE matches inside Python docstrings and
  trailing comments) is left for TO-DO, not fixed here.

### Task 1.8 — ⏸️ WAITING_HUMAN (AI+HUMAN_REVIEW) — live dry run
- **Files:** `artifacts/lean-dry-run.md` (new), `scope.md` (new, a pointer), ledger `- base: 7.1` line
- **Result:** lean `/review` used 88,142 subagent tokens (4 tool uses, 89 s, 3 real
  findings); the lean judge used 75,032 (4 tool uses, 33 s, 5 sound verdicts). About 163k
  per unit, against codex's 262–437k per call on similar ranges. Most lean tokens are
  agent overhead and repeated turns, not the 10–14k bundle.
- **Found along the way:** the resolver's own docstring tripped `names-resolve` (fixed in
  `ca44e9a`). `AI_SKILLS_REVIEW_MODE` still waits on `.env.example`.
- **Workarounds for a standalone plan:** `ledger-init.sh` labels the base after the plan
  filename, so I added a `- base: 7.1` line by hand. `judge.py` needs a `scope.md`, so I
  added a pointer to the plan. Both are lever candidates.
- **Waiting on Alex:** judge the numbers; add `.env.example`; confirm the 7.1 finish table.

### Task 1.8 — ✅ DONE — reviewed by Alex
- ~163k Sonnet tokens per unit fits a seat ("yes"). The schema stays outside the bundle.
- `.env.example`: Alex asked for a script → `~/cc/add-review-mode-env.sh` (idempotent,
  reads the file back). The 7.1 finish table is confirmed and approved (`e2f3272`).

### Task 1.R — round 1 (codex gpt-6-sol, full) — 9 findings, all fixed
- Report: `artifacts/review-7.1-r1.md`. Verdict DO NOT SHIP: 6 blocking, 3 should-fix.
- Fixed:
  - `3308dd6` — quoted filenames (06)
  - `4a388a1` — ARCHITECTURE.md inlined; adjacent code always declared uncovered; sidecar
    bound to its range (03, 04, 05)
  - `a671020` — unit's plan inlined; log limit applied after filtering (02, 07)
  - `fa783aa` — ARCHITECTURE.md descriptions, off-anchor (09)
  - this commit — Resume Context (08)
- 01 (`.env.example`) is fixed by Alex's script run plus a commit, recorded off-anchor
  when it lands.

