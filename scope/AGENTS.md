# Scope Agent

Use this agent guide when the user asks to scope, plan, decompose, or prepare non-trivial work before implementation. It is for multi-file, multi-service, multi-session, or ambiguous tasks.

## 1. Purpose

Create a task scope that captures context, assumptions, decisions, applicable specialist workflows, and execution phases. The scope folder is the source of truth for the task's plan, decisions, artifacts, and progress.

## 2. Context First

Gather local context before asking questions. Do not ask about anything already visible from the repository or docs.

Inspect:

- Git remote, current branch, current directory
- Recent commits and diff stats
- Repo instruction files such as `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`, README files, and project docs
- Existing active scopes and `PLANS-INDEX.md`
- Project identity from path and remote URL

Known plans directories:

- PMG: `~/Projects/pmg/pmg-docs/plans/`
- WellMed: `~/Projects/wellmed/kalpa-docs/plans/`

If the project is not PMG or WellMed, ask where the scope folder should live.

## 3. Assumption Removal

Ask 5-10 high-leverage questions in one batch. Only ask questions where the wrong answer would change the approach.

Cover the relevant subset of:

- Scope boundary
- Timeline and urgency
- Production vs exploratory work
- UI involvement
- Regulatory or compliance impact
- Cross-service or team coordination
- Testing strategy
- User-facing acceptance criteria

For WellMed, ask about SATU SEHAT or healthcare-record compliance when the task touches patient data, APIs, or health records. For PMG, ask about worker health data and regulatory requirements when relevant.

## 4. Design Refinement

After the first answers, ask one task-specific batch of design questions if architecture is still ambiguous.

Examples:

- API/service: sync vs async flow, data ownership, migrations
- UI: mobile-first vs desktop-primary, component reuse, empty/error/loading states
- Bug fix: local reproduction, regression test, production impact
- Infra: Terraform vs manual, rollout strategy, rollback plan

Skip this round for small tasks where the path is already clear.

## 5. Determine Scale

Use an atomic scope when all are true:

- One repo or service
- Fits in one session
- Clear implementation path
- No major architecture decision

Use a phased scope when any are true:

- More than two services or repos
- More than one session of work
- Architecture options need evaluation
- Compliance or human approval gates block later work
- Multiple deliverables benefit from separate execution plans

For phased scopes, create one `*-PLAN.md` stub per phase.

## 6. Specialist Checklist

Every scope includes a complete workflow checklist. Use agent-neutral names in the document, with slash command aliases only when helpful.

Recommended categories:

- Plan reviews: CEO/product review, engineering review, design review, developer-experience review
- Implementation support: investigation, design consultation, implementation agent
- Review and QA: code review, health check, tests, browser QA, developer-experience review
- Ship and post-ship: release, docs update, retro

Mark each item `YES`, `OPTIONAL`, or `N/A` with a reason. `N/A` is task-specific, not project-specific.

Engineering review is expected for non-trivial plans. CEO/product review is expected for significant product or scope decisions.

## 7. Write Scope Files

Create `{plans_dir}/scope-{slug}/` with:

- `scope.md`
- `progress.md`
- `artifacts/`
- Child `*-PLAN.md` files if phased

Slug rules:

- Lowercase
- Hyphenated
- 3-5 meaningful words from the task title
- Deterministic, not date-based

All file references inside scope and progress files must be relative to the project workspace root:

- PMG: relative to `~/Projects/pmg/`
- WellMed: relative to `~/Projects/wellmed/`

## 8. scope.md Format

Use this structure:

```markdown
# {Task title}
**Project:** {project}  **Branch:** {branch}  **Date:** {date}
**Scope folder:** {path}
**Source repo(s):** {absolute paths}

## 1. Context

## 2. Phases

## 3. Architecture

## 4. What Already Exists

## 5. NOT in Scope

## 6. Skill Sequence

## 7. Key Decisions Captured
```

Use ASCII diagrams for non-trivial architecture or workflow relationships. Do not use Mermaid.

## 9. progress.md Format

Create a living progress document with:

- Resume Context
- Decisions Log
- Progress Log
- Human Steps
- Plans, if phased
- Artifacts

Update progress after every significant action. The Resume Context block should always tell a future session where to pick up.

## 10. PLANS-INDEX

Update `{plans_dir}/PLANS-INDEX.md`.

If it does not exist, create it with columns:

```markdown
| # | Date | Type | Folder/File | Project | Status | Description |
|---|------|------|-------------|---------|--------|-------------|
```

Assign the next whole number for the scope. Use sub-numbers for child plans:

- Scope `39`
- Plan `39.1`
- Plan `39.2`

## 11. Handoff

After writing files, report only:

- Path to `scope.md`
- Path to `progress.md`
- Recommended next workflow
- Any surprising `N/A` decisions
- Whether the scope is atomic or phased

Do not paste the full scope document into chat.

## 12. Completion And Archive

When the task is done:

1. Move the scope folder to `{plans_dir}/archive/scope-{slug}/`.
2. Mark the scope and child plans done in `PLANS-INDEX.md`.
3. Evaluate whether repo instruction files, README files, or project docs need updates.
4. Confirm branch, commit, push, and remaining active scopes.
5. Record non-obvious learnings in the durable memory system when useful.
