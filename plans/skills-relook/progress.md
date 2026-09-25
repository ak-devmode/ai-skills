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
- **`/concurrency` pilot** ✅ DONE. 347 → 302 body lines with **no split** — cut copies of `herdr` content
  (§2 server/pane preconditions, env-leak + GLM traps, §6.1b layout/naming, §7.1 + §10 `--source recent`,
  §10 Ghostty/colors); rewrote the `/freeze` supersession as a plain rule; fixed stale design-record path.
  Fixed two defects in `herdr` the read surfaced: §4 still called workers "`/freeze`d" (live cross-skill
  contradiction with `/concurrency` §10) and §8 named `agent wait --until done` as the primary wait (hangs
  on codex). Kept the TERMINFO note in `herdr` §7 (was only in `/concurrency`). Lint: dup + supersession
  NOTEs cleared; only `size` remains. Files: `concurrency/SKILL.md` (0.4.0), `herdr/SKILL.md` (0.1.4).
- **`/plan` + `/closeout`** ✅ DONE. plan 852→818, closeout 842→784 body lines, no splits. Defects fixed:
  plan cited `§4.2`/`§4.3` (don't exist); §3.1 stamps the plan file while §8.1 said never modify it
  (contradiction → explicit exception); §3.1 missed stubs with no `Executed by` line (hit live this scope);
  §8.10 sat between 8.4 and 8.5 (moved, number kept). Both cited a memory file (`CLAUDE.md` §9.3 bans it).
  closeout §12.5–12.6 restated a memory format + "de-dup gap accepted" that contradict the harness's memory
  rules; "11-step engine" vs twelve steps; `SKILL.md:9` line citation; "v1.1" dry-run claim; missing 14.1
  label. Cut: plan changelog banner, ralph-loop + migration history, stale "/closeout not installed"
  fallback, closeout "used to say" blockquotes. De-duplicated: §4 entry format (owner /plan §7.7 +
  template) and residual-vs-trunk verification (owner /plan §11.1, absorbed closeout's grep-the-trunk detail).
  Lint: both plan↔closeout duplicate NOTEs cleared. Remaining plan↔scope dup = toolkit candidate #2.
- **`/scope` (+ `/prd`)** ✅ DONE. scope 826→792 body lines, no splits. Contradictions fixed: §5.9 +
  frontmatter said "each plan ≈ 1 context window" against Phase Boundaries' "context size is NOT a gate";
  §5.9 still wrote plan-stub index rows in the retired 7-column shape (the leak §5.8 exists to stop) → now
  `plans-index.py add`; "includes ALL 18" vs "emit only what applies"; `{N}` "from Step 5.7" (is 5.2).
  Cut: changelog banner, Step 0 `cat CLAUDE.md | head -60` (harness loads it), duplicate ambiguity-topics
  bullet, stale "extended skills not installed" fallback, duplicate append-only rule. 0.7.3→0.7.2 (no
  inbound refs; 8.x kept — `/ready-to-clear` cites 8.4). `/prd`: same CLAUDE.md cut, and it `cat`ed BOTH
  PLANS-INDEX files whole (~31k tokens WellMed) → resolve-plans-dir + grep.
  Remaining scope↔prd dup NOTEs = the shared context-gather block (toolkit candidate #3).
- **`/cross-repo-init`** ✅ DONE. 705→~680 body lines. Real bug: §2.1 `symbolic-ref | sed || echo main`
  never fell back (the `||` tests sed) → empty `DEFAULT_BRANCH` when `origin/HEAD` unset; fixed + tested in
  bash and zsh. Cut two memory-file citations and the instruction to add "memory pointers" to repo
  CLAUDE.md files. §7 restated the body (7.4a/7.8/7.11/7.12 + intro) → one-line rules pointing at the
  procedure; stale "v1.1 TO-DO" pointer cut. **Template defect with fleet reach:** `CLAUDE.md.template` §9.2
  wrote the pmg memory path into every scaffold → fixed; 13 repos already carry it → `plans/TO-DO.md`.
- **`/markdown-style`** ✅ DONE. Contradictions fixed: §10.1.1 gave child plans their own PROGRESS file
  (retired by /plan v3.3.0) + §10.3 schema lacked Operating Contract and per-plan sections; §8.9.2 "stub
  ships Draft, /plan deepens it" vs §8.2.2/"/plan refuses Draft" → the Draft→Ready flip is the human's go
  signal; §11.1.2 hardcoded plans paths (missing IRIS) vs §8.1.3 "never hardcode"; §11.7 intro "read into
  context… four rules keep it bounded" vs /plan §1.1 grep-don't-read + five rules; §1.2 "no emoji" vs the
  🔲/✅ markers /plan parses; stale `wellmed-system-architecture` + pre-numbering plan path. History
  blockquotes trimmed to one line. Also `/closeout` §13.1 still said "never append a per-plan row" against
  §11.7.5 + /plan §11.4 → fixed.
- **Linter: `memory-citation` ISSUE** ✅. The recurring defect of this pass (5 citations across 4 skills + a
  template) is deterministic → ISSUE tier. Last hit fixed (`closeout-extended` 1.0.1). Negative control:
  planted citation → exit 1; fleet → 0 ISSUE / 38 NOTE.
- **5.5 conciseness-floor log (2.2 + 2.3):** no flagrant breach. Checkpoint summaries ran ~15–25 lines —
  within the floor for multi-item reports, but the longest candidate for tightening. No lever needed.
- **5.5 conciseness-floor log:** see entry above.

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
| 8 | repo survey: default branch + branch classify (MERGED/LIVE, squash via `cherry`) + survey-branch cascade | `/cross-repo-init` §2.1–2.2 (and `/repo-cleanup`'s classifier) | pure git; the §2.1 bug shows prose shell drifts |

## Human Steps
| Step | Status |
|---|---|
| Clear + reload in Opus 5.5 with updated global prompt, then execute 2.1 | [x] Done (ran under 4.8; 5.5 seat is 2.2's concern) |
| Review 2.1 — `/review` done (SHIP, 8 bugs fixed in-band) | [x] Done |
| Open PR for `feature/skills-relook-opus5` | [x] N/A — Alex: no PR, push only (2026-09-25) |
| Merge `dev-workbench` `fix/opus-5-5-default` → `main` | [x] Done — ff to `227b0c2` (2026-09-25) |
