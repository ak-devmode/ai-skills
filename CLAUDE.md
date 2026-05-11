# CLAUDE.md — ai-skills

<!--
Agent context for Claude Code in this repo. Read on session start.

Companion files:
- ARCHITECTURE.md — skill catalog, invocation flow, key decisions, drift
- CROSS-REPO.md — standalone-leaf archetype, operational consumers

This repo IS the source of many of the skills you (Claude Code) are
running. Edits here change your own behavior in future sessions
immediately, via the symlinks at `~/.claude/skills/<name>`.
-->

---

## 1. What this repo is

Alex's personal Claude Code skills repo. Each top-level directory (except
`templates/` and `plans/`) is a skill registered with Claude Code via a
symlink at `~/.claude/skills/<name>` → `~/Projects/ai-skills/<name>`.
Edits land immediately — there is no build, no deploy, no version bump
required for behavior to change.

Skills published here govern Alex's planning + execution workflow
(`/prd`, `/scope`, `/plan`, `/closeout`, `/closeout-extended`,
`/cross-repo-init`), markdown formatting (`/markdown-style`), and a
handful of project-specific helpers (`kalpa/`, `member-record-amend`).
See `ARCHITECTURE.md §1` for the full catalog with status.

A sibling skills repo at `~/Projects/gstack/` (upstream
`garrytan/gstack`) is symlinked alongside this one. The two repos are
independent — share conventions, not code.

---

## 2. Trunk branch and workflow

- **Trunk branch:** `main`. Solo-dev repo (ak-devmode/ai-skills).
- Direct commits on `main` are the default. No PR workflow.
- Conventional commit prefix: free-form, but match recent history —
  `feat:`, `fix:`, `docs:`, `plan:`, `cross-repo-init:`, etc. Subject
  starts with the affected skill or area in brackets when applicable
  (e.g. `plan: [Task 5.5] ...`).
- Long-running work is tracked in `plans/<scope>/<scope>-PROGRESS.md`
  rather than git WIP. Multiple sessions append to the progress file;
  the work commits when a phase or scope completes.

---

## 3. Architecture decisions you must know

3.1 **SKILL.md frontmatter is the contract.** Every skill has a
`SKILL.md` at its root with:
- `name` — the slash-command name (no leading slash). Must match the
  directory name.
- `version` — semver. Bump when behavior changes.
- `description` — what the skill does + when to trigger. Voice triggers
  in a separate parenthesized clause if applicable.
- `allowed-tools` — explicit tool whitelist. Skills that ban
  AskUserQuestion list every tool BUT AskUserQuestion.

3.2 **Numbered inline questions, never AskUserQuestion.** Per
`feedback_no_askuserquestion.md` and `feedback_numbered_questions.md`.
Skills authored here halt and present numbered options in plain text
when they need disambiguation. Voice the question naturally; do not
emit a tool call.

3.3 **Numbered hierarchical headings throughout skill bodies.** `1`,
`1.1`, `1.1.1` per `feedback_style.md` and `/markdown-style`. Lets the
user reference a section by number when reviewing.

3.4 **ASCII diagrams only, never Mermaid.** Box-drawing characters
(`│ ├── └──`) are acceptable; plain ASCII (`+`, `-`, `|`, `>`, `*`) is
preferred. Same rule applies to skill output that the skill writes into
target repos.

3.5 **Cross-skill reuse, not duplication.** When you find a routine that
two skills need, factor it into one skill's section and have the other
reference it by section number. Current examples:
- `/closeout` Step 10 invokes `/plan` §12 archive logic.
- `/closeout-extended` invokes `/closeout`'s 11-step engine per neighbor
  repo in a worktree.

3.6 **Templates live in `templates/` (shared) or `<skill>/templates/`
(private).** `closeout-prep.md.template` is in the top-level `templates/`
because both `/plan` (writes it) and `/closeout` (reads it) need it.
`cross-repo-init/templates/` holds the CROSS-REPO / ARCHITECTURE /
CLAUDE templates because only `/cross-repo-init` consumes them.

3.7 **Symlinks, not copies, for `~/.claude/skills/`.** Adding a new
skill: create directory + SKILL.md, then
`ln -s ~/Projects/ai-skills/<name> ~/.claude/skills/<name>`. Removing:
delete the symlink first, then archive or delete the directory.

---

## 4. Key files

