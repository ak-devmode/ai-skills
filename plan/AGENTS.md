# Plan Execution Agent

Use this agent guide when the user asks to run, continue, resume, or step through a structured plan document, especially files named `*-PLAN.md` or `PLAN.md`.

## 1. Purpose

Execute tasks from a plan document, record progress in a paired progress file, and stop at human checkpoints. Treat the plan as the source of truth and the progress file as the audit trail.

## 2. Discovery

1. If the user names a plan file or plan number, locate it first in the current workspace, then in the project plans directory.
2. If no file is named, scan the current workspace and project plans directory for `*-PLAN.md` or `PLAN.md`.
3. If exactly one plan is found, use it.
4. If multiple plans are found, ask the user which one to run.
5. If no plan is found, report that clearly and stop.

Known plans directories:

- PMG: `~/Projects/pmg/pmg-docs/plans/`
- WellMed: `~/Projects/wellmed/kalpa-docs/plans/`

Check scope subdirectories — named `<N>-<slug>/` (current convention) or
`scope-<slug>/` (legacy) — for child plans generated from a scope.

Progress file naming:

- `39.2-foo-bar-PLAN.md` -> `39.2-foo-bar-PROGRESS.md`
- `foo-bar-PLAN.md` -> `foo-bar-PROGRESS.md`
- `PLAN.md` -> `PROGRESS.md`

The progress file lives beside the plan file.

## 3. First Run

If the progress file does not exist:

1. Validate that the plan is readable and parseable.
2. Create the progress file with a header and session timestamp.
3. Run the Phase 0 pre-flight before executing tasks.
4. Print a concise status summary with plan name, branch, current task, completed task count, parent scope, and blockers.

## 4. Phase 0 Pre-flight

Run once per plan. If the progress file already records Phase 0 as complete, skip it.

1. Verify every file path referenced by task inputs exists.
2. Verify Related Docs, ADR links, and parent scope paths resolve.
3. Stop if the plan status is `Draft`; only execute plans marked `Ready to execute` or `In Progress`.
4. If the plan has a parent scope, read its `scope.md` and `progress.md` for context.
5. Determine the branch:
   - If the plan specifies `Branch`, confirm with the user before checkout.
   - If no branch is specified, derive `feature/<plan-stem>` and announce it.
   - If there is no git repo, skip branch handling.
6. Never execute plan tasks on `main` or `master`.

Log Phase 0 in the progress file.

## 5. Execution Rules

1. Read the plan and progress file at the start of each invocation.
2. Find the first task without a completed progress entry, or a failed task that should be retried.
3. If the next task is `HUMAN`, do not execute it. Log `WAITING_HUMAN`, tell the user what to do, and stop.
4. If the next task is `AI`, execute it fully, log it, and continue until a checkpoint, human task, failure, or phase boundary.
5. If the next task is `AI+HUMAN_REVIEW`, execute it, log it, then stop for user review.
6. Stop at every `CHECKPOINT` until the user explicitly tells you to continue.
7. If a task fails, log `FAILED` with what happened and stop.

## 6. Progress Logging

Always append to the progress file. Never delete previous entries.

Each task entry should include:

- Status: `DONE`, `SKIPPED`, `FAILED`, or `WAITING_HUMAN`
- Started and completed timestamps
- What was done in 1-3 sentences
- Files created or modified using workspace-relative paths
- Issues or blockers

When resuming after a break, summarize the progress file before continuing.

## 7. Plan File Handling

1. Do not modify the plan file during execution unless the user explicitly asks you to revise the plan.
2. If the plan is wrong, stop and explain what needs correction.
3. Keep task execution within the task's stated inputs, action, output, and acceptance criteria.
4. Use numbered headings, checkbox action items, workspace-relative paths, and direct imperative task descriptions.

## 8. Commit And Push

If git is initialized:

1. Commit after each completed AI task with message format `plan: Task X.Y brief description`.
2. Push after each phase or checkpoint to back up progress.
3. Do not open PRs unless the user asks.

If the worktree is dirty before you start, preserve unrelated user changes and mention any risk before committing.

## 9. Completion

When every task is `DONE` or `SKIPPED`:

1. Extract deferred TODOs from skipped tasks, issue notes, `TODO`, and `FIXME` mentions.
2. Append those items to the project `TO-DO.md`.
3. Update `PLANS-INDEX.md` to mark the plan done.
4. If this is a child plan, update the parent scope progress and leave the plan in the scope folder.
5. If this is a standalone plan, archive the plan folder under `{plans_dir}/archive/{plan-stem}/`.
6. Report the completion summary and pending sibling plans, if any.

## 10. Handoff

When stopping, tell the user:

- Current plan and task
- What changed
- What was verified
- What remains
- Exact resume prompt, such as `continue plan 39.2`
