---
name: repo-cleanup
version: 1.3.0
description: |
  Branch hygiene and repo upkeep. Classifies all non-protected branches against the
  trunk(s) using layered signals (PR merge state, ancestry, gone-upstream, patch
  equivalence), safely prunes provably-merged local branches, emits a manual command
  block for squash-merged and remote deletions (never runs them), and runs housekeeping
  (worktree prune, stash report, parked-on-merged-branch check). Outputs a verdict
  table, a durable log with recovery SHAs, and an open-questions list.
  Default scope is the current repo. `--all <owner>` sweeps every repo in a GitHub
  org/user (see /repo-cleanup-all for the no-flags alias).
  In a **docs/plans repo** (one containing `plans/PLANS-INDEX.md`) it ALSO runs a
  plans-hygiene pass (§6): classify each active scope by completion, archive only
  the provably-complete ones (program members into their program's `archive/`),
  extract leftover TODOs, and fix PLANS-INDEX active/archived drift.
  Use when asked to "clean up branches", "prune branches", "repo cleanup",
  "branch hygiene", "which branches can I delete", "what's still in flight", or —
  in a docs repo — "archive completed scopes", "clean up the plans", "which
  scopes can I archive".
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
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
- **Docs-plans hygiene** (auto, additive): when the target repo contains
  `plans/PLANS-INDEX.md` (detected in Step 0), run §6 **in addition to** branch
  hygiene — it never replaces it. If the user's request is *only* about plans
  ("archive completed scopes", "clean up the plans"), you may run §6 alone and
  skip the branch flow. Both share the same discipline: one read-only
  classification pass → one confirmation gate → act → durable log.

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
   never checkout — but note it in the report). **Record the pre-existing dirty
   set** (`git status --porcelain` at start): any file already modified before this
   run is NOT ours — §6 must exclude it from any commit (a concurrent agent may be
   editing a scope in another context; see §6.5).
6. **Docs-plans repo detection:** if `plans/PLANS-INDEX.md` exists in the repo,
   set a flag to run §6 (Docs-plans hygiene) after the branch flow (or alone, per
   §2). If absent, skip §6 entirely.

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

### Step 2b — Content-landed check (dirty-cherry resolution)

A branch with a **merged PR but a dirty cherry** (`git cherry` shows `+` commits)
is NOT automatically SQUASHED — squash merges with conflict resolution, or later
trunk edits to the same files, change patch-ids and break signal 4. Before
bucketing, verify the content actually landed:

1. **Added-file check**: pick files the branch *added*
   (`git diff --diff-filter=A --name-only <merge-base>..<branch>`) and test they
   exist on trunk: `git cat-file -e origin/<trunk>:<path>`.
2. **Searchable-change check**: for modified files, grep trunk for a distinctive
   string the branch introduced (`git grep <token> origin/<trunk> -- <path>`).
3. **Timestamp check**: compare each `+` commit's date (`git log -1 --format=%ci`)
   against the PR's `mergedAt`. A commit *after* mergedAt was pushed post-merge
   and is genuinely unlanded work.

Outcomes:

- All `+` commits' content verified on trunk → **SQUASHED** (note "content
  verified" in the signals column).
- Any commit whose content is absent from BOTH trunks → **UNKNOWN**, with the
  orphaned commit SHA + subject named in Open Questions. Never delete a branch
  carrying an orphaned commit until the user decides (re-raise vs drop) — when
  they drop it, record the SHA in the log for recovery-until-GC.

This step exists because the dogfood run (pmg-integrations, 2026-06-04) found a
real orphaned CI fix that diff-naive logic would have silently deleted.

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
4. **The very LAST thing in the terminal summary — after everything else — must
   be a fenced block containing the exact commands the user has to run because
   the skill is permission-blocked from running them** (e.g. `git branch -D`),
   under a heading like `### Your actions (Claude is blocked from these)`.
   One command per line, nothing after the block. **NO trailing `#` comments
   on the command lines** — interactive zsh has `interactive_comments` off by
   default, so comment words get parsed as arguments, and glob chars in
   comments (e.g. `2(F)`) abort the whole line with `no matches found`.
   Put evidence in prose above the block or in the log file, never inline.
   If nothing is blocked, end with `No actions needed from you.` instead.

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

---

## 6. Docs-plans hygiene (conditional — runs when `plans/PLANS-INDEX.md` exists)

This phase does for **plan/scope docs** what §3 does for branches: classify every
active item by completion with evidence, archive only what is provably done, hand
the leftovers somewhere durable, and leave an audit trail. Runs additively after
branch hygiene, or alone if the request is plans-only (§2).

**Prime directives (docs):**

1. **Never archive on a guess.** Only move a scope whose completion is *evidenced*
   (D1). "Old" and "sitting in `plans/`" are NOT completion. Draft, parked,
   shelved, and in-progress scopes stay put.
2. **Never lose a leftover.** Every open TODO / deferred note in an archived scope
   is extracted to `TO-DO.md` first (D3) — or the scope is not archived.
3. **One classification pass, one confirmation gate, then act** (as §3).
4. **Only commit your own edits.** Stage by explicit path; exclude any file in the
   Step-0 pre-existing dirty set — a concurrent context may own it. Report excluded.

### D0 — Inventory the plans tree

Under `{repo}/plans/` (skip `archive/`), list and classify:
- **Scope folders** `<N>-<slug>/` — have a `progress.md` or `<N>-<slug>-PROGRESS.md`.
- **Standalone plans** `<N>-<slug>-PLAN.md` / `<slug>-PLAN.md`.
- **Program folders** `<slug>-program/` — have a `<slug>-brief.md`; they own their
  OWN `archive/`, and their live members are flat `<N>-<slug>/` folders elsewhere.
