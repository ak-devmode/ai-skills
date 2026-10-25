<!-- Contract: templates/verify-contracts.md §3. Writer: /scope (or /plan self-heal, Alex
     confirms). Readers: verify-run.py, verdict-gate.py, /verify, /closeout.
     A filled example is templates/examples/finish-conditions.md — never copy rows from it. -->
# Finish conditions — 10-decision-queue-harness

**Schema version:** verify/1
**Revision:** 2
**Approved:** pending
**Scope:** /Users/alexknecht/Projects/ai-skills/plans/10-decision-queue-harness/scope.md

One row per check. `check` is a shell command or the literal `judge`. A literal `|` in a
cell is `\|`. Every row is required; `unreachable_ok` is the only exemption, and it needs
Alex's reason.

| check_id | deliverable | owner | class | check | repo | dir | env | timeout | rung | unreachable_ok | evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| p1-names-resolve-ai-skills | Every identifier phase 10.1 references in ai-skills is declared | 10.1 | B | `python3 ~/Projects/ai-skills/scripts/resolve-identifiers.py --repo . --range $VERIFY_BASE..HEAD` | ai-skills | . | - | - | 4 | no | runner record |
| p1-names-resolve-dev-workbench | Every identifier phase 10.1 references in dev-workbench is declared | 10.1 | B | `python3 ~/Projects/ai-skills/scripts/resolve-identifiers.py --repo . --range $VERIFY_BASE..HEAD` | dev-workbench | . | - | - | 4 | no | runner record |
| p1-scope-deliverables | The scope's phase 10.1 deliverables landed as specified | 10.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p1-no-overbuild | No abstraction phase 10.1 did not need | 10.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p1-rejections-justified | Every /review rejection recorded for 10.1 is right | 10.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p2-names-resolve | Every identifier phase 10.2 references in ai-skills is declared | 10.2 | B | `python3 ~/Projects/ai-skills/scripts/resolve-identifiers.py --repo . --range $VERIFY_BASE..HEAD` | ai-skills | . | - | - | 4 | no | runner record |
| p2-scope-deliverables | The scope's phase 10.2 deliverables landed as specified | 10.2 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p2-no-overbuild | No abstraction phase 10.2 did not need | 10.2 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p2-rejections-justified | Every /review rejection recorded for 10.2 is right | 10.2 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p3-names-resolve | Every identifier phase 10.3 references in ai-skills is declared | 10.3 | B | `python3 ~/Projects/ai-skills/scripts/resolve-identifiers.py --repo . --range $VERIFY_BASE..HEAD` | ai-skills | . | - | - | 4 | no | runner record |
| p3-scope-deliverables | The scope's phase 10.3 deliverables landed as specified | 10.3 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p3-no-overbuild | No abstraction phase 10.3 did not need | 10.3 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p3-rejections-justified | Every /review rejection recorded for 10.3 is right | 10.3 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p4-names-resolve-ai-skills | Every identifier phase 10.4 references in ai-skills is declared | 10.4 | B | `python3 ~/Projects/ai-skills/scripts/resolve-identifiers.py --repo . --range $VERIFY_BASE..HEAD` | ai-skills | . | - | - | 4 | no | runner record |
| p4-names-resolve-dev-workbench | Every identifier phase 10.4 references in dev-workbench is declared | 10.4 | B | `python3 ~/Projects/ai-skills/scripts/resolve-identifiers.py --repo . --range $VERIFY_BASE..HEAD` | dev-workbench | . | - | - | 4 | no | runner record |
| p4-scope-deliverables | The scope's phase 10.4 deliverables landed as specified | 10.4 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p4-no-overbuild | No abstraction phase 10.4 did not need | 10.4 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p4-rejections-justified | Every /review rejection recorded for 10.4 is right | 10.4 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p1-unit-suite | ai-skills script suite passes, including new tests for packet.py (dead queue prints Blocked and exits 0, idempotent retry, wrong lane tag refused) and door.py (floor forces one-way, promote-only, renames/deletions count, fails closed) | 10.1 | B | `python3 -m unittest discover scripts/tests` | ai-skills | . | - | 600 | 4 | no | runner record |
| p1-queue-tests | Queue service test suite passes | 10.1 | B | ``uv run --directory queue pytest -q`` | dev-workbench | . | - | 600 | 4 | no | runner record |
| p1-queue-live-both-machines | The homelab queue is reachable over the tailnet and /api/stats shows real (non-test) packets from both the MBA and homelab | 10.1 | B | `curl -fsS "$DECISION_QUEUE_URL/api/stats" \| python3 -c "import json,sys; m=[x for x in json.load(sys.stdin).get('machines',[]) if not x.startswith('test')]; sys.exit(0 if any('homelab' in x for x in m) and any('homelab' not in x for x in m) else 1)"` | ai-skills | . | DECISION_QUEUE_URL=http://100.87.171.87:8787 | 60 | 5 | no | runner record |
| p1-reply-roundtrip | A real packet was answered by a pasted reply and closed by its own lane | 10.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p1-seam-unchanged | With no DECISION_QUEUE_URL, /plan and /concurrency behave exactly as before (inline numbered questions) | 10.1 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p2-unit-suite | ai-skills suite passes with findings-budget, reframe-judge, --reframed, round-1 effort and review-packet tests | 10.2 | B | `python3 -m unittest discover scripts/tests` | ai-skills | . | - | 600 | 4 | no | runner record |
| p2-exit-rule-replay | (id kept from rev 1; the exit rule was dropped in CEO review) A baseline lineage replayed through review.py: notes stop driving re-review, a reframe is judged with a recorded reason, and a re-proposed rejected reframe produces one packet | 10.2 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p3-driver-merge-observed | A driver-merged PR deployed to dev (image sha changed) and a floor-touching PR produced a packet instead of a merge | 10.3 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p4-unit-suite | ai-skills suite passes with scorecard tests | 10.4 | B | ``python3 -m unittest discover scripts/tests`` | ai-skills | . | - | 600 | 4 | no | runner record |
| p4-scorecard-reproduces | The scorecard re-run on the baseline window reproduces the corrected baseline (§3.1, rounds per lineage) within ±5 points | 10.4 | B | judge | ai-skills | . | - | - | 2 | no | judge reason |
| p4-ui-template | A UI packet renders old (deployed develop) and new (lane FE dev server) screenshots side by side | 10.4 | B | judge | dev-workbench | . | - | - | 2 | no | judge reason |
| p4-herdr-attention | A lane reaching PARTITION-DONE no longer raises the herdr attention count | 10.4 | B | judge | dev-workbench | . | - | - | 2 | no | judge reason |

## Changelog

| Rev | Date | Change | By |
|---|---|---|---|
| 1 | 2026-10-25 | Created | Alex |
| 2 | 2026-10-25 | CEO review: queue-down non-blocking + door fail-closed tests; live row gets env + /api/stats; phase 2 exit rule replaced by findings budget + reframe judge; scorecard counts per lineage | CEO review |
