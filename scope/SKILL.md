---
name: scope
version: 3.0.0
description: |
  Task scoping, skill router, and progress tracker. Reads current context (git diff,
  branch, CLAUDE.md, open files), eliminates assumptions via two rounds of structured
  questions, then outputs a phased scope with a full 14-skill checklist marking N/A
  skills with reasons. For multi-session work, generates plan stub files (one per phase,
  each ~1 context window) that /plan (task-runner) can execute. Creates a tracking
  folder (scope.md + progress.md) in the project's central plans directory.
  Progress.md is a living document updated throughout execution.
  Use when asked to "scope this", "plan this task", "what skills do I need", "before
  we start", "scope out", or at the beginning of any non-trivial feature or bug fix.
  Also trigger when a task touches multiple files, services, or spans more than one
  session.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
---

# /scope — Task Scoping, Skill Router & Progress Tracker

You are acting as a structured scoping agent. Your job: read context, ask two focused
rounds of questions to eliminate assumptions, then produce a phased PRD with a ranked
skill checklist. The output goes directly into plan execution — make it actionable.

The scope folder is the **single source of truth** for a task's plan, decisions, and
progress. It lives in a central plans directory (not in the source repo) so that work
spanning multiple repos is tracked in one place and past scopes form a searchable
engineering journal.

---

## Step 0 — Gather Context (run all bash blocks below, then synthesize)

Gather context before asking any questions. Never ask about something already
determinable from the environment.

```bash
# Detect project identity and branch
git remote -v 2>/dev/null | head -4
echo "---BRANCH---"
git branch --show-current 2>/dev/null || echo "unknown"
echo "---PWD---"
pwd
```

```bash
# Recent git activity (what changed, what's in flight)
git log --oneline -10 2>/dev/null || echo "no git history"
echo "---DIFF STAT---"
git diff --stat HEAD 2>/dev/null | head -30
git diff --staged --stat 2>/dev/null | head -20
```

```bash
# Open issues / work in progress indicators
cat CLAUDE.md 2>/dev/null | head -60 || cat .claude/CLAUDE.md 2>/dev/null | head -60 || echo "no CLAUDE.md"
```

```bash
# Check for active scopes in the plans directory
# PMG plans
ls -la ~/Projects/pmg/pmg-docs/plans/scope-* 2>/dev/null || echo "no active PMG scopes"
# WellMed plans
ls -la ~/Projects/wellmed/kalpa-docs/plans/scope-* 2>/dev/null || echo "no active WellMed scopes"
# Check SCOPE-INDEX if it exists
cat ~/Projects/pmg/pmg-docs/plans/PLANS-INDEX.md 2>/dev/null || true
cat ~/Projects/wellmed/kalpa-docs/plans/PLANS-INDEX.md 2>/dev/null || true
```

After running the above, synthesize what you know:
- Project (WellMed, PMG, other — from remote URL or PWD)
- Plans directory (derived from project — see Step 5)
- Branch name and what it implies about the task
- What files have changed and in which direction
- Any active scope folders already tracking work
- Project-specific context from CLAUDE.md (compliance needs, stack, etc.)

---

## Step 1 — Round 1: Assumption Removal

Generate 5–10 questions that, if answered wrong, would fundamentally change the
approach. Fire them all in a single `AskUserQuestion` call.

**Rules for Round 1:**
- Do NOT ask about things already determinable from git diff, branch name, or CLAUDE.md
- Cover: scope boundary, timeline, prod vs exploratory, UI involvement, compliance,
  coordination with other services/people, testing strategy
- For WellMed context: ask about SATU SEHAT compliance if the change touches patient
  data, API endpoints, or health records
- For PMG context: ask about worker health data handling, regulatory requirements
- Frame questions concisely — one line each, no preamble

