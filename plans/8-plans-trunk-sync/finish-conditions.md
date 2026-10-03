<!-- Contract: templates/verify-contracts.md §3. Writer: /scope (or /plan self-heal, Alex
     confirms). Readers: verify-run.py, verdict-gate.py, /verify, /closeout.
     A filled example is templates/examples/finish-conditions.md — never copy rows from it. -->
# Finish conditions — 8-plans-trunk-sync

**Schema version:** verify/1
**Revision:** 1
**Approved:** pending — Alex
**Scope:** plans/8-plans-trunk-sync/8-plans-trunk-sync-PLAN.md

One row per check. `check` is a shell command or the literal `judge`. A literal `|` in a
cell is `\|`. Every row is required; `unreachable_ok` is the only exemption, and it needs
Alex's reason.

| check_id | deliverable | owner | class | check | repo | dir | env | timeout | rung | unreachable_ok | evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| p1-names-resolve | Every identifier phase 8.1 references in ai-skills is declared | 8.1 | B | `python3 ~/Projects/ai-skills/scripts/resolve-identifiers.py --repo . --range $VERIFY_BASE..HEAD` | ai-skills | . | - | - | 4 | no | runner record |
| p1-tests-green | The script suite passes, including the eight plans-publish cases | 8.1 | B | `python3 -m unittest discover scripts/tests` | ai-skills | . | - | 600 | 4 | no | unittest output |
| p1-skills-lint | plan/SKILL.md has no linter issues | 8.1 | B | `python3 scripts/lint-skill.py plan --no-notes` | ai-skills | . | - | - | 4 | no | lint output |
| p1-scope-deliverables | The plan's §2 design landed as specified: paths-only staging, halt on conflict, read-back on origin | 8.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p1-no-overbuild | No abstraction phase 8.1 did not need | 8.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |

## Changelog

| Rev | Date | Change | By |
|---|---|---|---|
| 1 | 2026-10-03 | Created | Alex / Claude |
