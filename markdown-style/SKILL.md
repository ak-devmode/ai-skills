---
name: markdown-style
description: "Use for creating, updating, or revising structured .md documents — strategy docs, PRDs, plans, playbooks, integration specs, or any markdown maintained over time and loaded into future context windows. Trigger on: 'create a plan', 'draft a PRD', 'update the doc', 'write this up as a document', or references to versioned documents. Do NOT use for READMEs, quick notes, or throwaway content."
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - AskUserQuestion
---

# Markdown Document Style Guide

This skill is the base style guide for all structured markdown documents. Domain-specific skills inherit these rules and add their own. If a child skill contradicts this guide, the child skill wins for its domain.

---

## 1. Voice and Tone

1.1 **Conversational authority** — write like a smart operator explaining their business to another smart operator. Direct, no filler. Say what it is. No executive summary fluff, no hedging, no restating what the reader already knows.

1.2 No emoji. No "Conclusion" or "Summary" sections — the edit log is always last.

1.3 Use parenthetical asides for context that's not primary: "(corrected from v1)" or "(thesis — needs testing)".

---

## 2. Document Modes

Before creating a document, determine the mode. Both modes share the same structural rules.

**Mode selection rule:** If the document assigns, tracks, or hands off work, it's Mode B. If it aligns understanding, it's Mode A. Mixed documents default to Mode B — easier to ignore checkboxes in a strategy doc than to retrofit them later.

### 2.1 Mode A: Strategy / Architecture

For strategy docs, architecture overviews, position papers — **what and why**. Numbered prose items throughout. No checkboxes. Status and confidence tagging inline (see Section 5).

Standard sections — pick what fits: version header (always), priority stack, core definitions, target segments, operational sections, infrastructure/tools, future opportunities, assignments, templates, appendices, edit log (always).

### 2.2 Mode B: Implementation / Execution

For PRDs, migration plans, integration specs, operational playbooks — **what, when, and who**. Inherits all Mode A rules plus:

2.2.1 Version block includes a **Status** field (e.g., "Draft", "In Progress", "URGENT").

2.2.2 Top-level objectives are numbered items. Tasks use `[ ]` checkboxes with full hierarchical number, `@Owner`, and dependency notation:

```
2.2.2 Objective: Migrate WhatsApp to Chatwoot
  [ ] 2.2.2.1 Stand up Chatwoot instance on AWS — @Alex
  [ ] 2.2.2.2 Configure webhook routing — @Alex (depends on 2.2.2.1)
  [ ] 2.2.2.3 Test inbound message flow — @Fitri
  [ ] 2.2.2.4 Cutover production number — @Alex (blocks 2.2.3)
```

2.2.3 **Owner tags:** `@Name` on every task. Use `@TBD` if ownership is unclear.

2.2.4 **Acceptance criteria** follow each objective's task list: 1–3 concrete, testable conditions.

2.2.5 **Required diagram:** every Mode B document must include at least one ASCII diagram (in a fenced code block) in the first three sections showing the overall system, workflow, or dependency map. Implementation docs without a visual overview are consistently harder to onboard into. Never use Mermaid — it doesn't render in terminals, TextMate, or most plain-text contexts. **When editing an existing document that contains Mermaid blocks, convert them to ASCII as part of the edit.**

---

## 3. Structure and Formatting

### 3.1 Header and Version Block

Every document starts with:

```markdown
# Document Title

**Version:** X.Y
**Date:** DD Month YYYY
**Previous Version:** X.Y-1 (DD Month YYYY) — brief description
**Maintained by:** Names

### Key Changes vX.Y-1 → vX.Y
- Change 1
- Change 2
```

**Version increment rule:** Same-day or same-week edits are minor (1.1 → 1.2). Revisited in a new month, increment major (1.2 → 2.0). Never overwrite — always increment.

### 3.2 Numbering System

Use hierarchical decimal numbering throughout. Every section, subsection, and item gets a number tracing back to its parent.

```
# 1. Top Level Section
## 1.1 Subsection
### 1.1.1 Sub-subsection
1.1.1.1 Individual item — description on the same line
1.1.1.2 Next item
```

3.2.1 `#` headers: `# 4. Target Audiences`

3.2.2 `##` headers: `## 4.1 Segment 1: Relocating Families`

3.2.3 `###` headers: `### 4.1.1 Profile`

3.2.4 Body items: full hierarchical number followed by content on the same line.

3.2.5 **Numbering stops at 4 levels (X.Y.Z.N).** Below the 4th level, use plain prose, inline lists, or checkboxes (Mode B).

3.2.6 **Never use bullet points for body content.** Bullets are acceptable only inside tables, in the version change log, or in Mode B checkbox task lists.

### 3.3 Numbering Audit

**Run after every edit that adds or reorganizes content.** This is the most commonly skipped step — numbering errors compound across edits and make the document unreliable as a reference.

