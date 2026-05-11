# CROSS-REPO.md — Worked Examples

Reference for /cross-repo-init when scaffolding new repos. Three real-world
archetypes from Alex's setup.

---

## Example 1: Self-trunk hub (no upstream; multiple consumers)

**Repo:** pmg-integrations
**Role:** integrations trunk for the PMG project graph — its `lib/` adapters are
themselves the canonical patterns. No upstream Pattern Source.

```markdown
# CROSS-REPO.md — pmg-integrations

## Pattern Sources

<!-- pmg-integrations is the trunk of the PMG project graph. Its lib/ adapters
     are the patterns. No upstream to inherit from. Note: wellmed-infrastructure
     is the trunk of the Kalpa/WellMed application stack — a separate graph with
     separate patterns. The two trunks intentionally do not share a Pattern
     Source. -->

(none — self-trunk)

## Consumers

- pmg-chatwoot — HTTP webhook endpoints, shared SSM, deploy choreography
- pmg-docs — operational + architectural documentation (docs consumer, not code)

### External Dependents (not tracked repos — /closeout-extended skips)

- grafana (dashboard.pbmcgroup.com) — metrics + CloudWatch logs
- pbmcgroup.com — PMG corporate WordPress site
- padmacare.pbmcgroup.com — Padma Care WordPress, consumes Zoho drip webhooks
- webcam — narawangsa villa webcam (verify before contract-change review)

## Traversal Config

- max-depth-override: 2
- trunk-branch: develop

---

<!-- Last scaffolded/audited by /cross-repo-init: 2026-05-11 -->
```

**Why this shape:** pmg-integrations doesn't import from any other repo's source
tree. Its adapters (xendit, zoho-*, chatwoot-api, notion, ses, sns) are the
canonical PMG patterns. So Pattern Sources is empty — it's a self-trunk.
Consumers section is short (pmg-chatwoot + pmg-docs) because most production
dependents (Grafana, WordPress sites, webcams) aren't tracked git repos.
External dependents are documented for context but not traversed by
/closeout-extended.

---

## Example 2: Trunk repo (Pattern Source for many; no consumers across project boundaries)

**Repo:** wellmed-infrastructure
**Role:** trunk — defines shared adapters and patterns for the Kalpa/WellMed
application graph. No upstream sources.

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

## Traversal Config

- max-depth-override: 2
- trunk-branch: develop

---

<!-- Last scaffolded/audited by /cross-repo-init: 2026-05-11 -->
```

**Why this shape:** wellmed-infrastructure is the canonical source for shared
Go adapters and patterns. Pattern Sources is empty (it IS the trunk). Consumers
list is long because every WellMed leaf inherits from it. **Important:** it does
NOT list `pmg-integrations` as a Consumer — the PMG and WellMed projects are
independent application stacks with intentionally divergent patterns. The two
trunks live in separate graphs. /closeout-extended will not (and should not)
traverse between them on outward edges.

---

## Example 3: Leaf repo (filled Pattern Sources, empty Consumers)

**Repo:** wellmed-cashier (illustrative shape, not literal content)
**Role:** leaf — depends on the trunk, exposes no further contracts.

```markdown
# CROSS-REPO.md — wellmed-cashier

## Pattern Sources

- wellmed-infrastructure
  - adapters/* — error handling, retries, signature verification
  - lib/* — config loaders, logging

## Consumers

<!-- Leaf — nothing depends on this repo's exported contracts in the tracked graph. -->

## Traversal Config

- max-depth-override: 2
- trunk-branch: develop

---

<!-- Last scaffolded/audited by /cross-repo-init: 2026-05-11 -->
```

**Why this shape:** a leaf consumes one or more trunks (Pattern Sources) but
exposes no contracts back. /plan's pattern-first rule grep targets the listed
sub-paths in the Pattern Source. /closeout-extended walks upward to propose
trunk extensions when the leaf creates a new pattern.

---

## Notes for /cross-repo-init

When scaffolding a NEW repo's CROSS-REPO.md:

1. **Detect repo position in the graph** by inspecting `package.json` / `go.mod` /
   imports / existing webhook handlers / event subscriptions.
2. **Propose Pattern Sources** based on what shared-infra patterns the code
   actually imports. If there are no imports from any other repo, propose
   `(none — self-trunk)` — don't invent aspirational coupling.
3. **Propose Consumers** by checking known sister repos *within the same project
   graph* for inbound references. Don't cross project boundaries (PMG ↔ WellMed)
   — the two graphs are intentionally separate.
4. **Default trunk-branch to `develop`** unless the repo's actual default branch
   is named differently.
5. **Always present the proposal to the user via numbered inline questions** (no
   AskUserQuestion). User confirms/edits/rejects each section. Then write.
6. **External dependents** (production systems that consume the repo but aren't
   tracked git repos — WordPress sites, dashboards, webcams) go in a dedicated
   sub-section under Consumers so they're documented for humans but skipped by
   /closeout-extended traversal.

A self-trunk hub looks like Example 1. A trunk-with-many-consumers looks like
Example 2. A leaf looks like Example 3. A docs repo has empty both (load-bearing
for the project but not in the contract graph).
