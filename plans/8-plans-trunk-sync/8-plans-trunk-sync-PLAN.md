# Plans-repo trunk sync — PLAN

**Version:** 0.1
**Date:** 2026-10-03
**Plan #:** 8
**Created by:** Alex
**Executed by:**
**ADR:** N/A
**Status:** Draft — awaiting Alex's go
**Branch:** feature/8-plans-trunk-sync

---

## Related Docs

- `ai-skills/plan/SKILL.md` §8.2, §8.3, §8.5, §8.7, §11.4, §11.5
- `ai-skills/scripts/claim-scope-number.sh` — the same race, solved for scope numbers only
- `ai-skills/scripts/README.md`

---

## 1. Why

1.1 **What happened (2026-10-03).** A `/plan` run for 153.2 on homelab2026 committed
progress to kalpa-docs `main` after every task but pushed only at phase boundaries. Over
the same hours, MBA sessions closed 153.1 and pushed to the same `main`, touching the
same `plans/153-fe-fail-loud-sweep/progress.md`. homelab2026 reached **ahead 11 /
behind 21**. Seven commits of 153.2 progress existed on one disk only, and the eventual
sync needed a hand merge.

1.2 **Root cause.** §8.5 says "commit after each task; push after each phase". That is
right for the **code repo**, where the run owns a feature branch. It is wrong for the
**plans repo** when the plans repo is on its trunk (kalpa-docs, pmg-docs, iris-docs):
that trunk is shared by every session on every machine. A phase-long gap between commit
and push is a phase-long window for divergence, and the window grows with the number of
machines (now two, target three).

1.3 **Fix.** Every plans-repo write that `/plan` commits is published immediately: commit
only the paths this run wrote, rebase onto origin, push, and read back that origin has it.
A real conflict stops the run and asks — it is never auto-resolved.

1.4 **Not in this plan:** `/scope`, `/closeout`, `/repo-cleanup` also write to plans
trunks (scope birth, archive moves). They get the same helper in a follow-up, recorded
in `plans/TO-DO.md`. The code-repo half of §8.5 is unchanged.

---

## 2. Agreed Design

2.1 **One script: `scripts/plans-publish.sh <plans-dir> -m <msg> -- <path>...`**

```
  plans-dir repo on its trunk?  --no-->  commit only, exit 0 "branch: §8.5 applies"
            | yes
            v
  git add -- <paths>  (ONLY these; never -A)
  git commit -m <msg>
  git fetch origin <trunk>
  git rebase origin/<trunk>  --conflict-->  rebase --abort, exit 3 (HALT)
            |
  git push origin HEAD:<trunk>  --rejected-->  re-fetch + rebase once, push again
            |                   --still rejected / network-->  exit 4 (WARN)
            v
  read-back: HEAD is an ancestor of origin/<trunk>  --no-->  exit 4
            |
          exit 0 "published <sha>"
```

2.2 **Trunk** = the repo's `origin/HEAD` target. "On its trunk" = the current branch name
equals it. A linked worktree on a feature branch is "not on trunk" — that is the ai-skills
case (plans live in the code repo) and needs nothing new.

2.3 **Only the listed paths are staged.** A concurrent session's untracked file in the
same checkout (seen live: `artifacts/lane-brief.md`) must never ride along in this run's
commit. Empty pathspec is a usage error (exit 2).

2.4 **Exit contract.**

| Exit | Meaning | Local state | `/plan` does |
|---|---|---|---|
| 0 | Published, read back on origin | clean | continue |
| 2 | Usage error | untouched | stop — skill bug |
| 3 | Rebase conflict | rebase aborted; this run's commit intact, unpushed | **HALT**: print the conflicting files and ask Alex |
| 4 | Push failed (network, auth, repeated race) | commit intact, unpushed | warn once, continue; the next publish retries everything unpushed |

2.5 **Why halt on conflict instead of merging.** `progress.md` is an audit log the run
reasons from (§8.6 resume). A wrong auto-merge corrupts the record the next resume
trusts. Conflicts should be rare once pushes are immediate — the window shrinks from a
phase to seconds — so asking is cheap.

