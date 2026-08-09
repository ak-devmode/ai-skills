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

Alex's personal Claude Code skills repo. Each top-level directory except
`templates/`, `scripts/` and `plans/` is a skill, registered with Claude Code by a
symlink at `~/.claude/skills/<name>` → `~/Projects/ai-skills/<name>`.
(That exclusion list is `NON_SKILL_DIRS` in `setup.sh` — keep them in sync.)
Edits land immediately — there is no build, no deploy, no version bump
required for behavior to change.

Skills published here govern Alex's planning + execution workflow
(`/prd`, `/scope`, `/plan`, `/closeout`, `/closeout-extended`,
`/cross-repo-init`), markdown formatting (`/markdown-style`), and a
handful of project-specific helpers (`kalpa-*`, `member-record-amend`),
plus `/review`, which layers a Kalpa domain pass over gstack's engine.
See `ARCHITECTURE.md §1` for the full catalog with status.

A sibling skills repo at `~/Projects/gstack/` (upstream
`garrytan/gstack`) is symlinked alongside this one. The two repos are
independent — share conventions, not code.

---

## 2. Trunk branch and workflow

- **Trunk branch:** `main`. Solo-dev repo (ak-devmode/ai-skills).
- Direct commits on `main` are the default. No PR workflow.
- Conventional commit prefix: free-form, but match recent history —
  `feature:` (spelled out, not `feat:`), `fix:`, `docs:`, `plan:`,
  `cross-repo-init:`, etc. Subject
  starts with the affected skill or area in brackets when applicable
  (e.g. `plan: [Task 5.5] ...`).
- Long-running work is tracked in `plans/<scope>/<scope>-PROGRESS.md`
  rather than git WIP. Multiple sessions append to the progress file;
  the work commits when a phase or scope completes.

### 2.1 After every merge to `main` — propagate, don't assume

Skills are consumed by symlink from `~/.claude/skills/<name>` into this repo, so
Alex's machine picks up a merge instantly. **Nobody else's does.** A merge here is
not delivery. On each merge to `main`:

- [ ] Announce it to the team so they `git pull` their ai-skills clone. A
      teammate on a stale clone runs a stale skill and produces documents that
      silently violate the convention just changed.
- [ ] Check for **vendored copies** of these skills in other repos and refresh or
      delete them. Known copy: `kalpa-docs/claude-skills/` — four flat `.md`
      files hand-copied in March 2026, still frozen there, 305 lines against
      markdown-style's 548, missing §10 and §11 entirely and missing `/scope`
      altogether. A stale duplicate is worse than no copy: an agent working in
      that repo reads it and follows superseded rules.

> **Why this is a checklist item and not a habit.** The March copy was made once,
> for team onboarding, and never touched again — nothing in any skill told anyone
> it existed or that it had to track canon. Propagation that depends on someone
> remembering an undocumented copy is propagation that stops happening.

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
- `/closeout` Step 8 invokes `/cross-repo-init` for trio sync.
- `/closeout` Step 11 invokes `/plan` §11 archive logic.
- `/closeout-extended` invokes `/closeout`'s engine per neighbor repo in a
  worktree (inheriting the trio sync rather than duplicating it).

3.6 **Templates live in `templates/` (shared) or `<skill>/templates/`
(private).** `closeout-prep.md.template` is in the top-level `templates/`
because both `/plan` (writes it) and `/closeout` (reads it) need it.
`cross-repo-init/templates/` holds the CROSS-REPO / ARCHITECTURE /
CLAUDE templates because only `/cross-repo-init` consumes them.

**Scripts follow the same split** — `scripts/` (shared) or
`<skill>/scripts/` (private, e.g. `closeout/scripts/verify-archive.sh`).
See `scripts/README.md` for contracts and exit codes.

3.6.1 **Deterministic work goes in a script, not in prose.** If a step has
one correct answer — resolving a path, claiming a number, mutating a table,
classifying SHAs — an LLM following instructions is strictly worse than
executing code, because it fails differently every time and nobody notices.
Prose belongs to judgment: what to ask, when to stop, which trade-off wins.

> **Why this is a rule.** Two of Alex's worst index defects were prose steps.
> "Read PLANS-INDEX, find the highest number, increment" raced two sessions
> into the same scope number (110 → renumbered 111). "If no row exists,
> append one," with a seven-column template and no header writer, accreted
> 40 untabled rows that were for a while the only registration for scopes
> 101/106/107/108. Neither was a comprehension failure. Both were prose
> asked to be a program.

3.6.2 **A scripted edit must fail when it changes nothing.** Use
`scripts/edit-guard.py` for any multi-file or pre-commit edit rather than a
`python3 - <<PY` string-replace. It validates every anchor before writing
anything and exits non-zero on a miss, an ambiguous match, or a no-op.

> **Why.** On 2026-08-09, three scripted edits in one session reported success
> while changing nothing — an anchor that ignored leading whitespace, a regex
> anchored to `^### 12\\.` that skipped seven body items, and a `--folder`
> override that wrote an invented path over a correct one. Each printed a MISS
> to stdout; each was followed by a commit. This is the same failure family as
> `gstack-review-log` exiting 0 after writing nothing, and as §14.0's archive
> gate: **a green result is not a completed action.** Printing is not checking.

