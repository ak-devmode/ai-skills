# Plans-repo trunk sync + local trunk fast-forward — PROGRESS

**Plan:** `plans/8-plans-trunk-sync/8-plans-trunk-sync-PLAN.md`
**Branch:** `feature/8-plans-trunk-sync` (worktree `~/.herdr/worktrees/ai-skills/feature-8-plans-trunk-sync`)

---

## Resume Context

- **Status:** Phase 1 tasks 1.1–1.7, 1.R and 1.V done. Review r1 accepted by Alex; verify
  PASS (lean judge, advisory gate).
- **Next action:** fast-forward ai-skills `main` to this branch and push; then Task 1.8 —
  observe the next real kalpa-docs `/plan` run publish with no `ahead` left behind.
- **Open blockers:** none.

## Decisions

| Date | Decision | By |
|---|---|---|
| 2026-10-03 | ai-skills `main` is a shared trunk and publishes per task, like the docs repos (plan §2.2 had placed ai-skills off trunk; review 8.1-r1-02 surfaced it) | Alex |
| 2026-10-03 | Guards added beyond plan §2.4 — busy repo, stash not re-applied, failed add/commit (exit 3), unset origin/HEAD (exit 4) — came from tests and review r1, each with a test | Alex (review accept) |

## Artifacts

- `artifacts/review-8.1-r1.md` — lean review round 1 (DEGRADED: single Sonnet pass)
- `artifacts/verify-8.1-report.md` — verify PASS, lean judge (DEGRADED: not codex)

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

### Task 1.5 — ✅ DONE — `/plan` SKILL.md
- **Files:** `plan/SKILL.md` (3.11.0 → 3.12.0)
- **Result:** §8.5 split: 8.5a code repo (push per phase, unchanged), 8.5b plans repo —
  every plans-dir commit goes through `plans-publish.sh`, exit-code handling inline, a
  "record a plans-repo SHA only after publish returns 0" rule (plan risk 4.3), and the
  2026-10-03 incident as the why. One-line pointers to 8.5b in §8.2, §8.3, §8.7, §11.4
  (folder move + row in one publish), §11.5. Lint: 0 issues.

### Task 1.6 — ✅ DONE — `/closeout` + `herdr` teardown
- **Files:** `closeout/SKILL.md` §13.6 (1.4.0 → 1.5.0), `herdr/SKILL.md` §3 Teardown (0.1.5 → 0.1.6)
- **Result:** both teardowns end with `ff-local-trunk.sh <primary-repo>`; exit 3/4 are
  reported, never forced. Lint: 0 issues.

### Task 1.7 — ✅ DONE — script index
- **Files:** `scripts/README.md`
- **Result:** both scripts in the table (what each replaces, callers) and in Contracts
  (usage + exit codes).

### Task 1.R — round 1 — 8 findings, all fixed
- **Review:** `8.1-r1`, lean (`mode: lean (default)`; `AI_SKILLS_REVIEW_MODE` unset on this
  box), verdict SHIP, 0 blocking · 5 should-fix · 3 note.
- **Fixed:** 01 unset origin/HEAD now exit 4, not a silent 0 · 02 ai-skills `main`
  publishes too, stated in the script header and §8.5b (design call flagged for Alex) ·
  03/06 push and ff-merge failures carry git's message · 04 add/commit failures map to
  exit 3 · 05 exit-3 wording split (commit kept vs nothing committed) · 07 both scripts in
  CLAUDE.md §4 and ARCHITECTURE §1.4 · 08 this Resume Context.
- **Tests:** +3 (l unset origin/HEAD, m failed add, n rejected push says why) and a
  message assertion on ff case e. 23/23 in the two files.

### Task 1.V — ✅ DONE — `/verify 8.1`
- **Run:** `8.1-20261003T081128-05be`, lean judge. names-resolve, tests-green, skills-lint
  pass at rung 4; scope-deliverables, no-overbuild pass at rung 2. Gate: PASS, advisory,
  marker `⚠ judge: claude-lean` (review and verify both lean).
- **Judge notes acted on:** recorded the ai-skills-main decision and the review-driven
  guards in Decisions above.

#### Unplanned: publish wired into `/scope`, `/repo-cleanup`, `/closeout` (2026-10-03)
- **Files modified:** `scope/SKILL.md` (3.11.0: publish after 5.8 to reserve the number on
  origin, 5.10.2 stubs + table, §7.2 archive move as one publish, §8.3 explicit paths),
  `repo-cleanup/SKILL.md` (1.4.0: §6 commit via publish after the yes),
  `closeout/SKILL.md` (1.6.0: summary's commit line names the publish command),
  `scripts/plans-publish.sh` + `scripts/tests/test_plans_publish.py` (case o).
- **Why:** the follow-up plan §1.6 deferred; Alex approved it as direct small edits. The new
  archive-move test caught a real defect: after `git mv`, the old folder is in neither the
  tree nor the index, so `git add` failed. Paths that exist only in HEAD now skip the add
  and are still named to the commit. The closing TO-DO item for this follow-up is
  therefore not needed.