**Example questions (generate dynamically based on what's ambiguous):**
- "Is this greenfield or modifying existing code?"
- "Time available: single session today, or multi-session across days?"
- "Going to production this sprint, or exploratory/staging only?"
- "Does this have a UI component, or purely backend/infra?"
- "Should testing be in-scope here, or tracked separately?"
- "Does another service or team need to be coordinated?"
- "Any SATU SEHAT / regulatory compliance angle?" (WellMed only)
- "Is there a specific user-facing outcome to verify, or internal only?"

Ask only the questions where a wrong assumption would change your fundamental approach.
Skip anything already clear from context.

---

## Step 2 — Round 2: Design Refinement

After processing Round 1 answers, ask the task-specific design questions that
determine the best solution architecture, not just the right scope.

Generate questions based on task type:

**For new API/service work:**
- "Synchronous call chain or async/saga pattern?"
- "Which service owns the new data? Where does it live in the DB schema?"
- "New migration needed, or extending existing tables?"

**For UI features:**
- "Mobile-first or desktop-primary?"
- "Reuse existing component patterns or new design needed?"
- "What's the empty/error/loading state?"

**For bug fixes:**
- "Is there a regression test missing, or a genuine edge case not worth testing?"
- "Reproducible locally? Do you have a test case that triggers it?"
- "Has this affected production, or caught pre-merge?"

**For infra/devops:**
- "Terraform-managed or manual?"
- "Blue/green deployment or in-place?"
- "Rollback plan needed in scope?"

Fire Round 2 as a single `AskUserQuestion` batch (3–7 questions, task-specific).
If Round 1 already resolved the design questions (small task), skip Round 2 and
proceed directly to output.

---

## Step 3 — Determine Scale: Atomic vs Phased

Based on all answers, decide the execution model:

**Atomic** (single session, no child plans) if ALL of these are true:
- One service, one repo
- Fits in a single context window (~200k tokens of work)
- Clear implementation path, no architecture decisions to evaluate
- Scope can orchestrate gstack skills directly without breaking into plans

**Phased** (multiple plans, each ~1 context window) if ANY of these are true:
- Task spans > 2 services or repos
- Estimated work exceeds 1 context window (~200k tokens)
- Involves architecture decisions with options to evaluate
- Has a regulatory/compliance gate that blocks later work
- Multiple distinct deliverables that benefit from separate sessions

When phased, each phase becomes a plan file (~1 context window = ~1 session).
Scope generates plan stubs that `/plan` (task-runner) can execute. See Step 5.9.

If ambiguous after Round 1+2: ask "How much time do you have for this? [Full session
today / Just this hour / Multi-session across days]" before proceeding.

---

## Step 4 — Generate the Skill Checklist (N/A logic)

Every scope document includes ALL 18 skills. Mark each as YES, OPTIONAL, or N/A with
a reason. N/A is determined per-task, not per-project — both WellMed and PMG have
frontends and all skills are potentially applicable.

**N/A conditions:**

| Condition (task-specific) | Skills marked N/A |
|---|---|
| No UI component in this task | `/browse`, `/qa` (browser), `/design-consultation`, `/design-review`, `/design-html`, `/design-shotgun`, `/plan-design-review` |
| No browser session needed | `/setup-browser-cookies` |
| Not a bug fix or debugging task | `/investigate` → N/A |
| No developer-facing output (API, CLI, SDK, docs) | `/plan-devex-review`, `/devex-review` → N/A |
| No design exploration needed (known pattern) | `/design-shotgun` → N/A |
| Task is not going to prod this sprint | `/ship` → mark OPTIONAL |
| No user-visible change | `/document-release` → mark OPTIONAL |
| Small single-session task | `/retro` → mark OPTIONAL |

**Mandatory skills:**
- `/plan-ceo-review` is **always YES**. It catches "why are we doing it this way at all?"
  reframes that save entire phases of wasted work. Run it first, before eng review.

**Shortcut:** `/autoplan` runs `/plan-ceo-review` + `/plan-design-review` +
`/plan-eng-review` + `/plan-devex-review` in sequence with auto-decisions. Use it
instead of skills 1–4 individually when you want a fast full-review pass.

**Skill sequence table (fill in based on task):**

Skills are grouped by workflow phase. Mark each YES, OPTIONAL, or N/A with reason.

### Plan Reviews (run first)

