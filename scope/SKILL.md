---
name: scope
version: 3.6.0
description: |
  Task scoping, skill router, and progress tracker. Reads current context (git diff,
  branch, CLAUDE.md, open files), eliminates assumptions via two rounds of open-ended
  numbered inline questions, then outputs a phased scope with a full 18-skill checklist
  marking N/A skills with reasons. For multi-session work, generates plan stub files
  (one per phase, each ~1 context window) that /plan can execute. Creates
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

> **v3.6.0 (2026-08-09).** Deterministic steps now call `ai-skills/scripts/*`:
> plans-dir resolution, scope-number claiming (which **raced** as prose — scope 110
> collided), and PLANS-INDEX writes (whose old 7-column template matched no reader).
> `/ship` is N/A always rather than conditional. Step 0 greps the index instead of
> cat-ing ~31k tokens. Removed the standalone `mkdir artifacts` step and the
> close-background-shells step (harness-tracked now).

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
# Plans dir comes from the script — one owner, five callers (scripts/README.md).
# Exit 3 = unrecognized project (ask the user); exit 4 = docs repo not cloned.
PLANS_DIR="$(~/Projects/ai-skills/scripts/resolve-plans-dir.sh)" || exit
echo "PLANS_DIR=$PLANS_DIR"
ls -d "$PLANS_DIR"/[0-9]*-*/ 2>/dev/null || echo "no active scopes"
# GREP the index, never cat it — it is ~31k tokens in WellMed (/plan §1.1).
grep -n '^## ' "$PLANS_DIR/PLANS-INDEX.md" 2>/dev/null
grep -nE '^\| *[0-9]+ .*(Ready to execute|In progress|Active)' "$PLANS_DIR/PLANS-INDEX.md" 2>/dev/null | head -20
~/Projects/ai-skills/scripts/plans-index.py validate "$PLANS_DIR/PLANS-INDEX.md" 2>&1 | tail -5
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

```bash
~/Projects/ai-skills/scripts/repo-graph-snapshot.sh   # reads CROSS-REPO.md, emits the table
```

It fans out over the working set in parallel and emits the `## Repo Graph` table
directly — path, declared trunk, current branch, HEAD SHA, SDK pin, dirty flag, last
commit date.

**Flag these as drift to surface before Round 1** (none of them block; they need
acknowledging, and they often reframe the task — "consultation is still on the old SDK,
that changes phase 1"):

- current branch differs from the declared trunk on a repo we'll touch
- SDK pin differs across consumer repos (asymmetry)
- a declared repo is missing from `~/Projects/` (not cloned)
- a repo has uncommitted changes — someone else is mid-task there

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

Scan the combined diff (branch commits, unstaged, staged) for contract surfaces — the
list is in `references/conventions.md` §4.

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

### 0.7.1 Find the ADRs this work touches

WellMed keeps them at `kalpa-docs/adrs/`, PMG at `pmg-docs/adrs/`; ai-skills has none, so
skip. Extract 3–6 keywords from the task title, branch name and diff, then grep the ADR
files for them and read the title, status and relevant section of each match. Parallel is
fine — the greps are independent.

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

## Step 0.8 — API-Surface / Endpoint Map (gated on an `api/` dictionary)

Fires **only** when the workspace has an API dictionary — marker: an `api/README.md`
whose header declares the generated+annotated convention (e.g. WellMed
`kalpa-docs/api/`). If absent, skip and note in synthesis: "No `api/` dictionary —
endpoint-map step N/A." Presence-activated and generic: any repo that adopts an `api/`
dict opts in for free.

**Why.** This stops scopes from shipping "3/4-baked" — application logic without the
FE-facing gateway endpoint wired. Leaving the endpoint for later forces someone to
re-interpret the scope's intent at the integration layer, which diverges from the plan
and creates bug surface. The mapping belongs at scope time, not after.

**Produce `artifacts/endpoint-map.md`** — for each unit of new or changed app logic the
scope introduces, the gateway route that exposes it (**new or existing**) + its payload
contract source, read from the dict's registry (don't re-derive the shape from Go):

