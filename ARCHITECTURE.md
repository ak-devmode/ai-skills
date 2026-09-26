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

**Last refreshed:** 2026-09-25 (/closeout, scope 2 skills-relook — toolkit scripts, kalpa flatten, catalog)
**Maintained by:** manual edits + /closeout when invoked by plans rooted here

---

## 1. Components

<!-- Each top-level directory is either a skill (has SKILL.md), a shared
     resource directory (templates/), or scope-local planning state
     (plans/). One line per entry. -->

### 1.1 Planning + execution skills

- `prd/` — PRD generator: business need → structured PRD.
- `scope/` — scoping, skill router, progress tracker. Phases are bounded by work
  gates (A–F), never by context-window size.
- `plan/` — execution engine for `*-PLAN.md`: progress logging, ledger, human
  checkpoints; `/clear` suggested only at human/deploy/irreversible gates.
- `closeout/` — local self-heal + mandatory archive (Step 11 → /plan §11, gated by
  `closeout/scripts/verify-archive.sh`). Step 8 runs trio sync via /cross-repo-init.
- `closeout-extended/` — /closeout per CROSS-REPO.md neighbour, in ephemeral
  worktrees; never commits or pushes.
- `cross-repo-init/` — bootstrap + maintenance of the trio (CROSS-REPO.md,
  ARCHITECTURE.md, CLAUDE.md); templates in `cross-repo-init/templates/`.
- `ready-to-clear/` — fresh-subagent clear-readiness gate (disk truth vs git truth).
- `review/` — gstack engine + Kalpa/PMG domain pass.
- `scope-review/` — altitude-ordered review of a team member's scope.
- `concurrency/` — partition a scope into a verified DAG, dispatch the ready
  frontier to named herdr panes (worktree per writer), supervise.
- `herdr/` — herdr workflow layer: naming, worktree lifecycle, worker launch,
  layout, model routing. `herdr --skill` owns raw CLI syntax.
- `research/` — deep research: visible pane lanes (`research/scripts/lanes.py`) or
  the background `deep-research-lean` workflow.
- `repo-cleanup/`, `repo-cleanup-all/` — branch hygiene (+ plans hygiene in docs repos).
- `todo-sweep/` — verify TO-DO.md items against trunk.
- `grafana-remediate/` — nightly WellMed alarm remediation workflow.

### 1.2 Document-style skills

- `markdown-style/` — format rules for structured .md (numbered headings, checkbox
  TODOs, ASCII-only diagrams); owns plan/progress/scope/PLANS-INDEX conventions.
- `md2docx/` — markdown → branded .docx.

### 1.3 Project-specific skills

- `kalpa-*` — WellMed/Kalpa skills (`kalpa-coding-standards`, `kalpa-context`,
  `kalpa-generate-api`, `kalpa-migrate`, `kalpa-satu-sehat-fhir`). Flat top-level
  dirs, namespaced — a container dir registered only 2 of 6 (CLAUDE.md §3.8).
- `member-record-amend/`, `pha-console/` — PMG Padma Care skills.
- `nano-banana/` — image generation helper.

### 1.4 Shared resources

- `templates/` — templates shared across skills (`closeout-prep.md.template`:
  written by /plan, read by /closeout).
- `scripts/` — deterministic steps the skills call instead of describing them in
  prose (CLAUDE.md §3.6.1). Plans dir, scope numbering, PLANS-INDEX writes,
  folder sweep, context gather, `Executed by` stamp, Repo Graph snapshot +
  freshness gate, ledger bootstrap, dispatch log, herdr pane identity, branch
  survey, guarded edits, and the accretion linter (`lint-skill.py`). Contracts
  and exit codes: `scripts/README.md`.

### 1.5 Repo-local planning state

- `plans/` — ai-skills's own development work (not consumed by the skills):
  `PLANS-INDEX.md`, `TO-DO.md`, `<N>-<slug>/` active scopes, `archive/`.

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
        ─ runs scripts/ for deterministic steps
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