| # | Skill | Apply? | When | Notes |
|---|-------|--------|------|-------|
| 1 | /plan-ceo-review | **ALWAYS YES** | 1st | Reframe scope, challenge premises, find the 10-star version |
| 2 | /plan-eng-review | ? | 2nd | Architecture + data flow |
| 3 | /plan-design-review | ? | 2nd | Design audit before implementation |
| 4 | /plan-devex-review | ? | 2nd | DX audit — dev-facing APIs, CLIs, SDKs, docs |

### Implementation Support

| # | Skill | Apply? | When | Notes |
|---|-------|--------|------|-------|
| 5 | /investigate | ? | Pre-impl | Root cause debugging for bug fixes |
| 6 | /design-consultation | ? | Pre-impl | UI/UX design guidance |
| 7 | /design-html | ? | During impl | Production HTML/CSS from approved designs |
| 8 | /design-shotgun | ? | Pre-impl | Generate + compare design variants |

### Review & QA

| # | Skill | Apply? | When | Notes |
|---|-------|--------|------|-------|
| 9 | /review | ? | After impl | Pre-landing diff review |
| 10 | /health | ? | After impl | Code quality score (linter, tests, dead code) |
| 11 | /qa | ? | After ship | Browser-based QA on staging |
| 12 | /qa-only | ? | After impl | Run test suite (go test, npm test) |
| 13 | /browse | ? | During QA | Headless browser for UI verification |
| 14 | /devex-review | ? | After impl | Live DX audit — docs, getting-started, TTHW |
| 15 | /setup-browser-cookies | ? | Pre-QA | Set up browser session for QA |

### Ship & Post-ship

| # | Skill | Apply? | When | Notes |
|---|-------|--------|------|-------|
| 16 | /ship | ? | Final | PR creation + versioning |
| 17 | /document-release | ? | Post-ship | Sync docs with changes |
| 18 | /retro | ? | End of sprint | Retrospective |

---

## Step 5 — Determine Plans Directory & Write Output Files

### 5.1 Plans directory resolution

The scope folder lives in a **central plans directory**, not in the source repo.
Resolve based on the project detected in Step 0:

| Project | Plans directory |
|---|---|
| PMG (any repo under `~/Projects/pmg/`) | `~/Projects/pmg/pmg-docs/plans/` |
| WellMed (any repo under `~/Projects/wellmed/`) | `~/Projects/wellmed/kalpa-docs/plans/` |
| Other | Ask the user: "Where should the scope folder live?" |

If the plans directory doesn't exist, stop and tell the user — don't create it
silently (it implies the docs repo is missing).

### 5.2 Slug

Determine the slug: lowercase, hyphenated, 3–5 words from the task title.
Example: "wellmed-saga-handler-phase2", "pmg-report-export", "auth-refresh-bug"

The scope folder path is: `{plans_dir}/scope-{slug}/`

### 5.3 File references

Because the scope folder lives outside the source repo, **all file references in
scope.md and progress.md must use paths relative to the workspace root** (e.g.,
`padma-integrations/lib/xendit.js`, not `lib/xendit.js`). This avoids ambiguity
about which repo a path refers to.

For PMG: paths relative to `~/Projects/pmg/`
For WellMed: paths relative to `~/Projects/wellmed/`

### 5.4 Create scope.md

Create `{plans_dir}/scope-{slug}/scope.md` using this exact format:

