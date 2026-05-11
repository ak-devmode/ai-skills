# ARCHITECTURE — ai-skills

<!--
ai-skills is a personal Claude Code skills repo. There is no runtime
system — each top-level directory is a skill that Claude Code invokes
through its skill interface. The "architecture" here is the layout of
those skills and the cross-skill contracts (template files, shared
conventions) they participate in.

Optimized for agent consumption: Claude Code reads this file at session
start to understand which skills exist and how they fit together.
-->

**Last refreshed:** 2026-05-11
**Maintained by:** manual edits + /closeout when invoked by plans rooted here

---

## 1. Components

<!-- Each top-level directory is either a skill (has SKILL.md), a shared
     resource directory (templates/), or scope-local planning state
     (plans/). One line per entry. -->

### 1.1 Planning + execution skills

- `prd/` — Product Requirements Document generator. Translates a business
  need into a structured PRD.
- `scope/` — Task scoping, skill router, and progress tracker. Reads
  current context, eliminates assumptions via numbered inline questions,
  outputs a phased scope with skill checklist.
- `plan/` — Task Execution Engine. Executes tasks from a *-PLAN.md
  document with progress logging and human checkpoints. Currently v3.1.0;
  Phase 2 of the closeout-skills scope extended Phase 0 + the Pattern-First
  Rule.
- `closeout/` — Local repo self-heal after a /plan run. New (Phase 3 of
  the closeout-skills scope). Consumes `templates/closeout-prep.md.template`.
- `closeout-extended/` — Recursive cross-repo self-heal across the
  CROSS-REPO.md graph. New (Phase 4 of the closeout-skills scope). Works
  in ephemeral git worktrees; never commits or pushes.
- `cross-repo-init/` — Bootstrap the trio (CROSS-REPO.md, ARCHITECTURE.md,
  CLAUDE.md) for a repo. v1.1 (post-WellMed-dogfood). Templates live in
  `cross-repo-init/templates/`.

### 1.2 Document-style skills

- `markdown-style/` — Format rules for structured .md documents (PRDs,
  plans, playbooks). Numbered headings, checkbox TODOs, ASCII-only diagrams.

### 1.3 Project-specific skills

- `kalpa/` — WellMed/Kalpa-project-specific skills (`/coding-standards`,
  `/generate-api`, `/kalpa-context`, `/migrate`, `/review`,
  `/satu-sehat-fhir`). Subdirectory grouping — each skill is symlinked
  individually into `~/.claude/skills/`.
- `member-record-amend/` — PMG Padma Care skill: edit a member's Notion
  record with PHA-supplied free-text instructions. Append-only on Medical
  sections.

### 1.4 Shared resources

- `templates/` — Templates shared across skills. Currently:
  `closeout-prep.md.template` (read by /plan to write the ledger, read by
  /closeout to consume it). Moved here from `plan/templates/` during Task
  6.1 to make ownership-free templates discoverable.

### 1.5 Repo-local planning state

- `plans/` — Plans tracking ai-skills's own development work (not
  consumed by the skills it publishes). Layout follows the same
  convention as `pmg-docs/plans/` and `kalpa-docs/plans/`:
  - `plans/PLANS-INDEX.md` — registry of plans/scopes/PRDs for ai-skills work
  - `plans/TO-DO.md` — accumulated TODOs
  - `plans/<N>-<slug>/` — active scope folders (currently
    `plans/closeout-skills/`)
  - `plans/archive/` — completed scopes

---

## 2. Data Flow

<!-- "Data flow" here is the skill invocation lifecycle. -->

```
   Claude Code session                    ai-skills repo
   ──────────────────                    ──────────────

   User: "/scope this feature"
        │
        ▼
   Claude reads skill list from
   ~/.claude/skills/ (symlinks)
        │
        ▼
   Resolves symlink                ─►   ~/Projects/ai-skills/scope/SKILL.md
                                        ─ frontmatter (name, version,
                                          allowed-tools, description)
                                        ─ skill body (numbered sections)
        │
        ▼
   Skill executes inline in
   Claude's conversation:
        ─ reads CLAUDE.md, ARCHITECTURE.md, CROSS-REPO.md
          of TARGET repo (not this one)
        ─ may read templates/ files
        ─ may invoke other skills via Skill tool
        │
        ▼
   Skill writes output to:
        ─ TARGET repo (code edits)
        ─ TARGET project plans dir
          (e.g. pmg-docs/plans/, kalpa-docs/plans/)
        ─ ai-skills/plans/ ONLY when planning
          ai-skills's own development
```

Cross-skill invocation: `/closeout` invokes `/plan` §12 archive logic
(not re-implementing it). `/closeout-extended` invokes `/closeout` per
neighbor repo. `/scope` references the full skill catalog by name.

---

## 3. Key Decisions

3.1 **SKILL.md frontmatter is the contract.** Each skill has a
`SKILL.md` at its root with a frontmatter block listing `name`, `version`,
`description`, and `allowed-tools`. Claude Code reads frontmatter to
register the skill; the body is read on invocation. Changing the
frontmatter shape requires updating every skill in lockstep.

