<!-- Contract: templates/verify-contracts.md §3. Writer: /scope (or /plan self-heal, Alex
     confirms). Readers: verify-run.py, verdict-gate.py, /verify, /closeout.
     A filled example is templates/examples/finish-conditions.md — never copy rows from it. -->
# Finish conditions — 7-lean-review-verify

**Schema version:** verify/1
**Revision:** 1
**Approved:** rev 1 — Alex, 2026-10-02
**Scope:** plans/7-lean-review-verify/scope.md

One row per check. `check` is a shell command or the literal `judge`. A literal `|` in a
cell is `\|`. Every row is required; `unreachable_ok` is the only exemption, and it needs
Alex's reason.

| check_id | deliverable | owner | class | check | repo | dir | env | timeout | rung | unreachable_ok | evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| p1-names-resolve | Every identifier phase 7.1 references in ai-skills is declared | 7.1 | B | `python3 ~/Projects/ai-skills/scripts/resolve-identifiers.py --repo . --range $VERIFY_BASE..HEAD` | ai-skills | . | - | - | 4 | no | runner record |
| p1-scope-deliverables | The scope's phase 7.1 deliverables landed as specified | 7.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p1-no-overbuild | No abstraction phase 7.1 did not need | 7.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p1-rejections-justified | Every /review rejection recorded for 7.1 is right | 7.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p1-tests-green | The script suite passes, including the new lean, mode and run-cap tests | 7.1 | B | `python3 -m unittest discover scripts/tests` | ai-skills | . | - | 600 | 4 | no | unittest output |
| p1-skills-lint | review and verify SKILL.md have no linter issues | 7.1 | B | `python3 scripts/lint-skill.py review verify --no-notes` | ai-skills | . | - | - | 4 | no | lint output |

## Changelog

| Rev | Date | Change | By |
|---|---|---|---|
| 1 | 2026-10-02 | Created | Alex / Claude |
