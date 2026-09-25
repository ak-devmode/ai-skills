# skills-relook — Progress

## Operating Contract (pinned — re-read on resume)
1. Execution posture: risk-on within `ai-skills`; work on `feature/skills-relook-opus5`, never commit to `main`.
2. Model: execution runs in a **fresh Opus 5.5 context** (target seat). This scope was authored under 4.8.
3. Mismatch handling: a scope↔code mismatch → investigate in context, don't bake past a premise.
4. Cadence: task → commit → next; checkpoint ~30–40 min.

## Resume Context (overwritable — reflects current state)
Scope authored + ceo-reviewed 2026-09-23 (revisit). Phase-1 `AUDIT.md` done; early remediation
already landed per PLANS-INDEX. Global conciseness floor committed (`dev-workbench` `e4c4074`).
ceo-review decisions logged below (linter now / eval deferred; scope 2 ≠ scope 5; HOLD SCOPE).
**2.1 DONE + REVIEWED (2026-09-23):** accretion linter `scripts/lint-skill.py` built + dogfooded on
`/concurrency` (1 ISSUE oversize + 1 NOTE cleared); fleet baseline in `artifacts/`. `/review` ran
(Claude adversarial + critical pass; codex DEGRADED), found + fixed 8 fail-open/false-positive bugs,
verdict SHIP (`artifacts/review-2.1-lint-skill.md`). Gate C met; no PR (Alex, 2026-09-25 — push only).
**2.2 DONE (2026-09-25):** fleet on 5.5 (live + tracked config); verbosity measurement folded into 2.3.
**2.3 IN PROGRESS (2026-09-25):** linter reframed (size advisory; growth + cross-skill-duplicate NOTEs).
**Next:** `/concurrency` pilot — remove copies of `herdr` content (§2 preconditions + GLM traps, §10 Ghostty
fix), then the core five. Log floor breaches + toolkit candidates as found. Open blockers: none.

