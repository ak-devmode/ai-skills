# /review — ai-skills @ `3af6614..HEAD` (6 commits)

**Review:** `5.2-r3` · **Reviewer:** codex gpt-6-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**Findings:** 2 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 5.2 --finding <ID> (--fixed <sha> | --rejected "<reason>")`

## BLOCKING (1)

- **5.2-r3-01** `review/scripts/review.py:238` (fail-open) — The review prompt can use `BASE..HEAD`, but this line resolves `HEAD` only when the answer is recorded. If a commit lands while Codex is reviewing, the log claims Codex covered that unreviewed commit; the gate can then clear a fallback marker using false coverage. → Resolve the range to immutable commit SHAs before rendering the prompt, and require `record` to use those same SHAs.

## SHOULD FIX (1)

- **5.2-r3-02** `review/scripts/review.py:238` (silent-failure) — Both `rev-parse` exit codes are discarded. A failed resolution records an empty SHA and reports a successful review record, contrary to the documented resolved-SHA contract. → Check each exit code and require a nonempty commit SHA before appending any record.

## NOTE (0)


## Checked and clear

Adjacent code and called functions, LLM Output Trust Boundary, Dead Code & Consistency, LLM Prompt Issues, Completeness Gaps, Local maxima, Dirty comments, Doc claims

## Not applicable

Domain rules §3.1–§3.8: generic repo, SQL & Data Safety, Shell Injection, Enum & Value Completeness, Async/Sync Mixing, Column/Field Name Safety, Time Window Safety, Type Coercion at Boundaries, View/Frontend, Distribution & CI/CD Pipeline

**Verdict:** DO NOT SHIP

## What this review did not cover

- The filesystem-writing unittest suite and live demo could not run under read-only filesystem access; AST parsing and git diff checks ran.
- A network-backed Codex probe or live judge could not run because network access is restricted.
- Running-service behavior could not be checked; no service was available in this review environment.
- Browser behavior could not be checked; no browser session was available.
- Parallel specialist or sub-reviewer passes were not performed.