3.2 **Numbered inline questions, never AskUserQuestion.** Per Alex's
preference (`feedback_no_askuserquestion.md`,
`feedback_numbered_questions.md`), skills authored here use numbered
inline-text questions (`1. ... 2. ... 3. ...`), not the AskUserQuestion
tool. Skills that need disambiguation halt and ask in plain text.

3.3 **Numbered hierarchical headings.** Per `feedback_style.md` and
`/markdown-style`, all skill bodies use `1`, `1.1`, `1.1.1` heading
hierarchy so feedback can reference sections.

3.4 **ASCII diagrams only.** Mermaid is banned (unreadable in
terminals/less/TextMate). Box-drawing characters are acceptable; plain
ASCII is preferred. Same rule applies to skill output.

3.5 **Templates live in `templates/`, not per-skill.** Shared templates
(currently just `closeout-prep.md.template`) live in the top-level
`templates/` directory so multiple skills can reference one canonical
copy. Per-skill templates that are private to a single skill may live
under that skill's directory (e.g. `cross-repo-init/templates/` holds
the trio templates because they are only consumed by /cross-repo-init).

3.6 **Solo-dev repo, direct commits to main.** No PR workflow. Per-feature
work goes on main; in-progress work that spans sessions is tracked in
`plans/<scope>/<scope>-PROGRESS.md`.

3.7 **Skills are symlinked into Claude Code, not copied.** Edits land
in `~/.claude/skills/<name>` immediately because that path is a symlink
to this repo. There is no "deploy" step.

3.8 **Cross-skill reuse, not duplication.** /closeout reuses /plan §12
archive logic directly (does not duplicate). /closeout-extended invokes
/closeout per neighbor (does not duplicate self-heal logic). When a
common pattern emerges, factor it into one skill's section and have
others reference it by section number.

---

## 4. External Integrations

- **GitHub** — `git@github-akdevmode:ak-devmode/ai-skills.git` (solo
  repo on the ak-devmode account).
- **Claude Code** — the runtime that loads and invokes skills. No direct
  API integration; skills run inside Claude Code's existing conversation
  loop.
- **Symlinks to `~/.claude/skills/`** — operational integration only,
  not a code dependency.

---

## 5. Cross-Repo Position

ai-skills is a **standalone leaf** — see `CROSS-REPO.md`. It has no
upstream Pattern Sources and no contract Consumers. Operationally, every
project Alex works in inherits these skills via Claude Code's skill
mechanism, but the inheritance is not git-traversable.

PMG ↔ WellMed boundary is irrelevant here — ai-skills sits outside both
graphs.

---

## 6. Current Code State vs Target Architecture

<!-- Honest read on what's actually built vs what this doc describes.
     For a skills repo, "drift" means: skills declared in §1 that don't
     have a SKILL.md, or skill directories that exist but aren't documented
     in §1. Plus: contracts (frontmatter, conventions) that have evolved
     past what older skills follow. -->

### 6.1 Skill catalog status (2026-05-11)

| Skill | Status | Notes |
|---|---|---|
| `markdown-style` | Stable | Established before the closeout-skills scope. |
| `prd` | Stable | |
| `scope` | Stable | |
| `plan` | v3.1.0, recently updated | Phase 0 + Pattern-First Rule extensions from Phase 2 of closeout-skills. |
| `closeout` | New, Phase 3 of closeout-skills | Awaiting end-to-end dogfood pass. |
| `closeout-extended` | New, Phase 4 of closeout-skills | Awaiting end-to-end dogfood pass. |
| `cross-repo-init` | v1.1, recently bumped | Folded post-WellMed dogfood findings (assess-first, CLAUDE.md folding, branch-survey cascade). Phase 5 dogfooding it now. |
| `kalpa/` | Stable | Six WellMed-project skills. |
| `member-record-amend` | Stable | |

### 6.2 Active scope

- `plans/closeout-skills/` — closeout-skills scope is in Phase 5 (dogfood
  pass). As of 2026-05-11: PMG side complete (pmg-integrations,
  pmg-docs, pmg-chatwoot trios committed; pmg-integrations and
  pmg-chatwoot have open PRs); WellMed side complete (kalpa-docs +
  wellmed-infrastructure + 9 leaves + 2 marketing/sparse repos);
  ai-skills itself is the last leaf and this commit closes it.

### 6.3 Open items deferred to v1.1 of closeout-skills

`plans/TO-DO.md` accumulates calibration findings:

- Pattern-grep candidate pool vs contract-traversal graph (split in
  CROSS-REPO.md v1.1 — `grep-only: true` flag per Pattern Source).
- Auto-generate-diagrams: relax for unambiguous-happy-path hubs.
- ADR numbering collision audit during /cross-repo-init.
- `.claude/CLAUDE.md` reconciliation prompt during /cross-repo-init Step 2
  (the trigger that surfaced the assess-first lesson — already partly
  baked into v1.1, refine further).
- Feature-branch heuristic: note "merged into trunk" status inline rather
  than treating matched-name branches as live drift.
- Branch-aware code surveying cascade (already in v1.1; mark verified).
- Standard ARCHITECTURE.md §6 Drift section template (already in v1.1; mark verified).

---

<!-- Last scaffolded/audited by /cross-repo-init: 2026-05-11 -->
