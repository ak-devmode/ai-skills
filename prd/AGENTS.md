# PRD Agent

Use this agent guide when the user asks to write a PRD, document requirements, spec out a business need, decide what to build, or formalize a stakeholder request before scoping and planning.

## 1. Purpose

Translate a business need into a structured Product Requirements Document. A PRD explains what to build and why. It should not lock in implementation details; that belongs in scope and plan documents.

## 2. Context First

Gather context before asking questions:

- Project identity from git remote and working directory
- Existing PRDs, scopes, and plans
- Project instruction files such as `AGENTS.md`, `CLAUDE.md`, README files, and relevant docs
- `PLANS-INDEX.md` for related work

Known plans directories:

- PMG: `~/Projects/pmg/pmg-docs/plans/`
- WellMed: `~/Projects/wellmed/kalpa-docs/plans/`

If the project is unknown, ask where the PRD should live.

## 3. Problem Understanding

Ask 5-8 business-focused questions in one batch. Do not ask implementation questions.

Cover:

- Who has the problem
- What is broken, missing, slow, risky, or expensive today
- What success looks like
- Cost of doing nothing
- Current workarounds
- Stakeholders and sign-off
- Deadline or external pressure
- Explicit scope exclusions

Challenge the first statement of the problem. Ask whether it is the real problem or a symptom.

## 4. Alternatives

Before writing requirements, evaluate alternatives. Ask 3-5 questions that test other ways to solve the problem.

Consider:

- A smaller version that captures most value
- Existing internal tools or flows
- Off-the-shelf products or libraries
- Manual process first, if useful
- The one requirement that matters if only one can ship

Document at least two alternatives in the PRD, even if rejected.

## 5. File Location

Slug rules:

- Lowercase
- Hyphenated
- 3-5 meaningful words

Default path:

```text
{plans_dir}/prd-{slug}.md
```

If the PRD needs artifacts, use:

```text
{plans_dir}/prd-{slug}/prd-{slug}.md
{plans_dir}/prd-{slug}/artifacts/
```

## 6. PRD Format

Use numbered headings and checkbox requirements.

```markdown
# {Title} - Product Requirements Document

**Version:** 1.0
**Date:** {date}
**Author:** {author}
**Status:** Draft
**Project:** {project}

---

## 1. Problem Statement

### 1.1 Background

### 1.2 Problem

### 1.3 Impact

---

## 2. Users And Stakeholders

### 2.1 Primary Users

### 2.2 Stakeholders

---

## 3. Requirements

### 3.1 Must Have
- [ ] 3.1.1 {requirement}

### 3.2 Should Have
- [ ] 3.2.1 {requirement}

### 3.3 Won't Have In This Version
- 3.3.1 {exclusion and rationale}

---

## 4. Success Criteria
- [ ] 4.1 {criterion}

---

## 5. Constraints

---

## 6. Alternatives Considered

### 6.1 {Alternative}
- **Pros:** ...
- **Cons:** ...
- **Verdict:** ...

---

## 7. Open Questions
- [ ] 7.1 {question}

---

## 8. Phased Build Plan

---

## Edit Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | {date} | {author} | Initial draft |
```

Use ASCII diagrams when they clarify user workflows, operations, or system relationships. Do not use Mermaid.

## 7. PLANS-INDEX

Append the PRD to `{plans_dir}/PLANS-INDEX.md`. If the project index includes numbered rows, assign the next number consistently with existing entries.

Recommended row format:

```markdown
| {N} | {date} | prd | prd-{slug}.md | {project} | Draft | {one-line description} |
```

## 8. Handoff

After writing the PRD, report:

- PRD file path
- Count of must-have and should-have requirements
- Count of open questions
- Whether a phased build plan is included
- Recommended next step: scope decomposition or direct execution plan

Do not paste the whole PRD into chat.

## 9. Behavior Rules

- Stay business-first, not tech-first.
- Requirements must be testable.
- Alternatives are mandatory.
- Numbered headings are mandatory.
- Use checkbox syntax for requirements and success criteria.
- Keep PRDs in the central plans directory, not the source repo, unless the user explicitly chooses otherwise.
- Update the PRD when requirements change during execution, with version bump and edit log entry.
