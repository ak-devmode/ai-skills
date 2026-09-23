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
verdict SHIP (`artifacts/review-2.1-lint-skill.md`). Gate C met. **Next: 2.2** (model migration to
Opus 5.5). Open blockers: none. Branch `feature/skills-relook-opus5` has NO remote yet — push on Alex's say-so.

## Decisions Log (append-only)
- 2026-09-23 — Reframe: scope = an iterative dogfooded skill-eval/improvement loop, not a cleanup pass. (Alex, Q2/Q3/Q4)
- 2026-09-23 — Model target = Opus 5.5, fixed up front (not an output). 4.8→5.5 with the conciseness floor as the verbosity harness. (Alex)
- 2026-09-23 — Linter built in-scope; no `/feedback` to Anthropic. `plugin.json` restructure out.
- 2026-09-23 (ceo-review) — Split: **accretion linter builds now** (spine); **`plugin eval` harness deferred** to second-sighting regression. Mode = HOLD SCOPE. (Alex)
- 2026-09-23 (ceo-review) — Scope 2 (skills) and scope 5 (verify-lever, code/output/product) stay **separate — do not conflate**. (Alex)

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

## Human Steps
| Step | Status |
|---|---|
| Clear + reload in Opus 5.5 with updated global prompt, then execute 2.1 | [x] Done (ran under 4.8; 5.5 seat is 2.2's concern) |
| Review 2.1 — `/review` done (SHIP, 8 bugs fixed in-band) | [x] Done |
| Open PR for `feature/skills-relook-opus5` (first push — no remote yet) | [ ] Pending (gated on Alex) |
