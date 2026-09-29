# /review — ai-skills @ `e3b74ec..HEAD` (12 commits)

**Review:** `5.2-r1` · **Reviewer:** codex gpt-6-astra · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**Findings:** 9 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 5.2 --finding <ID> (--fixed <sha> | --rejected "<reason>")`

## BLOCKING (5)

- **5.2-r1-01** `plans/5-verify-lever/progress.md:47` (engine) — This public progress note records a non-allowlisted tenant identity, its environment mapping, and patient-data posture. Operating Contract #4 explicitly prohibits publishing these details here. → Move the operational details to the private test-suite documentation and retain only a generic decision reference in this range.
- **5.2-r1-02** `scripts/resolve-identifiers.py:322` (fail-open) — Group prefixes are indexed by variable name across the entire file. Two functions using `g` for different groups overwrite each other. Reproduced: `/users/list` and `/admin/stats` registrations cause the nonexistent `/admin/list` route to resolve successfully. → Resolve group bindings within their lexical scope and declaration order; report ambiguous bindings as unresolved.
- **5.2-r1-03** `scripts/verify_lib.py:210` (fail-open) — A judged record labeled `none unavailable` can supply a passing judge-only verdict. Both record commands accept that judge line, and authority checks only whether the record exists. Reproduced: the gate passes the check despite contract §5.1 requiring an absent judge to produce inconclusive. → Reject `none` in judged-record writers and make authority/gate validation treat non-execution as missing judge evidence.
- **5.2-r1-04** `review/scripts/review.py:197` (engine) — Review ID allocation is an unlocked read-count-append operation. Concurrent reviews of the same unit can mint identical finding IDs. A controlled interleaving produced two distinct blocking findings with one ID; one disposition then cleared both through coverage_blocks. → Lock allocation and append together, reserve each review ID atomically, and reject duplicate finding IDs when evaluating coverage.
- **5.2-r1-05** `verify/scripts/judge.py:220` (silent-failure) — The report command ignores the gate's return code and stderr, then unconditionally exits 0. Reproduced with gate exit 3: it reports `(gate error)` but succeeds and suppresses the actual malformed-input diagnostic. This violates the verification contract's error-exit guarantee. → Propagate gate evaluation errors and diagnostics; preserve blocking exit status while still allowing a report to be written.

## SHOULD FIX (4)

- **5.2-r1-06** `verify/scripts/judge.py:159` (engine) — The output validators do not enforce their schemas. Judge findings lacking `where`/`text` and malformed lever candidates are accepted, so verdicts can land before reporting crashes. The review validator also accepts `findings: {}` and raises an uncaught TypeError for `findings: null`, bypassing its documented malformed-answer fallback. → Validate container types, item types, and every required field in both writers before any append; return exit 3 for malformed output.
- **5.2-r1-07** `review/scripts/review.py:219` (silent-failure) — Zero-finding reviews append no record, so they never reserve a review ID. Reproduced: two clean reviews both use `9.1-r1` and overwrite the same report. With no existing artifacts directory, the first clean review also fails because directory creation occurs only inside append_verified. → Persist a review-level record even when findings are empty, allocate IDs from those records, and create the report directory independently.
- **5.2-r1-08** `review/scripts/review.py:208` (doc-claim) — The report promises that a fallback review marks the index until a codex review clears it, but the gate derives markers solely from verification final records. Reproduced: a fallback review plus codex verification produces no fallback marker. → Persist review execution metadata and include the latest applicable review's degraded status in the gate/index marker logic.
- **5.2-r1-09** `verify/scripts/demo.py:110` (fail-open) — The eval counts any blocked judge row as a caught defect when codex ran. It never requires a failing verdict. Reproduced: both judge checks returned inconclusive, yet `--check` exited 0 and claimed every planted defect was caught. → Require an explicit fail verdict and a corresponding defect-specific finding for each judge-caught defect; inconclusive must fail the eval.

## NOTE (0)


## Checked and clear

Lenses §1: read all 58 changed files and relevant adjacent implementations., Engine — Shell Injection: changed production subprocess calls use argument arrays; runner shell commands are explicit finish-table inputs., Engine — Enum & Value Completeness: traced changed feature-map statuses, finding categories, and verdict consumers., Engine — Version consistency: changed skill versions match their catalog entries., Lenses §4 — Over-build: checked shared implementations and excluded intentionally defective fixture code., Lenses §4 — Identifier declarations: the resolver passed on e3b74ec..HEAD., Lenses §5 — Dirty comments: no additional production workaround defect found., Verification: nine contract tests, one compile test, both changed skill lints, and git diff --check passed.

## Not applicable

Domain groups 3.1–3.8: generic repository; no Kalpa/PMG domain pass., Engine — SQL & Data Safety and ORM Column/Field Name Safety: no database implementation., Engine — Async/Sync Mixing: no async endpoints., Engine — Time Window Safety: no windowed aggregation or date-key lookup changes., Engine — View/Frontend: no rendered application surface., Engine — Distribution & CI/CD Pipeline: no build or publication pipeline changes.

**Verdict:** DO NOT SHIP

## What this review did not cover

- Full unittest suite: integration tests require writable temporary directories and Git repositories; this filesystem is read-only.
- Live codex probe/exec and VERIFY_EVAL=1: require model/network access and writable scratch artifacts; not executed.
- Claude Code skill registration and fallback invocation: no live Claude Code runtime validation performed.
- Parallel specialist sub-reviews: not dispatched under this review execution.
- Real concurrent filesystem test: the ID collision was reproduced with controlled in-memory interleaving, not concurrent disk writes.
