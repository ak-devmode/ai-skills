# /review — ai-skills @ `43528b53b2be074a09ce3149673cfda8653419ac..ba7e393050a120decf0b11413a528ec287ebeb93` (4 commits)

**Review:** `8.1-r1` · **Reviewer:** claude-lean mode: lean (default) · **Passes:** engine ✓ (inlined) · domain n/a — generic repo · lenses ✓ · lean: 11 of 11 file(s) inlined
**mode: lean (default)**
**DEGRADED (lean: single Sonnet pass over one bundle, no specialists, diff capped at 1,500 lines):** reviewer is `claude-lean mode: lean (default)` — not the codex gate; the gate reports `⚠ judge: review claude-lean mode: lean (default)` (and the index carries it) until a codex re-review of this unit.
**Findings:** 8 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 8.1 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>")`

## BLOCKING (0)


## SHOULD FIX (5)

- **8.1-r1-01** `scripts/plans-publish.sh:67` (fail-open lenses-2) — When origin/HEAD is unset (a repo made by `git init` + `remote add`, or a detached HEAD) `trunk` is empty. The script then takes the 'off trunk' branch, prints 'committed on ... (not trunk unknown)' and exits 0 without pushing. /plan §8.5b reads exit 0 as 'continue' and as the signal that a plans-repo SHA is safe to record. So on a shared trunk the original defect (progress on one disk only) comes back with a success code. ff-local-trunk.sh handles the same condition correctly with exit 2. No test covers it. → When origin/HEAD cannot be resolved, exit 2 (or 4) with a message. Treat only a resolved trunk with a different current branch as 'off trunk'. Add a test case for unset origin/HEAD.
- **8.1-r1-02** `scripts/plans-publish.sh:67` (domain CLAUDE.md-2) — 'On trunk' is decided only by branch name. CLAUDE.md §2 makes direct commits on `main` the default for ai-skills, and its plans live inside the code repo. A /plan run for ai-skills on main would push every task commit, skill edits included, to origin/main immediately. That contradicts §8.5a (push per phase) and §8.5b's own claim that ai-skills is 'off trunk'. The rule in plan/SKILL.md that every plans-dir commit goes through this script also covers task commits that mix code and plans. → Make publish-on-trunk depend on the repo being a plans-only repo, or on an explicit flag or config. At minimum, state in §8.5b that ai-skills on main also publishes, and decide whether that is wanted.
- **8.1-r1-03** `scripts/plans-publish.sh:94` (silent-failure lenses-3) — `g push ... 2>/dev/null` discards git's reason on both attempts. The final message says 'failed twice' for any cause: auth, a protected branch, a hook rejection, a non-fast-forward. The user cannot tell a transient race from a permanent refusal. /plan is told to 'warn once and continue' on exit 4, so a permanently rejected push is easy to carry for many tasks without notice. → Capture push stderr and include its last line in the exit-4 message instead of sending it to /dev/null.
- **8.1-r1-04** `scripts/plans-publish.sh:57` (silent-failure lenses-3) — Under `set -e`, a failing `git add` (a mistyped or nonexistent path, a held index.lock from a concurrent session in the same checkout) or a failing `git commit` exits with git's own code (128 or 1). The documented contract is only 0/2/3/4, and plan §8.5b handles only those. An undefined code leaves /plan with no instruction, and there is no lock or serialization between sessions that share a checkout. The busy check covers rebase and merge state but not index.lock. → Wrap add and commit in `|| die 3` or `|| die 2` with a message. Document that any other code is a halt, or map unknown codes to 3 in §8.5b.
- **8.1-r1-05** `scripts/README.md:65` (doc-claim lenses-6) — The README exit contract says '3 conflict or repo busy -- HALT, commit kept, nothing pushed'. The busy check (plans-publish.sh lines 49-53) runs before `git commit`, so on a busy repo nothing is committed and the named paths stay uncommitted. The stash-not-reapplied exit 3 also happens after the rebase, with the commit made locally but unpushed. → Say 'commit kept' only for the conflict and stash cases. For busy, say 'nothing committed'. The same wording is in the script header (line 19).

## NOTE (3)

- **8.1-r1-06** `scripts/ff-local-trunk.sh:46` (silent-failure lenses-3) — `merge --ff-only ... 2>/dev/null` hides git's actual refusal (untracked file in the way, tracked local change, mid-merge state). The die message only guesses 'local changes in the way?'. Separately, closeout §13.6 and herdr §3 document exits 3 and 4 only. This script also exits 2 when origin/HEAD is unset, which the callers do not mention. → Keep merge's stderr and append it to the exit-3 message. Add exit 2 to the two callers' handling.
- **8.1-r1-07** `CLAUDE.md:203` (doc-claim CLAUDE.md-4) — CLAUDE.md §4 'Key files' lists every shared script, and ARCHITECTURE §1.4 enumerates them. The range adds scripts/plans-publish.sh and scripts/ff-local-trunk.sh (plus the plan, closeout and herdr version bumps) without updating either list or the §6.1 catalog table. Both files are unchanged in this range. → Add both scripts to CLAUDE.md §4 and ARCHITECTURE §1.4 now, or confirm /closeout Step 8 will do it.
- **8.1-r1-08** `plans/8-plans-trunk-sync/8-plans-trunk-sync-PROGRESS.md:10` (doc-claim lenses-6 · scaffolding) — Resume Context still says 'Phase 0 done; executing Task 1.1 / Next action: Task 1.1', while the same file records tasks 1.1-1.7 as done. A resume from this file would redo finished work. closeout-prep.md §1 also still holds unfilled `{{...}}` placeholders. → Update Resume Context to the real state (all Phase 1 tasks done; next is review/verify/closeout).

## Checked and clear

SQL & Data Safety: no SQL in range, Shell Injection: no shell=True or eval, and the shell scripts quote their variables and use argument arrays, Rebase conflict path: aborts and keeps the commit, and test case c asserts that no rebase is left open, Read-back after update: both scripts verify against origin and do not trust exit codes, Dirty comments: none found in the hunks, Tests: both new scripts ship with test files, as CLAUDE.md §6 requires; conflict, race, offline, dirty-file and linked-worktree cases are present

## Not applicable

LLM Output Trust Boundary, Enum & Value Completeness, Async/Sync Mixing, Column/Field Name Safety, Distribution & CI/CD Pipeline, Kalpa/WellMed domain groups (SATU SEHAT, FHIR, tenant isolation, table ownership)

**Verdict:** SHIP

## What this review did not cover

- adjacent code outside the diff (lenses §1: the touched files in full, their callers and callees) — a lean review reads only the diff hunks in its bundle
- Adjacent code outside the diff (lenses §1): the touched SKILL.md files in full, scripts/tests/_helpers.py's run(), claim-scope-number.sh, and the plan §2.4 exit-code contract the scripts claim to follow were not read
- Execution: the 11 plans-publish tests and 9 ff-local-trunk tests were not run, and no git behavior was confirmed against a real git version. This includes whether `fetch origin <trunk>` updates origin/<trunk> and how `rev-parse --git-path` prints in linked worktrees
- Whether ARCHITECTURE.md, CLAUDE.md or the §6.1 catalog were updated outside this range, which only the diff-excluded files could settle
- Whether /closeout Step 8 (trio sync) is expected to cover the missing CLAUDE.md and ARCHITECTURE entries
