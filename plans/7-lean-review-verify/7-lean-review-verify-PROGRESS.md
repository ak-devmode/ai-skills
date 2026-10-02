# Lean /review and /verify — PROGRESS

**Plan:** `plans/7-lean-review-verify/7-lean-review-verify-PLAN.md`
**Branch:** `feature/7-lean-review-verify`

---

## Resume Context

- **Last completed:** Task 1.7
- **Next action:** Task 1.8 — live dry run (AI+HUMAN_REVIEW)
- **Open blockers:** none. There is no finish table yet; one is drafted and confirmed at
  Task 1.8's stop, before 1.V.

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

