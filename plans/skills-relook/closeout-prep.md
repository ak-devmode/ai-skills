# closeout-prep.md — skills-relook (scope 2)

**Schema version:** 1.0
**Plan:** plans/skills-relook/2.1-skills-relook-PLAN.md
**Started:** 2026-09-23T08:34:15Z
**Status:** in-progress

---

## §1 Execution Summary

- **Branch:** feature/skills-relook-opus5
- **Base:** main
- **Phases completed:** 0 of 3 (2.1 in progress)
- **Phases skipped:** none
- **Repos touched:** ai-skills
- **Last action:** Phase 0 pre-flight complete; building the accretion linter (Task 2.1.1)

---

## §2 Files Changed

### ai-skills

**code:**
- `scripts/lint-skill.py` — the accretion linter (new; stdlib-only, fail-loud). ISSUE tier: oversize/dup-section-number/frontmatter/stale-name. NOTE tier: determinism-as-prose/supersession-site.

**test:** _(none — repo has no automated suite; verified via negative-control fixture + dogfood, not committed)_

**config:** _(none)_

**doc:**
- `CLAUDE.md` — §6 "No linter currently" replaced with the linter's usage; §4 key-files list gains a `lint-skill.py` row.
- `scripts/README.md` — table row + contract block for `lint-skill.py`.
- `plans/skills-relook/artifacts/lint-baseline-2026-09-23.{md,txt,json}` — fleet baseline + dogfood dispositions (new).

**schema:** _(none)_

**migration:** _(none)_

---

## §6 Docs Loaded During Planning

- `CLAUDE.md` (repo root) — script conventions (§3.6), build/test/lint (§6 "no linter currently")
- `ARCHITECTURE.md` (repo root) — present, not deep-read (single-repo skill work)
- `CROSS-REPO.md` (repo root) — present; consumers are not code consumers of this work
- `scripts/README.md` — contract + docstring conventions for shared scripts
- `scripts/plans-index.py` (docstring) — the anti-cry-wolf validate/NOTE philosophy
- `plans/skills-relook/scope.md` + `AUDIT.md` — the defect classes to detect
- `plans/skills-relook/2.2-…-PLAN.md`, `2.3-…-PLAN.md` — sibling plans (§5.6.2)
- `concurrency/SKILL.md` — the dogfood target

---

## §7 Docs Likely Affected

- `CLAUDE.md` — §6 "No linter currently" line is now false once the linter lands
- `scripts/README.md` — new script needs a table row + contract block

---

## §8 Assumptions Made (unverified)

- Body-line oversize threshold = 250 (from AUDIT §6.4 target; ready-to-clear=176 is the model). Configurable via `--max-body-lines`.

---

## §11 Risk Flags / Uncertainty

- Live-contradiction detection is semantic and cannot be caught deterministically without an LLM/eval pass (deferred per scope §2.1). The linter ships a NOTE-tier *supersession-site* scan (where such contradictions hide) rather than a noisy semantic guesser — honoring the repo's "a validator that cries wolf gets ignored" principle (`scripts/README.md`, `plans-index.py`).

---

## Phase 1: 2.1 Accretion linter (started 2026-09-23T08:34:15Z)

### §9 Deferred Items (additional)
- Slim `/concurrency` (347→<250 body lines): move §10 traps + §7 supervision lore to `references/`. Routed to plan **2.3** (its explicit "apply the loop … + /concurrency" task). True-positive oversize flag; deferred, not dropped.
- ~~`prd` duplicate section numbers~~ — **RETRACTED.** `/review` proved this a false positive: the colliding `3.1/3.2/3.3` are inside `prd`'s fenced ```` ```markdown ```` template example (L164–280), not real sections. The linter's fence-aware fix now suppresses it correctly. No prd dup-number defect exists.
- `ready-to-clear` marginally oversize (258 vs 250). Trim in a later pass; do not raise threshold to mask it.

### §2 Files Changed (additional — /review hardening)
- `scripts/lint-skill.py` — hardened after `/review`: 8 fail-open/false-positive fixes (unclosed-frontmatter fail-open, UTF-8 crash, BOM, quoted/commented name, zero-indent allowed-tools, fenced-example headings, exit-2 on unresolved, 4-digit-year dup). 483→545 lines.
- `plans/skills-relook/artifacts/review-2.1-lint-skill.md` — the /review report (new).
- `plans/skills-relook/artifacts/lint-baseline-2026-09-23.{md,txt,json}` — regenerated (fleet 16→13 ISSUE after the prd false-positive fix).

### §11 Risk Flags (additional)
- Semantic live-contradiction detection (AUDIT §5.3 class) is NOT implemented — it needs an LLM/eval pass, deferred per scope §2.1. The shipped NOTE-tier supersession scan surfaces *where* such contradictions hide, but a human/eval must confirm. This is a known, deliberate coverage boundary, stated in the linter docstring and README.

---

---

## Phase 2: 2.2 Model migration to Opus 5.5 (started 2026-09-25)

### §2 Files Changed
**ai-skills — doc:**
- `herdr/SKILL.md` — §6 opus seat row: "Opus 4.8" → `opus[1m]` → Opus 5.5; re-verified date; version 0.1.3.

### §5 Cross-Repo Touchpoints
- `dev-workbench/config/claude-code/settings.json:191` — tracked copy pins `claude-opus-4-8`; live `~/.claude/settings.json` (not symlinked) is `opus[1m]` + `modelSettings.claude-opus-5-5`. Reinstall from tracked would roll back to 4.8. Not edited (repo on `feature/1password-migration`).

### §11 Risk Flags
- `~/.claude/settings.json` is a plain file, not a symlink to dev-workbench — live/tracked drift is structural, will recur.
- (resolved 2026-09-25) `dev-workbench` tracked settings aligned on `fix/opus-5-5-default` (`227b0c2`, pushed; merge pending).

### §2 Files Changed (additional)
**dev-workbench — config (unplanned):**
- `config/claude-code/settings.json` — `model` → `opus[1m]`; `modelSettings.claude-opus-5-5.effortLevel: high`. Branch `fix/opus-5-5-default`.

### §9 Deferred Items
- 2.2.3 measure 5.5 verbosity + 2.2.4 tune floor → folded into **2.3** (log floor breaches per skill; 2nd sighting → eval harness).

---

## Phase 3: 2.3 Apply the loop (started 2026-09-25)

### §2 Files Changed
**ai-skills — code:** `scripts/lint-skill.py` — size ISSUE→NOTE; new `growth` (git numstat, `--diff-filter=M`) + `cross-skill-duplicate` (5-gram containment) NOTEs; `--no-history`.
**ai-skills — doc:** `CLAUDE.md` §4/§6, `scripts/README.md` (contract); `plans/skills-relook/artifacts/lint-baseline-2026-09-25.json` (new).

### §8 Assumptions
- Growth thresholds (window 10, min +100, <20%) and dup thresholds (5-gram, ≥15 shingles, ≥0.30) tuned on one fleet snapshot 2026-09-25.

### §11 Risk Flags
- `cross-skill-duplicate` misses paraphrased copies (e.g. /concurrency GLM traps vs herdr §6) — found by reading, not the linter.
**ai-skills — doc (skills):** `concurrency/SKILL.md` 0.3.1→0.4.0 (dedup vs herdr, −45 lines); `herdr/SKILL.md` 0.1.3→0.1.4 (/freeze contradiction, wait primitive, TERMINFO note).
