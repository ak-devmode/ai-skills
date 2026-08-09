#!/usr/bin/env bash
# Claim the next scope number, defensively against concurrent sessions.
#
# Approach: the highest number is not knowable from one source. A local
# PLANS-INDEX.md misses numbers another session pushed; origin/main misses
# numbers claimed locally but not yet pushed; both miss a number that exists
# only as a folder or a branch name. So take the max across FOUR sources and
# increment. This is still not atomic — nothing short of a server write is —
# but it closes every gap that has actually bitten.
#
# Why this exists: /scope §5.2 said "read PLANS-INDEX.md, find the highest,
# increment" against the LOCAL working tree, while /plan §12.4 already knew to
# read origin/main "since concurrent sessions race for scope numbers." The two
# skills disagreed and the one that mints numbers was the wrong one. Scope 110
# collided and had to be renumbered 111.
#
# Usage:  claim-scope-number.sh <plans-dir>
# Output: the claimed integer on stdout; provenance on stderr.

set -euo pipefail

plans="${1:?usage: claim-scope-number.sh <plans-dir>}"
[ -d "$plans" ] || { echo "claim-scope-number: no such dir: $plans" >&2; exit 2; }

repo="$(git -C "$plans" rev-parse --show-toplevel 2>/dev/null || true)"
rel=""
[ -n "$repo" ] && rel="${plans#"$repo"/}"

# Collect whole numbers only. Sub-numbers (39.2) are phases of a scope, never
# scopes; a leading-anchored match on "| N " or "N-slug/" avoids catching them.
nums() { grep -oE '^\|[[:space:]]*[0-9]+[[:space:]]*\|' 2>/dev/null | grep -oE '[0-9]+' || true; }

max=0
note() { [ "$2" -gt "$max" ] && { max="$2"; src="$1"; }; return 0; }
src="(none)"

# 1. origin/main's index — catches numbers other sessions pushed.
remote_max=0
if [ -n "$repo" ] && [ -n "$rel" ]; then
  git -C "$repo" fetch --quiet origin main 2>/dev/null || true
  remote_max=$(git -C "$repo" show "origin/main:$rel/PLANS-INDEX.md" 2>/dev/null \
                 | nums | sort -n | tail -1 || true)
  remote_max="${remote_max:-0}"
fi
note "origin/main index" "$remote_max"

# 2. Local index — catches numbers claimed locally but unpushed.
local_max=0
if [ -f "$plans/PLANS-INDEX.md" ]; then
  local_max=$(nums < "$plans/PLANS-INDEX.md" | sort -n | tail -1 || true)
  local_max="${local_max:-0}"
fi
note "local index" "$local_max"

# 3. Folders on disk — catches a scope folder created before its index row
#    (and the reverse of the 2026-08 leak, where rows existed with no table).
folder_max=0
for d in "$plans"/[0-9]*-*/ "$plans"/archive/[0-9]*-*/ "$plans"/*-program/archive/[0-9]*-*/; do
  [ -d "$d" ] || continue
  n="$(basename "$d")"; n="${n%%-*}"
  case "$n" in ''|*[!0-9]*) continue ;; esac
  [ "$n" -gt "$folder_max" ] && folder_max="$n"
done
note "scope folders" "$folder_max"

# 4. Branch names across all remotes — catches a number claimed in a branch
#    whose index row has not landed. Matches scope-NNN / scope/NNN / NNN-slug.
branch_max=0
if [ -n "$repo" ]; then
  while read -r n; do
    case "$n" in ''|*[!0-9]*) continue ;; esac
    [ "$n" -gt "$branch_max" ] && branch_max="$n"
  done <<EOF
$(git -C "$repo" for-each-ref --format='%(refname:short)' refs/heads refs/remotes 2>/dev/null \
    | grep -oE '(scope[-/]|/)[0-9]+' | grep -oE '[0-9]+' || true)
EOF
fi
note "branch names" "$branch_max"

claimed=$((max + 1))

{
  echo "claim-scope-number: claiming $claimed (highest seen: $max, from $src)"
  printf '  %-20s %s\n' "origin/main index" "$remote_max" \
                        "local index"       "$local_max" \
                        "scope folders"     "$folder_max" \
                        "branch names"      "$branch_max"
  if [ "$remote_max" -ne "$local_max" ]; then
    echo "  ! local and origin/main disagree — another session has pushed or you have"
    echo "    unpushed index changes. $claimed is safe against both."
  fi
} >&2

printf '%s\n' "$claimed"
