# Lean /review and /verify — PLAN

**Version:** 0.1
**Date:** 2026-10-02
**Plan #:** 7
**Created by:** Alex
**Executed by:** Alex / Claude
**ADR:** N/A
**Status:** Ready to execute
**Branch:** feature/7-lean-review-verify

---

## Related Docs

- `ai-skills/review/SKILL.md`
- `ai-skills/verify/SKILL.md`
- `ai-skills/templates/verify-contracts.md`
- `ai-skills/scripts/README.md`
- `ai-skills/CLAUDE.md`

---

## 1. Why

1.1 Teammates have little or no codex and a regular Claude seat. With no codex, `/review`
falls back to gstack's 73 KB engine plus up to 8 specialist subagents, for up to 3 rounds
per unit, and `/verify`'s judge becomes an exploring Claude subagent. One phase uses up
a seat. Alex's codex runs measure 150k–400k input tokens per call (outliers 1–2.6M), most
of it re-reads from exploring.

1.2 **Fix:** a lean mode, on by default. It packs everything the reviewer or judge
needs into one file and hands it to one Sonnet subagent that reads only that file.
Today's behaviour stays as `full` and is one env var or flag away.

1.3 **Not in this plan:** `/scope`, `/plan`, `/closeout` and gstack are not modified.
`/plan` §6.8 calls `/review` and `/verify` as before and inherits the mode.

---

## 2. Agreed Design

2.1 **Mode resolution — one script, both skills.** Default `lean`.
`AI_SKILLS_REVIEW_MODE=full` (set in `~/.claude/settings.json` → `env`) restores today's
behaviour. Per-run `--full` / `--lean` override it. Precedence: flag > env > default. An
unrecognised env value is an error (exit 2), never a silent `lean`. Every report header
prints `mode: <lean|full> (<flag|env|default>)`.

2.2 **`full`** = today's `/review` §2 codex gate + §3 Claude fallback, and today's `/verify`
§3.3–§3.5. Unchanged.

2.3 **`/review` lean.**
- `review.py prepare --lean` writes one self-contained bundle: the diff, capped at 1,500
  changed lines; gstack `review/checklist.md` (read only); only this project's
  `domain.md` group (`GROUPS[proj]`); `lenses.md`.
- Files past the cap are written to an `uncovered` sidecar and listed in the bundle as not
  covered. Never silently partial.
- One Sonnet subagent (`Agent`, `model: sonnet`) reads only the bundle and writes
  findings JSON matching `review/schemas/review-output.schema.json`.
- Recorded by the existing `review.py record`: stable IDs, dispositions, accept and gate
  all unchanged. Reviewer line `claude-lean <reason>`. Header `DEGRADED (lean …)`.
- No gstack engine load, no specialists.
- Round cap 3, the same as full mode (Alex, 2026-10-02): rounds 2 and 3 re-review the fix
  commits, exactly as today.

2.4 **`/verify` lean.** Runner, finalize and gate unchanged (zero model tokens).
`judge.py prepare --lean` writes a self-contained bundle: `scope.md`, the finish table,
the run's records, the review log, a diff stat and the capped diff. One Sonnet subagent
pass. Judge line `claude-lean <reason>`. The index keeps `⚠ judge:` — a lean judge is
never shown as codex.

