# CEO review — scope 5 (verify-lever), 2026-09-26

**Mode:** HOLD SCOPE · **Approach:** C (scripts + runner evidence set the floor; codex judge
has one-way authority) · **Outside voice:** codex (`gpt-6-astra`, codex-cli 0.157.1), completed
**Reviewed:** scope.md, progress.md, 5.1–5.3 stubs, artifacts/scope-brief.md,
artifacts/research-poteto-2026-09-26.md · **Commit at review:** `dfa255c`

## 1. Step 0

### 1.1 Premise
A second-family judge is worth it, and there is evidence: `review/SKILL.md` §1.1.1 records
codex catching 2/2 fail-open bugs Claude's pass structurally missed (WellMed 108.6). Scripts
win where there is one right answer; the judge wins on judgment — over-building, whether
evidence proves the deliverable, whether a rejected finding was really wrong.

### 1.2 Decisions
| # | Decision | Answer |
|---|---|---|
| D1 | Approach: A scripts only (5/10) · B judge fills verdict (8/10) · C one-way authority (10/10) | **C** |
| D2 | Mode | **HOLD SCOPE** |
| D3 | Team codex access | Team has access, can't be forced to set it up → a non-codex judge must surface in PLANS-INDEX (became F6) |

## 2. Findings (all accepted, 2026-09-26)

| # | Section | Finding | Remedy accepted |
|---|---|---|---|
| F1 | Architecture | codex runs read-only; can't drive envs or `/browse` | Split /verify: deterministic runner (`verify-run.py`) + judge reading evidence only; `check` = command or `judge` |
| F2 | Errors | codex failure modes unnamed (model-unusable happened live this session) | Judge header codex/claude-fallback/none; no model pin; no failure mode can pass |
| F3 | Errors | resolve-identifiers silent green on unknown kinds | `found · resolved · unsupported` line; unsupported never passes |
| F4 | Security | trial wrote class-A evidence into the public repo | Class-A evidence private only; runner refuses public repos; permitted public fields listed |
| F5 | Tests | nothing verifies the verifier | Known-bad fixture scope `/verify` must fail |
| F6 | Observability | fallback invisible | `⚠ judge: <fallback>` in the phase's index status via plans-index.py; cleared by a later codex verdict |
| F7 | Deployment | a broken gate blocks the whole team on `git pull` | Advisory mode for the first 3 clean scopes, then blocking; `--skip-verify "<reason>"` loud |
| F8 | Long-term | lever backlog had no home | `## Lever candidates` in each project's `plans/TO-DO.md`; grep = second sighting |
| N1 | codex #1 | gate still a skill instruction | Enforced at the index: no Done without a gate pass |
| N2 | codex #2 | downgrade-to-inconclusive passed the gate | Required fail/inconclusive blocks; unreachable only where declared |
| N3 | codex #3 | evidence not bound to what it tested | SHA(s), deployed version, finish-table revision per row; stale SHA rejected |
| N4 | codex #4 | append-only + any-fail = never recovers | Stable `check_id` + `run_id`; latest run per check decides |
| N5 | codex #5 | grep isn't validation | v1 named kinds vs authoritative declarations, namespace-aware; counterexample tests |
| N6 | codex #6 | trial could pass without proving anything | Three outcomes through the runner: pass, planted failure blocks, env unavailable |
| N7 | codex #8 | /review-on-codex assumed | Capability spike on a real past diff first |
| N8 | codex #9 | findings could be dropped silently | Raw findings with stable IDs; every ID dispositioned; `fixed <sha>` touches the location |
| N9 | codex #11 | HTML-comment examples survive copying | Examples in `templates/examples/`; generated-file test |

**Cross-model:** no disagreement. Codex independently matched F1, F4, F6 and added seven —
two (N2, N4) broke the first draft of approach C. Sections with no issues: Code Quality,
Performance, Design (no UI).

## 3. Error & rescue registry

| Codepath | Failure | Rescued? | Result | Visible? |
|---|---|---|---|---|
| codex judge | not installed / not authed | Y | `judge: none <reason>` or claude-fallback | header + index ⚠ |
| codex judge | model unusable (CLI too old) | Y | same | header + index ⚠ |
| codex judge | timeout / empty / refusal | Y | `judge: none`, rows stay at runner result | header + index ⚠ |
| codex judge | malformed verdict | Y | treated as `judge: none` | header + index ⚠ |
| verify-run.py | row not executable | Y | `inconclusive` + reason → blocks if required | verdict row |
| verify-run.py | env unreachable | Y | `verified-unreachable` only if declared, else inconclusive | verdict row |
| verify-run.py | public repo target for class A | Y | refuse, exit non-zero | stderr |
| resolve-identifiers | unsupported kind | Y | counted, never pass | summary line |
| verdict-gate | stale SHA evidence | Y | rejected | gate output |
| plans-index.py | Done without gate pass | Y | refuse | exit non-zero |

## 4. Failure modes registry
No CRITICAL GAP remains after the accepted remedies (every failure above is rescued, tested
by the fixture or script self-tests, and visible).

## 5. Dream state delta
```
 NOW                        AFTER SCOPE 5                    12 MONTHS
 "done" = agent says so --> codex review per commit;    -->  feature map with live status +
 Alex's eye is the gate     runner evidence per unit;        evidence; tenants per env from
                            index shows fallback + gate      the test-suite program; PMG + IRIS
                            (advisory -> blocking)           on the same contract
```

## 6. Implementation tasks (synthesized)
- [ ] T1 (P1) contracts incl. gate semantics, evidence placement, examples dir — 5.1 Task 1.1 (F4, N2, N3, N4, N8, N9)
- [ ] T2 (P1) resolve-identifiers v1 with counterexample tests — 5.1 Task 1.2 (F3, N5)
- [ ] T3 (P1) verify-run.py runner — 5.1 Task 1.3 (F1, F4, N3)
- [ ] T4 (P1) verdict-gate + plans-index enforcement + fallback marker + advisory flag — 5.1 Task 1.4 (F6, F7, N1, N2, N4)
- [ ] T5 (P1) /verify runner+judge, judge header, no pin — 5.2 Task 2.1 (F1, F2, N8)
- [ ] T6 (P1) /review codex spike then migration — 5.2 Task 2.2 (N7, N8)
- [ ] T7 (P1) verifier fixtures — 5.2 Task 2.3 (F5)
- [ ] T8 (P1) three-outcome trial, private evidence — 5.2 Task 2.4 (F4, N6)
- [ ] T9 (P2) advisory→blocking rollout + --skip-verify — 5.3 Task 3.2 (F7)
- [ ] T10 (P2) lever candidates in TO-DO.md — 5.3 Task 3.3 (F8)

## 7. Review report

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | CLEAR | mode: HOLD_SCOPE, 0 critical gaps after 17 accepted remedies |
| Outside Review | codex (`codex exec`, plan-review) | Independent 2nd opinion | 1 | completed | 11 findings; 3 overlap, 7 new, 1 already covered |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 0 | — | next |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | N/A | no UI |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | YES in scope checklist |

- **OUTSIDE COVERAGE:** codex, plan-review, completed, 11 findings (all folded into N1–N9 or F-matches).
- **CROSS-MODEL:** Claude (native) + codex (external) — 3 shared findings, 7 codex-only, 5 Claude-only (F2, F3, F5, F7, F8); zero disagreements.
- **VERDICT:** CEO CLEARED — eng review required.

NO UNRESOLVED DECISIONS
