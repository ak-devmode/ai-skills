<!-- EXAMPLE — a filled closeout-prep.md, for reading only. The template is
     templates/closeout-prep.md.template; never copy entries from here into a ledger. -->
# closeout-prep.md — example-scope

**Schema version:** 1.0

---

## §2 Files Changed

### pmg-integrations

**code:**
- `src/handlers/chatwoot.js` — Chatwoot inbound webhook handler

**test:** _(none)_

**config:** _(none)_

**doc:** _(none)_

**schema:** _(none)_

**migration:** _(none)_

---

## §3 Patterns Followed

### pmg-integrations

- `handleWebhook()` in `src/handlers/chatwoot.js:42`
  ← `src/handlers/xendit.js:42` (pattern reference)
  deviation: skipped idempotency check (Chatwoot signs with timestamp, prevents replay)

- `publishEvent()` in `src/handlers/chatwoot.js:118`
  ← `kalpa-infrastructure/adapters/event.go:15` (pattern reference)

---

## §4 Patterns Created (no existing reference found)

### pmg-integrations

- `validateWebhookSignature()` in `src/handlers/chatwoot.js:104`
  - alternatives-considered:
    - `kalpa-infrastructure/adapters/signature.go:15` — rejected: SHA256-only, Chatwoot signs with SHA512
    - `(none found in: local repo, kalpa-infrastructure, npm:crypto)`
  - recommendation: extend `kalpa-infrastructure/adapters/signature.go` to accept algo arg; this is a candidate for fold-up in /closeout-extended upward traversal

---

## §5 Cross-Repo Touchpoints

- **Contract:** `POST /webhooks/chatwoot/inbound` payload — added `metadata.source_channel`
  - Consumers (from CROSS-REPO.md): pmg-chatwoot
  - Consumer-side checked: NO — flagged for /closeout-extended outward traversal

---

## §6 Docs Loaded During Planning

- `CLAUDE.md` (repo root)
- `ARCHITECTURE.md` (repo root)
- `CROSS-REPO.md` (repo root)
- `docs/integrations/chatwoot.md`

---

## §7 Docs Likely Affected

- `CLAUDE.md` — new `metadata.source_channel` field in webhook payload; section "Webhook contracts" needs update
- `ARCHITECTURE.md` — Data Flow diagram still shows pre-metadata flow; needs refresh
- `docs/integrations/chatwoot.md` — example payload outdated

---

## §8 Assumptions Made (unverified)

- Assumed `/pmg/chatwoot/api_token` in SSM is still valid — did not test
- Assumed Chatwoot's webhook signature algo is SHA512 per current docs — did not verify against running instance

---

## §9 Deferred Items

- Backfill historical webhook records with `source_channel` — deferred, no urgency, recommend @alex
- Update integration test fixtures to include new field — deferred to follow-up scope

---

## §10 Test Coverage Map

### Source: scope 42 §4.2

| Node | Test file | Happy | Unhappy | Edge |
|------|-----------|-------|---------|------|
| handleWebhook (Chatwoot) | `test/handlers/chatwoot.test.js` | ✓ | ✓ | — |
| validateWebhookSignature | _(none — new method)_ | ✗ | ✗ | ✗ |
| metadata.source_channel propagation | _(none — new contract)_ | ✗ | ✗ | ✗ |

---

## §11 Risk Flags / Uncertainty

- /plan was uncertain whether `metadata.source_channel` should be `string` or `enum` — went with string for now. Worth revisiting if more channels added.
- Pre-existing weak spot: no integration test covers the full inbound webhook → Chatwoot inbox → broadcast outbound flow. Out of scope for this plan but flagged.

---