```markdown
# {Task title}
**Project:** {detected project}  **Branch:** {branch}  **Date:** {today's date}
**Scope folder:** {plans_dir}/scope-{slug}/
**Source repo(s):** {list of repos this task touches, with absolute paths}

## Context
{1–3 sentences: what this is, why it's being done, what triggered it}

## Phases
{Only if phased — omit entirely for single-phase tasks}

### Phase 1 — {name}
{Description of deliverables and what "done" looks like for this phase}

### Phase 2 — {name}
...

## Architecture
{Include if the task involves non-trivial system design. Use plain ASCII art diagrams
in fenced code blocks (never Mermaid). Omit for simple bug fixes or single-file changes.}

## What Already Exists
{List relevant existing code, infrastructure, and patterns that this task builds on.
Include file paths (relative to workspace root). This section helps future Claude
sessions understand what NOT to rebuild.}

## NOT in Scope
{Explicit exclusions — things that are related but deliberately deferred or out of
bounds. Prevents scope creep in execution.}

## Skill Sequence

### Plan Reviews

| # | Skill | Apply? | When | Notes |
|---|-------|--------|------|-------|
| 1 | /plan-ceo-review | [ ] **ALWAYS** | 1st | Reframe scope, challenge premises |
| 2 | /plan-eng-review | [ ] YES | 2nd | {reason or N/A: reason} |
| 3 | /plan-design-review | [N/A] | — | {why not applicable} |
| 4 | /plan-devex-review | [N/A] | — | {why not applicable} |

### Implementation Support

| # | Skill | Apply? | When | Notes |
|---|-------|--------|------|-------|
| 5 | /investigate | [N/A] | — | {why not applicable} |
| 6 | /design-consultation | [N/A] | — | {why not applicable} |
| 7 | /design-html | [N/A] | — | {why not applicable} |
| 8 | /design-shotgun | [N/A] | — | {why not applicable} |

### Review & QA

| # | Skill | Apply? | When | Notes |
|---|-------|--------|------|-------|
| 9 | /review | [ ] YES | After impl | {tailored note} |
| 10 | /health | [ ] YES | After impl | {tailored note} |
| 11 | /qa | [N/A] | — | {why not applicable} |
| 12 | /qa-only | [ ] YES | After impl | {test command} |
| 13 | /browse | [N/A] | — | {why not applicable} |
| 14 | /devex-review | [N/A] | — | {why not applicable} |
| 15 | /setup-browser-cookies | [N/A] | — | {why not applicable} |

### Ship & Post-ship

| # | Skill | Apply? | When | Notes |
|---|-------|--------|------|-------|
| 16 | /ship | [ ] YES | Final | {tailored note} |
| 17 | /document-release | [ ] YES | Post-ship | {tailored note} |
| 18 | /retro | [ ] OPTIONAL | Sprint end | {tailored note} |

## Key Decisions Captured
{Bullet list of Round 1 + Round 2 answers that shaped this scope}
- ...
```

### 5.5 Create progress.md

Create `{plans_dir}/scope-{slug}/progress.md` using this exact format:

```markdown
# Progress: {Task title}

## Resume Context
<!-- Updated after every significant action. Paste the first 20 lines of this file
     into a new conversation to get oriented. -->
**Scope:** {plans_dir}/scope-{slug}/scope.md
**Last action:** Scope created ({today's date})
**Next action:** {first YES skill from checklist}
**Open blockers:** {any human steps or external dependencies, or "None"}
**Key files changed:** None yet

---

## Decisions Log
<!-- Running list of non-obvious decisions made during execution and WHY.
     These are the highest-value lines for future sessions. -->

- ({today's date}) {Any key decisions from scoping rounds that shaped the approach}

---

## Progress Log

| Date | Skill/Action | Status | Notes |
|------|--------------|--------|-------|
| {date} | /scope | Done | Scope created — {one-line summary} |

---

## Human Steps

| Step | Status | Notes |
|------|--------|-------|
{If any human steps were identified during scoping, list them here. Otherwise:}
| (none identified yet) | — | — |

---

## Plans
<!-- For phased scopes: child plan files and their execution status.
     Omit this section for atomic scopes. -->

| # | Plan File | Phase | Status | Notes |
|---|-----------|-------|--------|-------|
{For each plan stub created, one row with its sub-number. Example:}
{| 39.1 | 39.1-cashier-settlement-PLAN.md | Phase 1 — Schema | Draft | |}
{| 39.2 | 39.2-cashier-settlement-PLAN.md | Phase 2 — Logic | Draft | |}
{Otherwise omit section entirely.}

---

## Artifacts
<!-- Files created during execution that live outside the source repo
     (dashboards, configs, email templates, etc.) -->

(none yet)
```

### 5.6 Create artifacts/ subdirectory

```bash
mkdir -p {plans_dir}/scope-{slug}/artifacts
```

This directory holds any non-code artifacts produced during execution (dashboard JSON,
email templates, architecture diagrams, exported configs, etc.). Reference them from
progress.md when created.

### 5.7 Sweep related files into scope folder

