# /review — ai-skills @ `1c5531b02519517725557688342a4d0d40e21f6c..a314d0b81f50c0f1476076592ec6af9a063ec2d4` (1 commits)

**Review:** `10.4-r6` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 2 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (0)


## SHOULD FIX (1)

- **10.4-r6-01** `scripts/README.md:198` (doc-claim lenses: doc claims · reopens 10.4-r3-06) — The fix for 10.4-r3-06 swapped one prose excuse for a false present-tense claim: the README now says "the driver declares it in `.env.example`", but `.env.example` is untouched in this range and has no DQ_UI_DEMO_TENANT entry at HEAD. resolve-identifiers.py over 1c5531b..HEAD reports `[FAIL] env DQ_UI_DEMO_TENANT does not resolve` at scripts/packet.py:375, so the /verify identifier row fails on this unit. CLAUDE.md §5 (the list of optional script overrides, 'seven') is also not updated. The configuration dependency r3-06 flagged is still undeclared. → Add DQ_UI_DEMO_TENANT to .env.example (and to CLAUDE.md §5's env list) in this range, or change the README to state it is not yet declared and keep r3-06 open until it is.

## NOTE (1)

- **10.4-r6-02** `scripts/packet.py:377` (doc-claim lenses: doc claims) — The real-patient guard compares payload.tenant, a field the same author writes, to $DQ_UI_DEMO_TENANT, a value the same author sets; nothing ties the screenshot to that tenant. README:200 presents it as the protection against WellMed dev/staging patient data. It catches a forgotten tenant field, not a shot taken on a real tenant labelled as the demo one. → Word the README and docstring as a declaration check (the author attests the shot is from the demo tenant) rather than a data guard, or capture the tenant from the shot source rather than the payload.

## Checked and clear

10.4-r3-05 resolved: ui_payload_errors decodes with validate=True and refuses invalid base64, non-PNG signature and >1,500,000-byte images; empty data part decodes to b'' and is refused as not-PNG, fail-open: DQ_UI_DEMO_TENANT unset or empty refuses; non-dict payload refuses; check runs before any outbox write (tests assert no outbox), cap consistency: 1,500,000 bytes = 2,000,000 base64 chars, matching the schema's length bound, regression tests: test_ui_image_content_checks and test_ui_demo_tenant_guard; 65 packet tests pass at HEAD, engine checklist: no SQL, concurrency, LLM-trust or secret surface in the range

## Not applicable

domain rules — generic repo, rejected 10.4-r3-01..04 — no new evidence in this range

**Verdict:** SHIP

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- codex gate: codex out of credits (probe: none codex out of credits)
- gstack specialist fan-out (security, testing, red-team, …) not dispatched: single-context Claude pass over an 82-line fix range
- end-to-end POST of a ui packet to a running queue (no service running in this read-only pane)
- revert-and-rerun proof that the new tests fail without the fix (pane is read-only)
