# /review — ai-skills @ `14954fc4e1c04c22e762154eceeb7f8ab4f68007..3e1517e3acae01d20dc8b23a6467a6145bf191fc` (8 commits)

**Review:** `10.2-r1` · **Reviewer:** claude-fallback codex out of credits (operator) · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits (operator)` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits (operator)` (and the index carries it) until a codex re-review of this unit.
**Findings:** 3 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.2 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>")`

## BLOCKING (1)

- **10.2-r1-01** `review/scripts/review.py:1100` (fail-open) — `dispose --reframed ... --by judge` is accepted on the driver's word: reframe_check only regex-matches `--by` against ^(judge|user)\b, and verdict-gate.py:153 applies the same regex. Neither looks for a `reframe-verdict` record with verdict `accepted` whose reframe `removes` this finding, so the 'fresh judge, never the driver' property from scope §4.2 / Task 2.2 is not enforced anywhere. A driver can dispose any finding, blocking included, as `reframed --by judge` with any post-review commit. The gate then counts it like a deferral, and /verify never audits it as a rejection. The only backstop is that some later review's range contains the commit, which never checks that the original finding went away. The same applies to an accepted reframe that `overturns` a recorded decision: the [REFRAME] stop is printed text only, and `--by judge` still passes. → The class is a claimed provenance with no check against the log. `--by judge`: require the latest `reframe-verdict` of a review in the finding's lineage to be `accepted`, with no `overturns`, and with this finding in its reframe's `removes`. Refuse otherwise, in dispose, and block it in the gate as well. `--by user`: keep it, but record and show it as the user's call. Check that the 'accepted but overturns' path cannot be recorded as `--by judge`.

## SHOULD FIX (1)

- **10.2-r1-02** `scripts/verify_lib.py:491` (engine) — The lineage fix applies retroactively to every existing review log, and only rules_version is versioned (decision 65), not the lineage rule. I re-ran the gate, old vs new, over all 299 review logs under ~/Projects. Archived unit kalpa-docs 194.1 gains `BLOCK rereview:194.1-r7-01`. Under the old rule, r6 (base == r5's head) continued r5 → r7 was round 3 → capped, and the recorded `accept` stood in for the re-review. Under the new rule r5 has no `fixed` disposition, so r6 roots a new lineage, r7 is round 2, and the stop no longer stands. 11 logs change `capped` membership in total. Second failure mode: for base == phead the old code decided without git, but `_range_holds` now runs `git rev-list` and returns None when history is pruned or unreadable. The review is then 'unsure' and joins the repo's highest-round lineage. On 149.2 this moves r36 from round 2 to 8 and r23 from 3 to 5, and in principle it can merge an unrelated lineage into a capped one. → Version the lineage rule the way decision 65 versions the loop rules. A review record without `rules_version` >= 2 keeps the old `base == phead` continuation, so closed units' stops stand. Apply the fix-sha test only to stamped records. Add a regression test with a pre-cutover log in the 194.1 shape: an accept-stop at old round 3 still satisfies the gate.

## NOTE (1)

- **10.2-r1-03** `review/scripts/review.py:365` (engine) — `prepare` without --scope/--unit assumes round 1 and RULES_VERSION. So `effort:` prints the trial-bumped tier even for a lineage rooted before the cutover, which decision 65 says keeps its own effort. `record` (with --scope) recomputes `effort`/`effort_base` from the lineage's real rules and not from the tier codex actually ran at. The stamp the scorecard compares can therefore disagree with the run. → Either have record stamp the effort codex-exec was actually given (pass it through), or print a WARN from prepare when it ran without --scope/--unit that the effort shown assumes rules 2.

## Checked and clear

check_continues refuses a --continues that names no earlier same-repo review, fill_template single-pass substitution (diff text containing {{...}} is not re-substituted), validate() back-compat: answers without reopens/reframe default to null, chains() cycle guard and rules>=2 gating, reframe-record downgrade-only: accept without meets_objective/simplifies/deletes becomes rejected, budgeted_note only relaxes off-anchor note re-review under rules 2+, round 2+, gate: reframed commit must land and must not predate the finding; capped-accept stop never stands in for a reframe, EFFORT_LEVELS matches codex-exec.py --effort choices, test suite: python3 -m unittest discover scripts/tests — 343 tests OK (2 skipped)

## Not applicable

Kalpa/PMG domain groups (generic repo), Task 2.5 packets (not in range; waits on 10.1 packet.py)

**Verdict:** SHIP AFTER BLOCKING

## What this review did not cover

- codex: out of credits per operator; Claude single-context fallback
- gstack engine not executed in full and specialist fan-out (security, testing, red-team, etc.) not dispatched: a focused single-context pass over review.py, verdict-gate.py and verify_lib.py, plus the SKILL.md §5 rules
- gstack-review-log telemetry not written or read back (read-only review pane)
- prompts (review.md, review-lean.md, reframe-judge.md) and test_review.py read only by diff skim, not line by line
- reframe judge not run end to end against codex
