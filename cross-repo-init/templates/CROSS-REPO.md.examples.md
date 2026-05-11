# CROSS-REPO.md — Worked Examples

Reference for /cross-repo-init when scaffolding new repos. Two real-world archetypes from Alex's setup.

---

## Example 1: Hub repo (consumes + exposes)

**Repo:** pmg-integrations
**Role:** integrations hub — consumes shared infra patterns, exposes contracts to PMG consumers

```markdown
# CROSS-REPO.md — pmg-integrations

## Pattern Sources

- wellmed-infrastructure
  - adapters/* — error handling, retries, signature verification, event publishing
  - lib/* — shared utilities, logging, config loaders

## Consumers

- pmg-chatwoot — router webhook payloads, broadcast events
- padmacare-wp — Zoho signup drip webhook
- KP2MI-foreign-workers — worker status webhook payloads
- mcu-status — MCU report ingestion webhooks

## Traversal Config

- max-depth-override: 2
- trunk-branch: develop

---

<!-- Last scaffolded/audited by /cross-repo-init: 2026-05-11 -->
```

**Why this shape:** pmg-integrations is the integration hub. It follows patterns from wellmed-infrastructure (Pattern Source — upward), and four PMG repos depend on its webhook contracts (Consumers — outward). When you change a contract here, /closeout-extended walks to those four consumers. When you write a new method here, /plan greps wellmed-infrastructure first.

---

## Example 2: Trunk repo (Pattern Source for many)

**Repo:** wellmed-infrastructure
**Role:** trunk — defines shared adapters and patterns; no upstream sources

```markdown
# CROSS-REPO.md — wellmed-infrastructure

## Pattern Sources

<!-- This repo IS the trunk. No upstream patterns. -->

## Consumers

- wellmed-backbone — adapters, error handling, retries
- wellmed-cashier — adapters, signature verification, retries
- wellmed-consultation — adapters, event publishing, lib utilities
- wellmed-fe — lib (config loaders, logging only)
- wellmed-gateway-go — adapters (all), lib (all)
- wellmed-pharmacy — adapters, error handling
- pmg-integrations — adapters/* (cross-org reference, infrastructure parity)

## Traversal Config

- max-depth-override: 2
- trunk-branch: develop

---

<!-- Last scaffolded/audited by /cross-repo-init: 2026-05-11 -->
```

**Why this shape:** wellmed-infrastructure is the canonical source for shared adapters. Pattern Sources is empty — there's nothing upstream. The Consumers list is long because everything WellMed (plus pmg-integrations) follows its patterns. /closeout-extended walking *upward* into this repo means a consumer is proposing an extension to a canonical pattern — these proposals require explicit user confirmation per /closeout-extended's 3D upward semantics.

---

## Notes for /cross-repo-init

When scaffolding a NEW repo's CROSS-REPO.md:

1. **Detect repo position in the graph** by inspecting `package.json` / `go.mod` / imports / existing webhook handlers / event subscriptions.
2. **Propose Pattern Sources** based on what shared-infra patterns the code already imports or duplicates locally (candidates for fold-up).
3. **Propose Consumers** by checking known sister repos for inbound references (imports, webhook URL allowlists, event subscriptions targeting this repo's contracts).
4. **Default trunk-branch to `develop`** unless the repo's actual default branch is named differently.
5. **Always present the proposal to the user via numbered inline questions** (no AskUserQuestion). User confirms/edits/rejects each section. Then write.

A hub looks like Example 1. A trunk looks like Example 2. A leaf has filled Pattern Sources and empty Consumers. A docs repo has empty both (load-bearing for the project but not in the contract graph).
