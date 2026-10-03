# Verify report — unit 8.1

**mode: lean (default)**

**Run:** `8.1-20261003T081128-05be` · **Judge:** claude-lean mode: lean (default) · **Table revision:** 1
**Gate:** PASS (8.1, 0 block(s), 0 not judged, mode advisory) · ⚠ judge: claude-lean mode: lean (default) ⚠ judge: review claude-lean mode: lean (default)

## 1. Checks

| Check | Result | Rung | Reason |
|---|---|---|---|
| p1-names-resolve | pass | 4/4 | runner: exit 0; judge concurs |
| p1-no-overbuild | pass | 2/2 | judge: Two flat bash scripts, two test files and surgical SKILL.md edits. There is no registry, plugin layer, config system or parallel implementation of an existing pattern. The extras are small guards against concrete failure modes, each with a test: the busy-repo check (test k), --autostash plus the stash check (test j), the unset origin/HEAD exit (test l), and trunk-checked-out-in-a-linked-worktree handling in ff-local-trunk.sh (test h). None adds a new abstraction layer. |
| p1-scope-deliverables | pass | 2/2 | judge: Read from the inlined diff. Paths-only staging: plans-publish.sh runs `git add -- paths` then `git commit -- paths` (never -A); test e checks the commit holds only progress.md and that an untracked and a staged sibling file stay put. Halt on conflict: a failed rebase runs `rebase --abort` and exits 3, and test c asserts exit 3, the local commit kept, origin unchanged, and no rebase-merge dir left. Read-back: after push the script re-fetches and requires `merge-base --is-ancestor HEAD origin/<trunk>` or exits 4. Exit 2 for empty pathspec, exit 4 for push or fetch failure, and a feature branch committing only all match plan 2.4. ff-local-trunk.sh matches 2.6: it refuses with exit 3 when local trunk is ahead, uses merge --ff-only, falls back to `fetch origin trunk:trunk`, and reads back against origin. /plan 8.5a/8.5b, closeout 13.6, herdr teardown and README are wired. One deviation from the plan is not recorded as a decision (see findings): plan 2.2 puts ai-skills on a feature branch 'off trunk', but the script and 8.5b now also publish when ai-skills sits on main. |
| p1-skills-lint | pass | 4/4 | runner: exit 0; judge concurs |
| p1-tests-green | pass | 4/4 | runner: exit 0; judge concurs |

## 2. Findings

- **medium** · conformance · `p1-scope-deliverables` · scripts/plans-publish.sh:1145; plan/SKILL.md 8.5b; plan PLAN 2.2 — Plan 2.2 says ai-skills (plans in the code repo, feature branch) is 'off trunk' and needs nothing new. The shipped script decides 'on trunk' by branch name only, so a /plan run on ai-skills `main` also rebases and pushes every plans-dir commit, carrying code commits with it. 8.5b and the script header now state this, but the progress file has no Decisions Log or '#### Unplanned:' entry for it. It appears only in Resume Context as an open design call for Alex (review finding 02 was filed 'fixed' by documenting it, not by changing behavior). Alex should confirm or reverse it and log it as a decision.
- **low** · conformance · `p1-scope-deliverables` · plans/8-plans-trunk-sync/8-plans-trunk-sync-PROGRESS.md — Behaviors beyond plan 2.4 are not logged as '#### Unplanned:' or Decision entries: exit 3 for a busy repo (rebase or merge in progress), exit 3 for an un-reapplied autostash, exit 3 for a failed add or commit, exit 4 for unset origin/HEAD, and the ff-local-trunk worktree lookup. They are described in task Result lines and the README, so the information exists, but not under the headings /plan 8.10 reads.
- **low** · evidence · `p1-tests-green` · verdict log: runner records p1-names-resolve and p1-tests-green — Both runner records show dirty=true at sha 5a4b72d, so the working tree had uncommitted changes (likely the verdict log or progress files) when the suite ran. Nothing suggests script or test sources were dirty, but the record cannot prove it.
- **low** · rejection-audit · `p1-scope-deliverables` · plans/8-plans-trunk-sync/artifacts/review-8.1.jsonl — There are 0 rejections and all 8 findings are 'fixed'. I checked each fix against the diff: 01 (exit 4 and test l), 03 (push stderr in the message, test n), 04 (add and commit wrapped in die 3, test m), 05 (README and header wording split), 06 (merge stderr in the ff message), 07 (CLAUDE.md and ARCHITECTURE lines present) and 08 (Resume Context updated) all hold. 02 is 'fixed' only by documenting the behavior, which is honest but leaves the design call open (see the medium finding).

## 3. Lever candidates

Recorded, not built: a lever is built on the second sighting (verify-contracts.md §4.9).
None.

## 4. Feature map

`n/a`

## 5. Gate blocks

None.
