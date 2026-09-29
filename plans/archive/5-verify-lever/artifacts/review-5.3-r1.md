# /review — ai-skills @ `5f06a4c830f932b2cd083750d3cacaa3c0c7b230..5e5d3a265de4fa16e5936a690a9e5029ed3a6d88` (8 commits)

**Review:** `5.3-r1` · **Reviewer:** codex gpt-6-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**Findings:** 9 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 5.3 --finding <ID> (--fixed <sha> | --rejected "<reason>")`

## BLOCKING (3)

- **5.3-r1-01** `scripts/finish-table.py:230` (engine) — `init` requires a `--phase`, but `/plan` §5.6.2a directs it to create a table with only `--predates` when every phase has started. That self-heal path always exits with a usage error. → Allow zero `--phase` arguments when `--predates` is nonempty, and test the all-started case.
- **5.3-r1-02** `scope/SKILL.md:704` (engine) — Commitless phases retain a Verify task and receive a judge row, but `judge.py prepare` requires a nonempty commit range for every row’s repo. `/verify` therefore stops before judging these phases. → Define and implement a verification path for commitless phases that does not require an invented commit range.
- **5.3-r1-03** `plan/SKILL.md:446` (fail-open) — The new workflow promises review before Done, but `verdict-gate.py` checks dispositions only if a review log exists. A code phase with passing finish rows and no `/review` run can be marked Done. → Make the gate require review records covering each declared code repo and revision range before accepting Done.

## SHOULD FIX (6)

- **5.3-r1-04** `closeout/SKILL.md:213` (engine) — The requested `--all --json` output puts only check IDs in each unit’s `blocks`. It never puts `no final verdict` or `an unfinished run` there, so the prescribed test cannot identify units that need `/verify` before archive. → Return structured block reasons with each unit, then use those reasons for the retry decision.
- **5.3-r1-05** `scripts/plans-index.py:538` (fail-open) — `gate-count` treats an archived scope as clean solely because its index rows lack ⚠. It does not check a passing verdict or even require a gated row, so an all-predating or unverified table can advance the five-scope blocking threshold. Passing an index explicitly alongside `--discover` can count it twice. → Deduplicate index paths and count only scopes with at least one gated unit whose `--all` verdict passes.
- **5.3-r1-06** `scripts/lever-candidates.py:59` (silent-failure) — If a finalized judged run’s raw judge JSON is missing, `collect` silently uses `{}` and drops every judge-named lever candidate, while closeout can report that there are none. → Require readable raw judge output for a run judged by a model; return an evaluation error when it is missing.
- **5.3-r1-07** `verify/scripts/judge.py:162` (engine) — Judge-produced lever candidates are checked for `lever_id` shape, but their `check_id` is not checked against this run’s checks. An invented ID can enter the TO-DO ledger with `Touches: ?` and be counted as a later sighting. → Reject lever candidates whose `check_id` is absent from `check_ids`.
- **5.3-r1-08** `scripts/clone-behind.py:45` (silent-failure) — `FETCH_HEAD` can be refreshed by a fetch of another branch. The script then skips fetching `main` and can print nothing while `origin/main` is stale, contrary to its freshness claim. → Track the time of a successful `origin main` fetch specifically, or fetch that ref on every check.
- **5.3-r1-09** `verify/SKILL.md:125` (doc-claim) — This live skill instruction still says the advisory gate lasts until three clean scopes; the configured threshold and the other updated instructions say five. → Change the threshold here to five.

## NOTE (0)


## Checked and clear

Engine shell-injection checks on changed Python subprocess calls, Dirty-comment lens on changed implementation comments, Mechanical skill lint: zero issues for scope, plan, closeout, and verify

## Not applicable

Domain rules: this revision is in the generic ai-skills repo, Engine SQL and ORM data-safety checks: no database code in the range, Engine async endpoint, frontend, and time-window checks: no such runtime surface in the range, Distribution CI and publish checks: no release workflow or new packaged artifact in the range

**Verdict:** DO NOT SHIP

## What this review did not cover

- Run the Python unittest suite: the read-only sandbox prevents its temporary repositories, fixtures, and logs from being written.
- Exercise setup, finish-table, ledger, and closeout end to end: the required filesystem writes are unavailable.
- Run the network freshness fetch or live codex demo: network access is restricted.
- Run parallel specialist sub-reviews: agent delegation is not authorized for this review.
