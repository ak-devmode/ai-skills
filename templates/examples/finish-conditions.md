<!-- EXAMPLE — illustrative only. Rows 1–3 are scope 5's own; the class-A row uses a
     hypothetical test-suite CLI named `suite`. Contract: templates/verify-contracts.md §3. -->
# Finish conditions — 5-verify-lever

**Schema version:** verify/1
**Revision:** 2
**Scope:** ~/Projects/ai-skills/plans/5-verify-lever/scope.md

One row per check. `check` is a shell command or the literal `judge`. A literal `|` in a
cell is `\|`. Every row is required; `unreachable_ok` is the only exemption, and it needs
Alex's reason.

| check_id | deliverable | owner | class | check | repo | dir | env | timeout | rung | unreachable_ok | evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| scripts-tests-green | Script test suite passes | 5.1 | B | `python3 -m unittest discover scripts/tests` | ai-skills | . | - | - | 4 | no | runner record: exit 0 |
| contracts-no-example-rows | Templates generate without example rows | 5.1/1.1 | B | `python3 -m unittest scripts/tests/test_contracts.py` | ai-skills | . | - | 60 | 4 | no | runner record: exit 0 |
| contracts-cover-scope | Every §4.1 contract has a named reader and writer | 5.1/1.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason citing verify-contracts.md sections |
| sign-in-live | Sign-in journey works on the dev tenant | 5.2 | A | `suite sign-in --tenant clinic_3 --json` | wellmed/wellmed-testsuite | . | SUITE_ENV=dev | 180 | 5 | yes: dev VPN is not always up; unreachable is recorded, not passed silently | private runner record + screenshot in the test-suite |

## Changelog

| Rev | Date | Change | By |
|---|---|---|---|
| 1 | 2026-09-26 | Table created from scope.md §4.1 | Alex / Claude |
| 2 | 2026-09-26 | Added `sign-in-live` for the Phase 2 trial | Alex / Claude |