| Logic unit (service / handler / saga) | Gateway route (METHOD path) | New / Existing | Payload contract source | In this scope? |
|---|---|---|---|---|

Rules:
- Every create/update/read the scope adds **must** map to a gateway route. A logic unit
  with no route is a completeness gap — either pull the route into scope, or record why
  the FE surface is deliberately deferred and to which follow-up.
- Use the dict (`api/<domain>.md` + the route→DTO registry) to identify the route and
  its contract category rather than re-deriving from source — this is the token/time
  saver, and it's only safe because the dict is generated + staleness-checked.
- This artifact feeds **`/plan-eng-review`** as the completeness gate: eng review checks
  each mapped route is wired end-to-end, and that the big-data/payload tradeoffs
  (pagination, filter surface, what's in the body) are decided **at the contract** — those
  are completeness decisions wearing a technical costume.

Tag the endpoint-map in scope.md (a `## Endpoint Map` section or a pointer to the
artifact) so `/plan` and `/plan-eng-review` pick it up.

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

Cover where ambiguity actually exists — scope boundary, prod vs exploratory, UI
involvement, compliance angle, coordination with other people or services, testing,
cross-repo touchpoints, what's deliberately excluded, and which existing pattern to
follow. Generate the questions from *this* task; a generic list produces generic answers.

End with: "Answer by number. Skip any that don't apply."

---

## Step 2 — Round 2: Design Refinement

After processing Round 1 answers, ask the task-specific design questions that determine the best solution architecture. Same format: numbered, open-ended, no multiple choice, single response. Target 3–10 questions depending on complexity.

Ask what determines the architecture, by task type: for a new API/service — sync vs
async and why, which service owns the data and its schema home, new migration vs extend,
contract surface and consumers. For UI — mobile-first vs desktop, which existing
component patterns to reuse, empty/error/loading behaviour, the end-to-end happy path.
For a bug fix — missing regression test vs genuine edge case, reproducible locally, hit
production or caught pre-merge, suspected root-cause area. For infra — Terraform-managed
vs manual, blue/green vs in-place, rollback in scope, what breaks downstream on failure.

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
`/plan` can execute. See Step 5.9.

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
| Always — Alex does not use `/ship` | `/ship` → **always N/A** (see below) |
| No user-visible change | `/document-release` → mark OPTIONAL |
| Small single-session task | `/retro` → mark OPTIONAL |

**Table Identity Map (Step 4.5) is likewise conditional:** mark it N/A with a one-line reason when the scope has **no DB table write/DDL surface**; run it when the scope creates, alters, re-owns, or adds a write path to a table.

**Mandatory skills:**
- `/plan-ceo-review` is **always YES**. It catches "why are we doing it this way at all?"
  reframes that save entire phases of wasted work. Run it first, before eng review.

**`/ship` is always N/A — not conditional.** Alex does not use it, in any repo. Mark it
`N/A — not in use; promotion is /review → PR → merge → /closeout` and move on. Do not
re-litigate it per scope, and do not ask whether this scope is prod-bound in order to
decide: the answer does not depend on the scope. CI covers tests and diff review, deploy
is automatic on merge, `/document-release` covers docs, and `/closeout` covers cleanup.

**Shortcut:** `/autoplan` runs `/plan-ceo-review` + `/plan-design-review` +
`/plan-eng-review` + `/plan-devex-review` in sequence with auto-decisions. Use it
instead of skills 1–4 individually when you want a fast full-review pass.

**Skill sequence table (fill in based on task):**

Skills are grouped by workflow phase. Mark each YES, OPTIONAL, or N/A with reason.

**The tables live in `templates/skill-checklist.md`** — four sections (Plan Reviews,
Implementation Support, Review & QA, Ship & Post-ship) covering all 18. Read it when
writing the checklist; don't reproduce it from memory.

Consider all 18 — that is the forcing function — but **emit only what applies.** Mark
each YES / OPTIONAL / N/A with a one-line reason, and collapse an all-N/A cluster to a
single line (`N/A x7 — no UI surface`) rather than seven near-identical rows.

## Step 4.5 — Table Identity Map (when the scope writes to / alters DB tables)

**Trigger — skip with an N/A reason otherwise.** Run this step only when the scope
**creates or alters a table, changes a table's write-owner, or adds a write path to
an existing table.** Signals: migration files, `AutoMigrate`/raw DDL, ORM model
changes, schema-registry edits, a new write repository/method. A scope with **no DB
write/DDL surface** marks this N/A (Step 4). This is a database-table discipline, not
a general contract step — proto/API cascades are Step 0.6.

**Why.** Write-ownership and column-shape are where drift and premise errors live (the
scope-48 retro: reviewers can't catch errors about structure they can't see). Forcing
the *current* structure onto the page, cited, before proposing changes is what stops a
plan from silently inventing, dropping, renaming, or re-owning a table.

**Produce two things:**

1. **A canonical table-identity reference** — one row per table the scope touches,
   grounded in **primary source, cited `repo/path:line`** (never inferred from docs):

   | Table | Write-owner (MS) | Physical schema | Key columns | Read-by | Source cite |
   |---|---|---|---|---|---|

   For a small surface (1–3 tables) this lives inline in scope.md. For a large or
   multi-repo surface, emit `artifacts/schema-reference.md` and reference it from
   scope.md — one shape source, so the scope body and plan stubs can't drift. Size it
   to the surface; do not pad.

2. **A deviation ledger** — every change to the write/DDL surface, each with the cited
   current-state it departs from:

   | Table | Deviation (create / drop / rename / re-own / change-shape) | From (current, cited) | To (target) | Rationale |
   |---|---|---|---|---|

**The rule — deny-by-default on deviation.** The default is **match the existing
structure**. Every deviation-ledger row is an **explicit decision requiring user
approval** before it enters plan stubs (Step 5.9). /scope surfaces the ledger at
handoff (Step 6); unapproved deviations are **not** baked into phase tasks. A table the
scope only **reads** is pinned as a dependency (owner + consumed shape), **not** gated —
you can't deviate what you don't own. The target shape may be go-forward (per an ADR /
design doc); this gate makes each go-forward deviation an approved decision, it does not
forbid it.

**Ownership-guard tie-in (WellMed).** "Which MS write-owns each table" is the ADR-028
one-owner-per-table question. Cross-check each written table against
`wellmed-backbone/internal/db/migration/adr028_ownership.go`; a deviation that crosses an
owner boundary is an ADR-028 amendment — flag it in ADR Alignment (§5.4) and treat its
approval as a gate-A decision.

## Step 5 — Determine Plans Directory & Write Output Files

### 5.1 Plans directory resolution

The scope folder lives in a **central plans directory**, not in the source repo.
Already resolved in Step 0 by `scripts/resolve-plans-dir.sh`; reuse that value. On
exit 3 (unrecognized project) ask the user where the scope folder should live; on
exit 4 (resolved but missing) stop — a missing plans dir means the docs repo isn't
cloned, and creating it silently hides that.

### 5.2 Slug and scope number

Determine the slug: lowercase, hyphenated, 3–5 words from the task title.
Example: "wellmed-saga-handler-phase2", "pmg-report-export", "auth-refresh-bug"

**Claim `{N}` with the script — never by reading the index yourself:**

```bash
N="$(~/Projects/ai-skills/scripts/claim-scope-number.sh "$PLANS_DIR")"
```

It maxes over four sources — `origin/main`'s index, the local index, scope folders on
disk, and branch names — and prints its provenance to stderr. Read that stderr: when
local and origin disagree, another session has pushed or you have unpushed rows, and
the note says so.

> **Why this is a script.** This step used to say "read `PLANS-INDEX.md`, find the
> highest, increment" against the **local working tree**, while `/plan` §11.4 already
> knew to read `git show origin/main:…` "since concurrent sessions race for scope
> numbers." The two skills disagreed and the one that mints numbers was the wrong
> one. Scope 110 collided and had to be renumbered 111.

`{N}` prefixes the scope folder and every child plan.

The scope folder path is: `{plans_dir}/{N}-{slug}/` (e.g.
`~/Projects/pmg/pmg-docs/plans/32-pmg-testsuite/`). Archive folder name uses
the same convention: `{plans_dir}/archive/{N}-{slug}/`.

### 5.2.1 Program-member scopes (ADR-029)

A member of an existing program still gets a normal **flat, top-level**
`{plans_dir}/{N}-{slug}/` folder and a normal index row — member scopes never live
inside the program folder. Full lifecycle, detection, the `{slug}-brief.md` naming rule,
and the graduation steps are in `references/conventions.md` §1. On completion the member
archives into the **program's own** `archive/`, not the repo-wide one (§7.1).

### 5.3 File references

Workspace-relative paths throughout, per `/markdown-style` §8.8 — relative to
`~/Projects/pmg/` or `~/Projects/wellmed/`, because the scope folder lives outside the
source repo and a bare filename is ambiguous about which repo it means.

### 5.4 Create scope.md

Write from `templates/scope.md.template`. Section conventions are `/markdown-style`
§11; omit a Required-if section with a one-line reason rather than leaving it empty.

**`Created by` is DERIVED, never hardcoded** — read the name off git config at run
time (`git config user.name`, falling back to `--global`). If nothing is configured
anywhere, write `TBD` and say so. Never substitute a name from an example, this file,
or another scope; see `references/postmortems.md` for what that cost.

`Created by` records who *conceived* the scope, written once at creation. Who
*executes* it is recorded per phase by `/plan` §3.1, because a scope's phases
routinely run in different hands than the one that scoped it.

### 5.5 Create progress.md

Write from `templates/progress.md.template`. Conventions are `/markdown-style` §10.

Two things carry the weight. The **Operating Contract** is pinned and re-read on every
resume — it holds the ground rules agreed at kickoff (execution posture, mismatch
handling, check-in cadence), numbered so they can be cited. Seed it with the template's
three defaults if none were stated. The **Resume Context** block is the only
overwritable section in the file; everything else is append-only.

### 5.6 Create the artifacts/ subdirectory alongside scope.md and progress.md.

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

### 5.8 Update PLANS-INDEX.md — via the script, never by hand

```bash
~/Projects/ai-skills/scripts/plans-index.py add "$PLANS_DIR/PLANS-INDEX.md" \
  --num "$N" --status "📝 Draft ($(date +%F))" --folder "\`{N}-{slug}/\`" \
  --desc "{3–4 sentences: what this is and what it changes}" \
  --creator "$(git config user.name)"
```

The script refuses to append against a non-canonical header instead of leaking a
mismatched row. Canonical shape, both tables:

```markdown
| # | Status | Folder | Description | Created by |
|---|--------|--------|-------------|------------|
```

**Write the Description as 3–4 real sentences, not a label.** This column is Alex's
high-level tracker — he reads it from the console to see what has been going on across
the project, so it is the one place worth spending words (`/markdown-style` §11.7.4).
Say what the scope changes and why, not just its title.

If `PLANS-INDEX.md` doesn't exist, create it with the two canonical tables
(`## Active Plans` and `## Completed / Archived`, each with the header above) and
start at 1.

> **Why the shape is enforced in code.** The old version of this step carried a
> seven-column template (`| {n} | {date} | scope | {path} | {project} | {status} |
> {desc} |`) that matched no reader. PMG's index still had two conflicting shapes as
> late as 2026-08-09 and 39 of its Active rows rendered their description **nowhere**,
> because an undeclared column shifted every cell right. `plans-index.py` exists so a
> shape mismatch is a refusal rather than a silent leak.

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

Write each from `templates/plan-stub.md.template`; conventions are `/markdown-style`
§8 and §8.9.

**The Gate field is required on every phase-boundary CHECKPOINT.** `/plan` reads it to
decide whether to suggest `/clear` (A/D/E — a natural pause) or roll through (B/C). The
final phase uses the gate that best describes its exit.

**A table-write phase carries the identity map.** If a phase creates, alters or re-owns
a table, its CHECKPOINT Review field must name the Step 4.5 deviations landing in that
phase — an unapproved deviation is not eligible to ship. Crossing an owner boundary
makes it gate A (or E if irreversible), never a roll-through B/C.

**Sizing is a within-phase concern, never a phasing trigger.** Do not split a phase
because you estimate it exceeds a context window; compaction plus intra-phase resume
checkpoints handle that. Split one phase into two files only when the work is *both*
very large *and* detail-dense, and label the split "same gate, sequential sessions."

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

**`/plan` §11 owns archive logic — follow it, don't duplicate it.** `/closeout` §13 does
the same. This step adds only the routing that is specific to a scope:

7.1 **Where it goes.** A standalone scope moves to `{plans_dir}/archive/{N}-{slug}/`. A
**program member** moves into the program's own `{plans_dir}/{program-slug}/archive/`
instead — never the repo-wide archive (ADR-029 §2.3.4). Detect membership by scanning
`{plans_dir}/*-program/*-brief.md` for a row naming this scope.

7.2 **The index row moves in the same commit as the folder**, via
`scripts/plans-index.py move --num {N} --to archived`. Omit `--folder` unless the path
actually changes — the row's existing path is usually right, and the script refuses a
path that does not resolve.

7.3 **Program members:** flip the member's row in `{slug}-brief.md` to Archived and
point it at the new path. The brief stays the members registry across the lifecycle.

## Step 8 — Post-flight Cleanup (runs after archive)

After archiving (Step 7), run the full post-flight checklist. These steps are NOT
optional — they are part of scope completion. Do not declare the scope done until
all post-flight items are addressed.

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

Check the index for other active scopes in this project. If a logical next one exists (a
downstream scope that was waiting on this, or the next in a series), offer to continue.

Before telling the user to `/clear`, **run `/ready-to-clear` — mandatory.** Spawn the
fresh validator with paths plus the claim "scope {N} fully complete and archived". On
`NOT READY`, perform the listed fixes and re-validate; after 3 cycles, surface the
failures inline and do **not** tell them to clear. On `UNAVAILABLE` (the validator
could not be spawned) the gate did not run — report that and the reason, and do not
tell them to clear either; there is no in-context substitute for it. Only on `READY`,
quote the resume reconstruction and give them the exact prompt to paste.

If there are no follow-on scopes, just report completion.

## Ongoing: Progress Tracking Rules

`/markdown-style` §10 owns these — append-only, the Resume Context is the only
overwritable block, decisions go in both the Decisions Log and the Progress Log, paths
are workspace-relative. Three additions specific to a scope's execution:

- **Update the Resume Context every time you append to the Progress Log.** It is the
  "paste this to get oriented" block; a stale one is worse than an empty one.
- **A human step discovered mid-execution goes in the Human Steps table immediately**,
  as `[ ] Pending` — not in prose, where it will be missed.
- **On resume, read the pinned Operating Contract first**, then the Resume Context, then
  `scope.md`. Summarize where things stand before doing anything.

## Behavior Rules

- **Context-first, no interview style.** Read everything before asking anything.
- **Both rounds are single batches.** Never ask one question at a time.
- **N/A is per-task, not per-project.** WellMed and PMG both have UIs.
- **No gstack branding in output files.** scope.md and progress.md look like your own docs.
- **Slug is deterministic.** Based on task title, not date. Dates go inside the file.
- **Plans dir must exist** (see §5.1 — stop, don't create silently).
- **Central, not local.** Scope folders always go in the plans directory, never in the source repo's `docs/` folder.
- **Progress is append-only.** Never delete or overwrite previous Progress Log entries. The Resume Context block is the only section that gets overwritten (it always reflects current state).
