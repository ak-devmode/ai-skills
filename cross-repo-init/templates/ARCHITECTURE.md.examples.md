# ARCHITECTURE.md — Worked Example

Reference for /cross-repo-init when scaffolding new repos. One filled archetype using pmg-integrations as the subject.

---

## Example: pmg-integrations (hub repo)

```markdown
# ARCHITECTURE — pmg-integrations

**Last refreshed:** 2026-05-11
**Maintained by:** /closeout (auto) + manual edits

---

## 1. Components

- `handlers/xendit/*` — Xendit payment webhook handlers (created, paid, expired, refunded)
- `handlers/zoho/*` — Zoho Books/Desk/CRM webhook handlers
- `handlers/chatwoot/*` — Chatwoot router webhook (inbound message classification + routing)
- `lib/broadcast/*` — WhatsApp broadcast sender via Meta Business API
- `lib/sla-escalation/*` — Per-agent cascading SLA timers and auto-reassignment
- `lib/day0/*` — Payment day-0 reconciliation cron + DLQ replay
- `operations/*` — Manual operator scripts (lookup-member-card, consolidate-invoices, etc.)
- `cron/*` — Scheduled jobs (reconciliation, drip-alert sweeps, polling)

---

## 2. Data Flow

```
External webhook (Xendit / Zoho / Chatwoot / Meta)
        |
        v
+-----------------+
| handlers/*      | <-- HMAC verify, idempotency key check
+-----------------+
        |
        +--> [classify intent] --+
        |                        |
        v                        v
+-----------------+      +-----------------+
| Chatwoot API    |      | Zoho API        |
| (inbox + assign)|      | (Books/Desk/CRM)|
+-----------------+      +-----------------+
        |
        v
+-----------------+
| broadcast (Meta)| <-- template send w/ named params, throttling
+-----------------+
```

---

## 3. Key Decisions

- **Secrets:** all via AWS SSM Parameter Store, never hardcoded. Pattern: `/pmg/<service>/<key>`. Always use `--with-decryption` on read.
- **Idempotency:** every webhook handler stores message ID in idempotency table before any side effect. Replays from DLQ are safe.
- **WhatsApp templates:** Meta NAMED parameter format (not positional). Code substitutes by name, not index.
- **Template categories:** AUTHENTICATION vs UTILITY vs MARKETING — switching categories requires Meta-side rebuild, not a deploy-side toggle.
- **Conventional commits:** use spelled-out prefixes (`feature:`, `fix:`, `docs:`), NOT short forms (`feat:`). Chatwoot commitlint enforces.
- **Branch convention:** new feature branches off `develop`, not `main`.

---

## 4. External Integrations

- **Xendit** — payment processing (cards, eWallets, virtual accounts). Secrets at `/pmg/xendit/*` in SSM. Pre-settlement refunds use `payment_request_id` (pr-*), NOT `payment_id` (pymt-*).
- **Zoho** — Books (invoicing), Desk (tickets/SLA), CRM (customer master). Per-department layout IDs differ; do not hardcode in Deluge functions.
- **Chatwoot** — self-hosted at pmg-prod-internal (10.10.3.112). Rails API token at `/pmg/chatwoot/api_token`. Restart via production-deploy.sh; skipping `db:migrate` causes silent 422s.
- **Meta WhatsApp Business API** — template send, throttling, 131049 backoff. Templates in NAMED param format.
- **AWS SSM Parameter Store** — single source of truth for secrets. KMS-encrypted SecureStrings; always use `--with-decryption`.
- **Notion API** — member records database (Padma Care). No public billing API — use internal `/api/v3/getBillingHistory` only when documented.
- **Grafana** — dashboard.pbmcgroup.com for ops dashboards. CloudWatch wildcard dim requires `matchExact=false`.

---

## 5. Cross-Repo Position

Integration hub. Consumes patterns from wellmed-infrastructure (adapters, lib utilities). Exposes webhook contracts to pmg-chatwoot, padmacare-wp, KP2MI-foreign-workers, mcu-status. See CROSS-REPO.md for the full graph.

---

<!-- Last scaffolded/audited by /cross-repo-init: 2026-05-11 -->
```

---

## Notes for /cross-repo-init

When scaffolding ARCHITECTURE.md for a new repo:

1. **Auto-detect components** from the directory structure (top-level dirs, package boundaries, service entry points).
2. **Skip the data-flow diagram** if you can't determine it from code alone — leave the template placeholder and ask the user to fill it in. A wrong diagram is worse than a missing one.
3. **Lift Key Decisions from memory** (auto-memory) and existing CLAUDE.md if present. Don't invent decisions.
4. **External Integrations are usually discoverable** from imports, environment variable usage, and SSM parameter names.
5. **Cross-Repo Position should reference CROSS-REPO.md** — keep them coherent; don't duplicate the full list here.
6. **Keep total length under 200 lines.** If detection produces more, split into `docs/architecture/<component>.md` and link from here.

For a trunk repo (like wellmed-infrastructure): components list is the shared adapters; Key Decisions covers patterns (error handling, retries, signature verification); Cross-Repo Position says "trunk — pattern source for all wellmed-* and pmg-integrations."

For a leaf repo (like padmacare-wp): components are minimal; Key Decisions covers integration-specific quirks; Cross-Repo Position notes the small set of contracts it consumes.

For a docs repo (like pmg-docs): components = the plan/scope/PRD directory structure; Data Flow may be N/A; External Integrations is rarely populated.
