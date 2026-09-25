# Scope 2 — skills-relook: the iterative skill-improvement loop

**Status:** 🔨 In progress — scoped 2026-09-23 (revisit; phase-1 audit + early remediation already landed)
**Created by:** Alex Knecht
**Primary repo (worktree):** `ai-skills` · branch `feature/skills-relook-opus5`
**Model target:** Opus 5.5 (`claude-opus-5-5`) — decided, not an output. Execution runs in a fresh 5.5 context.
**Inputs:** `plans/skills-relook/AUDIT.md` (phase-1 verdict) · memory `project_skills_relook_revisit_inputs.md`

---

## 1. Objective

Not "finish pruning the accreted skills." Build **an iterative loop that evals and
improves Alex's skills, dogfooded with his own skills** — the durable mechanism, not a
one-time cleanup. The phase-1 audit (`AUDIT.md`) already named the disease (accretion:
stale-for-their-own-size, determinism-as-prose, live contradictions) and the cure (move
determinism to scripts, facts to on-demand refs, delete what the harness owns, cap the
judgment layer). This scope builds the loop that applies that cure continuously.

## 2. The three collapsed threads

1. **Accretion linter = the spine (build now).** A custom linter catching AUDIT.md §1's
   defect classes — SKILL.md dilution/oversize, live contradictions, determinism-as-prose.
   High-value, cheap, holds the line forever. Dogfooded: the skills lint the skills.
   `claude plugin eval` (behavior regression, `--json` CI, ≥ v2.1.210) is **deferred** —
   authoring a suite per skill is expensive and speculative; build it on the *second
   sighting* of an actual skill regression, not up front (YAGNI, mirrors scope-5's lever rule).
2. **Model era = Opus 5.5.** Bump seats/pins `claude-opus-4-8` → `claude-opus-5-5`
   (locus: `herdr` §6 seat launch commands + any pins across skills/config). 5.0/5.5 were
   too verbose → rolled back to 4.8; the **conciseness floor** now in global
   `~/.claude/CLAUDE.md` is the harness that makes 5.5 obey-able. The loop measures
   obedience/verbosity as it slims each skill.
3. **`/concurrency` (scope 3) closed + archived** → enters the audit surface as a skill
   the loop evals.

## 3. Out of scope

Resuming the old remediation checklist mechanically · `/feedback` to Anthropic (build it
ourselves) · `plugin.json` monorepo restructure so `plugin validate` runs (weak
structure-checker, not worth it) · `plugin eval` suite authoring (deferred to second-sighting
regression, §2.1).

**Do NOT conflate with scope 5 (verify-lever).** They look similar (both "verify against a
source") but are different machines: **this scope verifies *skills* against their own quality
bar; scope 5 verifies *code/output/product* against its design source.** Kept separate by
decision — do not merge.

## 4. Phases

| # | Phase | Gate | Ends with |
|---|-------|------|-----------|
| 2.1 | **Accretion linter** (targets AUDIT.md §1 defects); dogfood on one skill first (`/concurrency`, fresh + small). Eval harness deferred. | C | linter flags/clears `/concurrency`, reviewable PR |
| 2.2 | **Model migration to 5.5** — bump seats/pins `→ claude-opus-5-5`; conciseness floor applied; loop measures obedience per skill | C | fleet on 5.5, verbosity within floor |
| 2.3 | **Apply the loop** to core skills — slim + model-tuned per the loop's verdicts | C | core skills re-passed through the loop, PR |

Gates are all C (reviewable units) — no human-blocking, deploy, or irreversible steps;
the model-seat switch (2.2) is reversible config.

## 5. Skill checklist

- `/plan-ceo-review` — **YES** (run on `scope.md`; catches "why a loop at all" reframes).
- `/plan-eng-review` — YES (linter + eval harness is real code).
- `/review` — YES per phase PR.
- `/plan-devex-review` — OPTIONAL (skills are the dev-facing surface).
- `/ship` — N/A (not in use).
- UI cluster (`/browse`, `/qa`, `/design-*`, `/setup-browser-cookies`, `/plan-design-review`) — **N/A x8** — no UI surface.
- `/investigate` — N/A — not a bug fix.
- Table Identity Map (4.5) — N/A — no DB write/DDL surface.
- `/document-release` — OPTIONAL. `/retro` — OPTIONAL. `/closeout` — YES at end.

## 6. Repo graph

Single-repo (`ai-skills`) for the loop + linter; `dev-workbench` touched for the global
conciseness floor (done 2026-09-23) and any seat-launch config. CROSS-REPO.md consumers
are not code consumers of this work — N/A to walk.

## 7. Open items for execution

- [ ] Linter form: standalone script in `scripts/` (matches AUDIT.md "determinism into scripts") vs a skill; decide in 2.1.
- [ ] Mode: HOLD SCOPE (ceo-review 2026-09-23) — rigor on the linter, resist boiling the eval-harness ocean.
- [ ] Does 5.5 + conciseness floor actually clear the verbosity that forced the 4.8 rollback — the measured gate of 2.2.