2.6 **`/plan` wiring.** §8.5 splits in two:
- **8.5a Code repo** — unchanged: commit per task, push per phase.
- **8.5b Plans repo** — every commit that touches the plans dir (progress entries per
  §8.2, `closeout-prep.md` per §8.3, scope `progress.md` per §8.7/§11.5, PLANS-INDEX per
  §11.4) goes through `plans-publish.sh`. Exit 3 halts the run.

---

## 3. Phase 1 — Publish helper + `/plan` wiring

### 1.1 `plans-publish.sh`
- **Type**: AI
- **Input**: §2.1–§2.4; `claim-scope-number.sh` for house style (approach comment, stderr provenance)
- **Action**: Write the script per §2. `set -euo pipefail`; trunk from `git symbolic-ref
  refs/remotes/origin/HEAD`; one retry on a rejected push; read-back with `git merge-base
  --is-ancestor HEAD origin/<trunk>` after a fresh fetch.
- **Output**: `ai-skills/scripts/plans-publish.sh`

### 1.2 Tests
- **Type**: AI
- **Input**: `scripts/tests/_helpers.py` pattern
- **Action**: `test_plans_publish.py` against a temp bare origin and two clones (two
  "machines"). Cases: (a) clean publish → 0, on origin; (b) origin moved, no overlap →
  rebased, 0; (c) both edited the same lines of `progress.md` → 3, rebase aborted, local
  commit intact, tree clean; (d) feature branch → commit only, 0, nothing pushed;
  (e) an untracked sibling file is not committed; (f) push race — origin moves between
  fetch and push → retried, 0; (g) unreachable origin → 4, commit intact; (h) empty
  pathspec → 2.
- **Output**: `ai-skills/scripts/tests/test_plans_publish.py`

### 1.3 `/plan` SKILL.md
- **Type**: AI
- **Input**: §2.6
- **Action**: Split §8.5 into 8.5a/8.5b. In §8.2, §8.3, §8.7, §11.4, §11.5 replace "commit"
  for plans-dir writes with a `plans-publish.sh` call, including the exit-3 halt text.
  Keep the edit surgical — no other sections move.
- **Output**: `ai-skills/plan/SKILL.md`

### 1.4 Script index
- **Type**: AI
- **Action**: Add `plans-publish.sh` to `scripts/README.md` with its exit contract.
- **Output**: `ai-skills/scripts/README.md`

### 1.5 Live check on kalpa-docs
- **Type**: AI+HUMAN_REVIEW
- **Input**: the next real `/plan` run that writes to kalpa-docs
- **Action**: Confirm each progress commit lands on origin within the task (`git status
  -sb` shows no `ahead` after a task), and that the MBA's `git pull` sees it.
- **Output**: one line per observed publish in this plan's progress file

### 1.R Review
- **Type**: AI
- **Action**: `/review` on this plan's range, per `/plan` §6.8.

### 1.V Verify
- **Type**: AI
- **Action**: `/verify 8.1`.

### 🔲 CHECKPOINT: plans writes publish immediately
- [ ] Suite green, including `test_plans_publish.py`
- [ ] `plan/SKILL.md` lints clean
- [ ] One live publish observed on kalpa-docs with no `ahead` left behind

---

## 4. Risks

4.1 **Push on every task adds latency.** One fetch + push per task, ~1–3 s. Accepted —
small next to a task's runtime, and the cost of the gap was a hand merge.

4.2 **Offline machine.** Exit 4 keeps working locally and retries on the next publish, so
an offline run degrades to today's behaviour instead of blocking.

4.3 **Rebase rewrites this run's local SHAs.** Anything that recorded a plans-repo SHA
before the rebase would point at a dead commit. `/review`/`/verify` record **code-repo**
SHAs, not plans-repo ones; 1.3 checks no plans-repo SHA is persisted before publishing.

---

## 5. Closing Cleanup

- [ ] Add a `plans/TO-DO.md` item: wire `plans-publish.sh` into `/scope`, `/closeout`, `/repo-cleanup`
- [ ] Archive `plans/8-plans-trunk-sync/` → `plans/archive/8-plans-trunk-sync/` and move the index row (`plans-index.py move`)
- [ ] Update CLAUDE.md recent work
