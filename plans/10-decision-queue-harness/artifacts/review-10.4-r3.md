# /review — ai-skills @ `361ae685b906ef3638bde5fd29e6e537363397b1..1c5531b02519517725557688342a4d0d40e21f6c` (3 commits)

**Review:** `10.4-r3` · **Reviewer:** codex gpt-6.1-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**Findings:** 6 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (3)

- **10.4-r3-01** `scripts/resolve-identifiers.py:363` (fail-open 2) — The exemption covers every google.golang.org/protobuf/ package, including generated messages. Both timestamppb.Timestamp{NonexistentField: 1} and descriptorpb.FieldDescriptorProto{NonexistentField: 1} now produce zero references instead of unresolved fields. Verification therefore reports these invalid references as a clean pass. → Restrict exemptions to actual runtime packages or structs. Preserve scanning for types/known/*pb, descriptorpb and pluginpb, and add negative message-field cases beside the runtime-options test.
- **10.4-r3-02** `scripts/packet.py:646` (engine Enum & Value Completeness) — The newly enabled UI packets have no matching queue renderer. In the plan's pinned dev-workbench ef9bae0 consumer, render._payload sends ui through _generic, which reads payload.body. The new payload forbids body; the supplied fixture renders only <div class="body"></div>, hiding both screenshots and all callouts. → Land the queue's UI renderer with this producer change. Handle both rich/detail views and permit embedded PNG images in app.py's CSP; verify rendering with this exact fixture.
- **10.4-r3-03** `schemas/packet.schema.json:100` (engine Completeness Gaps) — The image allowance exceeds the queue's transport limit. Its pinned app.py accepts only 262,144 request bytes. A packet containing two valid 200,548-byte PNGs passes this schema but serializes to 535,825 bytes and receives HTTP 400. packet.py then marks it permanently rejected, so flush never delivers the decision. → Align producer image limits and aggregate serialized-packet limits with the queue's request budget. Update the receiving limit and exercise boundary-sized PNG pairs through the request handler, including rejection/retry behavior.

## SHOULD FIX (3)

- **10.4-r3-04** `schemas/packet.schema.json:101` (doc-claim 6) — The claim that the queue enforces the same cap is false. Its pinned vendored schema still treats ui as unconstrained: payload:{} passes there while this schema rejects all six missing fields. The consumer's existing schema-parity test also fails against this revision. → Propagate the canonical schema to queue/decision_queue/schema/packet.schema.json with the landing, retain the parity guard, and verify the UI-required fields and image limits on the receiver.
- **10.4-r3-05** `schemas/packet.schema.json:100` (engine LLM Output Trust Boundary) — The pattern validates a MIME label and character alphabet, not a PNG. Invalid base64 such as data:image/png;base64,A, arbitrary bytes, and SVG bytes labelled image/png all validate successfully. Such packets are accepted without usable screenshot evidence despite the documented PNG-only guarantee. → Strictly decode base64 and validate the decoded PNG content and byte limit for both old and new images. Apply equivalent checks at the receiver and add malformed, truncated and mislabelled-image cases.
- **10.4-r3-06** `scripts/README.md:198` (dirty-comment 5 · scaffolding) — “permission-denied in the lane that wrote this” excuses an unfinished configuration dependency. The procedure requires DQ_UI_DEMO_TENANT, but supplies neither its declaration nor a setup path; the driver action needed to complete the workflow remains only prose. → Declare the configuration input and document how each project supplies its demo-tenant value to lane environments. Remove the permission workaround after completing that dependency; update the matching schema guidance.

## NOTE (0)


## Checked and clear

Adjacent-code and sideways sweeps: all 16 touched files, called helpers, validation/extraction paths and pinned queue consumers inspected., Engine checks for SQL/data safety, race changes, shell injection, async/sync mixing, type coercion and time windows found no additional defects on affected paths., Test/fixture hunks inspected: no removed or disabled tests, weakened assertions, added retries or relaxed timing bounds., Lenses §3 silent failure and §4 over-build: no additional introduced defects., Eight schema tests passed; all five changed Python files compiled in memory; exact-range git diff --check passed.

## Not applicable

Kalpa/PMG/IRIS domain rules: generic repository., Build: CLAUDE.md declares no build step., Skill frontmatter and skill-body lint: no SKILL.md changed., CI/release/distribution changes, data migrations/repairs, cache-policy bypasses and dynamic-import changes.

**Verdict:** SHIP AFTER BLOCKING

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- Full unittest suite could not complete successfully: 452 tests attempted, 496 errors and two skips; temporary-repository tests were blocked by the absence of writable temporary directories.
- Dedicated Python/Markdown lint: no configured linter for these files; compilation and whitespace checks were available.
- gstack-gate-diff failed because temporary-index and artifact writes were denied; gate hunks were inspected manually.
- gstack-approval-classes could not bind the supplied SHA as origin/<base>; no remote ref points at that base. Manual inspection found no approval-classes.json in the exact base tree.
- Live HTTP/database queue round-trip tests were not run under the read-only, network-restricted environment; pinned handler functions were probed in memory.
- Browser rendering and screenshot acceptance were not performed.
- Independent specialist subreviews were not run; this review used one agent.
