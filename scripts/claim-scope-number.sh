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

# Scope folder numbers among `ls-tree -d --name-only` paths (one per line). Directories
# only: a file like plans/2026-10-24-notes.md is not scope 2026 (review 9.1-r1-04).
tree_nums() { grep -oE "(^|/)[0-9]+-[^/]*$" | sed -E 's#^/##; s#-.*##' || true; }

max=0
note() { [ "$2" -gt "$max" ] && { max="$2"; src="$1"; }; return 0; }
src="(none)"

# Records mode (scope 9: plans/README.md declares `**Index render:**`): the committed
# PLANS-INDEX.md can lag the records until the bot renders, so the local read is a fresh
# render, and archived rows live in archive/INDEX.md.
records=""
grep -qE '^\*\*Index render:\*\*' "$plans/README.md" 2>/dev/null && records=1

# 1. origin/main — its index, archive index and scope folders: numbers other sessions pushed.
remote_max=0
if [ -n "$repo" ] && [ -n "$rel" ]; then
  git -C "$repo" fetch --quiet origin main 2>/dev/null || true
  remote_max=$( { git -C "$repo" show "origin/main:$rel/PLANS-INDEX.md" 2>/dev/null | nums
                  git -C "$repo" show "origin/main:$rel/archive/INDEX.md" 2>/dev/null | nums
                  git -C "$repo" ls-tree -d --name-only origin/main -- "$rel/" "$rel/archive/" 2>/dev/null | tree_nums
                } | sort -n | tail -1 || true)
  remote_max="${remote_max:-0}"
fi
note "origin/main index" "$remote_max"

# 2. Local index — catches numbers claimed locally but unpushed.
local_max=0
if [ -n "$records" ]; then
  # A render that fails (a clobbered record block) must stop the claim, not read as 0:
  # an unpushed loose-PRD number would be claimed a second time (review 9.1-r1-03).
  rendered=$(python3 "$(dirname "$0")/plans-index.py" render --stdout "$plans") \
    || { echo "claim-scope-number: the local records do not render — fix them first (plans-index.py check $plans)" >&2; exit 3; }
  local_max=$(printf '%s\n' "$rendered" | nums | sort -n | tail -1 || true)
elif [ -f "$plans/PLANS-INDEX.md" ]; then
  local_max=$(nums < "$plans/PLANS-INDEX.md" | sort -n | tail -1 || true)
fi
local_max="${local_max:-0}"
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
#    A number counts only when that branch's tip has it in THIS plans dir — the scope
#    folder, or a row in its index / archive index / loose records (a branch that
#    registered the number before making the folder, review 9.1-r1-05): ai-skills'
#    `docs/171-tooling-todos` was kalpa-docs scope 171's tooling branch, and claimed 172
#    for ai-skills scope 9. A repo hosts more than one graph's branch names; only this
#    graph's own files say whose number it is.
branch_max=0
if [ -n "$repo" ] && [ -n "$rel" ]; then
  while read -r ref n; do
    case "$n" in ''|*[!0-9]*) continue ;; esac
    [ "$n" -gt "$branch_max" ] || continue
    { git -C "$repo" ls-tree -d --name-only "$ref" -- "$rel/" "$rel/archive/" 2>/dev/null | tree_nums
      for f in PLANS-INDEX.md archive/INDEX.md index-loose.md; do
        git -C "$repo" show "$ref:$rel/$f" 2>/dev/null | nums || true  # absent file: pipefail
      done
    } | grep -x "$n" >/dev/null && branch_max="$n"  # no -q: an early exit SIGPIPEs the writers under pipefail
  done <<EOF
$(git -C "$repo" for-each-ref --format='%(refname:short)' refs/heads refs/remotes 2>/dev/null \
    | while read -r ref; do
        printf '%s\n' "$ref" | grep -oE '(scope[-/]|/)[0-9]+' | grep -oE '[0-9]+' \
          | sed "s#^#$ref #" || true
      done)
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
