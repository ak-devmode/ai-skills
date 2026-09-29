# /review — ai-skills @ `45b9788fe63d1ee45527144beddd9afd790b1b8f..c3516efe49532c78995a0f8190f7bb91b0f81e65` (1 commits)

**Review:** `5.3-r4` · **Reviewer:** codex gpt-6-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**Findings:** 2 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 5.3 --finding <ID> (--fixed <sha> | --rejected "<reason>")`

## BLOCKING (1)

- **5.3-r4-01** `scripts/clone-behind.py:47` (fail-open lenses §2) — isfile() follows symlinks. A stamp symlink to a recently modified regular file is treated as proof of a fetch, so the script skips fetch and can silently report a stale clone as current. → Use lstat() to reject symlinks, validate the stamp contents, and add a test for a fresh symlinked stamp.

## SHOULD FIX (1)

- **5.3-r4-02** `scripts/clone-behind.py:62` (doc-claim lenses §6) — An unwritable stamp now produces a warning before the behind-clone line, but plan/SKILL.md §6.7 and verify/SKILL.md §2.0.1 still instruct agents to show “that line” in the singular. Showing only the first line hides the actionable stale-clone warning. → Emit one combined line, or update both callers to display every output line.

## NOTE (0)


## Checked and clear

lenses §1 adjacent code, lenses §3 silent failure, lenses §4 local maxima, lenses §5 dirty comments, engine: Race Conditions & Concurrency, engine: Shell Injection, engine: Dead Code & Consistency, engine: Completeness Gaps

## Not applicable

domain rules: generic repository, engine: SQL & Data Safety, engine: LLM Output Trust Boundary, engine: Enum & Value Completeness, engine: Async/Sync Mixing, engine: Column/Field Name Safety, engine: LLM Prompt Issues, engine: Time Window Safety, engine: Type Coercion at Boundaries, engine: View/Frontend, engine: Distribution & CI/CD Pipeline, browser and running-service checks: no surface in this range

**Verdict:** SHIP AFTER BLOCKING

## What this review did not cover

- The rollout tests could not run: the read-only sandbox has no writable temporary directory for their Git fixtures.
- A live origin/main fetch could not be exercised because network access is restricted.
- Parallel specialist sub-reviews were not run because sub-agent delegation was not authorized.