2.5 **`/verify` fix loop capped at 2 runs per unit, in both modes** (Alex, 2026-10-02). A
blocked verify gets fixed and re-run once. After a unit's second finalized run, `judge.py
report` prints `[CONVERGENCE] verify <unit> run 2 of 2: STOP`. The skill then stops and
asks, inline: `1.` one more run, or `2.` stop here. The count comes from `final` lines in
the unit's verdict log, so it is a script result, not a session's memory. Same shape as
`/review`'s round-3 hard stop.

---

## 3. Phase 1 — Lean mode

### 1.1 Mode resolver script
- **Type**: AI
- **Input**: `ai-skills/scripts/verify_lib.py`, `ai-skills/scripts/README.md`, `ai-skills/.env.example`, `ai-skills/CLAUDE.md`
- **Action**: Write `scripts/review-mode.py [--full|--lean]` per §2.1. Prints one line,
  `mode: <lean|full> (<flag|env|default>)`; exit 0, or 2 on a bad env value or both flags.
  Declare `AI_SKILLS_REVIEW_MODE` in `.env.example` and CLAUDE.md §5. Add the script to
  `scripts/README.md` and CLAUDE.md §4.
- **Output**: `ai-skills/scripts/review-mode.py`, `ai-skills/scripts/tests/test_review_mode.py`, doc edits
- **Acceptance**: a table-driven test covers every flag × env combination, including a bad
  env value and both flags together; the full suite stays green.

### 1.2 `claude-lean` judge line in the contract
- **Type**: AI
- **Input**: `ai-skills/scripts/verify_lib.py` (`JUDGE_LINE`), `ai-skills/scripts/verify-run.py`, `ai-skills/verify/scripts/judge.py`, `ai-skills/review/scripts/review.py`, `ai-skills/scripts/verdict-gate.py`, `ai-skills/templates/verify-contracts.md` §4.6
- **Action**: Accept `claude-lean <reason>` wherever `claude-fallback` is accepted, and
  update the malformed-line messages. The gate already treats any non-`codex ` judge or
  reviewer as `⚠ judge:`; pin that for `claude-lean` with a test, not an assumption.
- **Output**: edits to the files above + tests in `test_verdict_gate.py` / `test_judge.py` / `test_review.py`
- **Acceptance**: a `claude-lean` review or judge produces `⚠ judge: … claude-lean …` and
  is never counted as codex coverage.

### 1.3 `review.py prepare --lean` bundle
- **Type**: AI
- **Input**: `ai-skills/review/scripts/review.py`, `ai-skills/review/prompts/review.md`, `ai-skills/review/rules/domain.md`, `ai-skills/review/rules/lenses.md`
- **Action**: Add `--lean` per §2.3. Inline the diff file by file, in diff order, until the
  next file would pass 1,500 changed lines; every file after that goes to the `uncovered`
  sidecar. Inline only the `domain.md` sections in `GROUPS[proj]`, plus `lenses.md` and
  the gstack checklist. The bundle tells the reviewer to read nothing else. Print the
  same five lines as today, plus `bundle:` and `uncovered:` paths.
- **Output**: edits to `review.py`, a lean prompt template `ai-skills/review/prompts/review-lean.md`, tests
- **Acceptance**: tests show a diff under the cap inlined whole; a diff over the cap
  inlined up to it, with the rest named in `uncovered`; a generic repo with no domain
  section; a wellmed vs iris repo inlining different sections.

### 1.4 `review.py record` for lean
- **Type**: AI
- **Input**: `ai-skills/review/scripts/review.py` (`cmd_record`, round/convergence logic)
- **Action**: Add `--uncovered FILE` and `--mode LINE`. Merge the uncovered files into
  "What this review did not cover" in the script, never trusting the model to copy them.
  Put the mode line and `DEGRADED (lean: single Sonnet pass, no specialists, diff capped
  at 1,500 lines)` in the header. Round logic is unchanged: cap 3 for every reviewer.
- **Output**: edits to `review.py`, tests
- **Acceptance**: tests cover the uncovered list showing in the report, the lean header,
  and lean rounds stopping at 3 exactly like codex.

### 1.5 `judge.py prepare --lean` bundle
- **Type**: AI
- **Input**: `ai-skills/verify/scripts/judge.py`, `ai-skills/verify/prompts/judge.md`
- **Action**: Add `--lean` per §2.4: inline `scope.md`, the table, the run's records, the
  review log, the diff stat and the diff capped at 1,500 lines (rest listed as not
  inlined). The judge is told to read nothing else, and to return `inconclusive` for any
  check the bundle cannot decide.
- **Output**: edits to `judge.py`, `ai-skills/verify/prompts/judge-lean.md`, tests in `test_judge.py`
- **Acceptance**: tests show the bundle is self-contained (no `{{…}}` left, every listed
  input present), the cap and listing work, and the existing non-lean prompt is unchanged.

### 1.5a `/verify` run cap — 2 per unit
- **Type**: AI
- **Input**: `ai-skills/verify/scripts/judge.py` (`report`), `ai-skills/scripts/verify_lib.py`, `ai-skills/templates/verify-contracts.md`
- **Action**: Per §2.5, `judge.py report` counts the unit's `final` lines in
  `artifacts/verify-<unit>.jsonl`. On the 2nd and every later run it prints
  `[CONVERGENCE] verify <unit> run <n> of 2: STOP` and writes the same line into the
  report. Mode does not change the cap. Document the cap in `verify-contracts.md`.
- **Output**: edits to `judge.py` / `verify_lib.py`, contract text, tests in `test_judge.py`
- **Acceptance**: tests show run 1 has no line; run 2 prints STOP; run 3 prints STOP again
  with its count; full and lean runs count toward the same cap.

### 1.6 `/review` SKILL.md
- **Type**: AI
- **Input**: `ai-skills/review/SKILL.md`
- **Action**: Add a mode step before §2 that runs `review-mode.py` and branches: `full` →
  §2/§3 unchanged; `lean` → a new section with prepare `--lean`, one Sonnet `Agent` whose
  whole prompt is "read `<bundle>`, write JSON matching `<schema>` to `<out>`, modify
  nothing", and record with `claude-lean`; §5 round rules apply unchanged. Document `--full` /
  `--lean` and the env var in the frontmatter description and §6. Bump `version`.
- **Output**: `ai-skills/review/SKILL.md`
- **Acceptance**: `scripts/lint-skill.py review` passes; the full path's text is unchanged
  apart from the branch into it.

### 1.7 `/verify` SKILL.md
- **Type**: AI
- **Input**: `ai-skills/verify/SKILL.md`
- **Action**: Same branch at §3.2–§3.5: `lean` skips the codex probe and runs one Sonnet
  subagent over the lean bundle, with judge line `claude-lean <reason>`. §5.1 reporting
  leads with the mode line. Add the run-cap stop (§2.5): on a `[CONVERGENCE] … STOP`
  line, ask before another run. Bump `version`.
- **Output**: `ai-skills/verify/SKILL.md`
- **Acceptance**: `scripts/lint-skill.py verify` passes.

### 1.8 Live dry run — measure, don't estimate
- **Type**: AI+HUMAN_REVIEW
- **Input**: range `eea708c..45fcd32` in `ai-skills` (the resolver fixes: 5 commits, ~190 lines)
- **Action**: Run lean `/review` and lean `/verify` on that range with
  `AI_SKILLS_REVIEW_MODE` unset. Record the subagents' token usage and wall time in
  `artifacts/lean-dry-run.md`, next to the codex numbers for a comparable range.
  Delete the dry run's review/verdict records afterwards; it is a measurement, not a
  review of record.
- **Output**: `ai-skills/plans/7-lean-review-verify/artifacts/lean-dry-run.md`
- **Acceptance**: measured tokens per lean review and per lean judge are recorded; Alex
  judges whether they fit a regular seat.

### 1.R Review
- **Type**: AI
- **Action**: `/review --full` (codex) on this plan's range, per `/plan` §6.8.
- **Acceptance**: every finding dispositioned; Alex accepts.

### 1.V Verify
- **Type**: AI
- **Action**: `/verify 7.1` in full mode.
- **Acceptance**: gate reported; advisory blocks named, not softened.

### 1.9 Turn on full mode for Alex, announce to the team
- **Type**: HUMAN
- **Action**: Add `"AI_SKILLS_REVIEW_MODE": "full"` to the `env` block of
  `~/.claude/settings.json` (Claude can make the edit on request), restart the session,
  and confirm `review-mode.py` prints `mode: full (env)`. After merge, tell the team to
  `git pull` (CLAUDE.md §2.1) and that `--full` exists.
- **Acceptance**: Alex's `/review` header reads `mode: full (env)`.

---
### 🔲 CHECKPOINT: Lean mode shipped
**Gate**: A human
**Review**: the dry-run token numbers in `artifacts/lean-dry-run.md`; the review outcomes;
the `/verify` gate result.
**Resume**: "continue plan 7"
---

## 4. Risks

4.1 **`/plan` doesn't mention the verify cap.** `/plan` §6.8 runs `/verify` once per unit
and doesn't describe a fix loop. The cap lives in `/verify` and its `[CONVERGENCE]`
line, so `/plan` needs no edit.

4.2 **Narrower coverage is real.** Lean cannot follow a lead outside the bundle and runs
no specialists. The header and the `⚠ judge:` index marker are what keep it from being
mistaken for full coverage.

4.3 **`model: sonnet`** resolves to the current Sonnet (5.5). No pinned model ID in the
skills, so a new Sonnet is picked up without edits.

---

## 5. Closing Cleanup

- [ ] Archive `plans/7-lean-review-verify/` → `plans/archive/7-lean-review-verify/` and move the index row (`plans-index.py move`)
- [ ] Update CLAUDE.md §9.2 recent work
- [ ] Extract deferred items to `plans/TO-DO.md`