```
prd/SKILL.md                    — PRD generator
scope/SKILL.md                  — task scoping + skill router
plan/SKILL.md                   — task execution engine (Phase 0 + Pattern-First Rule)
plan/tests/verification-recipes.md  — manual test recipes for /plan rules
closeout/SKILL.md               — local self-heal
closeout-extended/SKILL.md      — cross-repo recursive self-heal
closeout-extended/tests/upward-traversal-recipe.md
cross-repo-init/SKILL.md        — trio bootstrap
cross-repo-init/templates/      — CROSS-REPO / ARCHITECTURE / CLAUDE templates + examples
markdown-style/SKILL.md         — markdown formatting rules
kalpa/<sub-skills>/SKILL.md     — WellMed/Kalpa-project skills
member-record-amend/SKILL.md    — PMG Padma Care record-edit skill
templates/closeout-prep.md.template   — ledger schema (shared by /plan + /closeout)
plans/PLANS-INDEX.md            — local plans tracking ai-skills development
plans/<scope>/                  — active scope folders
plans/archive/                  — completed scopes
plans/TO-DO.md                  — accumulated TODOs (v1.1 items, etc.)
CROSS-REPO.md                   — this trio
ARCHITECTURE.md
CLAUDE.md
```

---

## 5. Environment variables

N/A. Skills run inside Claude Code's session and inherit whatever
environment Claude Code itself has. No `.env` file, no SSM, no API keys
managed at this layer.

---

## 6. Build / test / lint

No build. No automated test suite. Skill verification is manual via
Claude Code invocation:

- **Add a skill or edit SKILL.md** — restart any open Claude Code
  session for the change to register (the skill list is loaded at
  session start).
- **Test a skill change** — invoke `/<name>` in a session and observe
  behavior. For multi-step skills (`/plan`, `/scope`, `/closeout`),
  follow the verification recipes under `<skill>/tests/` when present.
- **Markdown style of skill bodies** — eyeball + `/markdown-style`
  conventions. No linter currently.

---

## 7. What NOT to do

- **Do not use `AskUserQuestion`** in skills authored here. Use numbered
  inline-text questions. Same rule applies when writing user-facing
  text inside skills.
- **Do not fork an existing skill into a parallel implementation.** If
  `/closeout` and `/plan` need the same archive logic, /closeout
  invokes /plan §12 — never duplicates it. (See §3.5 of this file and
  Pattern-First Rule in `plan/SKILL.md` §7.)
- **Do not add a feature without a /scope or /plan entry.** Multi-step
  work tracked in `plans/<scope>/`; one-off small fixes can go direct
  with a clear commit message.
- **Do not break SKILL.md frontmatter contract.** `name` must match the
  directory; `allowed-tools` must be accurate (Claude Code enforces
  this).
- **Do not edit the symlinks in `~/.claude/skills/` to point elsewhere
  in a single repo.** Pointing a symlink at the wrong directory silently
  loads the wrong skill at session start.
- **Do not modify gstack skills** in `~/Projects/gstack/` from this
  repo's workflow. That's an upstream-tracking repo with `git pull`;
  edits there create conflict pain.

---

## 8. Cross-repo position

8.1 **Standalone leaf** — no upstream Pattern Sources, no contract
Consumers in the git graph. Operational consumers are every Claude Code
installation via symlinks. See `CROSS-REPO.md`.

8.2 PMG ↔ WellMed boundary is irrelevant here — ai-skills sits outside
both graphs.

---

## 9. Plans and memory

9.1 **ai-skills's own plans** live in `~/Projects/ai-skills/plans/`. This
is distinct from `~/Projects/pmg/pmg-docs/plans/` and
`~/Projects/wellmed/kalpa-docs/plans/` (which track work in those
projects). Per `reference_ai_skills_plans_dir.md`, `/scope` and `/plan`
recognize this dir.

9.2 **Active scope:** `plans/closeout-skills/` — building /closeout,
/closeout-extended, /cross-repo-init plus the /plan extensions. Phase 5
(dogfood pass) is wrapping up: PMG side complete (pmg-integrations
PR #68, pmg-chatwoot PR #115, pmg-docs pushed direct to main); WellMed
side complete (kalpa-docs + wellmed-infrastructure + 9 leaves); ai-skills
itself is the last leaf, closed by the trio commit that introduced this
file.

9.3 **Global agent memory** at
`~/.claude/projects/-Users-alexknecht-Projects-pmg/memory/` is shared
across PMG and ai-skills work (the memory path is project-scoped to the
pmg directory but happens to load when working in any project Alex
opens). Repo-relevant pointers:

- `feedback_no_askuserquestion.md` — banned in skills authored here
- `feedback_numbered_questions.md` — numbered inline, not bulleted
- `feedback_style.md` — communication/working-style
- `feedback_branch_workflow.md` — solo-dev, work on current branch
- `feedback_reuse_branches.md` — commit fixes onto open branches
- `feedback_iterative_prompt_tuning.md` — one-at-a-time, sequential
- `reference_ai_skills_plans_dir.md` — `/scope` + `/plan` recognize plans/
- `project_closeout_skills.md` — closeout-skills scope status pointer
- `project_pmg_wellmed_trunks.md` — independent-trunks rule (for skills
  that reason about cross-repo work)

---

<!-- Last scaffolded/audited by /cross-repo-init: 2026-05-11 -->
