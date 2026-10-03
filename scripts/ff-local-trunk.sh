#!/usr/bin/env bash
# Fast-forward a repo's local trunk to origin after worktree work merges — never more.
#
# Approach: a unit runs in a herdr worktree, its branch merges on GitHub, /closeout
# removes the worktree and deletes the branch — and the primary checkout's trunk is still
# where it was before the work began, so the disk Alex works from lacks what just merged.
# This closes that gap as the last step of teardown. It only ever fast-forwards: local
# trunk commits origin lacks, or a dirty file the update would overwrite, are reported
# (exit 3) and nothing changes. A local branch is a ref shared by every worktree, so the
# update goes wherever trunk is checked out — or, if nowhere, straight to the ref.
#
# Usage:  ff-local-trunk.sh <repo> [<trunk>]     trunk defaults to origin/HEAD's target
# Exit:   0 current or advanced · 2 usage · 3 not a fast-forward / blocked, nothing
#         changed, tell Alex · 4 fetch failed

set -euo pipefail

die() { echo "ff-local-trunk: $2" >&2; exit "$1"; }

repo="${1:-}"
[ -n "$repo" ] || die 2 "usage: ff-local-trunk.sh <repo> [<trunk>]"
git -C "$repo" rev-parse --git-dir >/dev/null 2>&1 || die 2 "not a git repo: $repo"
g() { git -C "$repo" "$@"; }

trunk="${2:-}"
if [ -z "$trunk" ]; then
  trunk="$(g symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  trunk="${trunk#origin/}"
  [ -n "$trunk" ] || die 2 "origin/HEAD is not set — pass the trunk explicitly"
fi

g fetch -q origin "$trunk" || die 4 "fetch of origin/$trunk failed — nothing changed"
g show-ref -q --verify "refs/heads/$trunk" || { echo "no local $trunk branch — nothing to advance"; exit 0; }

ahead="$(g rev-list --count "origin/$trunk..$trunk")"
behind="$(g rev-list --count "$trunk..origin/$trunk")"
[ "$ahead" -eq 0 ] || die 3 "local $trunk has $ahead commit(s) origin lacks (behind $behind) — not a fast-forward, nothing changed"
[ "$behind" -gt 0 ] || { echo "$trunk already current with origin"; exit 0; }

old="$(g rev-parse --short "$trunk")"
# Where is trunk checked out? `worktree list` covers the primary checkout and every linked one.
where="$(g worktree list --porcelain | awk -v ref="branch refs/heads/$trunk" '
  /^worktree / { wt = substr($0, 10) }  $0 == ref { print wt; exit }')"

if [ -n "$where" ]; then
  git -C "$where" merge -q --ff-only "origin/$trunk" 2>/dev/null \
    || die 3 "$trunk is checked out at $where and could not fast-forward (local changes in the way?) — nothing changed"
else
  where="(ref only — $trunk is not checked out)"
  g fetch -q origin "$trunk:$trunk" || die 3 "could not fast-forward the $trunk ref — nothing changed"
fi

# Read back: the ref must now equal origin's.
[ "$(g rev-parse "$trunk")" = "$(g rev-parse "origin/$trunk")" ] \
  || die 3 "$trunk does not match origin/$trunk after the update"
echo "advanced $trunk $old..$(g rev-parse --short "$trunk") ($behind commit(s)) at $where"