- **Loose `.md`** — classify by content (D0.1); do NOT assume every loose file is a plan.

D0.1 **Loose-file taxonomy** (mis-archiving a reference doc is a bug):
- **Plan** (`*-PLAN.md`) → archive candidate.
- **Reference / vision doc** (describes a *system*, not a unit of work; no PLAN
  suffix; e.g. `manifest-complete-flow.md`) → **NEVER archive**; living reference.
- **Operational queue / log** (a generated run-list, e.g. a bulk-send queue) →
  archivable once its run is consumed.
- **Registry** (`PLANS-INDEX.md`, `TO-DO.md`) → never archived; these get edited.

### D1 — Read the authoritative status

For each active-tree item, gather completion signals, priority order:

| # | signal | where | reading |
|---|--------|-------|---------|
| 1 | PLANS-INDEX status/desc | the item's row | "Done (date)"/"Shipped"/"Live in prod" = strong done; "Draft"/"Ready"/"Active"/"PARKED"/"SHELVED"/"HOLD" = NOT done |
| 2 | progress phase checkboxes | `progress.md` OR `<N>-<slug>-PROGRESS.md` — **glob BOTH, naming is non-uniform** | all phases done = done; any Draft/Pending/⏳ = not |
| 3 | closeout-prep status | `closeout-prep.md` if present | **WEAK** — `Status: in-progress` is common even on shipped scopes; presence ≠ done |
| + | leftover scan | unchecked `[ ]`, "deferred/remaining/gated/parked" notes | must be captured (D3) before archiving |

Signals 1+2 are authoritative; 3 is a tiebreaker only.

### D2 — Classify

| verdict | criteria | action |
|---------|----------|--------|
| ARCHIVE | signals 1+2 agree done/shipped/live AND leftovers are capturable | D3 → D4 |
| KEEP_ACTIVE | any phase draft/ready/in-progress/not-started | leave; report status |
| PARKED | explicit PARKED / HOLD / SHELVED | leave; report — **never archive** |
| GATED | shipped but a cleanup / observation-window / operator-cutover step still pending | Open Questions — confirm before archiving |
| UNCLEAR | signals conflict, or a standalone plan with no completion record | Open Questions — ask, never guess |

Render one verdict table `| item | type | verdict | evidence |`. Every verdict must
be explainable from its evidence column — no bare verdicts (mirror §3.3).

### D3 — Extract leftovers to TO-DO.md (before any move)

For each ARCHIVE item:
- Scan its progress/plan for open `[ ]` + deferred/parked notes.
- **Check whether `TO-DO.md` ALREADY has a `## … (Scope N / Plan N)` section** —
  extraction is often incremental. If so, verify coverage; do NOT duplicate.
- Else append `## {Title} (Scope N) — follow-ups` + the open items + a `Source:` line.
- Distinguish **scope-end deliverables that live in THIS repo** (e.g. an ADR the
  scope deferred to `adrs/`) — offer to complete those before archiving, rather
  than parking them; code-repo deliverables stay as TODOs.

### D4 — Archive to the RIGHT location + update the index

1. **git mv to the correct archive:**
   - **Standalone scope / plan** → `plans/archive/<N>-<slug>/` (keep the numeric
     prefix on newer scopes; retain the original name).
   - **Program member** (the scope is listed in some
     `plans/<slug>-program/<slug>-brief.md`) → `plans/<slug>-program/archive/<N>-<slug>/`,
     **NOT** the repo-wide archive (ADR-002 §2.3.4 / ADR-029 — mirrors /scope §7.1
     + /closeout). Also flip that member's row in `<slug>-brief.md` to **Archived**
     + the new path.
   - Use `git mv` (history preserved as a rename).
2. **Fix stale `Source:` pointers** in `TO-DO.md`: any line pointing at the pre-move
   path → repoint to the new `archive/…` path (a moved scope leaves danglers).
3. **PLANS-INDEX.md:** move the item's row(s) (scope + all child phase rows) from
   the "Active / In Progress" table to "Archived (Complete)". The Archived table has
   **fewer columns** (no Status/Project) — strip them, fold the outcome ("Done
   {date}") into the Description, set Location to the `archive/…` path.
4. **Index-hygiene sub-check:** scan the Active table for rows whose Location is
   ALREADY `archive/…` (done + physically archived but stranded in Active) → move
   those to the Archived table too. Then verify: no duplicate row IDs, no empty
   rows, Active holds only genuinely-live items.

### D5 — Confirmation gate, act, log

1. Present in ONE gate: the D2 verdict table + proposed moves + leftover
   extractions + the Open-Questions list (GATED/UNCLEAR). Use **numbered inline
   questions**, not AskUserQuestion, for the docs pass. Nothing moves until the user
   picks the archive set.
2. On approval, do D3→D4 for the confirmed set.
3. **Commit only your own edits.** `git add` the specific paths you changed + the
   renames — NEVER `git add -A` / `commit -a`. Exclude every path in the Step-0
   pre-existing dirty set and report them ("left uncommitted — modified by another
   context"). Verify the branch first (docs repos like `pmg-docs` commit direct to
   `main` — confirm the repo's convention) and **ask before committing** (respect
   commit-gating).
4. Log to the §1.4 destination (same file as branch hygiene): verdict table,
   what was archived + where, leftovers extracted, index-hygiene fixes, Open Questions.

### D6 — This phase must NEVER

- Archive a PARKED / SHELVED / HOLD / in-progress / not-started scope.
- Archive a reference/vision doc (D0.1) or a registry file.
- Archive a program member into the repo-wide `archive/` (goes to the program's own).
- Duplicate a `TO-DO.md` section that already exists.
- Commit a file it did not itself edit (the concurrent-context exclusion).
