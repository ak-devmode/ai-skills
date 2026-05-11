# CLAUDE.md — Examples by Archetype

Reference patterns for /cross-repo-init to consult when scaffolding or
folding CLAUDE.md content. Three archetypes covered:

1. **Application-trunk Go service** (heavy ADR-anchored content)
2. **Pattern-trunk shared library** (different shape — patterns flow OUT)
3. **Frontend leaf** (slim — Nuxt/React HTTP client)
4. **Stub repo** (placeholder with explicit STUB warnings)
5. **Standalone marketing site** (outside the application graph entirely)

---

## Archetype 1: Application-trunk Go service

Real example: `wellmed-backbone`. The main application repo with sole saga
orchestration, multi-tenant DB resolution, contract definitions for the
rest of the mesh.

**Length:** ~200 lines (substantial; this is the contract authority).

**Sections that matter most here:**
- §3 Architecture decisions — heavy. 5-7 ADR-anchored rules.
- §5 Environment variables — comprehensive table.
- §7 What NOT to do — derived from ADRs + saga rules.

**Distinctive content:**
- ULID vs UUID rule with code example (CRITICAL for primary keys)
- Saga orchestration explicit ownership
- Multi-tenant DB pattern (ConnectionManager + TransactionManager)
- Per-service auth tokens (ADR-007)
- Bahasa Indonesia communication preference + auto-save knowledge rules
  (for wellmed-backbone specifically; not universal)

---

## Archetype 2: Pattern-trunk shared library

Real example: `wellmed-infrastructure`. The Go SDK + adapter library +
AWS infrastructure scaffolding. Patterns flow OUT to every other
wellmed-* service.

**Length:** ~200 lines.

**Sections that matter most here:**
- §1 What this service is — emphasizes pattern source role + DEVELOP vs MAIN drift
- §4 Adapter pattern (load-bearing) with full code example showing the
  service-side wrapper
- §5 SSM secret management — per-service manifest workflow + services-and-ports
  table (the canonical reference for the whole mesh)
- §6 When to grep this repo for patterns — explicit pointers to which
  go-sdk packages and go/adapter shapes to reference

**Distinctive content:**
- Drift section is load-bearing: main is IAM-only origin shape; develop has
  the SDK + adapter library + installpb + migration/seeder tools
- New-repo provisioning via `scripts/bootstrap-repo.sh`
- Two Go modules in one repo: `go-sdk/` and `go/`

---

## Archetype 3: Frontend leaf (Nuxt/React)

Real example: `wellmed-fe`. EMR web frontend that talks to Gateway HTTP.

**Length:** ~120 lines (slimmer than Go services).

**Sections that matter most here:**
- §1 What this service is — short. Frontend-only, no Go deps.
- §3 Architecture — shorter (4-5 decisions, mostly stack + API target rules)
- §4 Key files — Nuxt-shaped (core/, layers/, infra/)
- §7 What NOT to do — short list (no direct internal gRPC, no hardcoded env)

**Distinctive content:**
- pnpm workspace structure
- "All API calls go through wellmed-gateway-go HTTP" — no exceptions
- Deploy scripts live in this repo's `infra/`, NOT in wellmed-infrastructure
- SSM-based config via deploy-time fetch

---

## Archetype 4: Stub repo (special)

Real example: `wellmed-catalog` (as of 2026-05-11). Repo exists but has
no implementation — ~2 weeks of uncommitted work lives on someone's local.

**Length:** ~80 lines.

**Critical: opens with explicit STUB warning.**

```markdown
# CLAUDE.md — wellmed-catalog

Agent context for Claude Code in this repo. Read this on session start.

> **STUB REPO.** Zero implementation as of 2026-05-11. ~2 weeks of
> uncommitted Catalog work lives on someone's local machine. This file is
> scaffolding — refresh when implementation lands.

---

## 1. What this service WILL be

**wellmed-catalog** is the planned Tier-3 Integration Mapper for WellMed.
[Intended responsibilities from ADRs / system architecture]

Status: **STUB** — see ARCHITECTURE.md §6 for the honest read.

---

## 3. If you're here to implement Catalog

When the local work lands, this CLAUDE.md needs to be replaced with the
actual agent context. Until then:

3.1 **Don't fabricate implementation.** Don't write speculative gRPC
handlers or DB schemas — wait for the canonical work to land.

3.2 **Reference design docs:** [ADR-012, ADR-013, kalpa-docs §3.x]

3.3 **Pattern Sources when implementation begins:** [wellmed-infrastructure,
wellmed-backbone, etc.]
```

**What's distinctive:**
- Explicit "STUB" banner at the top
- Use of "WILL be" instead of "is" for the description
- Section "If you're here to implement X" with anti-fabrication rules
- "Refresh this trio when implementation lands" as explicit follow-up

---

## Archetype 5: Standalone marketing site (outside the graph)

Real example: `kalpa-company-profile`. Laravel/PHP marketing site for
KalpaHealth corporate. Has nothing to do with the WellMed application
mesh.

**Length:** ~60 lines (minimal — most trio fields don't apply).

**Sections that matter most here:**
- §1 Stack — Laravel/Blade/Vite. Explicitly note this is the only PHP repo.
- §3 Conventions — Laravel idioms (controllers thin, services etc.). No
  Go conventions apply.
- §5 Cross-repo position — standalone leaf, outside both PMG and WellMed
  graphs. /closeout-extended doesn't walk this repo.

**What's distinctive:**
- Explicitly states "if you're here, you're working on marketing/branding
  content, not on the WellMed product"
- Doesn't try to fit the Go-service shape
- Empty Pattern Sources, empty Consumers in CROSS-REPO.md

---

## Notes for /cross-repo-init when matching archetype

- **Most wellmed-* code services match Archetype 1 or 2.** Use them as
  base; fold any pre-existing `.claude/CLAUDE.md` content into the
  archetype shape.
- **Frontend repos (wellmed-fe, wellmed-hq-fe) match Archetype 3.** Don't
  force Go-service patterns on them.
- **Detect stub** via §2.3 signals (only README.md + .gitignore + single
  main branch) BEFORE applying any archetype — stub trumps the others.
- **Marketing/non-graph repos** declare archetype "standalone" and use the
  minimal Archetype 5 shape.

The skill should propose the archetype match to the user at Step 5.1 and
let them confirm or override before scaffolding.
