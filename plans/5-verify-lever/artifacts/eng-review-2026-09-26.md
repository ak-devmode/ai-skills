# Eng review — scope 5 (verify-lever), 2026-09-26

**Mode:** FULL_REVIEW (HOLD SCOPE from CEO review honored; complexity trigger noted, not re-asked)
**Outside voice:** codex (`gpt-6-astra`, codex-cli 0.157.1), completed
**Test plan:** `artifacts/eng-review-test-plan-2026-09-26.md`

## 1. Findings (all accepted, 2026-09-26)

| # | Section | Finding | Remedy accepted |
|---|---|---|---|
| E1 | Architecture | reusing gstack's internal codex probe couples to upstream internals + its 1h failure cache | own ~20-line fresh probe per call |
| E2 | Code quality | TSV breaks on free-text evidence | JSONL + dispatch-log.py write-then-read-back |
| E3 | Architecture | plans-index.py has no status command; agents edit the index directly | `status` (preventive) + `validate` fails on unverified Done (detective, SessionStart surfaces) |
| E4 | Architecture | "current unit's range" undefined | ledger-init records per-repo base SHA at phase start; range = base..HEAD |
| E5 | Code quality | revisioned finish table inside write-once scope.md | own `finish-conditions.md` with changelog |
| E6 | Tests | no test entrypoint — script tests would never run | `scripts/tests` stdlib unittest + CLAUDE.md Test line |
| E7 | Performance | hung live check freezes /plan | per-row timeout (120 s default) → inconclusive |
| X1 | codex #1 | judge rows could never pass under downgrade-only | one-way authority on runner rows; judge rows take the judge verdict |
| X2 | codex #2 | no finalization protocol | pending → judged → final; judge bound to run_id; atomic; pending blocks |
| X3 | codex #3 | no per-unit check ownership | owner column; checkpoint runs owned rows, closeout all |
| X4 | codex #4 | runner commands lack execution context | repo / dir / env per row; resolved values in evidence |
| X5 | codex #5 | direct-to-main review sees an empty diff | explicit unit range passed to /review + /verify; empty = failure |
| X6 | codex #6 | closeout would archive a failing verdict as healed | no HEALED; archive + `⚠ verify failed` row + TO-DO |
| X7 | codex #7 | feature-map maintenance crosses closeout's repo boundary | handoff artifact; applied in the test-suite repo or /closeout-extended |
| X8 | codex #8 | closeout re-run manufactures a second sighting | candidates carry run_id + scope; only a different scope/run counts |
| X9 | codex #9 | fixtures passable by an always-failing judge | defect-specific findings, clean controls, repaired copies; judge:none fails the suite |

**Cross-model:** no disagreement; codex's 9 were all new, four of them defects in rules the
CEO review had just added.

## 2. Test coverage (planned code)
```
scripts/resolve-identifiers.py   4 kinds x {resolves, missing, comment-only, same-diff decl}, unsupported
scripts/verify-run.py            pass, fail, non-executable, timeout, context recorded, public refusal, read-back fail
scripts/verdict-gate.py          pass, missing, under-rung, fail→fixed, runner downgrade blocks, judge row passes,
                                 pending blocks, undeclared-unreachable, stale SHA, validate catches hand edit,
                                 fallback marker set/clear, advisory
/verify judge [→EVAL]            fixtures: defect-specific findings, controls pass, repaired pass, judge:none fails
/review on codex [→EVAL]         planted || true, workaround comment, invented env var; explicit range on main
three-outcome trial [→E2E]       pass, planted failure blocks, env unavailable
```

## 3. Failure modes
No critical gap: every new codepath above has a named failure, a test, and a visible result
(verdict row, gate output, index marker, or non-zero exit).

## 4. Parallelization
```
Lane A: 1.0 test entrypoint -> 1.2 resolve-identifiers   (scripts/, scripts/tests/)
Lane B: 1.1 contracts                                     (templates/)
Lane C: 1.3 runner -> 1.4 gate + plans-index + ledger-init (scripts/) — after 1.0 and 1.1
```
A and B can run in parallel; C waits for both (it implements B's contracts, tests land in A's
entrypoint). Lanes A and C both touch `scripts/` — run C after A merges. Phases 2 and 3 are
sequential (each consumes the previous).

## 5. Review report

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | CLEAR | HOLD_SCOPE, 0 critical gaps, 17 accepted |
| Outside Review | codex (`codex exec`, plan-review x2) | Independent 2nd opinion | 2 | completed | CEO 11 · eng 9 |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR | 16 issues, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | N/A | no UI |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | YES in scope checklist |

- **OUTSIDE COVERAGE:** codex, plan-review (CEO + eng), completed both; 20 findings total.
- **CROSS-MODEL:** Claude native + codex external — zero disagreements across both reviews; codex added 16 findings Claude missed, Claude added 12 codex didn't raise.
- **VERDICT:** CEO + ENG CLEARED — ready to implement.

NO UNRESOLVED DECISIONS
