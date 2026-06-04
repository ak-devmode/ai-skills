# Repo Cleanup Agent

Use this agent guide when the user asks to clean up branches, prune merged work,
check what's still in flight, or run repo/branch hygiene.

## 1. Purpose

Classify every non-protected branch with layered evidence, prune only what git can
prove is merged, and hand the human a copy-paste block for anything force-y. Leave
a durable audit trail (verdict table + recovery SHAs) in the owning docs repo.

## 2. Core Rules

1. **Never force-delete.** `git branch -D` and `git push --delete` are emitted as
   manual commands, never executed. The user's permission config denies `-D` on
   purpose — do not bypass it by other means (`update-ref`, `gh api DELETE`).
2. **Only act on the user's own branches** (author match per SKILL.md §1.2).
   Teammates' branches are report-only regardless of merge state.
3. **Protected branches** (`main`, `master`, `develop`, `staging`, `production`,
   `origin/HEAD` target) are never classified or touched.
4. **One read-only pass → one verdict table → one confirmation gate → act.**

## 3. Signal Priority

PR merge state (ground truth) > ancestry (`--merged`) > `[gone]` upstream >
patch equivalence (`git cherry`) > three-dot diff (tiebreaker only, never sole
evidence). `git fetch --prune` must run before any signal is read.

## 4. Buckets

SAFE_PRUNE (ancestry-merged → `git branch -d`) · SQUASHED (PR-merged but not
ancestry → manual `-D` block) · IN_FLIGHT (open PR / recent commits) ·
ABANDONED? · TEAM · UNKNOWN (last three → Open Questions list).

## 5. Modes

Default = current repo. `--all <owner>` = sweep the GitHub org/user (org is the
source of truth, not local dirs); repos without a local clone get remote-only,
report-only analysis. `/repo-cleanup-all` is a thin alias for `--all`.

## 6. Config Lives in SKILL.md §1

Account↔owner mapping, identity emails, repo roots, log destinations, protected
list. Teammates onboard by editing that section only — logic never hardcodes
user specifics.
