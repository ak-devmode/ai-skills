# /review — dev-workbench @ `66aebf01f4f021a84386956e578228665fd4bea6..bfe080853c845c23b6673dec8acf5bba6de0e2be` (5 commits)

**Review:** `10.4-r17` · **Reviewer:** claude-fallback codex out of credits (driver brief) · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits (driver brief)` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits (driver brief)` (and the index carries it) until a codex re-review of this unit.
**Findings:** 1 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.4 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (0)


## SHOULD FIX (0)


## NOTE (1)

- **10.4-r17-01** `queue/decision_queue/render.py:309` (engine) — The 10.4-r15-01 fix makes the feed copy what it shows, but ingest still accepts a v2 packet whose stored reply disagrees with its recommended flag. One packet now offers two copy buttons with different answers: the feed copies 'Option 1: …' (rebuilt from the flag), and the detail page copies the stored 'Option 2: …'. Neither page flags the disagreement. The copy defect is resolved; the inconsistent packet is not caught. → At ingest (validate.packet_error), refuse a v2 packet whose reply is not lane_tag + the prefill packet.py builds from the recommended option ('Option N: label.' or 'ack'). Alternatively, render a mismatch badge on both cards.

## Checked and clear

10.4-r15-01 resolved: the feed's hidden textarea is rebuilt from packet identity + the displayed recommended option via _feed_reply, matching packet.py lane_tag + prefill byte-for-byte (same \s*\(recommended\) re.I strip); optionless packets copy '… ack'; output escaped; reply is written only at ingest (db.py), so no persisted user edit is bypassed; test fails with the fix reverted, 10.4-r15-02 resolved: vendored patterns end in (?![\s\S]); queue test runs under jsonschema (Python re), so it discriminates, and asserts the cap itself still passes, 10.4-r15-03 resolved: per-letter case-insensitive label lookahead; _label strips the marker on every option so a v1 non-recommended marker cannot render as a second recommendation (the conflicting-marker-at-write side is ai-skills 10.4-r16-03), 10.4-r15-04 resolved: _age normalises naive to UTC on both operands, default now is aware; test covers all four naive/aware mixes, 10.4-r14-03 vendored: schema_version integer-typed; queue test covers true/false/'2' (2.0 is an integer under Draft 2020-12 and takes the v2 branch, so checks are not skipped), vendored schema identical (minus $comment) to ai-skills worktree schemas/packet.schema.json at e9325f1, queue suite: uv run pytest -q with DQ_SCHEMA_SOURCE pointed at the ai-skills worktree schema — 103 passed (Postgres-backed tests ran), lenses: fail-open, silent failure, adjacent code (_card_v2 feed/detail, _label callers, db.insert reply)

## Not applicable

domain rules — generic repo, SQL migration, auth checklist groups — no surface in range

**Verdict:** SHIP

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- codex cross-model pass: not run per driver brief (codex out of credits)
- gstack specialist fan-out not dispatched: single-context Claude pass over a 126-line fix range
- no browser: the copy button's clipboard behaviour was checked from rendered HTML only
