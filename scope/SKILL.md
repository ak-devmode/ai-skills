---
name: scope
version: 3.1.0
description: |
  Task scoping, skill router, and progress tracker. Reads current context (git diff,
  branch, CLAUDE.md, open files), eliminates assumptions via two rounds of open-ended
  numbered inline questions, then outputs a phased scope with a full 18-skill checklist
  marking N/A skills with reasons. For multi-session work, generates plan stub files
  (one per phase, each ~1 context window) that /plan (task-runner) can execute. Creates
  a tracking folder (scope.md + progress.md) in the project's central plans directory.
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
# Detect project from PWD, then read ONLY the matching plans directory
case "$(pwd)" in
  *Projects/pmg*)        PLANS_DIR="$HOME/Projects/pmg/pmg-docs/plans" ;;
  *Projects/wellmed*)    PLANS_DIR="$HOME/Projects/wellmed/kalpa-docs/plans" ;;
  *Projects/ai-skills*)  PLANS_DIR="$HOME/Projects/ai-skills/plans" ;;
  *)                     PLANS_DIR="" ;;
esac
if [ -n "$PLANS_DIR" ]; then
  echo "PLANS_DIR=$PLANS_DIR"
  ls -la "$PLANS_DIR"/scope-* 2>/dev/null || echo "no active scopes"
  echo "---INDEX---"
  cat "$PLANS_DIR/PLANS-INDEX.md" 2>/dev/null || echo "no PLANS-INDEX.md yet"
else
  echo "Unrecognized project — ask the user where the plans directory should live"
fi
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

Ask 5–15 open-ended questions in a **single response** as a numbered list. The user answers by number. **Never use multiple-choice or pre-framed answer options** — open-ended only. The user prefers many specific questions over a few broad ones.

**Rules for Round 1:**
- Do NOT ask about things already determinable from git diff, branch name, or CLAUDE.md
- Each question is one line, no preamble, numbered (1, 2, 3...)
- Cover where ambiguity exists: scope boundary, timeline, prod vs exploratory, UI involvement, compliance, coordination with other services/people, testing strategy, cross-repo touchpoints
- For WellMed context: include SATU SEHAT compliance angle if the change touches patient data, API endpoints, or health records
- For PMG context: include worker health data handling, regulatory angle where relevant
- Skip anything already clear from context — every question must move the design