3.3.1 Every `X.Y.Z.N` item sits under a `### X.Y.Z` or `## X.Y` header.

3.3.2 No duplicate numbers anywhere in the document.

3.3.3 Section numbers are sequential with no gaps.

3.3.4 Cross-references (e.g., "see Section 5.2") still point to the right place.

### 3.4 Formatting Rules

3.4.1 `---` horizontal rule between top-level sections only. Not between subsections.

3.4.2 `**Bold**` for key terms on first introduction and status labels. Do not over-bold.

3.4.3 No italic for emphasis.

3.4.4 `~~Strikethrough~~` to preserve stale content without deleting it. Group stale items at the end of their section.

---

## 4. Visual Information Hierarchy

**Diagrams over tables over prose** for showing how things relate.

### 4.1 Diagrams

4.1.1 Default to ASCII art diagrams (inside fenced code blocks) for any section describing relationships between 3 or more elements. Never use Mermaid. Diagram conventions by use case:

```
Process flows / decision trees:
    [Start] --> [Validate] --> [Process]
                    |
                    v (fail)
                [Error Handler] --> [Notify]

System architecture / data flow:
    [Client] --> [API Gateway] --> [Auth Service]
                      |                 |
                      v                 v
                 [App Server] --> [Database]

Timelines / phases:
    Phase 1          Phase 2          Phase 3
    |--- Setup ------|--- Build ------|--- Ship ---|
    Jan              Mar              Jun

Entity relationships:
    [User] 1--* [Order] *--1 [Product]
                  |
                  1--* [LineItem]
```

### 4.2 Tables

4.2.1 Tables are for direct comparisons and structured reference data (API endpoints, error codes, parameter lists). If the data has relationships or hierarchy, use a diagram instead.

---

## 5. Status and Confidence Tagging

Tag claims and plans by confidence level inline:

5.1 Facts and decisions: stated plainly with no qualifier.

5.2 Hypotheses: "(thesis — needs testing)" or "(thesis — needs validation)".

5.3 Open questions: "Open question: [the question]" as its own item or inline.

5.4 Corrections from previous versions: "(corrected from vX where Y was stated)".

5.5 Dependencies: stated explicitly — "this blocks X" or "depends on Y".

---

## 6. Editing Existing Documents

6.1 Increment version number and add a Key Changes entry at the top.

6.2 Make edits in place — don't append to the bottom.

6.3 Run the numbering audit (Section 3.3).

6.4 Update the edit log.

---

## 7. Edit Log

Always the final section. Table format. Entries should not exceed 2-3 sentences.

```markdown
# Edit Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 30 Sep 2025 | Author | Initial version — brief description |
| 2.0 | 24 Feb 2026 | Author | Description of changes. Keep to 2-3 sentences max. |
```

---

## 8. Plan Documents (Mode B Extension)

Plan documents drive autonomous task execution via the task-runner skill. They inherit all Mode B rules plus the following.

### 8.1 Naming Convention

8.1.1 All plan files use the suffix convention: `[topic]-PLAN.md` (e.g., `ci-hardening-PLAN.md`, `consultation-extraction-PLAN.md`). The prefix `PLAN-*.md` is legacy and should not be used for new documents.

8.1.2 Plain `PLAN.md` (no prefix or suffix) is acceptable only for single-plan repositories where there is no ambiguity.

8.1.3 Store plans in `kalpa-docs/plans/[topic]/[topic]-PLAN.md` for cross-cutting plans. For repo-local plans that will never cross into other repos, they may live in `docs/` within the repo — but must be migrated to kalpa-docs archive on completion (see 8.4).

### 8.2 Required Header Fields

8.2.1 Plan documents require these additional header fields beyond the standard version block:

```markdown
**Author:** Name
**ADR:** path/to/adr.md  (or "N/A")
**Status:** Draft | Ready to execute | In Progress | Complete
```

8.2.2 Status must be set to "Ready to execute" before handing off to the task-runner. A plan with "Draft" status will be rejected by the pre-flight check.

### 8.3 Related Docs Section (Required)

8.3.1 Every plan document must include a `## Related Docs` section immediately after the header block, before Phase 1. This scopes the authoring cross-check (8.3.2) and the task-runner pre-flight validation.

```markdown
## Related Docs
- `path/to/architecture-overview.md`
- `path/to/adrs/ADR-001-decision.md`
- `path/to/relevant-readme.md`
```

8.3.2 **Authoring cross-check (required before marking status "Ready to execute").** After drafting the plan, read each document listed in Related Docs and verify the plan's task list covers all specified requirements, constraints, and acceptance criteria mentioned in those docs. Flag any gaps as tasks or notes in the plan before proceeding. This is the correct moment to catch dropped features — not at execution time.

### 8.4 Closing Cleanup (Required on Completion)

When all tasks in a plan are marked complete in the progress file:

8.4.1 Move the plan file (`[topic]-PLAN.md`) to `kalpa-docs/plans/archive/`.

8.4.2 Move the paired progress file (`[topic]-PROGRESS.md`) to `kalpa-docs/plans/archive/` alongside the plan.

8.4.3 Do not leave completed plans or progress logs in repo-local `docs/` directories. The kalpa-docs archive is the single source of completed work history.

8.4.4 If the plan lived in a repo-local `docs/` directory, confirm the archive move with the user before deleting the original location, since git history already tracks the file.

---

## 9. PRD Documents (Mode B Extension)

PRDs define what to build and why. They are the authoring step before a Plan — a PRD answers the product question, a Plan answers the execution question. PRDs are authored in claude.ai (Opus) and handed off to Claude Code for plan creation.

### 9.1 Naming and Storage

9.1.1 All PRD files use the suffix convention: `[feature]-PRD.md` (e.g., `consultation-booking-PRD.md`, `satu-sehat-sync-PRD.md`).

9.1.2 Store PRDs in `kalpa-docs/development/prds/[feature]-PRD.md`.

9.1.3 Status field in the header block: `Draft | In Review | Approved`. A PRD must be **Approved** before a Plan is created from it.

### 9.2 Required Sections

Every PRD must include these sections in this order. All follow Mode B formatting (numbered items, `[ ]` tasks, `@Owner` tags where applicable).

**9.2.1 Problem Statement.** One to three numbered items. State the problem, who experiences it, and why solving it now matters. No solution language here — this section is about the gap, not the fix.

**9.2.2 Users and Goals.** Identify the specific user types this feature serves. For each, state what they need to accomplish and what currently blocks them. If a user type is out of scope, name them explicitly and say so.

**9.2.3 Requirements.** Two subsections:
- *Functional* — what the system must do. Write as testable statements: "The system must X when Y." No ambiguous language ("should", "could", "might").
- *Non-functional* — performance, security, compliance constraints. For any feature touching patient data: add a SATU SEHAT compliance item if applicable, and a data-at-rest/in-transit requirement.

**9.2.4 Acceptance Criteria.** Numbered list of boolean conditions. Each condition can be verified without ambiguity. "Works correctly" is not acceptable — "Returns HTTP 200 with a valid FHIR Bundle when given a valid NIK" is.

**9.2.5 Out of Scope.** Explicit list. If you don't write this section, reviewers will assume everything not listed in Requirements is in scope. Name the things that are tempting but excluded, and briefly state why.

**9.2.6 Dependencies.** Systems, services, ADRs, or external decisions this feature depends on. State whether each dependency is already resolved or is a blocker. Format:

```markdown
- `ADR-003-queue-strategy.md` — resolved, SQS confirmed
- Satu Sehat IHS ID lookup API — unresolved, needed before implementation
```

**9.2.7 Open Questions.** Numbered list. Each question has an owner (`@Name`) and a resolution deadline if known. Unresolved questions with no owner block Approved status.

**9.2.8 Feeds Into.** State the Plan file this PRD will generate. If the Plan doesn't exist yet, state the intended path:

```markdown
**Plan:** `kalpa-docs/plans/consultation-booking/consultation-booking-PLAN.md` (to be created)
```

### 9.3 Authoring Guidance

9.3.1 Write requirements in the voice of the system, not the user. "The user can filter by date" is a user story — fine for discovery, but requirements should read: "The system must return appointments filtered by date range when `date_from` and `date_to` are provided."

9.3.2 Every requirement must map to at least one acceptance criterion. If you can't write a criterion for it, the requirement is too vague.

9.3.3 After drafting, read the relevant architecture docs (wellmed-system-architecture, service READMEs, ADRs) and verify no known constraints are violated. Flag any conflicts as Open Questions — don't silently design around constraints.

9.3.4 For WellMed features: always explicitly address multi-clinic data isolation. If a feature only applies to a single clinic context, state that. If it crosses clinic boundaries, flag it — that's an architectural decision that needs an ADR.

9.3.5 Before changing status to Approved: confirm all Open Questions are resolved or explicitly deferred with a documented reason. An unresolved question in an Approved PRD means the plan will hit it mid-execution.

### 9.4 Handoff to Plan

9.4.1 When the PRD is Approved, the Plan author (in Claude Code) reads the PRD and builds a `[feature]-PLAN.md` per Section 8. The PRD is the primary Related Doc for that Plan.

9.4.2 The Plan should trace each Phase back to a requirement or acceptance criterion in the PRD. If a task in the Plan has no traceable PRD requirement, it either shouldn't be there or the PRD is missing a requirement.

---

*Keywords (for skill-trigger matching):* strategy document, marketing plan, PRD, product requirements, working document, plan, update the doc, revise the plan, add to the document, versioned document, structured markdown, operational playbook, migration plan, integration spec, code documentation, implementation plan, architecture doc, PLAN.md, task runner, execution plan
