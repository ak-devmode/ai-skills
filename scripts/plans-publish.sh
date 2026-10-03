#!/usr/bin/env bash
# Commit a /plan write to a plans repo and, when that repo is on its trunk, publish it
# to origin immediately.
#
# Approach: a plans trunk (kalpa-docs, pmg-docs, iris-docs main) is shared by every
# session on every machine. /plan used to commit per task but push per phase, so a
# phase-long window let machines diverge — on 2026-10-03 homelab2026 sat 11 ahead / 21
# behind on kalpa-docs with 153.2 progress on one disk only. So: commit ONLY the paths
# this run wrote (a sibling session's files in the same checkout never ride along),
# rebase onto origin, push, and read back that origin has HEAD. A rebase conflict is
# never auto-resolved — progress.md is the record the next resume reasons from — it
# aborts and exits 3 so /plan halts and asks. A failed push (offline, auth, a race that
# repeats) keeps the commit and exits 4; the next publish carries it.
#
# Off trunk (a feature branch or a worktree on one) it only commits: /plan §8.5a's
# push-per-phase applies there. A code repo whose trunk is itself shared (ai-skills on
# `main`) publishes too, and that push carries any code commits before it — on a trunk
# every machine writes, no commit should sit unpublished.
#
# Usage:  plans-publish.sh <plans-dir> -m <message> -- <path>...
#         paths are relative to <plans-dir>, or absolute
# Exit:   0 published (or committed off trunk) · 2 usage · 3 HALT — conflict or stash not
#         re-applied (commit kept, nothing pushed), or repo busy / add / commit failed
#         (nothing committed) · 4 not published (commit kept), warn and continue

set -euo pipefail

die() { echo "plans-publish: $2" >&2; exit "$1"; }

dir="${1:-}"; [ -n "$dir" ] && shift || die 2 "usage: plans-publish.sh <plans-dir> -m <msg> -- <path>..."
[ -d "$dir" ] || die 2 "no such dir: $dir"
msg=""
while [ $# -gt 0 ]; do
  case "$1" in
    -m) msg="${2:-}"; shift 2 || die 2 "-m needs a message" ;;
    --) shift; break ;;
    *) die 2 "unexpected argument: $1" ;;
  esac
done
[ -n "$msg" ] || die 2 "-m <message> is required"
[ $# -gt 0 ] || die 2 "no paths given — name the files this run wrote (never -A)"

repo="$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null)" || die 2 "not a git repo: $dir"
paths=()
for p in "$@"; do
  case "$p" in /*) paths+=("$p") ;; *) paths+=("$(cd "$dir" && pwd)/$p") ;; esac
done

g() { git -C "$repo" "$@"; }

# Another session mid-rebase/merge in this checkout: touching it would tangle both.
for state in rebase-merge rebase-apply MERGE_HEAD; do
  sp="$(g rev-parse --git-path "$state")"
  case "$sp" in /*) ;; *) sp="$repo/$sp" ;; esac
  [ -e "$sp" ] && die 3 "repo busy ($state in progress) — HALT, resolve that first"
done

# 1. Commit only these paths. `commit -- <paths>` leaves anything else a sibling session
#    staged where it was (a real rebase below can unstage it — content is kept).
err="$(g add -- "${paths[@]}" 2>&1)" || die 3 "git add failed, nothing committed — HALT: ${err##*$'\n'}"
if g diff --cached --quiet -- "${paths[@]}"; then
  echo "plans-publish: nothing new in the given paths" >&2
else
  err="$(g commit -q -m "$msg" -- "${paths[@]}" 2>&1)" || die 3 "git commit failed, nothing committed — HALT: ${err##*$'\n'}"
fi

trunk="$(g symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || true)"
trunk="${trunk#origin/}"
[ -n "$trunk" ] || die 4 "origin/HEAD is not set, so trunk is unknown — commit kept, NOT pushed. Fix: git -C $repo remote set-head origin -a"
branch="$(g symbolic-ref --short -q HEAD || true)"
if [ "$branch" != "$trunk" ]; then
  echo "committed on ${branch:-detached HEAD} (not trunk ${trunk:-unknown}) — push per phase, /plan §8.5a"
  exit 0
fi

# 2. Rebase onto origin — only when origin actually moved, so the common case never
#    touches the working tree. --autostash lets a sibling's uncommitted edits sit through
#    it (their content survives; their staged state does not); if they cannot be
#    re-applied, git keeps them in the stash and we halt.
sync() {
  g fetch -q origin "$trunk" || die 4 "fetch failed — commit kept locally, retried on the next publish"
  g merge-base --is-ancestor "origin/$trunk" HEAD && return 0
  local stashes_before stashes_after
  stashes_before="$(g stash list | wc -l)"
  if ! g rebase -q --autostash "origin/$trunk" >/dev/null 2>&1; then
    local conflicted
    conflicted="$(g diff --name-only --diff-filter=U | tr '\n' ' ')"
    g rebase --abort >/dev/null 2>&1 || true
    die 3 "rebase onto origin/$trunk conflicts in: ${conflicted:-<see git status>} — HALT. Local commit kept, nothing pushed."
  fi
  stashes_after="$(g stash list | wc -l)"
  [ "$stashes_after" -gt "$stashes_before" ] && die 3 "rebased, but uncommitted changes in this checkout did not re-apply — they are in stash@{0}. HALT."
  return 0
}

sync
# 3. Push; origin moving between fetch and push is a race, retried once.
if ! g push -q origin "HEAD:$trunk" >/dev/null 2>&1; then
  sync
  err="$(g push -q origin "HEAD:$trunk" 2>&1)" \
    || die 4 "push to origin/$trunk failed twice — commit kept locally, retried on the next publish. git: ${err##*$'\n'}"
fi

# 4. Read back: an exit code is not proof that origin has it.
g fetch -q origin "$trunk" || die 4 "read-back fetch failed — push not confirmed"
g merge-base --is-ancestor HEAD "origin/$trunk" || die 4 "origin/$trunk does not contain HEAD after push"
echo "published $(g rev-parse --short HEAD) to origin/$trunk"
