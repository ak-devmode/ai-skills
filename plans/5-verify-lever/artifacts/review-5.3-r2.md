# /review — ai-skills @ `5e5d3a265de4fa16e5936a690a9e5029ed3a6d88..530874f7000381f5b48150418f940367a11bf7b7` (12 commits)

**Review:** `5.3-r2` · **Reviewer:** codex gpt-6-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**Findings:** 5 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 5.3 --finding <ID> (--fixed <sha> | --rejected "<reason>")`

## BLOCKING (3)

- **5.3-r2-01** `verify/scripts/judge.py:97` (fail-open) — For a commitless unit with no recorded base, --no-commits skips the range check entirely. Commits made in the row's repo can therefore be judged without a diff or a required review. → Record a phase-start base for the repo and require zero commits in base..HEAD; fail when the base or count is unavailable.
- **5.3-r2-02** `scripts/verdict-gate.py:130` (fail-open) — A failed git rev-list returns None and is treated as zero commits. The mandatory-review check silently skips a repo or base it cannot evaluate. → Block on None with the git error; skip only a confirmed count of zero.
- **5.3-r2-03** `scripts/verdict-gate.py:134` (fail-open) — Review coverage only checks that the reviewed head follows the unit base. A review on a discarded branch, or one preceding a blocking finding's fix, can satisfy the gate while the relevant commits remain unreviewed. The latter contradicts /plan §6.8. → Require the reviewed head to be on the current branch and require a later review covering each fixed blocking finding's commit.

## SHOULD FIX (2)

- **5.3-r2-04** `scripts/clone-behind.py:56` (engine) — An unwritable stamp raises an uncaught OSError after a successful fetch, so this startup check exits nonzero before reporting freshness despite its stated never-fail contract. → Handle stamp-write errors and continue to the revision count; a failed cache write need not discard a successful fetch.
- **5.3-r2-05** `scripts/finish-table.py:159` (engine) — A blank or comma-only --predates value passes this truthiness check but parses to no units. init then succeeds with a table containing neither gated nor predating phases. → Parse --predates before this check and require at least one parsed phase or predating unit.

## NOTE (0)


## Checked and clear

Engine: shell injection in changed subprocess calls, Engine: judge-output shape and known-check validation, Local-maxima: new paths and CLI flags resolve to their implementations, Dirty comments: changed comments do not excuse a workaround, Changed skill files: lint reports zero issues, Changed Python files: AST parsing succeeds, Revision diff: git diff --check succeeds

## Not applicable

Domain rules: this is the generic ai-skills repo, Engine: SQL, ORM, and database-field safety, Engine: async endpoints, frontend views, and time-window logic, Engine: distribution and publish pipeline checks

**Verdict:** DO NOT SHIP

## What this review did not cover

- Network access is restricted; the origin/main freshness fetch could not be exercised.
- No running service was available for live integration checks.
- No browser session was available for browser checks.
- The read-only filesystem prevented the unittest suite and write-based fixtures from running.
- Parallel specialist sub-reviews were not run; delegation was not authorized for this review.