3.7 **Symlinks, not copies, for `~/.claude/skills/`.** Adding a new
skill: create directory + SKILL.md, then run `./setup.sh` — it links
every top-level dir, arbitrates name collisions, and prunes links whose
source is gone. Removing: delete the directory, then re-run `./setup.sh`.
Restart the session for either to register.

3.8 **Skills are top-level directories with a `SKILL.md`. Never nested.**
Claude Code does not reliably register a skill one level deeper than
`~/.claude/skills/<name>/SKILL.md`. A container directory silently
publishes *some* of its children and drops the rest.

> **Why this is a rule and not a preference.** `kalpa/` was a container
> holding six sub-skills with no `SKILL.md` of its own. `setup.sh` linked
> the container; Claude Code registered **two** of the six. The other four
> — `coding-standards`, `kalpa-context`, `satu-sehat-fhir`, and `review` —
> were invisible for months, and because the bare name `review` was never
> claimed, every `/review` Alex ran was gstack's. Fixed 2026-08-09 by
> flattening to `kalpa-*` top-level dirs; `setup.sh` now fails loudly on a
> SKILL.md-less directory that contains nested ones.

3.9 **Namespace project-scoped skills.** Kalpa/WellMed skills are
`kalpa-<name>`. A generic name (`migrate`, `generate-api`, `review`) in a
shared namespace is a collision waiting for whichever installer runs last.
`setup.sh` arbitrates bare-name collisions in ai-skills' favour, but a
name that can't collide is better than a name that gets arbitrated.

---

## 4. Key files

```
prd/SKILL.md                    — PRD generator
scope/SKILL.md                  — task scoping + skill router (judgment + gates only)
scope/references/               — conventions + postmortems, loaded on demand
scope/templates/                — scope.md / progress.md / plan-stub / skill-checklist
plan/SKILL.md                   — task execution engine (Phase 0 + Pattern-First Rule)
plan/tests/verification-recipes.md  — manual test recipes for /plan rules
closeout/SKILL.md               — local self-heal
closeout-extended/SKILL.md      — cross-repo recursive self-heal
closeout-extended/tests/upward-traversal-recipe.md
cross-repo-init/SKILL.md        — trio bootstrap + maintenance (invoked by /closeout Step 8)
cross-repo-init/templates/      — CROSS-REPO / ARCHITECTURE / CLAUDE templates + examples
markdown-style/SKILL.md         — markdown formatting rules
review/SKILL.md                 — two-pass review: gstack engine + Kalpa domain pass
kalpa-*/SKILL.md                — WellMed/Kalpa project skills (flat, namespaced — §3.8)
member-record-amend/SKILL.md    — PMG Padma Care record-edit skill
templates/closeout-prep.md.template   — ledger schema (shared by /plan + /closeout)
scripts/README.md               — contracts + exit codes for the shared scripts
scripts/resolve-plans-dir.sh    — plans-dir resolution (one owner, 5 callers)
scripts/claim-scope-number.sh   — scope numbering, race-defensive across 4 sources
scripts/plans-index.py          — PLANS-INDEX validate/add/move, schema-enforcing
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
  invokes /plan §11 — never duplicates it. (See §3.5 of this file and
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

9.2 **Recent work:** `plans/closeout-skills/` (complete) shipped /closeout,
/closeout-extended, /cross-repo-init plus the /plan Phase 0 + Pattern-First
extensions across the PMG and WellMed fleets. Most recent direct-to-main
work (2026-06-01): gate-driven phasing across /scope, /plan, /markdown-style,
and /closeout Step 8 trio-sync via /cross-repo-init.

9.3 **Agent memory is scoped by working directory — it does NOT follow you
across projects.** Each project gets its own store at
`~/.claude/projects/<cwd-slug>/memory/`. Nine exist; two are real
(`-Users-alexknecht-Projects-pmg`, 148 files, and
`-Users-alexknecht-Projects-WellMed`, 224) and the rest are splinters
minted by starting a session from a subdirectory.

> **Correction (2026-08-09).** This section previously claimed the
> pmg-scoped store "happens to load when working in any project Alex
> opens." It does not. Every memory file this repo's skills cited as
> justification lives *only* in the pmg store, so those citations
> dead-ended whenever a skill ran in WellMed — which is most of the time.

**Therefore: a skill authored here never cites a memory path.** A skill
that depends on a rule states the rule in its own body. Memory is for
*this* session's agent, not a cross-project reference library, and a
citation an agent cannot open is worse than no citation — it reads as a
file the reader should have been able to find.

Project-resident docs are the correct thing to cite instead, because they
travel with the repo: the target repo's `CLAUDE.md`, its
`ARCHITECTURE.md`, `CROSS-REPO.md`, and for WellMed the ADR index at
`kalpa-docs/adrs/` and `kalpa-docs/FLEET.md`.

---

<!-- Last scaffolded by /cross-repo-init: 2026-05-11; manual consistency pass: 2026-06-01 -->
