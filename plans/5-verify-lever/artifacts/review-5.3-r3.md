# /review — ai-skills @ `530874f7000381f5b48150418f940367a11bf7b7..45b9788fe63d1ee45527144beddd9afd790b1b8f` (5 commits)

**Review:** `5.3-r3` · **Reviewer:** codex gpt-6-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**Findings:** 3 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 5.3 --finding <ID> (--fixed <sha> | --rejected "<reason>")`

## BLOCKING (1)

- **5.3-r3-01** `scripts/clone-behind.py:46` (fail-open) — A directory at the stamp path is treated as a fresh, successful fetch. With the default max-age, the check skips fetching and can silently report nothing while the clone is behind. The new test creates this directory but forces max-age to zero, so it misses this path. → Accept only a valid regular stamp file as freshness evidence; otherwise fetch and test the default max-age path.

## SHOULD FIX (2)

- **5.3-r3-02** `scripts/clone-behind.py:59` (silent-failure) — A stamp-write error is swallowed. When no stamp can be written, every invocation fetches again, silently defeating the documented max-age limit. → Report the cache-write failure while continuing to report the fetch result.
- **5.3-r3-03** `plans/TO-DO.md:361` (doc-claim) — The claim that `/scope` records `origin/<trunk>` conflicts with `repo-graph-snapshot.sh`, which emits local `HEAD`. The proposed fix therefore targets a different snapshot contract from the one this repo produces. → Correct the diagnosis against the actual snapshot writer and checker before specifying the fix.

## NOTE (0)


## Checked and clear

Adjacent runtime code and called functions for the changed scripts, Shell injection in changed subprocess calls, Review gate handling of git count failures and fixed blocking findings, Changed Python files parse as AST, Revision diff passes git diff --check

## Not applicable

Domain rules: this is the generic ai-skills repo, SQL, ORM, and database-field checks, Async endpoints, frontend views, and time-window checks, Distribution and publish pipeline checks, New enum or status consumer checks

**Verdict:** DO NOT SHIP

## What this review did not cover

- Network access was restricted, so a live origin fetch could not be checked.
- No running service was available for integration checks.
- No browser session was available for browser checks.
- Write access was unavailable for fixtures or other write-side checks.
- The unittest suite could not run: its temporary-directory setup failed under the read-only filesystem.
- Parallel specialist sub-reviewers were not authorized for this review.