Check `{plans_dir}/` for files related to this scope's slug — PRDs, concepting docs,
or any other working files created before the scope folder:

```bash
ls {plans_dir}/*{slug}* 2>/dev/null | grep -v "scope-{slug}"
```

Move matching files into the scope folder so all task-related documents travel together:
```bash
mv {plans_dir}/prd-{slug}*.md {plans_dir}/scope-{slug}/ 2>/dev/null
mv {plans_dir}/*{slug}*.md {plans_dir}/scope-{slug}/ 2>/dev/null
```

Exclude `PLANS-INDEX.md`, `TO-DO.md`, and any files already inside subdirectories.
After this step, only the scope folder remains in `plans/` for this task — no orphaned
working files at the top level.

### 5.8 Update PLANS-INDEX.md

**Auto-assign the next sequential plan number.** Read `{plans_dir}/PLANS-INDEX.md`,
find the highest `#` value in both Archived and Active tables (ignore sub-numbers like
`39.1` — only whole numbers count), and increment by 1. This becomes `{N}` for the
scope and all its child plans.

If creating the file for the first time, add the header and start numbering at 1:

```markdown
# Plans Index

All scopes, PRDs, and plans across the project. Types: `prd` (business requirements),
`scope` (multi-skill orchestration), `plan` (single-session executable task).

| # | Date | Type | Folder/File | Project | Status | Description |
|---|------|------|-------------|---------|--------|-------------|
```

Append the scope entry with its assigned number:

```markdown
| {N} | {date} | scope | scope-{slug}/ | {project} | Active | {one-line description} |
```

### 5.9 Generate plan stubs (phased scopes only)

If the scope is **phased** (Step 3), generate a plan stub file for each phase.
Each plan ≈ 1 context window ≈ 1 session of work.

Plan stubs use **sub-numbers** of the scope's assigned `{N}` from Step 5.7:
- Phase 1 → `{N}.1`
- Phase 2 → `{N}.2`
- etc.

Plan stub filename: `{plans_dir}/scope-{slug}/{N}.{P}-{slug}-PLAN.md`
where `{P}` is the phase number (1, 2, 3, ...).

Example: scope #39, slug `cashier-settlement`, 3 phases →
- `scope-cashier-settlement/39.1-cashier-settlement-PLAN.md`
- `scope-cashier-settlement/39.2-cashier-settlement-PLAN.md`
- `scope-cashier-settlement/39.3-cashier-settlement-PLAN.md`

Use the `/plan` (task-runner) format:

```markdown
# Plan {N}.{P}: {Phase name}

**Version:** 0.1 (stub — detail filled at session start)
**Date:** {today's date}
**Author:** Alex
**Status:** Draft
**Plan #:** {N}.{P}
**Parent scope:** {plans_dir}/scope-{slug}/scope.md
**Branch:** {branch or TBD}

## Related Docs
- `{plans_dir}/scope-{slug}/scope.md` — parent scope
- `{plans_dir}/scope-{slug}/progress.md` — progress tracker

---

## Phase {P}: {Phase Name}

### Task {P}.1: {Task Title}
- **Type**: AI | HUMAN | AI+HUMAN_REVIEW
- **Input**: {what files/context this task needs}
- **Action**: {what to do — outline level, detail filled at session start}
- **Output**: {what files/artifacts this task produces}
- **Acceptance**: {how to verify success}

### Task {P}.2: {Task Title}
...

---
### 🔲 CHECKPOINT: Phase {P} Complete
**Review**: {what the human should verify}
**Resume**: "continue the {N}.{P} {slug} plan"
---
```

**Sizing rule:** If a phase looks like it exceeds ~200k tokens of work (many files,
complex logic, multiple integrations), split it into two plans. Better to have more
small plans than one that won't fit in a context window.

Also add a PLANS-INDEX entry for each plan stub (sub-numbered under the scope):
```markdown
| {N}.{P} | {date} | plan | scope-{slug}/{N}.{P}-{slug}-PLAN.md | {project} | Draft | Phase {P} — {phase description} |
```

---

## Step 6 — Handoff Summary

After writing the files, output to the user:

