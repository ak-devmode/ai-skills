# Markdown Style Agent

Use this agent guide when creating, updating, or revising structured Markdown documents that will be maintained over time: strategy docs, PRDs, plans, playbooks, integration specs, architecture notes, and operational docs.

Do not use this guide for quick notes, throwaway scratch files, or simple READMEs unless the user asks for structured document style.

## 1. Voice

Write like a smart operator explaining the work to another smart operator.

- Direct, specific, no filler
- No executive-summary padding
- No hedging when the facts are clear
- No emoji
- No generic `Conclusion` or `Summary` section
- The edit log is always last

Use parenthetical asides for secondary context, such as `(thesis - needs validation)` or `(corrected from v1)`.

## 2. Document Modes

Choose a mode before writing.

Mode A: Strategy or Architecture

- Explains what and why
- Uses numbered prose
- Does not use checkbox tasks unless the document assigns work

Mode B: Implementation or Execution

- Explains what, when, and who
- Uses checkboxes for tasks
- Includes owners and dependencies when assigning work
- Includes acceptance criteria
- Includes at least one ASCII diagram in the first three sections for non-trivial workflows

Mixed documents default to Mode B.

## 3. Header And Version Block

Every maintained document starts with:

```markdown
# Document Title

**Version:** X.Y
**Date:** DD Month YYYY
**Previous Version:** X.Y-1 (DD Month YYYY) - brief description
**Maintained by:** Names

### Key Changes vX.Y-1 -> vX.Y
- Change 1
- Change 2
```

Increment versions instead of overwriting history:

- Same-day or same-week edits: minor version
- Revisited in a new month or substantial rewrite: major version

## 4. Numbering

Use hierarchical decimal numbering throughout.

```markdown
# 1. Top Level Section
## 1.1 Subsection
### 1.1.1 Sub-subsection
1.1.1.1 Body item - description
```

Rules:

- Headers and body items must trace to their parent number.
- Stop at four levels: `X.Y.Z.N`.
- Below four levels, use prose, inline lists, tables, or checkboxes.
- Avoid bullets for body content except in version change logs, tables, and task lists.

## 5. Task Lists

Mode B tasks use checkbox syntax with full hierarchical numbering, owner, and dependencies.

```markdown
- [ ] 2.2.2.1 Stand up Chatwoot instance on AWS - @Alex
- [ ] 2.2.2.2 Configure webhook routing - @Alex (depends on 2.2.2.1)
- [ ] 2.2.2.3 Test inbound message flow - @Fitri
```

Use `@TBD` when ownership is unclear.

Acceptance criteria should be concrete and testable.

## 6. Diagrams

Prefer diagrams over tables over prose for relationships and flows.

Use ASCII diagrams in fenced `text` blocks. Do not use Mermaid unless the user explicitly asks.

```text
[Client] -> [API Gateway] -> [Service]
                              |
                              v
                           [Database]
```

Use diagrams for:

- Architecture
- Workflows
- Decision trees
- State machines
- Timelines
- Entity relationships

When editing a document that already contains Mermaid and the section is in scope, convert it to ASCII.

## 7. Tables

Use tables for direct comparison and structured reference data:

- API endpoints
- Error codes
- Parameters
- Responsibility matrices
- Requirements comparison

If the information has hierarchy, flow, or dependency, prefer a diagram.

## 8. Status And Confidence

Tag uncertain claims inline:

- Facts and decisions: plain statement
- Hypotheses: `(thesis - needs testing)` or `(thesis - needs validation)`
- Open questions: `Open question: ...`
- Corrections: `(corrected from vX where Y was stated)`
- Dependencies: `depends on X`, `blocks Y`

## 9. Editing Existing Documents

When updating a maintained document:

1. Increment the version.
2. Add Key Changes at the top.
3. Make edits in place.
4. Update cross-references.
5. Run a numbering audit.
6. Update the edit log.

Do not append new content at the bottom unless it belongs in the edit log or an appendix.

## 10. Numbering Audit

Run this after every structural edit:

- Every body item sits under the correct parent heading.
- No duplicate numbers exist.
- Section numbers are sequential with no gaps.
- Cross-references still point to the right section.

## 11. Plan Documents

Plan documents use Mode B plus these rules:

- File suffix: `[topic]-PLAN.md`
- Plain `PLAN.md` only when there is no ambiguity
- Required fields: `Author`, `ADR`, `Status`
- Status must be `Ready to execute` before a task runner executes it
- Include `Related Docs` before Phase 1
- Cross-check every Related Doc before marking the plan ready

When a plan completes, archive the plan and progress file according to the project planning workflow.

## 12. Edit Log

The edit log is always the final section.

```markdown
# Edit Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 30 Sep 2025 | Author | Initial version. |
```
