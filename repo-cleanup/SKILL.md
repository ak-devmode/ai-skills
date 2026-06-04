---
name: repo-cleanup
version: 1.0.0
description: |
  Branch hygiene and repo upkeep. Classifies all non-protected branches against the
  trunk(s) using layered signals (PR merge state, ancestry, gone-upstream, patch
  equivalence), safely prunes provably-merged local branches, emits a manual command
  block for squash-merged and remote deletions (never runs them), and runs housekeeping
  (worktree prune, stash report, parked-on-merged-branch check). Outputs a verdict
  table, a durable log with recovery SHAs, and an open-questions list.
  Default scope is the current repo. `--all <owner>` sweeps every repo in a GitHub
  org/user (see /repo-cleanup-all for the no-flags alias).
  Use when asked to "clean up branches", "prune branches", "repo cleanup",
  "branch hygiene", "which branches can I delete", or "what's still in flight".
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - AskUserQuestion
---

# /repo-cleanup — Branch Hygiene & Repo Upkeep

You are acting as a careful repo janitor. Your job: classify every branch with
evidence, delete only what git itself can prove is merged, hand the human a
copy-paste block for everything force-y, and leave a durable audit trail.

**Prime directives:**

1. **Never force-delete.** `git branch -D` and `git push --delete` are NEVER executed
   by this skill — they go in the Manual Actions block for the human to run (the `!`
   prefix in Claude Code runs a command inline). The user's permission config denies
   `-D` deliberately; do not work around it (no `update-ref -d`, no `gh api DELETE`).
2. **Only touch branches the user authors.** Teammates' branches are report-only,
   always — even with a merged PR. List them under Open Questions with a recommended
   action the user can relay.
3. **One read-only classification pass, one confirmation gate, then act.** Never
   interleave analysis and deletion.
4. **Protected branches are untouchable**: anything in the Config protected list,
   plus the repo's `origin/HEAD` target, regardless of classification.

---

## 1. Config

> **Teammates: edit this section to onboard yourself.** Everything user-specific
> lives here; the logic below never hardcodes accounts, emails, or paths.

### 1.1 gh account → owner mapping

The skill switches `gh` to the right account per repo, and **restores the
originally-active account when done** (`gh auth switch` mutates global state).

| gh account  | covers owners/orgs                  |
|-------------|-------------------------------------|
| ak-devmode  | kalpa-health, ak-devmode            |
| ak-padma    | Padma-Medical-Group                 |

GitHub owner lookups are case-insensitive; the table holds canonical casing.
If a repo's origin owner is not in this table: **ask** which account to use —
never guess.

### 1.2 My identities (author matching)

Branches whose last commit author matches none of these are TEAM branches
(report-only):

| kind  | value                          |
|-------|--------------------------------|
| email | alex@pbmcgroup.com             |
| email | (any email in local git config user.email across repo roots) |

### 1.3 Repo roots (local clone discovery for `--all`)

| root                          |
|-------------------------------|
| ~/Projects/wellmed            |
| ~/Projects/pmg                |
| ~/Projects                    | (one level deep, fallback)

### 1.4 Log destinations

| owner                | log directory                                       |
|----------------------|-----------------------------------------------------|
| kalpa-health         | ~/Projects/wellmed/kalpa-docs/development/          |
| Padma-Medical-Group  | ~/Projects/pmg/pmg-docs/development/                |
| (unmapped)           | ask: repo-local `development/` or terminal-only     |

Log filename: `repo-cleanup-log-YYYY-MM-DD.md` (append a section per repo on
`--all` sweeps; append a numbered suffix if the file exists from an earlier
run the same day).

### 1.5 Protected branches (never classified, never touched)

`main`, `master`, `develop`, `staging`, `production`, plus the branch
`origin/HEAD` points at.

---

## 2. Modes

- **Default**: operate on the current repo (or the repo at a path the user names).
- **`--all <owner>`**: sweep every non-archived repo in the GitHub org/user.
  If `<owner>` is omitted, ask which configured owner to sweep (offer the
  owners from §1.1). Enumerate via `gh repo list <owner> --no-archived
  --limit 200 --json name,defaultBranchRef`. **The org is the source of truth,
  not local directories** — local-only repos (not pushed to the org) are out of
  scope. For each org repo, find a local clone by scanning §1.3 roots for a
  matching `origin` URL:
  - clone found → full classification + local prune flow
  - no clone → remote-only analysis via `gh` API; report-only row, no deletions

---

## 3. Sequence

### Step 0 — Preflight

1. `gh auth status` — record the originally-active account (restore it in Step 8).
2. Determine repo owner from `origin` URL → look up account in §1.1 → `gh auth
   switch --user <account>` if needed. A misleading `Could not resolve to a
   Repository` error from `gh` usually means the WRONG ACCOUNT is active — check
   the mapping before concluding there are no PRs.
3. `git fetch --prune` — mandatory first; stale remote-tracking refs poison every
   later signal, and `[gone]` detection depends on it.
4. Detect trunk: `git symbolic-ref refs/remotes/origin/HEAD` (run
   `git remote set-head origin --auto` if unset).
5. Verify the working tree is clean enough to proceed (a dirty tree is fine — we
   never checkout — but note it in the report).

### Step 1 — Trunk reference gate

Ask the user what to classify "merged" against, with a detected recommendation:

- Repo has only `main` → recommend `main`, confirm inline.
- Repo has `develop` + `main` (promotion-chain repo) → recommend **both**
  ("merged" = reachable from *either*). This is strictly safest: squash-merged
  develop→main promotions make the two diverge, so checking one can lie.
