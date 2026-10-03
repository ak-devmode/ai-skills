# Plans-repo trunk sync + local trunk fast-forward — PROGRESS

**Plan:** `plans/8-plans-trunk-sync/8-plans-trunk-sync-PLAN.md`
**Branch:** `feature/8-plans-trunk-sync` (worktree `~/.herdr/worktrees/ai-skills/feature-8-plans-trunk-sync`)

---

## Resume Context

- **Status:** Phase 0 done; executing Task 1.1.
- **Next action:** Task 1.1 — write `scripts/plans-publish.sh`.
- **Open blockers:** none.

---

## Session: 2026-10-03

### Phase 0 — ✅ DONE
- Every Input path and Related Doc resolves. Status: Ready to execute (Alex approved
  2026-10-03, "yes do it here"). Branch `feature/8-plans-trunk-sync` per the plan.
- Worked in a git worktree, not the primary checkout: skills load live from
  `~/Projects/ai-skills` via symlink, and a `/plan` run for 153.2 in another pane is
  reading `plan/SKILL.md` from it right now. Mid-edit skills would reach that session.
- Read: CLAUDE.md, ARCHITECTURE.md, CROSS-REPO.md (standalone leaf; no Pattern Sources).
- Ledger: created `closeout-prep.md`, base `ai-skills 43528b5`.
- Executed by: stamped `Alex / Claude`. Finish table rev 1 approved by Alex 2026-10-03.

### Task 1.1 — ✅ DONE — `plans-publish.sh`
- **Files:** `scripts/plans-publish.sh` (new)
- **Result:** Commits only the named paths (`git add -- p` then `git commit -- p`, so a
  sibling's staged files stay staged), then on trunk: fetch, rebase only if origin moved,
  push, one retry on rejection, read-back via `merge-base --is-ancestor`. Exit 0/2/3/4 per
  plan §2.4, plus exit 3 for a checkout another session has mid-rebase or mid-merge.
- **Issues:** `--autostash` keeps a sibling's uncommitted edits through a real rebase,
  but not their staged state. Skipping the rebase when origin has not moved makes that
  rare; recorded in §11 of the ledger.

### Task 1.2 — ✅ DONE — tests for `plans-publish.sh`
- **Files:** `scripts/tests/test_plans_publish.py` (new)
- **Result:** 11 cases, bare origin + clones A/B: (a) clean publish, (b) rebase over B's
  unrelated push, (c) conflict → 3, commit kept, nothing pushed, no rebase left open,
  (d) feature branch commits only, (e) untracked and staged sibling files untouched,
  (f) push race via a pre-push hook that makes B push first → retried, (g) unreachable
  origin → 4, (h) usage → 2, (i) an earlier unpushed commit rides the next publish,
  (j) sibling's uncommitted edit survives a rebase, (k) busy repo → 3. All pass.
- **Issues:** first run caught two defects in 1.1 — the busy check tested a repo-relative
  path from the wrong cwd, and a no-op rebase unstaged a sibling's file. Both fixed in 1.1.

### Task 1.3 — ✅ DONE — `ff-local-trunk.sh`
- **Files:** `scripts/ff-local-trunk.sh` (new)
- **Result:** Fetches, refuses (exit 3) if local trunk has commits origin lacks, then
  fast-forwards wherever trunk is checked out — primary or any linked worktree, found via
  `worktree list --porcelain` — or, if nowhere, updates the ref with
  `fetch origin trunk:trunk`, which git itself refuses unless it is a fast-forward.
  Read-back compares the ref to `origin/<trunk>`.
- **Issues:** none.

### Task 1.4 — ✅ DONE — tests for `ff-local-trunk.sh`
- **Files:** `scripts/tests/test_ff_local_trunk.py` (new)
- **Result:** 9 cases: (a) primary on trunk advanced, (b) primary on a feature branch —
  ref advanced, checkout untouched, (c) already current, (d) local trunk ahead → 3,
  unchanged, (e) untracked file in the way → 3, file intact, (f) unreachable origin → 4,
  (g) explicit `develop`, (h) trunk checked out in a linked worktree → advanced there,
  (i) usage → 2. All pass first run.
