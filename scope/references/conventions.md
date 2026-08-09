# /scope — conventions reference

Detail pulled out of SKILL.md so it is retrievable rather than resident. Read the section
you need; nothing here is required on a run that doesn't hit it.

## 1. Program-member scopes (ADR-029; PMG port ADR-002)

A **program** is a `plans/{program-slug}/` folder with a `{slug}-brief.md` member list —
e.g. `catalog-program/catalog-brief.md`, `control-tower-program/control-tower-brief.md`.

### 1.1 The brief's name is derived, never bare

`{slug}-brief.md` = the program folder's slug with any `-program` suffix dropped
(ADR-029 v1.2). `control-tower-program/` → `control-tower-brief.md`. A new program
scaffold creates that slugged file, **never** a bare `brief.md`.

### 1.2 Members are flat and top-level

A member scope gets a normal `{plans_dir}/{N}-{slug}/` folder and a normal PLANS-INDEX
row, exactly like a standalone scope. **Members never live inside the program folder** —
the `C{n}`/`M{n}` folders there are placeholders (`NOT-YET-SCOPED.md`), not scopes. This
keeps every scope visible to a `plans/*` scan and to the index.

### 1.3 Detecting membership

The user names a program or one of its `C{n}`/`M{n}` members, or the task maps to a
member row in some `plans/*/*-brief.md`.

### 1.4 Graduation, after the scope files exist (ADR-029 §2.3.2)

- Update the program brief's member row to point at `{N}-{slug}` and mark it scoped.
- Retire the placeholder: rewrite `C{n}-{slug}/NOT-YET-SCOPED.md` to a one-line pointer
  at `{N}-{slug}`, or remove the placeholder folder — the brief now carries the mapping.

### 1.5 Lifecycle

**stub** (placeholder in the program folder) → **live** (flat `{N}-{slug}/`,
index-visible) → **archived** (`{program-slug}/archive/{N}-{slug}/`, *not* the repo-wide
`archive/`). See SKILL.md §7.1.

## 2. Plans directories

Resolved by `scripts/resolve-plans-dir.sh`, which is the single owner of this mapping:

| Project | Plans directory |
|---|---|
| any repo under `~/Projects/pmg/` | `~/Projects/pmg/pmg-docs/plans/` |
| any repo under `~/Projects/wellmed/` | `~/Projects/wellmed/kalpa-docs/plans/` |
| `~/Projects/ai-skills/` | `~/Projects/ai-skills/plans/` |

Exit 3 = unrecognized project, ask the user. Exit 4 = resolved but absent, which means
the docs repo isn't cloned — stop, don't create it.

## 3. PLANS-INDEX shape

Canonical, both tables, enforced by `scripts/plans-index.py`:

```
| # | Status | Folder | Description | Created by |
```

Rules live in `/markdown-style` §11.7. The two that get broken most: table membership
follows **disk state** (a folder under `archive/` belongs in Completed), and the row
moves in the **same commit** as the folder.

Write the Description as 3–4 real sentences. It is Alex's console status tracker, not a
label — see `/markdown-style` §11.7.4.

## 4. Contract surfaces (Step 0.6)

Treat as a contract surface: `*.proto`; `**/schema.prisma`; `openapi.{yaml,yml,json}`;
`*.graphql`, `*.graphqls`; anything under `proto/`, `contracts/`, `schemas/`.

When one changes and `CROSS-REPO.md` exists, **every Consumer is in scope by default** —
per consumer, add: regenerate stubs/client/types, update call sites, run its tests.
Deferral is allowed but must be explicit and named in `## NOT in Scope`.
