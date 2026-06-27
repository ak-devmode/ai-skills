---
name: scope
version: 3.3.0
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

## Phase Boundaries — the one rule the rest of this skill points at

A phase is a unit of deliverable work bounded by a **gate**: a reason the work
*must* pause or split that comes from the work itself, not from context-window size.
There are exactly six gate types:

- **A. Human gate** — work can't proceed until a human acts: edits/approves content,
  performs an external action (paste a snippet, create an SSM param, flip DNS), or
  makes a go/no-go call after seeing the prior output.
- **B. Concurrency boundary** — independent workstreams over disjoint file sets that
  could each be built/tested/committed/PR'd without colliding. Splitting here enables
  parallel execution or clean independent PRs.
- **C. Review/merge gate** — a chunk that should land as one reviewable PR before the
  next builds on it (PR-sized, not context-sized).
- **D. Deploy/verify gate** — must be deployed and observed in an environment before
  the next step is safe (ship the contract → verify consumers → migrate).
- **E. Risk/irreversibility gate** — a destructive or one-way step (data migration,
  big-bang cutover) earns its own phase + rollback note, regardless of size.
- **F. Compliance gate** — a regulatory checkpoint (e.g. SATU SEHAT) that blocks
  later work.

**Token/context size is NOT a gate.** Automatic context compaction means a single
phase may span multiple sessions; a large phase gets intra-phase resume checkpoints
inside its one plan file (see §5.9), it does not get split into more phases. Conversely,
several gate-free chunks of work belong in ONE phase even if that phase is large —
do not mint a new phase just because you estimate the work won't fit one window.

