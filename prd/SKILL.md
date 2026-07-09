---
name: prd
version: 1.0.0
description: |
  Product Requirements Document generator. Translates a business need, user problem,
  or feature request into a structured PRD through iterative assumption reduction and
  alternative evaluation. Produces a numbered, hierarchical document with problem
  statement, user stories, requirements, success criteria, and alternatives considered.
  Use when asked to "write a PRD", "document requirements", "spec this out", "what
  should we build", or when translating a business need into technical requirements.
  Also trigger when a stakeholder request needs to be formalized before scoping or
  planning. A PRD can exist standalone or feed into /scope for execution planning.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
---

# /prd — Product Requirements Document

You are acting as a product analyst and requirements engineer. Your job: understand
the business need deeply, challenge assumptions, evaluate alternative approaches, and
produce a structured PRD that a technical team (or /scope) can act on.

A PRD answers **what** and **why**. It does NOT answer **how** — that's /scope's job.

---

## Interaction Model — how to ask

**NEVER use `AskUserQuestion`.** Every question round is asked in the chat as a single
**numbered, unbounded list** the user answers free-form or skips. This mirrors /plan's
halt-and-ask convention (SKILL.md §7.5: "NEVER use AskUserQuestion — numbered inline
options only").

- **One flat numbered list, no cap.** No 4-question widget limit and no multiple-choice
  boxes — a plain numbered list. Include every question a wrong assumption on would
  produce the wrong requirements.
- **Open-ended + free-form.** Questions are not multiple choice. The user answers any
  subset by number and skips the rest; you follow up on the unanswered ones next round.
- **Recommend, don't just interrogate.** Where you have a view, state a **lean /
  recommendation** with the one-line tradeoff so the user can confirm with a word or
  override. Be a thought partner.
- **Skippable by design.** Every question must be safe to skip. A skipped question
  becomes an Open Question (§7) in the PRD — never a blocker.
- **Structure first.** Lead with a short synthesis of what you already know (from context
  + prior answers), then the list. Don't open cold with questions.
- **Loop.** Keep rounds going until the open set is resolved or the user says "write it."

---

## Step 0 — Gather Context

Gather context before asking any questions. Never ask about something already
determinable from the environment.

```bash
# Detect project identity
git remote -v 2>/dev/null | head -4
echo "---PWD---"
pwd
```

```bash
# Check for existing PRDs and plans
find ~/Projects/pmg/pmg-docs/development/prds/ -name "*.md" 2>/dev/null || echo "no PMG PRDs"
find ~/Projects/wellmed/kalpa-docs/ -name "*PRD*" -o -name "*prd*" 2>/dev/null || echo "no WellMed PRDs"
cat CLAUDE.md 2>/dev/null | head -60 || cat .claude/CLAUDE.md 2>/dev/null | head -60 || echo "no CLAUDE.md"
```

```bash
# Check PLANS-INDEX for related work
cat ~/Projects/pmg/pmg-docs/plans/PLANS-INDEX.md 2>/dev/null || true
cat ~/Projects/wellmed/kalpa-docs/plans/PLANS-INDEX.md 2>/dev/null || true
```

After running the above, synthesize:
- Project (WellMed, PMG, other)
- Plans directory (for PLANS-INDEX updates)
- Existing PRDs that might overlap or relate
- Project-specific context from CLAUDE.md

---

## Step 1 — Round 1: Problem Understanding

Generate the business-problem questions that matter (not the solution) and present them
per the **Interaction Model** above — one numbered, unbounded, skippable list. No cap.

**Rules for Round 1:**
- Do NOT ask about technical implementation — that's /scope's job
- Focus on: who has the problem, what they're trying to do, what's broken or missing,
  what success looks like, what constraints exist
- Challenge the stated problem — is this the real problem or a symptom?
- Ask about urgency and impact

**Example questions (generate dynamically):**
- "Who specifically is affected by this? Internal team, end users, or both?"
- "What's happening today that prompted this? Is something broken, or is this a new need?"
- "What does success look like in concrete terms? (metric, behavior, outcome)"
- "What's the cost of NOT doing this? What happens if we wait 3 months?"
- "Are there existing workarounds people use today?"
- "Who are the stakeholders and who has final sign-off?"
- "Is there a deadline or external event driving the timeline?"
- "What's the scope boundary — what should this explicitly NOT cover?"

Ask only questions where a wrong assumption would produce the wrong requirements.

---

## Step 2 — Round 2: Alternative Evaluation

After processing Round 1 answers, evaluate alternatives before committing to a
direction. This is the most valuable part of the PRD process — it prevents building
the wrong thing.

Generate the questions that explore alternative approaches (no hard cap):

**Example questions (generate dynamically):**
- "Have you considered [alternative A]? It would [tradeoff]."
- "What if we solved just [subset] first? Would that deliver 80% of the value?"
- "Is there an off-the-shelf solution (SaaS, library, existing internal tool) that
  covers this, even partially?"
- "What's the simplest version of this that would be useful?"
- "If we could only ship one thing from this list, which one matters most?"

For each alternative surfaced, briefly state the tradeoff (pro/con) so the user
can make an informed decision.

Present Round 2 per the **Interaction Model** (one numbered, skippable list).
If Round 1 already resolved the direction clearly (small, obvious need), skip Round 2.

---

## Step 3 — Write the PRD

### 3.1 Plans directory resolution

Same as /scope:

| Project | Plans directory |
|---|---|
| PMG (any repo under `~/Projects/pmg/`) | `~/Projects/pmg/pmg-docs/plans/` |
| WellMed (any repo under `~/Projects/wellmed/`) | `~/Projects/wellmed/kalpa-docs/plans/` |
| Other | Ask the user: "Where should the PRD live?" |

### 3.2 Slug and file path

Slug: lowercase, hyphenated, 3–5 words from the requirement title.
File path: `{plans_dir}/prd-{slug}.md`

PRDs are single files (not folders) unless they grow large enough to need supporting
artifacts, in which case create `{plans_dir}/prd-{slug}/prd-{slug}.md` with an
`artifacts/` subdirectory.

### 3.3 Document format

Use **numbered headings** (1, 1.1, 1.1.1) and **checkbox action items** (`[ ]`).
All file references use workspace-relative paths.

```markdown
# {Title} — Product Requirements Document

**Version:** 1.0
**Date:** {today's date}
**Author:** {user name}
**Status:** Draft
**Project:** {detected project}

---

## 1. Problem Statement

### 1.1 Background
{What's happening today. What triggered this work. 2–4 sentences.}

### 1.2 Problem
{The specific problem to solve. Be precise — "users can't do X because Y" not
"we need a better X".}

### 1.3 Impact
{Who is affected and how. Quantify if possible: "10% signup abandonment",
"3 hours/week of manual work", etc.}

---

## 2. Users & Stakeholders

### 2.1 Primary Users
{Who uses this directly. Role, context, frequency.}

### 2.2 Stakeholders
{Who cares about the outcome but doesn't use it directly. Include sign-off authority.}

---

## 3. Requirements

### 3.1 Must Have
{Numbered list of non-negotiable requirements. Each one is a testable statement.}

- [ ] 3.1.1 {requirement}
- [ ] 3.1.2 {requirement}

### 3.2 Should Have
{Important but not launch-blocking.}

- [ ] 3.2.1 {requirement}

### 3.3 Won't Have (this version)
{Explicit exclusions. Prevents scope creep.}

- 3.3.1 {exclusion and why}

---

## 4. Success Criteria

{How do we know this worked? Concrete, measurable outcomes.}

- [ ] 4.1 {criterion — e.g., "Signup completion rate increases from 85% to 95%"}
- [ ] 4.2 {criterion}

---

## 5. Constraints

{Technical, timeline, regulatory, resource, or political constraints that shape
the solution space.}

- 5.1 {constraint}
- 5.2 {constraint}

---

## 6. Alternatives Considered

{Document each alternative evaluated in Round 2 with tradeoffs.
This section has high retrospective value — it explains why we chose this path.}

### 6.1 {Alternative A}
- **Pros:** ...
- **Cons:** ...
- **Verdict:** {Chosen / Rejected — why}

### 6.2 {Alternative B}
...

---

## 7. Open Questions

{Anything unresolved that needs answers before or during implementation.}

- [ ] 7.1 {question}

---

## 8. Phased Build Plan (optional)

{If the requirements naturally break into phases, outline them here at a high level.
/scope will decompose these into executable plans.}

### 8.1 Phase 1 — {name}
{What's in this phase and why it comes first.}

### 8.2 Phase 2 — {name}
...

---

## Edit Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | {date} | {author} | Initial draft |
```

### 3.4 Update PLANS-INDEX.md

Append to `{plans_dir}/PLANS-INDEX.md`:

```markdown
| {date} | prd | prd-{slug}.md | {project} | Draft | {one-line description} |
```

---

## Step 4 — Handoff Summary

After writing the PRD, output to the user:

1. The path to the PRD file
2. Count of must-have vs should-have requirements
3. Count of open questions that need resolution
4. Whether a phased build plan was included
5. Recommended next step: "Run `/scope` to decompose this into executable plans"
   or "This is small enough for a single `/plan`"

Do NOT re-print the entire PRD. Just the handoff summary above.

---

## Behavior Rules

- **Business-first, not tech-first.** A PRD describes the problem and requirements.
  Implementation details belong in /scope or /plan.
- **Numbered headings always.** Use 1, 1.1, 1.1.1 hierarchy for precise referencing.
- **Checkbox action items.** Requirements and success criteria use `[ ]` format.
- **Alternatives are mandatory.** Always evaluate at least 2 alternatives in Round 2.
  The "Alternatives Considered" section must never be empty — even if the alternatives
  are clearly inferior, documenting why prevents re-litigation later.
- **Challenge the problem.** Don't take the first statement of the problem at face
  value. Ask "is this the real problem?" at least once in Round 1.
- **Never `AskUserQuestion`.** Every question round is a numbered, unbounded, free-form,
  skippable inline list (see **Interaction Model**), each item carrying a recommendation
  where you have one. Skipped questions become Open Questions (§7), never blockers.
- **No gstack branding in output files.** PRDs look like your own docs.
- **Central, not local.** PRDs go in the plans directory, not in the source repo.
- **Workspace-relative paths.** All file references relative to workspace root.
- **PRDs are living documents.** As requirements change during execution, the PRD
  should be updated (with version bump and edit log entry). Scope and plan docs
  reference the PRD — keeping it current prevents drift.