1. The path to `scope.md` (so they can open it)
2. The path to `progress.md` (so they know where tracking lives)
3. The recommended first skill to run (first YES in the checklist)
4. One-line summary of any N/A decisions that might surprise them
5. Whether this is single-phase or phased, and what Phase 1 ends with

Do NOT re-print the entire scope.md. Just the handoff summary above.

### 6.1 gstack review skill targeting

When the recommended next step is a gstack review skill (`/plan-ceo-review`,
`/plan-eng-review`, `/plan-design-review`, `/plan-devex-review`, or `/autoplan`),
always point it at the **scope folder** (`scope.md`), not at individual plan stubs.
This lets gstack review, improve, and reorder across ALL phases holistically —
restructuring phase boundaries, moving tasks between plans, and optimizing the
overall sequence.

Example handoff:
- "Run `/autoplan` on `scope-{slug}/scope.md`"
- NOT "Start with `/plan-ceo-review` on `39.1-{slug}-PLAN.md`"

After gstack completes, copy any artifacts it creates in `~/.gstack/projects/$SLUG/`
to `{scope-folder}/artifacts/` so the scope folder stays self-contained.

---

## Step 7 — Archive (end of task)

When the user indicates the task is complete (all YES skills done, or user says
"archive this"), or when you detect all skill checklist items are done:

7.1 Move the scope folder to `{plans_dir}/archive/scope-{slug}/`.

7.2 Update `PLANS-INDEX.md`: change the status from `Active` to `Done ({date})`
for the scope row and all its child plan rows.

7.3 Confirm to the user what was archived and where.

---

## Ongoing: Progress Tracking Rules

These rules apply **throughout execution**, not just during the /scope skill itself.
They govern how progress.md is maintained as work proceeds.

### Rule 1: Update progress.md after every significant action

After any of the following, append to the Progress Log table and update the
Resume Context block:

- A skill from the checklist completes (log: date, skill name, status, key findings)
- A phase is completed (log: phase name, commit hash, test count if applicable)
- A key decision is made during execution (also add to Decisions Log section)
- A blocker is discovered or resolved (also update Human Steps table)
- An artifact is created (also add to Artifacts section)

**Update the Resume Context block every time you update the Progress Log.** The
Resume Context must always reflect the current state — it's the "paste this to
get oriented" block.

### Rule 2: Decisions go in two places

Non-obvious decisions made during execution go in:
1. The **Decisions Log** section (with date and rationale)
2. The **Progress Log** table (brief note in the Notes column)

Decisions that change the scope itself (reframes, additions, cuts) should also be
reflected in scope.md — update the relevant Phase description or add to
"Key Decisions Captured."

### Rule 3: File references use workspace-relative paths

All file paths in progress.md use paths relative to the workspace root
(e.g., `padma-integrations/lib/xendit.js`). Never bare filenames.

### Rule 4: Human steps are tracked

When a human step is discovered during execution (SSM parameter to create, webhook
URL to change, etc.), add it to the Human Steps table in progress.md with status
`[ ] Pending`. Update to `[x] Done` when completed.

### Rule 5: On context resume, read scope + progress first

When a user asks to resume work on a scope (or you detect an active scope folder
relevant to the current task):

1. Read `progress.md` — the Resume Context block tells you where things stand
2. Read `scope.md` — the plan and skill checklist tell you what's next
3. Summarize current state to the user before proceeding
4. Continue from where the Resume Context says to pick up

---

## Behavior Rules

- **Context-first, no interview style.** Read everything before asking anything.
- **Both rounds are single batches.** Never ask one question at a time.
- **N/A is per-task, not per-project.** WellMed and PMG both have UIs.
- **No gstack branding in output files.** scope.md and progress.md look like your own docs.
- **Slug is deterministic.** Based on task title, not date. Dates go inside the file.
- **Plans dir must exist.** If the resolved plans directory doesn't exist, stop and tell the user. Don't create it (it implies the docs repo is missing or not cloned).
- **Central, not local.** Scope folders always go in the plans directory, never in the source repo's `docs/` folder.
- **Progress is append-only.** Never delete or overwrite previous Progress Log entries. The Resume Context block is the only section that gets overwritten (it always reflects current state).