If a boundary isn't one of A–F, it is not a phase boundary — it's just a long phase.
Every CHECKPOINT this skill emits records its gate type so /plan knows whether to
pause-and-clear (A/D/E — you're stopping anyway) or roll straight through (B/C).

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
  # Active scope folders are numbered `<N>-<slug>/` (wellmed/PMG convention).
  ls -d "$PLANS_DIR"/[0-9]*-*/ 2>/dev/null || echo "no active scopes"
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

## Step 0.5 — Cross-Repo Graph Discovery (gated on CROSS-REPO.md)

If `CROSS-REPO.md` exists in the current repo, this work is multi-repo by default.
Most plumbing inconsistencies in microservice work come from agents reading one repo
in isolation and silently assuming branch/version/contract parity with the rest of
the graph. Make the graph state explicit and mechanical here so plan can't drift.

If `CROSS-REPO.md` does NOT exist:
- Note this in the synthesis ("repo is graph-orphaned — no Pattern Sources or
  Consumers declared")
- If the work clearly spans repos (e.g., the user mentions another repo, or git
  diff touches a shared contract), suggest running `/cross-repo-init` first
- Otherwise proceed to Step 1 as a single-repo task

If `CROSS-REPO.md` exists, run the blocks below.

### 0.5.1 Parse Pattern Sources and Consumers

```bash
# Print the Pattern Sources + Consumers tables for parsing
cat CROSS-REPO.md
```

Extract every repo path from the Pattern Sources, Consumers (Direct gRPC + Edge +
Documentation), and any other graph tables. Build the working set: `{current repo}
∪ Pattern Sources ∪ Consumers`. External Dependents (AWS, Redis, third-party APIs)
are not walked here — only sibling repos in `~/Projects/`.

### 0.5.2 Snapshot each repo's state

For each repo in the working set, capture:

```bash
# For each repo path from CROSS-REPO.md:
REPO=~/Projects/wellmed/wellmed-consultation  # example
echo "=== $REPO ==="
git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo "MISSING_REPO"
git -C "$REPO" branch --show-current 2>/dev/null
git -C "$REPO" log -1 --format='%ai %s' 2>/dev/null
# SDK pin (Go repos)
grep -E 'wellmed-infrastructure|go-sdk' "$REPO/go.mod" 2>/dev/null | head -2
# Uncommitted work signal
git -C "$REPO" status --short 2>/dev/null | head -3
```

Record per repo:
- **Path** (absolute, under `~/Projects/`)
- **Trunk branch declared** (from CROSS-REPO.md if listed, else infer)
- **Current branch** (`git branch --show-current`)
- **Current HEAD SHA** (short, 7 chars)
- **Pinned SDK version** if applicable (from `go.mod` / `package.json`)
- **Dirty?** (yes if `git status --short` non-empty)
- **Last commit date** (so plan can judge staleness)

Flag any of these as **drift to surface to the user before Round 1**:
- Current branch ≠ declared trunk branch on a repo we'll touch
- Pinned SDK version differs across consumer repos (asymmetry)
- A repo in the graph is missing from `~/Projects/` (not cloned)
- A repo has uncommitted changes (someone else is mid-task there)

These don't block — they just need to be acknowledged. Drift discovered here often
reframes the task ("oh, consultation is still on the old SDK, that changes phase 1").

### 0.5.3 Hold the snapshot for scope.md

Keep the table in working memory. It will be written verbatim into scope.md's
`## Repo Graph` section in Step 5.4. /plan reads this section to validate freshness
before executing (see /plan's scope freshness validation pass).

---

## Step 0.6 — Contract Cascade Detection

Microservice plumbing inconsistencies usually originate from contract-surface changes
(proto files, Prisma schemas, OpenAPI specs, GraphQL schemas) being made in one repo
without the consumer updates being explicitly in-scope. Detect this mechanically.

### 0.6.1 Scan the diff for contract-surface files

```bash
# Combined diff (staged + unstaged + recent commits on this branch)
git diff --name-only HEAD~5..HEAD 2>/dev/null
git diff --name-only HEAD 2>/dev/null
git diff --staged --name-only 2>/dev/null
```

Treat these as contract surfaces:
- `*.proto` — gRPC contracts
- `prisma/schema.prisma`, `**/schema.prisma` — Prisma data model (DB contract)
- `openapi.yaml`, `openapi.yml`, `openapi.json`, `**/openapi.*` — REST contracts
- `*.graphql`, `*.graphqls`, `schema.graphql` — GraphQL contracts
- Files under `proto/`, `contracts/`, `schemas/` directories

### 0.6.2 If contract files changed, auto-cascade

If ANY contract-surface file is in the diff AND `CROSS-REPO.md` exists:

1. **Every Consumer from CROSS-REPO.md is in-scope by default.** Add each to the
   Repo Graph table with a "Consumer update required" note.
2. **Add a per-Consumer task to the scope.** For each Consumer repo:
   - "Regenerate proto stubs / Prisma client / OpenAPI types from updated contract"
   - "Update call sites that use the changed surface"
   - "Run consumer's test suite against updated contract"
3. **Surface this to the user in Round 1** as a confirmation, not a question — they
   may legitimately want to defer a consumer to a later scope, but the default is
   that contract changes cascade.

Example Round 1 framing:
> "Contract changes detected in `proto/canonical_visit.proto`. Default scope
> includes Consumer updates in wellmed-consultation, wellmed-cashier, and
> wellmed-gateway-go. Confirm cascade, or call out which Consumers defer."

### 0.6.3 If no contract files changed

Note in synthesis: "No contract-surface changes detected — Consumer repos read-only
for this scope." Skip the cascade.

---

## Step 0.7 — ADR-First Check

Architectural decisions live in central docs, not in-repo. When agents work in a
single repo, they re-derive answers to questions that have already been decided
across the project — often worse than the ADR says. Surface relevant ADRs before
asking the user any Round 1 questions, so the user can correct premises rather than
answering questions whose answers are already on disk.

### 0.7.1 Resolve the ADR directory

```bash
# Resolve based on project (matches Step 0 PLANS_DIR logic)
case "$(pwd)" in
  *Projects/pmg*)     ADR_DIR="$HOME/Projects/pmg/pmg-docs/adrs" ;;
  *Projects/wellmed*) ADR_DIR="$HOME/Projects/wellmed/kalpa-docs/adrs" ;;
  *Projects/ai-skills*) ADR_DIR="" ;;  # no ADRs for ai-skills itself
  *)                  ADR_DIR="" ;;
esac
[ -n "$ADR_DIR" ] && ls "$ADR_DIR" 2>/dev/null | head -30
```

If `ADR_DIR` is empty or missing, skip this step.

### 0.7.2 Grep ADRs for task keywords

Extract 3–6 keywords from the task title, branch name, and diff (e.g., for branch
`feature/visit-saga-rollback`: keywords = `visit, saga, rollback, orchestrat`).
Grep each ADR file for matches:

```bash
# Example — adjust keywords to the task
grep -li -E '(visit|saga|rollback|orchestrat)' "$ADR_DIR"/*.md 2>/dev/null
```

For each matching ADR, read the title + status + relevant section.

### 0.7.3 Surface ADRs before Round 1

Present matched ADRs to the user as a confirmation block, not a question:

> **ADR alignment check** — work appears to touch these decisions:
> - **ADR-005** (saga orchestration ownership) — `Status: Accepted v1.1`
> - **ADR-006** (no mid-saga module gRPC calls) — `Status: Accepted`
>
> Default assumption: this work **conforms** to both. If it **extends** or
> **contradicts** any of them, say so now — that changes scope and may require
> an ADR amendment in this scope.

Record the user's response (conform / extend / contradict + which ADRs) for the
`## ADR Alignment` section of scope.md.

If no ADRs match: note "No ADR matches for keywords — proceeding without ADR
alignment block" in synthesis.

---

## Step 1 — Round 1: Assumption Removal

Ask 5–15 open-ended questions in a **single response** as a numbered list. The user answers by number. **Never use multiple-choice or pre-framed answer options** — open-ended only. The user prefers many specific questions over a few broad ones.

**Rules for Round 1:**
- Do NOT ask about things already determinable from git diff, branch name, or CLAUDE.md
- Each question is one line, no preamble, numbered (1, 2, 3...)
- Cover where ambiguity exists: scope boundary, timeline, prod vs exploratory, UI involvement, compliance, coordination with other services/people, testing strategy, cross-repo touchpoints
- For WellMed context: include SATU SEHAT compliance angle if the change touches patient data, API endpoints, or health records
- For PMG context: include worker health data handling, regulatory angle where relevant
- **If CROSS-REPO.md exists** (Step 0.5 ran): ALWAYS include a cross-repo coordination question that lists the Consumer repos by name and asks which are in-scope vs deferred. Don't ask abstractly ("any other repos?") — name them.
- **If Step 0.6 detected contract changes:** lead with the cascade-confirmation framing, not a question — the default is that all Consumers update.
- **If Step 0.7 surfaced ADRs:** confirm conform/extend/contradict before any other questions — premises first, design second.
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

Generate questions based on task type — these are seeds, not a script; expand to 3–10
that actually move the design:

- **New API/service:** sync vs async/saga (and why); which service owns the data + DB schema home; new migration vs extend; contract surface + consumers.
- **UI feature:** mobile-first vs desktop; which existing component patterns to reuse (point to closest); empty/error/loading behavior; the end-to-end happy path.
- **Bug fix:** missing regression test vs genuine edge case; reproducible locally; hit production or caught pre-merge; suspected root-cause area.
- **Infra/devops:** Terraform-managed vs manual; blue/green vs in-place; rollback in scope; what downstream breaks on failure.

If Round 1 already resolved the design questions (small task), skip Round 2 and proceed directly to output. Otherwise fire as a single numbered response.

---

## Step 3 — Determine Scale: Atomic vs Phased

Based on all answers, decide the execution model. **Phasing is decided by gates
(A–F from "Phase Boundaries" above), never by estimated token size.**

**Atomic** (single plan, no phase splits) if the work crosses **zero** gates:
- No human hand-off mid-stream, no deploy-then-verify dependency, no irreversible
  step that wants its own rollback, no compliance checkpoint
- The deliverables are coupled enough that one PR / one review makes sense
- This holds even if the work is large — a big gate-free task is one atomic plan
  that may span several sessions via compaction + intra-phase checkpoints, not
  several phases

**Phased** (one plan file per phase) if the work crosses **one or more gates**:
- Count the gates A–F the work crosses; each gate is a phase boundary
- Tightly-coupled, gate-free chunks between two gates collapse into a single phase
- Tag each resulting boundary with its gate type — it flows into the CHECKPOINT
  (§5.9) so /plan knows whether to pause-and-clear (A/D/E) or roll through (B/C)

When phased, each phase becomes one plan file. Scope generates plan stubs that
`/plan` (task-runner) can execute. See Step 5.9.

**Sanity check before finalizing the phase count:** for each proposed boundary, name
the gate (A–F). If you can't, the two phases are really one — merge them. This is the
guard against over-phasing a single coherent build into size-driven fragments.

If genuinely ambiguous after Round 1+2 (you can't tell whether a human hand-off
exists): ask the one question that resolves it, e.g. "Does anything here wait on you
or another person mid-stream, or is it one straight build?" — not "how much time do
you have," which conflates size with gates.

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

### 5.2 Slug and scope number

Determine the slug: lowercase, hyphenated, 3–5 words from the task title.
Example: "wellmed-saga-handler-phase2", "pmg-report-export", "auth-refresh-bug"

**Auto-assign the next sequential scope number `{N}`.** Read
`{plans_dir}/PLANS-INDEX.md`, find the highest `#` value across both Archived
and Active tables (ignore sub-numbers like `39.1` — only whole numbers count),
and increment by 1. This `{N}` prefixes the scope folder and every child plan,
matching the wellmed/PMG convention.

If `PLANS-INDEX.md` doesn't yet exist, the header is created in Step 5.8 and
`{N}` starts at 1.

The scope folder path is: `{plans_dir}/{N}-{slug}/` (e.g.
`~/Projects/pmg/pmg-docs/plans/32-pmg-testsuite/`). Archive folder name uses
the same convention: `{plans_dir}/archive/{N}-{slug}/`.

### 5.2.1 Program-member scopes (ADR-029)

If the work being scoped is a **member of an existing Program** (a
`plans/{program-slug}/` folder with a `{slug}-brief.md` member list — e.g.
`catalog-program/catalog-brief.md`, `control-tower-program/control-tower-brief.md`),
it still gets a normal **flat,
top-level** `{plans_dir}/{N}-{slug}/` folder and a normal PLANS-INDEX row
(Step 5.8). **Member scopes never live inside the program folder** — the
`C{n}`/`M{n}` folders there are placeholders (`NOT-YET-SCOPED.md`), not scopes.

The program control surface is named **`{slug}-brief.md`** — the program folder's
slug with any `-program` suffix dropped (ADR-029 v1.2; e.g. `control-tower-program/`
→ `control-tower-brief.md`). A new program scaffold creates that slugged file, never
a bare `brief.md`.

Detect a program member when: the user names a program or one of its `C{n}`/`M{n}`
members, or the task maps to a member row in some `plans/*/*-brief.md`.

After the scope files exist, complete the graduation (ADR-029 §2.3.2):
- Update the program `{slug}-brief.md` member row to point at `{N}-{slug}` and mark it
  scoped (was "not yet scoped").
- Retire the placeholder: rewrite its `C{n}-{slug}/NOT-YET-SCOPED.md` to a one-line
  pointer at `{N}-{slug}` (or remove the placeholder folder — `{slug}-brief.md` now carries
  the member→scope mapping).

This keeps every scope flat-numbered and visible to a `plans/*` scan and to
PLANS-INDEX, while the program `{slug}-brief.md` stays the members registry.

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
**Scope folder:** {plans_dir}/{N}-{slug}/
**Source repo(s):** {absolute paths to repos this task touches}

## Context
{1–3 sentences: what this is, why it's being done, what triggered it}

## Repo Graph
{Required if CROSS-REPO.md exists in the primary repo (Step 0.5 ran). Omit
 otherwise with a one-line note "Single-repo task — no CROSS-REPO.md present."

 The SHA snapshot below is the freshness contract /plan validates against
 before executing. Do NOT edit these SHAs by hand once recorded — if state
 changes, /plan will surface the drift.}

| Repo | Role | Trunk | Current Branch | HEAD SHA | SDK Pin | In Scope? | Notes |
|---|---|---|---|---|---|---|---|
| wellmed-backbone | primary | develop | feature/foo | abc1234 | n/a (trunk) | YES | the change |
| wellmed-consultation | consumer | develop | develop | def5678 | go-sdk v1.4.2 | YES | proto regen + call site |
| wellmed-cashier | consumer | develop | develop | 9876fed | go-sdk v1.4.0 | DEFERRED | scope #N+1 |
| wellmed-infrastructure | pattern source | develop | develop | aaa1111 | — | READ-ONLY | reference patterns |

**Drift flagged in Step 0.5:** {list each drift or "none"}
**Snapshot taken:** {today's date} {time if multi-session work expected}

## ADR Alignment
{Required if Step 0.7 surfaced ADR matches. Omit otherwise with one-line note
 "No ADR matches for task keywords."}

| ADR | Title | Status | This work … |
|---|---|---|---|
| ADR-005 | Saga orchestration ownership | Accepted v1.1 | Conforms |
| ADR-006 | No mid-saga module gRPC calls | Accepted | Conforms |

If any row says "Extends" or "Contradicts", note the rationale and whether an
ADR amendment is in-scope for this work.

## Phases
{Phased scopes only — per phase: ### Phase N — {name} + description of deliverables}

## Architecture
{Optional — ASCII diagrams only, omit for simple bug fixes}

## What Already Exists
{Existing code/infra/patterns this builds on. Workspace-relative paths.}

## NOT in Scope
{Explicit exclusions to prevent scope creep. If Step 0.6 detected a contract
 cascade and some Consumers are deferred, list them here by name.}

## Skill Sequence
{Four tables grouped by phase — Plan Reviews, Implementation Support, Review & QA,
 Ship & Post-ship. Fill in the 18-skill checklist from Step 4.}

## Key Decisions Captured
{Bullets from Round 1 + Round 2 answers that shaped this scope}
```

The full skill checklist tables (18 rows across four sections) follow the same shape shown in Step 4. Each row gets `[ ] YES` / `[ ] OPTIONAL` / `[N/A]` with a tailored note. Mandatory: `/plan-ceo-review` is always YES.

**Boilerplate collapse:** still *consider* all 18 (the forcing function), but in the emitted scope.md, when a task has no UI surface, collapse the seven design/browser skills (`/browse`, `/qa`, `/design-consultation`, `/design-review`, `/design-html`, `/design-shotgun`, `/plan-design-review`) into a single line — `N/A ×7 — no UI surface` — instead of seven near-identical rows. Same for any other all-N/A cluster. Keep YES/OPTIONAL rows itemized.

### 5.5 Create progress.md

See `/markdown-style` §10 (Progress Files) for full conventions: Resume Context block schema, append-only rule, Decisions Log dual-entry. The required structure:

```markdown
# Progress: {Task title}

## Resume Context
**Scope:** {plans_dir}/{N}-{slug}/scope.md
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
mkdir -p {plans_dir}/{N}-{slug}/artifacts
```

This directory holds any non-code artifacts produced during execution (dashboard JSON,
email templates, architecture diagrams, exported configs, etc.). Reference them from
progress.md when created.

### 5.7 Sweep related files into scope folder

Check `{plans_dir}/` for files related to this scope's slug — PRDs, concepting docs,
or any other working files created before the scope folder:

```bash
ls {plans_dir}/*{slug}* 2>/dev/null | grep -v "{N}-{slug}"
```

Move matching files into the scope folder so all task-related documents travel together:
```bash
mv {plans_dir}/prd-{slug}*.md {plans_dir}/{N}-{slug}/ 2>/dev/null
mv {plans_dir}/*{slug}*.md {plans_dir}/{N}-{slug}/ 2>/dev/null
```

Exclude `PLANS-INDEX.md`, `TO-DO.md`, and any files already inside subdirectories.
After this step, only the scope folder remains in `plans/` for this task — no orphaned
working files at the top level.

### 5.8 Update PLANS-INDEX.md

`{N}` was already resolved in Step 5.2 and used to name the scope folder; this
step just appends the index row.

If `PLANS-INDEX.md` doesn't yet exist, create it with the header below and
start numbering at 1:

```markdown
# Plans Index

All scopes, PRDs, and plans across the project. Types: `prd` (business requirements),
`scope` (multi-skill orchestration), `plan` (single-session executable task).

| # | Date | Type | Folder/File | Project | Status | Description |
|---|------|------|-------------|---------|--------|-------------|
```

Append the scope entry with its assigned number:

```markdown
| {N} | {date} | scope | {N}-{slug}/ | {project} | Active | {one-line description} |
```

### 5.9 Generate plan stubs (phased scopes only)

If the scope is **phased** (Step 3), generate a plan stub file for each phase.
Each plan ≈ 1 context window ≈ 1 session of work.

Plan stubs use **sub-numbers** of the scope's assigned `{N}` from Step 5.7:
- Phase 1 → `{N}.1`
- Phase 2 → `{N}.2`
- etc.

Plan stub filename: `{plans_dir}/{N}-{slug}/{N}.{P}-{slug}-PLAN.md`
where `{P}` is the phase number (1, 2, 3, ...).

Example: scope #39, slug `cashier-settlement`, 3 phases →
- `39-cashier-settlement/39.1-cashier-settlement-PLAN.md`
- `39-cashier-settlement/39.2-cashier-settlement-PLAN.md`
- `39-cashier-settlement/39.3-cashier-settlement-PLAN.md`

See `/markdown-style` §8 (Plan Documents) and §8.9 (Plan Stubs) for full conventions. The required stub shape:

```markdown
# Plan {N}.{P}: {Phase name}

**Version:** 0.1 (stub — detail filled at session start)
**Date:** {today's date}
**Author:** Alex
**Status:** Draft
**Plan #:** {N}.{P}
**Parent scope:** {plans_dir}/{N}-{slug}/scope.md
**Branch:** {branch or TBD}

## Related Docs
- `{plans_dir}/{N}-{slug}/scope.md` — parent scope
- `{plans_dir}/{N}-{slug}/progress.md` — progress tracker

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
**Gate**: {A human | B concurrency | C review/merge | D deploy/verify | E irreversible | F compliance}
**Review**: {what the human should verify}
**Resume**: "continue the {N}.{P} {slug} plan"
---
```

The **Gate** field is required on every phase-boundary CHECKPOINT. /plan reads it to
decide whether to suggest `/clear` (A/D/E — a natural pause) or continue without
prompting (B/C). The final phase of a scope uses the gate that best describes its
exit (often E for a cutover, or C if it just merges).

**Sizing rule (token size is a within-phase concern, never a phasing trigger):** Do
NOT split a phase because you estimate it exceeds a context window. A phase may span
multiple sessions — automatic compaction carries the working set, and the plan file's
intra-phase resume checkpoints (`"continue the {N}.{P} plan"`) let a fresh session
pick up mid-phase. Only split one phase into two plan files as a last resort when the
work is *both* very large *and* detail-dense (e.g. a wide refactor where exact
signatures must survive across sessions) — and when you do, label the split boundary
explicitly as "same gate, sequential sessions," not a new gate.

Also add a PLANS-INDEX entry for each plan stub (sub-numbered under the scope):
```markdown
| {N}.{P} | {date} | plan | {N}-{slug}/{N}.{P}-{slug}-PLAN.md | {project} | Draft | Phase {P} — {phase description} |
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
- "Run `/autoplan` on `{N}-{slug}/scope.md`"
- NOT "Start with `/plan-ceo-review` on `39.1-{slug}-PLAN.md`"

After gstack completes, copy any artifacts it creates in `~/.gstack/projects/$SLUG/`
to `{scope-folder}/artifacts/` so the scope folder stays self-contained.

---

## Step 7 — Archive (end of task)

When the user indicates the task is complete (all YES skills done, or user says
"archive this"), or when you detect all skill checklist items are done:

7.1 Move the scope folder to `{plans_dir}/archive/{N}-{slug}/`.

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
- **Plans dir must exist** (see §5.1 — stop, don't create silently).
- **Central, not local.** Scope folders always go in the plans directory, never in the source repo's `docs/` folder.
- **Progress is append-only.** Never delete or overwrite previous Progress Log entries. The Resume Context block is the only section that gets overwritten (it always reflects current state).
