#!/usr/bin/env bash
# Resolve the central plans directory for the current (or given) path.
#
# Approach: map a working path to its project's docs repo. This is the single
# owner of a mapping that was previously copy-pasted as a `case` block into
# /scope, /plan, /prd, /markdown-style and /member-record-amend — five copies
# that could disagree, and did (see plans/skills-relook/AUDIT.md §6.3).
#
# Usage:  resolve-plans-dir.sh [path]         # default: $PWD
# Output: absolute plans dir on stdout, nothing else.
# Exit:   0 resolved · 3 unrecognized project · 4 resolved but dir missing

set -euo pipefail

target="${1:-$PWD}"
# Resolve to an absolute, symlink-free path so a symlinked checkout still maps.
target="$(cd "$target" 2>/dev/null && pwd -P || echo "$target")"

case "$target" in
  */Projects/pmg/*|*/Projects/pmg)             plans="$HOME/Projects/pmg/pmg-docs/plans" ;;
  */Projects/wellmed/*|*/Projects/wellmed)     plans="$HOME/Projects/wellmed/kalpa-docs/plans" ;;
  */Projects/ai-skills/*|*/Projects/ai-skills) plans="$HOME/Projects/ai-skills/plans" ;;
  *)
    echo "resolve-plans-dir: unrecognized project for '$target'" >&2
    echo "  known: ~/Projects/{pmg,wellmed,ai-skills}. Ask the user where plans live." >&2
    exit 3
    ;;
esac

if [ ! -d "$plans" ]; then
  # Never create it silently — a missing plans dir means the docs repo is absent,
  # which is a different problem from a missing folder.
  echo "resolve-plans-dir: resolved '$plans' but it does not exist." >&2
  echo "  The docs repo is probably not cloned. Do NOT create it." >&2
  exit 4
fi

printf '%s\n' "$plans"