## Decisions Log (append-only)
- 2026-09-23 — Reframe: scope = an iterative dogfooded skill-eval/improvement loop, not a cleanup pass. (Alex, Q2/Q3/Q4)
- 2026-09-23 — Model target = Opus 5.5, fixed up front (not an output). 4.8→5.5 with the conciseness floor as the verbosity harness. (Alex)
- 2026-09-23 — Linter built in-scope; no `/feedback` to Anthropic. `plugin.json` restructure out.
- 2026-09-23 (ceo-review) — Split: **accretion linter builds now** (spine); **`plugin eval` harness deferred** to second-sighting regression. Mode = HOLD SCOPE. (Alex)
- 2026-09-23 (ceo-review) — Scope 2 (skills) and scope 5 (verify-lever, code/output/product) stay **separate — do not conflate**. (Alex)
- 2026-09-25 — 2.2.3/2.2.4 (measure 5.5 verbosity, tune floor) **folded into 2.3**: 2.3 runs entirely on 5.5 and IS the measurement; log each floor breach per skill; a second sighting of the same breach triggers the deferred eval harness. Avoids building the harness ceo-review deferred. (Alex)
- 2026-09-25 — Stay on Opus 5.5 (5.0/5.1 disliked; 5.5 good so far). Tracked `dev-workbench` settings aligned to live `opus[1m]`, not symlinked. (Alex)
- 2026-09-25 — **250-line cap dropped as a bar.** Size is a symptom; splitting mandatory rules into `references/` makes them less likely to be followed. Linter: size ISSUE → NOTE; new NOTE checks `growth` (git history, deleted/added < 20% over last 10 modifying commits — git chosen over a snapshot baseline: nothing to go stale, same metric as AUDIT §1) and `cross-skill-duplicate` (word 5-gram containment ≥ 0.3; fleet: all hits real, zero noise; misses paraphrase). 2.3 now cuts superseded / harness-owned / contradictory / duplicated text; `references/` only for rare-branch content. (Alex)
- 2026-09-25 — **Standing lens for 2.3: toolkit candidates.** Deterministic, CLI-executable steps written as prose get logged in *Toolkit candidates* below as found (pulled back from scope 5's verify intent; model = `resolve-plans-dir.sh`, the ADR/scope resolvers). (Alex)

## Progress Log (append-only)
- 2026-09-23 — Scope authored (scope.md, progress.md, stubs 2.1–2.3). Conciseness floor added to global CLAUDE.md.
- 2026-09-23 — /plan | 2.1 complete — `scripts/lint-skill.py` built, dogfooded on `/concurrency`, fleet baseline captured; CLAUDE.md/README wired. At Gate C (review + PR pending). Executed by Alex / Claude.
- 2026-09-23 — /review | Gate C — Claude adversarial subagent + critical pass (codex DEGRADED: timed out). Found 8 fail-open/false-positive bugs, ALL fixed in-band + regression-tested. Fleet 16→13 ISSUE (prd dup was a false positive — fenced template example; retracted). Report: `artifacts/review-2.1-lint-skill.md`. Verdict SHIP.

## Plan 2.1: Accretion linter (loop harness)

**Status:** ✅ All tasks done — at Gate C (review + PR).

### Resume Context (Plan 2.1)
Linter built + proven. Verdict on `/concurrency`: 1 ISSUE (oversize 347>250, → 2.3) + 1 NOTE (cleared).
Nothing left in 2.1. Next scope action is 2.2. Dispositions + fleet worklist in
`artifacts/lint-baseline-2026-09-23.md`.

### Session: 2026-09-23 (Opus 4.8)
- **Task 2.1.1 — accretion linter** ✅ DONE. `scripts/lint-skill.py` (stdlib-only, fail-loud, `expected · found · where · next`). ISSUE tier: oversize / duplicate-section-number / frontmatter well-formedness / stale renamed-skill refs. NOTE tier: determinism-as-prose / supersession-site. Maps AUDIT §1.1/§1.2/§1.3 + §5.5/§5.6. Semantic contradiction (§5.3) deferred to eval pass.
  - Files: `scripts/lint-skill.py` (new).
  - Dogfooding caught + fixed two cry-wolf bugs (lettered-subsection collapse; benign "removed"). Negative-control fixture proved all four ISSUE checks fire (exit 1).
- **Task 2.1.2 — dogfood `/concurrency` + baseline** ✅ DONE. Verdict logged above; fleet baseline (26 skills: 16 ISSUE / 14 NOTE) → `artifacts/lint-baseline-2026-09-23.{md,txt,json}`. Acted on flags: oversize routed to 2.3, NOTE cleared, new `prd` dup-number finding recorded.
- **Task 2.1.3 — dogfood entrypoint** ✅ DONE. The `scripts/` script IS the entrypoint skills run against themselves; wired into `CLAUDE.md` §6 + §4 and `scripts/README.md` (table + contract).

## Plan 2.2: Model migration to Opus 5.5

**Status:** ✅ Done — 2 tasks done, 2 folded into 2.3 (Alex, 2026-09-25).

### Resume Context (Plan 2.2)
Plan complete. Fleet on 5.5 live and in tracked config (`dev-workbench` `fix/opus-5-5-default`,
pushed, merge pending). Verbosity measurement lives in 2.3 now.

### Session: 2026-09-25 (Opus 5.5)
- **Phase 0** ✅ DONE. Plan stub has no `Status`/`Executed by` fields (same as 2.1, which ran). Branch
  confirmed `feature/skills-relook-opus5`. Sibling plans + scope re-read. Ledger found, appending phase header.
- **Task 2.2.1 — bump `claude-opus-4-8` → `claude-opus-5-5`** ✅ DONE. Grep across ai-skills (excl. plans):
  no literal pins. Seats use the global default. Live `~/.claude/settings.json` = `"model": "opus[1m]"`
  (alias → 5.5; this session runs `claude-opus-5-5`) with `modelSettings.claude-opus-5-5.effortLevel: high`.
  Only drift in-repo: `herdr` §6 seat table said "Opus 4.8" — fixed.
  - Files: `herdr/SKILL.md` (seat row + re-verified date; 0.1.2 → 0.1.3; lint clean).
  - Found, not fixed: `dev-workbench/config/claude-code/settings.json:191` pins `claude-opus-4-8` (other repo).
- **Task 2.2.2 — conciseness floor active** ✅ DONE. `~/.claude/CLAUDE.md` symlinks to
  `dev-workbench/config/claude-code/CLAUDE.md`; "Conciseness floor" bullet present and loaded this session.
- **Task 2.2.3 — measure loop under 5.5** ⏭️ FOLDED into 2.3 (decision log 2026-09-25).
- **Task 2.2.4 — tune floor if breached** ⏭️ FOLDED into 2.3 (same).
#### Unplanned: align `dev-workbench` tracked settings to live
- **Files modified:** `dev-workbench/config/claude-code/settings.json` (`model` → `opus[1m]`; add
  `modelSettings.claude-opus-5-5.effortLevel: high`). Branch `fix/opus-5-5-default` off `origin/main`
  via a temp worktree (1password branch untouched); commit `227b0c2`, pushed. Why: reinstall would roll back to 4.8.

## Plan 2.3: Apply the loop to the core skills

**Status:** 🔨 In progress.

### Resume Context (Plan 2.3)
Linter reframed + fleet baseline `artifacts/lint-baseline-2026-09-25.json` (0 ISSUE / 45 NOTE, 26 skills).
Next: `/concurrency` pilot, then `/closeout`, `/cross-repo-init`, `/markdown-style` (growth NOTEs), `/plan`, `/scope`.

### Session: 2026-09-25 (Opus 5.5)
- **Phase 0** ✅ DONE. Plan stub reframed by decision (log 2026-09-25) — the 250-line target and
  "eval suite per skill" tasks are superseded; cure = cut superseded/harness-owned/contradictory/duplicated text.
- **Linter reframe** ✅ DONE. `scripts/lint-skill.py`: size → NOTE; + `growth` (git) + `cross-skill-duplicate`;
  `--no-history`. Verified: fleet run exit 0; non-git skill reports skipped growth check aloud; a skill named
  twice doesn't self-match. Files: `scripts/lint-skill.py`, `scripts/README.md`, `CLAUDE.md` §4/§6,
  `plans/skills-relook/artifacts/lint-baseline-2026-09-25.json`.
- **5.5 conciseness-floor log:** no breach observed in this session so far (2.2 + 2.3 start).

## Toolkit candidates (append as found — deterministic steps still written as prose)
| # | Candidate | Where it lives as prose now | Why deterministic |
|---|---|---|---|
| 1 | herdr pane identity + layout (rename, `report-metadata`, split-right-half) | `herdr` §2/§5, `/concurrency` §6.1b | fixed naming scheme + fixed geometry (Alex) |
| 2 | plan/scope folder create + related-file sweep (`mkdir`/`mv prd-{slug}*`) | `/plan` §2.5, `/scope` ~L643 — duplicated | fixed path derivation from slug; linter dup hit |
| 3 | session-start context gather (`cat CLAUDE.md \| head -60 …`) | `/prd` ~L67, `/scope` ~L100 — duplicated | fixed file list; linter dup hit |
| 4 | `Executed by` stamp from git config | `/plan` §3.1 | one correct answer |
| 5 | Repo Graph freshness classify (SHA/branch → unchanged/advanced/diverged/missing) | `/plan` §5.6.1 | pure git classification |
| 6 | closeout-prep.md bootstrap from template + phase header | `/plan` §5.13 | template copy + timestamp |
| 7 | dispatch-log JSONL append | `/concurrency` §6.4 | fixed record shape |

## Human Steps
| Step | Status |
|---|---|
| Clear + reload in Opus 5.5 with updated global prompt, then execute 2.1 | [x] Done (ran under 4.8; 5.5 seat is 2.2's concern) |
| Review 2.1 — `/review` done (SHIP, 8 bugs fixed in-band) | [x] Done |
| Open PR for `feature/skills-relook-opus5` | [x] N/A — Alex: no PR, push only (2026-09-25) |
| Merge `dev-workbench` `fix/opus-5-5-default` → `main` | [x] Done — ff to `227b0c2` (2026-09-25) |
