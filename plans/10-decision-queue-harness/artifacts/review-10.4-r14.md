# /review — ai-skills @ `698b443d5b3dbcc1c09a2bf6b5a9ac18b8aa393f..36f52cf0ba98e6f5d9b695e63d4d20fe7aa6cc8b` (3 commits)

**Review:** `10.4-r14` · **Reviewer:** codex gpt-6.1-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**Findings:** 6 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (3)

- **10.4-r14-01** `scripts/packet.py:760` (engine Enum & Value Completeness) — The default switches to v2 before the existing queue consumer supports it. dev-workbench/queue/decision_queue/schema/packet.schema.json still requires version 1 and rejects context, evidence, why, and the empty generic payload. The receiver returns HTTP 400, which this client permanently marks rejected, so flushing after a receiver upgrade will not recover those packets. Its database projections and renderer also omit the new fields. → Complete the receiver contract migration across its vendored schema, database read paths, and renderer before changing the producer default. Cover generic, data-model, and UI packets, and retain v1 as the default until that cutover.
- **10.4-r14-02** `plan/SKILL.md:507` (doc-claim 6) — The shipped /plan command still supplies plain option labels and --body without --context. With this range's default, it exits 1 before writing any packet. The data-model variant also lacks required context and option explanations. Consequently, /plan's decision and GATE-BLOCKED paths cannot emit their required packets. → Update every direct packet.py invocation in /plan §6.9 to the v2 contract, including generic, data-model, and two-way variants, or explicitly pin legacy invocations to v1. Reuse canonical examples across the skills.
- **10.4-r14-03** `schemas/packet.schema.json:10` (fail-open 2) — The numeric enum has no integer type guard. schema_check.py uses Python membership, so JSON true satisfies [1, 2], while its boolean-aware const checks select neither version branch. A packet with schema_version=true, options=[{"recommended":true}], arbitrary generic payload, and oversized context validates with zero errors. → Require an integer discriminator and make numeric enum comparisons in schema_check.py distinguish booleans from numbers. Add negative cases proving invalid version types cannot bypass option, payload, and cap validation.

## SHOULD FIX (3)

- **10.4-r14-04** `scripts/packet.py:372` (silent-failure 3) — show() prints option explanations but never prints context or evidence. The terminal fallback therefore omits the situation and supporting information when the queue is unavailable or unset. For optionless info packets, the entire context disappears from the displayed card. → Render v2 context and provide access to evidence in the shared terminal renderer, covering both new packets and --id reprints, including optionless info packets.
- **10.4-r14-05** `schemas/packet.schema.json:106` (engine LLM Output Trust Boundary) — The schema rejects only '(recommended)' and '(Recommended)', whereas the CLI rejects every capitalization. A non-recommended option labelled 'Alternative (RECOMMENDED)' validates successfully, allowing schema-based writers to display a conflicting recommendation. → Apply the same case-insensitive recommendation-marker rule in the schema and CLI. Cover uppercase and mixed-case markers on both recommended and non-recommended options.
- **10.4-r14-06** `scripts/tests/test_packet.py:692` (fail-open 2 · scaffolding) — The unreadable-body-file test now defaults to v2, which rejects --body-file and missing context before attempting any file read. Its exit-code and traceback assertions therefore pass even if legacy body-file error handling regresses. → Restore the body-file test with explicit v1 arguments and assert the specific unreadable-file diagnostic. Add equivalent negative coverage for the new v2 --evidence-file path.

## NOTE (0)


## Checked and clear

Lenses §1: all 20 changed files read completely; called validator/classifier functions and adjacent producers and queue consumers inspected., Shell Injection: changed subprocess construction uses argument arrays., Lenses §4: new CLI flags, schema fields, and referenced paths resolve., Repository skill contract: frontmatter and version bump checked; concurrency skill lint reported zero issues., Packet schema suite: 10 tests passed, including exact cap boundaries and invalid-fixture rejection reasons., Python compilation check passed for shared scripts; git diff --check passed.

## Not applicable

SQL & Data Safety: no SQL mutations or migrations added in this range., Async/Sync Mixing: no async execution surface., Time Window Safety: no changed date-window logic., Timing-Dependent Tests: no added or relaxed timing assertions., Distribution & CI/CD Pipeline: no pipeline or release changes., Approval Classes and Data Repairs: no approval-class declaration at the exact base and no repair paths.

**Verdict:** SHIP AFTER BLOCKING

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- Build: the repository declares no build target; Python sources were compiled in memory.
- Full unittest suite was attempted but could not complete: the read-only sandbox prevents temporary repositories and files; unittest reported 519 errors across 480 tests, with 2 skipped.
- Live /plan and /concurrency invocation was not exercised in Claude Code.
- Live queue delivery, database persistence, and browser rendering were not exercised in this read-only, network-restricted session.
- The receiver's jsonschema validator and pytest suite could not run because its dependencies were unavailable; compatibility was checked against its vendored schema using the stdlib validator.
- The required approval-class helper refused the exact base with APPROVAL_SOURCE_UNAVAILABLE because it prepended origin/ to the commit SHA; absence of the declaration was checked directly at that base.
