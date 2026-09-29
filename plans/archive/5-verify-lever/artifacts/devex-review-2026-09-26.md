# DX review (triage) — scope 5 (verify-lever), 2026-09-26

**Product type:** Claude Code skill suite + local CLI scripts · **Mode:** DX TRIAGE (install +
first verdict; Passes 1 and 3; skill checklist) · **Outside voice:** skipped (triage)

## 1. Persona
```
Who:       Kalpa/PMG teammate running /scope /plan /review /closeout in the Claude Code terminal
Context:   learns of the change from a "git pull ai-skills" announcement; the gate appears mid-/plan
Tolerance: low — didn't ask for a gate; it lands inside paid work
Expects:   skills just work after a pull; no new installs; no herdr
```

## 2. Developer perspective (before the review)
Pull, `./setup.sh` (README §2.1 — silent on codex and Python), restart. First `/plan`
checkpoint: `judge: claude-fallback (codex not installed)` and a ⚠ in PLANS-INDEX with no fix
shown; a row reads `inconclusive: timed out after 120s` with no hint whether it is their code
or the env; advisory mode lets them continue carrying two warnings. They have never seen a
passing verdict.

## 3. Journey (triage stages)
| Stage | Developer does | Friction | Status |
|---|---|---|---|
| Install | `git pull && ./setup.sh`, restart | codex/Python prerequisite invisible | fixed — setup warns with exact fix |
| First verdict | waits for a real checkpoint | no safe first run; no example of a pass | fixed — `/verify --demo` + README section |

## 4. Decisions
| # | Decision | Answer |
|---|---|---|
| D1 | Persona | as above |
| D2 | Time to first verdict | < 5 min: setup check + `/verify --demo` |
| D3 | First contact | `/verify --demo`, plus a README "Verification" orientation section |
| D4 | Mode | TRIAGE |
| G1 | Error contract | every new message: what · why · cause class (code/env/tooling) · next command · docs, actual values; tested |
| G2 | Setup when codex missing | warn with the fix, exit 0 |
| G3 | Stale ai-skills clone | `/verify` + `/plan` print one line when behind `origin/main` |

## 5. Scorecard
| Dimension | Before | After |
|---|---|---|
| Getting started | 3/10 | 8/10 (restart after pull is Claude Code's, not ours) |
| Error messages | 4/10 | 8/10 |
| Passes 2, 4–8 | not evaluated (triage) | — |
| Time to first verdict | > 10 min, work-dependent | < 5 min, 3 steps |
| Magical moment | missing | `/verify --demo`: the other model names planted defects |

## 6. Review report

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | CLEAR | HOLD_SCOPE, 17 accepted |
| Outside Review | codex (`codex exec`, plan-review x2) | Independent 2nd opinion | 2 | completed | CEO 11 · eng 9 |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR | 16 issues, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | N/A | no UI |
| DX Review | `/plan-devex-review` | Developer experience gaps | 1 | CLEAR | score 3.5/10 → 8/10, TTHW >10 min → <5 min |

- **OUTSIDE COVERAGE:** codex completed for CEO and eng plan reviews; skipped for DX (triage).
- **VERDICT:** CEO + ENG + DX CLEARED — ready to implement (`/plan 5.1`).

NO UNRESOLVED DECISIONS