Cross-skill invocation: `/closeout` invokes `/cross-repo-init` (Step 8,
trio sync) and `/plan` §11 archive logic (Step 11) — not re-implementing
either. `/closeout-extended` invokes `/closeout` per neighbor repo and
inherits the trio sync. `/scope` references the full skill catalog by name.

---

## 3. Key Decisions

3.1 **SKILL.md frontmatter is the contract.** Each skill has a
`SKILL.md` at its root with a frontmatter block listing `name`, `version`,
`description`, and `allowed-tools`. Claude Code reads frontmatter to
register the skill; the body is read on invocation. Changing the
frontmatter shape requires updating every skill in lockstep.

3.2 **Numbered inline questions, never AskUserQuestion.** Per Alex's
preference, skills authored here use numbered
inline-text questions (`1. ... 2. ... 3. ...`), not the AskUserQuestion
tool. Skills that need disambiguation halt and ask in plain text.

3.3 **Numbered hierarchical headings.** Per `/markdown-style`, all skill bodies use `1`, `1.1`, `1.1.1` heading
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

3.6 **Solo-dev repo, direct commits to main.** No PR workflow. Multi-session
work is tracked in `plans/<N>-<slug>/progress.md` (child plans as sections
inside it).

3.7 **Skills are symlinked into Claude Code, not copied.** Edits land
in `~/.claude/skills/<name>` immediately because that path is a symlink
to this repo. There is no "deploy" step.

3.8 **Cross-skill reuse, not duplication.** /closeout reuses /plan §11
archive logic directly (does not duplicate). /closeout-extended invokes
/closeout per neighbor (does not duplicate self-heal logic). When a
common pattern emerges, factor it into one skill's section and have
others reference it by section number.

3.9 **Deterministic work goes in `scripts/`, and every writer reads back.** A
step with one correct answer is code, not prose; a script that writes verifies
the destination before reporting success (CLAUDE.md §3.6.1–3.6.2).

3.10 **Size is advisory, not a cap.** The accretion linter fails only on
mechanical defects; size, growth-without-deletion and cross-skill duplication are
NOTEs. Never split a mandatory rule into `references/` to hit a line count
(scope 2 decision, 2026-09-25).

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

### 6.1 Skill catalog status (2026-09-25)

| Skill | Version | Notes |
|---|---|---|
| `plan` | 3.8.0 | Scripts for folder, stamp, Repo Graph gate, ledger. |
| `scope` | 3.8.0 | Step 0 = `context-gather.sh`; stub index rows via `plans-index.py`. |
| `closeout` | 1.3.0 | Memory steps follow harness conventions; residual verify owned by /plan §11.1. |
| `closeout-extended` | 1.0.1 | |
| `cross-repo-init` | 1.5.0 | Branch survey = `repo-survey.sh`; CLAUDE template no longer writes memory paths. |
| `markdown-style` | 1.3.0 | Child plans have no own progress file; Draft→Ready is the go signal. |
| `prd` | 1.1.0 | Step 0 = `context-gather.sh`. |
| `concurrency` | 0.5.0 | Dedup'd against herdr; pane naming + dispatch log via scripts. |
| `herdr` | 0.1.5 | Opus seat = 5.5 (`opus[1m]`). |
| `review` | 2.2.0 | |
| `ready-to-clear` | 1.1.0 | |
| `kalpa-*` | unversioned | Flattened 2026-08-09. |

### 6.2 Active scope

- Scope 5 (verify-lever) per `plans/PLANS-INDEX.md`. Closed recently: scope 6
  (research-lanes, 2026-09-26) and scope 2 (skills-relook, 2026-09-25) — see
  `plans/archive/`.

### 6.3 Known gaps

- Paraphrased cross-skill duplicates are invisible to `lint-skill.py`; the
  semantic eval pass is deferred to a second sighting of drift (`plans/TO-DO.md`).
- 13 repos' CLAUDE.md files still carry the pmg memory path the old trio template
  wrote (`plans/TO-DO.md`).

---

<!-- Last scaffolded by /cross-repo-init: 2026-05-11; /closeout refresh: 2026-09-25 -->