- `--all` mode: build ONE table of per-repo recommendations and present it once
  for adjustment (AskUserQuestion or inline edit) — never ask per-repo.

### Step 2 — Classification pass (read-only)

For every local branch and every `origin/*` branch not in the protected list,
gather signals in this priority order (higher signals are authoritative; lower
ones are tiebreakers, never sole prune evidence):

| # | signal | command | meaning |
|---|--------|---------|---------|
| 1 | PR state | `gh pr list --head <branch> --state all --json state,number,mergedAt,url` | merged = ground truth regardless of merge strategy; open = in flight; closed-unmerged = abandoned? |
| 2 | Ancestry | `git branch --merged <trunk>` (each selected trunk) | classic merge — provably safe |
| 3 | Gone upstream | `git branch -vv` shows `[gone]` | remote deleted after merge (GitHub auto-delete) — strong squash indicator |
| 4 | Patch equivalence | `git cherry <trunk> <branch>` — all `-` | content is upstream even if rebased/squashed |
| 5 | Three-dot diff | `git diff <trunk>...<branch> --stat` empty | weakest; tiebreaker only |
| + | Metadata | `git log -1 --format='%ae|%an|%cr|%H'`, `git rev-list --left-right --count <trunk>...<branch>` | author, age, ahead/behind |

**Buckets:**

| verdict | criteria | action |
|---------|----------|--------|
| SAFE_PRUNE | ancestry-merged (signal 2) to a selected trunk | `git branch -d` (executed after gate) |
| SQUASHED | merged PR (1) or `[gone]`+patch-equivalent (3+4), but NOT ancestry-merged | Manual Actions block (`-D` is config-denied) |
| IN_FLIGHT | open PR, or ahead of trunk with commits newer than 30 days | never touch |
| ABANDONED? | ahead of trunk, no open PR, last commit > 30 days (or closed-unmerged PR) | Open Questions |
| TEAM | author not in §1.2 | report-only, Open Questions, whatever the other signals say |
| UNKNOWN | conflicting signals | Open Questions |

### Step 3 — Verdict table

Render one table (per repo on `--all`):

```
| branch | author | age | ahead/behind | PR | signals | verdict |
```

`signals` is a compact evidence string, e.g. `PR#42 merged, [gone], cherry-clean`.
Every verdict must be explainable from its signals column — no bare verdicts.

### Step 4 — Confirmation gate (exactly one)

AskUserQuestion: **(a)** prune SAFE_PRUNE only · **(b)** SAFE_PRUNE + show Manual
Actions block for SQUASHED/remote · **(c)** report only, delete nothing.
On `--all`, one gate for the whole sweep (the table already showed per-repo detail).

### Step 5 — Execute local prunes

For SAFE_PRUNE only: `git branch -d <branch>` (never `-D`). Record
`<branch> <sha>` pairs as you go — these are the recovery artifact. If `-d`
unexpectedly refuses, demote the branch to UNKNOWN and move on; do not escalate
to `-D`.

### Step 6 — Manual Actions block

Emit (never execute) a fenced block the user can run with the `!` prefix:

```bash
# SQUASHED local branches (verified merged via PR; git can't prove it, so -D is needed)
git -C <repo> branch -D <branch>   # PR#42 merged 2026-05-30, sha <sha>
# Remote branches safe to delete (your own, merged-PR-confirmed)
git -C <repo> push origin --delete <branch>   # PR#42
```

TEAM branches never appear here — they go in Open Questions with a suggested
message to the branch owner.

### Step 7 — Housekeeping

- `git worktree list` → flag stale/prunable; run `git worktree prune`.
- `git stash list` → report stashes older than 30 days (report-only).
- **Parked-on-merged-branch check**: if HEAD is on a branch classified
  SAFE_PRUNE/SQUASHED, offer to `git checkout <trunk>` first (a recurring
  drift mode worth catching here).
- Trunk sync: if local trunk is behind `origin/<trunk>` and fast-forwardable,
  offer the ff pull.
- Naming audit (report-only): branches not matching `feature/*|fix/*|docs/*|
  refactor/*|test/*|ci/*|chore/*`.

### Step 8 — Report, log, restore

1. Terminal: final verdict table + Manual Actions block + Open Questions list.
2. Write the log to the §1.4 destination: date, repo(s), trunk reference used,
   full table, **deleted branches with SHAs**, Manual Actions block, housekeeping
   results, Open Questions.
3. `gh auth switch --user <original-account>` if Step 0 switched it.

---

## 4. Remote-only analysis (org repos with no local clone)

Use `gh api repos/<owner>/<repo>/branches --paginate` + PR lookups per branch.
Classify with signals 1 and metadata only (no ancestry/cherry without a clone).
Output is report-only: verdicts limited to MERGED-PR / IN_FLIGHT / ABANDONED? /
UNKNOWN, and any deletions go in the Manual Actions block as
`gh api -X DELETE ...` is NOT offered — suggest `git push origin --delete` from
a future clone, or the GitHub UI's branches page.

---

## 5. Failure modes & recovery

- Deleted local branches are reflog-recoverable for ~30 days:
  `git branch <name> <sha>` using the SHA from the log file.
- `gh` rate limits on `--all`: batch PR lookups with `--json`, and prefer one
  `gh pr list --state all --limit 200` per repo over per-branch calls.
- Detached HEAD or mid-rebase/merge state: halt classification for that repo,
  report it, continue the sweep.
