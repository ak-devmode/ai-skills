# /review — ai-skills @ `352f53a8191086e19a49f6af40bf0cd99f96c437..95d20cee7bc190f855c3bb21e023105fb2f9e5cc` (4 commits)

**Review:** `10.2-r4` · **Reviewer:** codex gpt-6.1-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**Findings:** 3 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.2 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>")`

## BLOCKING (2)

- **10.2-r4-01** `review/scripts/review.py:1683` (fail-open 2) — The repeat hold is enforced only by reframe-prepare. reframe-record can still accept the repeated proposal, print “build it”, and authorize --by judge without the user's decision. Reproduced in memory: repeat_of detected the earlier rejection, but recording an acceptance returned 0 and judge_took returned None. → Check repeat_of under the recording lock before granting acceptance; repeated or uncheckable proposals must remain the user's call. Ensure disposition and gate consumers enforce that hold too.
- **10.2-r4-02** `review/scripts/review.py:1471` (fail-open 2) — Door paths are repo-relative, but finding paths can be absolute. The raw comparison misses an absolute migration finding even when door.py reports that migration as one-way. The new user_call logic consequently records no hold and permits --by judge. An in-memory probe classified the absolute path as two-way and the equivalent relative path as one-way. → Normalize finding anchors into the reviewed checkout's relative paths before matching door hits; hold when an anchor cannot be resolved safely.

## SHOULD FIX (1)

- **10.2-r4-03** `review/scripts/review.py:1539` (engine Enum & Value Completeness) — Case 2 considers every historical acceptance instead of each reframe's latest verdict. Re-recording an accepted reframe as rejected or as requiring the user still leaves its old acceptance suppressing stuck packets indefinitely. Reproduced with an acceptance followed by rejection: packet_stuck returned None. → Reduce reframe verdicts to the latest record per review, then test acceptance and judge_may_take, matching judge_took's semantics.

## NOTE (0)


## Checked and clear

Lenses §1: all six touched files and relevant adjacent functions read, Lenses §4: local maxima and invented references, Lenses §5: dirty comments, Gate integrity: changed test hunks inspected; no unjustified relaxation found, Python syntax: all five touched Python files compile in memory, Skill lint: passed with two advisory notes, git diff --check: passed for the specified range

## Not applicable

Domain rules: generic repository, SQL, ORM fields, data migrations and database races, Async endpoints, frontend rendering and cross-language type coercion, Time-window calculations and new timing assertions, CI/CD and artifact publishing, Build: CLAUDE.md §6 declares no build

**Verdict:** SHIP AFTER BLOCKING

## What this review did not cover

- Complete unittest verification: attempted python3 -m unittest discover scripts/tests, but filesystem tests cannot create temporary fixture directories in the read-only sandbox.
- Approval-class check: attempted the required command; it exited 3 because it resolves the supplied SHA as origin/<SHA> and reported APPROVAL_SOURCE_UNAVAILABLE.
- Live Claude Code skill invocation: unavailable in this review environment.
- Specialist sub-reviewers: delegation was not authorized for this gate.