**Example open-ended questions (generate dynamically based on what's ambiguous):**

1. Is this greenfield or modifying existing code, and which files specifically?
2. How much time is available — single session today, or multi-session across days?
3. Is this going to production this sprint, or exploratory/staging only?
4. Is there a UI component, or is this purely backend/infra?
5. Should testing be in-scope here, or tracked separately?
6. Which other services or teammates need coordination?
7. What's the SATU SEHAT / regulatory angle, if any? (WellMed)
8. What user-facing outcome should we verify, or is this internal only?
9. Which existing patterns should this follow — point me to the closest reference if you know one
10. What's deliberately out of scope so I don't expand into it?

End with: "Answer by number. Skip any that don't apply."

---

## Step 2 — Round 2: Design Refinement

After processing Round 1 answers, ask the task-specific design questions that determine the best solution architecture. Same format: numbered, open-ended, no multiple choice, single response. Target 3–10 questions depending on complexity.

Generate questions based on task type:

**For new API/service work:**
1. Synchronous call chain or async/saga pattern, and what drives the choice?
2. Which service owns the new data, and where does it live in the DB schema?
3. New migration needed, or extending existing tables?
4. What's the contract surface (endpoints, events, schema fields) and which other services consume it?

**For UI features:**
1. Mobile-first or desktop-primary?
2. Which existing component patterns should this reuse? Point to closest example.
3. What's the empty / error / loading state behavior?
4. What does the happy path look like end-to-end?

**For bug fixes:**
1. Is there a regression test missing, or is this a genuine edge case not worth testing?
2. Is it reproducible locally — do you have a test case that triggers it?
3. Has this affected production, or was it caught pre-merge?
4. What's the suspected root cause area?

**For infra/devops:**
1. Terraform-managed or manual?
2. Blue/green deployment or in-place?
3. Rollback plan needed in scope?
4. What downstream systems break if this fails?

If Round 1 already resolved the design questions (small task), skip Round 2 and proceed directly to output. Otherwise fire as a single numbered response.

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
| ai-skills (`~/Projects/ai-skills/`) | `~/Projects/ai-skills/plans/` |
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

See `/markdown-style` §11 (Scope Documents) for full conventions. The required structure:

```markdown
# {Task title}
**Project:** {detected project}  **Branch:** {branch}  **Date:** {today's date}
**Scope folder:** {plans_dir}/scope-{slug}/
**Source repo(s):** {absolute paths to repos this task touches}

## Context
{1–3 sentences: what this is, why it's being done, what triggered it}

## Phases
{Phased scopes only — per phase: ### Phase N — {name} + description of deliverables}

## Architecture
{Optional — ASCII diagrams only, omit for simple bug fixes}

## What Already Exists
{Existing code/infra/patterns this builds on. Workspace-relative paths.}

## NOT in Scope
{Explicit exclusions to prevent scope creep}

## Skill Sequence
{Four tables grouped by phase — Plan Reviews, Implementation Support, Review & QA,
 Ship & Post-ship. Fill in the 18-skill checklist from Step 4.}

## Key Decisions Captured
{Bullets from Round 1 + Round 2 answers that shaped this scope}
```

The full skill checklist tables (18 rows across four sections) follow the same shape shown in Step 4. Each row gets `[ ] YES` / `[ ] OPTIONAL` / `[N/A]` with a tailored note. Mandatory: `/plan-ceo-review` is always YES.

### 5.5 Create progress.md

See `/markdown-style` §10 (Progress Files) for full conventions: Resume Context block schema, append-only rule, Decisions Log dual-entry. The required structure:

```markdown
# Progress: {Task title}

## Resume Context
**Scope:** {plans_dir}/scope-{slug}/scope.md
**Last action:** Scope created ({today's date})
**Next action:** {first YES skill from checklist}
**Open blockers:** {human steps or external deps, or "None"}
**Key files changed:** None yet

---

## Decisions Log
- ({today's date}) {Key decisions from scoping rounds that shaped the approach}

---

## Progress Log

| Date | Skill/Action | Status | Notes |
|------|--------------|--------|-------|
| {date} | /scope | Done | Scope created — {one-line summary} |

---

## Human Steps

| Step | Status | Notes |
|------|--------|-------|
| (none identified yet) | — | — |

---

## Plans
{Omit this section for atomic scopes. For phased scopes:}

| # | Plan File | Phase | Status | Notes |
|---|-----------|-------|--------|-------|
| {N}.1 | {N}.1-{slug}-PLAN.md | Phase 1 — {name} | Draft | |
| {N}.2 | {N}.2-{slug}-PLAN.md | Phase 2 — {name} | Draft | |

---

## Artifacts
(none yet)
```

The Resume Context block is the only section overwritten on update; everything else is append-only.

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

See `/markdown-style` §8 (Plan Documents) and §8.9 (Plan Stubs) for full conventions. The required stub shape:

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
- **Input**: {workspace-relative paths}
- **Action**: {outline — detail filled at session start}
- **Output**: {files/artifacts produced}
- **Acceptance**: {how to verify}

---
### 🔲 CHECKPOINT: Phase {P} Complete
**Review**: {what the human should verify}
**Resume**: "continue the {N}.{P} {slug} plan"
---
```

**Sizing rule:** If a phase looks like it exceeds ~200k tokens of work (many files, complex logic, multiple integrations), split it into two plans. More small plans beat one that won't fit in a context window.

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

## Step 8 — Post-flight Cleanup (runs after archive)

After archiving (Step 7), run the full post-flight checklist. These steps are NOT
optional — they are part of scope completion. Do not declare the scope done until
all post-flight items are addressed.

### 8.1 Close background shells

Check for any background shells or processes started during scope execution.
Wrap them up or inform the user if they cannot be closed programmatically.

### 8.2 Run /closeout-extended (self-heal)

Invoke `/closeout-extended` to run the full self-healing pass: doc drift detection
and edits (CLAUDE.md, READMEs, ARCHITECTURE.md), pattern audit, cross-repo audit
walking `CROSS-REPO.md`, test execution, and memory writes for cross-cutting findings.

This replaces the previous ad-hoc post-flight doc updates and learnings capture —
`/closeout-extended` does it more thoroughly with explicit pattern + drift checks.

Fallback chain if extended skills are not installed:
- `/closeout` (local-only self-heal) if available
- Otherwise, do manual doc-update review + memory writes inline:
  - Update CLAUDE.md if test counts, file descriptions, architecture, or scripts changed
  - Update READMEs for affected packages
  - Save non-obvious learnings to memory (gotchas, workflow feedback, system references)
- Note the gap so /closeout can be installed for next scope

### 8.3 Confirm branch, commit, push

Verify all changes are committed and pushed:
- Run `git status` to check for uncommitted changes
- Commit any remaining changes (scope archive, doc updates from /closeout-extended)
- Push to remote

### 8.4 Context clearing & next scope

This is the final step. After all cleanup is done:

8.4.1 Check `PLANS-INDEX.md` for other active scopes in the same project.

8.4.2 If a logical next scope exists (e.g., a downstream scope that was waiting
on this one, or the next numbered scope in a series), offer to continue:

```
Scope #{N} complete and archived. Next active scope:
  → #{next} {scope-name} — {description from index}

Ready to start? I'll clear context and begin:
  /plan {next-scope-first-plan-number}

(Y to clear context and continue / N to stop here)
```

8.4.3 If the user says yes, tell them to run `/clear` then provide the exact
prompt to paste:

```
Run /plan {next-plan-number}
```

8.4.4 If there are no active follow-on scopes, simply report completion:

```
✅ Scope #{N} fully complete. No active follow-on scopes found.
```

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
