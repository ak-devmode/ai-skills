# Finish conditions — 5-verify-lever

**Schema version:** verify/1
**Revision:** 3
**Scope:** ~/Projects/ai-skills/plans/5-verify-lever/scope.md

One row per check. `check` is a shell command or the literal `judge`. A literal `|` in a
cell is `\|`. Every row is required; `unreachable_ok` is the only exemption, and it needs
Alex's reason. Phase 1 (5.1) rows were written retroactively at 5.2 Task 2.4 (dogfood); its
range is fixed: `8173b95..e3b74ec`.

| check_id | deliverable | owner | class | check | repo | dir | env | timeout | rung | unreachable_ok | evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| scripts-tests-green | The script test suite passes | 5.1 | B | `python3 -m unittest discover scripts/tests` | ai-skills | . | - | 300 | 4 | no | runner record |
| names-resolve | Every identifier Phase 1 references is declared | 5.1 | B | `python3 scripts/resolve-identifiers.py --repo . --range 8173b95..e3b74ec` | ai-skills | . | - | - | 4 | no | runner record |
| contracts-generate-clean | Templates generate without example rows; every contract names reader + writer | 5.1/1.1 | B | `python3 -m unittest discover scripts/tests -p test_contracts.py` | ai-skills | . | - | - | 4 | no | runner record |
| gate-semantics-tested | verdict-gate enforces §5 end to end | 5.1/1.4 | B | `python3 -m unittest discover scripts/tests -p test_verdict_gate.py` | ai-skills | . | - | 300 | 4 | no | runner record |
| scope-deliverables | scope.md §4.1 deliverables landed as specified | 5.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| no-overbuild | No abstraction Phase 1 did not need | 5.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| test-plan-followed | The eng-review test plan's edge cases and critical paths are covered | 5.3 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |

## Changelog

| Rev | Date | Change | By |
|---|---|---|---|
| 1 | 2026-09-26 | Created for the 5.1 dogfood (5.2 Task 2.4); Phase 1 rows retroactive | Alex / Claude |
| 2 | 2026-09-26 | `names-resolve` resolves Phase 1's refs against today's declarations (`--decl-rev HEAD`): the dogfood's first run found `VERIFY_PROJECTS` undeclared, now declared in `.env.example` | Alex / Claude |
| 3 | 2026-09-26 | Per the codex judge: `--decl-rev HEAD` moved the goalposts for a closed unit — reverted, so Phase 1 is judged against its own declarations (it fails; fixed in 5.2 `e4aaa0a`). `test-plan-followed` covers the whole scope's plan → owner 5.3 | Alex / Claude |
