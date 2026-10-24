<!-- Contract: templates/verify-contracts.md §3. Writer: /scope (or /plan self-heal, Alex
     confirms). Readers: verify-run.py, verdict-gate.py, /verify, /closeout.
     A filled example is templates/examples/finish-conditions.md — never copy rows from it. -->
# Finish conditions — 9-generated-plans-index

**Schema version:** verify/1
**Revision:** 1
**Approved:** pending
**Scope:** /Users/alexknecht/Projects/ai-skills/plans/9-generated-plans-index/scope.md

One row per check. `check` is a shell command or the literal `judge`. A literal `|` in a
cell is `\|`. Every row is required; `unreachable_ok` is the only exemption, and it needs
Alex's reason.

| check_id | deliverable | owner | class | check | repo | dir | env | timeout | rung | unreachable_ok | evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| p1-names-resolve | Every identifier phase 9.1 references in ai-skills is declared | 9.1 | B | `python3 ~/Projects/ai-skills/scripts/resolve-identifiers.py --repo . --range $VERIFY_BASE..HEAD` | ai-skills | . | - | - | 4 | no | runner record |
| p1-scope-deliverables | The scope's phase 9.1 deliverables landed as specified | 9.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p1-no-overbuild | No abstraction phase 9.1 did not need | 9.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p1-rejections-justified | Every /review rejection recorded for 9.1 is right | 9.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p2-scope-deliverables | The scope's phase 9.2 deliverables landed as specified | 9.2 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p3-names-resolve-kalpa-docs | Every identifier phase 9.3 references in kalpa-docs is declared | 9.3 | B | `python3 ~/Projects/ai-skills/scripts/resolve-identifiers.py --repo . --range $VERIFY_BASE..HEAD` | wellmed/kalpa-docs | . | - | - | 4 | no | runner record |
| p3-names-resolve-kalpa-iris | Every identifier phase 9.3 references in kalpa-iris is declared | 9.3 | B | `python3 ~/Projects/ai-skills/scripts/resolve-identifiers.py --repo . --range $VERIFY_BASE..HEAD` | wellmed/kalpa-iris | . | - | - | 4 | no | runner record |
| p3-names-resolve-pmg-docs | Every identifier phase 9.3 references in pmg-docs is declared | 9.3 | B | `python3 ~/Projects/ai-skills/scripts/resolve-identifiers.py --repo . --range $VERIFY_BASE..HEAD` | pmg/pmg-docs | . | - | - | 4 | no | runner record |
| p3-names-resolve-ai-skills | Every identifier phase 9.3 references in ai-skills is declared | 9.3 | B | `python3 ~/Projects/ai-skills/scripts/resolve-identifiers.py --repo . --range $VERIFY_BASE..HEAD` | ai-skills | . | - | - | 4 | no | runner record |
| p3-scope-deliverables | The scope's phase 9.3 deliverables landed as specified | 9.3 | B | judge | wellmed/kalpa-docs | . | - | - | 2 | no | judge reason |
| p3-no-overbuild | No abstraction phase 9.3 did not need | 9.3 | B | judge | wellmed/kalpa-docs | . | - | - | 2 | no | judge reason |
| p3-rejections-justified | Every /review rejection recorded for 9.3 is right | 9.3 | B | judge | wellmed/kalpa-docs | . | - | - | 2 | no | judge reason |
| p1-unit-suite | ai-skills script suite passes, including new tests for records, render, migrate, check and every changed reader | 9.1 | B | `python3 -m unittest discover scripts/tests` | ai-skills | . | - | 600 | 4 | no | runner record |
| p1-no-hand-edit-prose | No skill instructs a direct edit or append of PLANS-INDEX.md | 9.1 | B | `! grep -rnE 'Append to .{0,40}PLANS-INDEX\|edit PLANS-INDEX.md by hand' --include=SKILL.md --include=AGENTS.md .` | ai-skills | . | - | - | 4 | no | runner record |
| p1-concurrent-writes-disjoint | Two writes to different scopes touch disjoint files and never the shared index in bot mode | 9.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p2-closed-scopes-archived | 168, 155 and 161 sit under archive/ with no Active rows left; Alex-confirmed pmg scopes archived | 9.2 | B | judge | wellmed/kalpa-docs | . | - | - | 2 | no | judge reason |
| p3-check-passes-all-graphs | plans-index.py check passes on all four graphs after migration | 9.3 | B | `for d in wellmed/kalpa-docs/plans pmg/pmg-docs/plans wellmed/kalpa-iris/iris-docs/plans ai-skills/plans; do python3 scripts/plans-index.py check ~/Projects/$d \|\| exit 1; done` | ai-skills | . | - | 300 | 4 | no | runner record |
| p3-iris-gate-blocking | IRIS gate mode still resolves to blocking after its index prose moves | 9.3 | B | `python3 -c "import sys,os; sys.path.insert(0,'scripts'); import verify_lib as v; print(v.gate_mode(os.path.expanduser('~/Projects/wellmed/kalpa-iris/iris-docs/plans/I1-acquire')))" \| grep -qx blocking` | ai-skills | . | - | - | 4 | no | runner record |
| p3-bot-observed | On kalpa-docs origin/main the bot rendered a record-only push and overwrote a hand edit with its note | 9.3 | B | judge | wellmed/kalpa-docs | . | - | - | 2 | no | judge reason |

## Changelog

| Rev | Date | Change | By |
|---|---|---|---|
| 1 | 2026-10-24 | Created | Alex |
