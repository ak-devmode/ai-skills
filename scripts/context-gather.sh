#!/usr/bin/env bash
# Session-start context for /scope Step 0 and /prd — one fixed read-only sweep.
#
# Approach: print labelled sections an agent synthesizes from: identity (remote,
# branch, cwd), recent activity (log, diff stat), and the plans dir (active scope
# folders, live index rows, PRDs, index validation). CLAUDE.md is deliberately NOT
# printed — the harness already loads it into context, and re-reading it here was
# pure cost. PLANS-INDEX is grepped, never cat'ed (~31k tokens in WellMed; /plan §1.1).
#
# Why this exists: /scope and /prd each carried their own copy of these blocks
# (linter cross-skill-duplicate), and /prd's copy cat'ed BOTH projects' indexes whole.
#
# Usage:  context-gather.sh [repo-dir]         (default: $PWD)
# Output: `== section ==` blocks on stdout. Always exits 0 — every probe is best-effort;
#         a missing plans dir prints the resolver's exit reason instead of failing.

set -uo pipefail

dir="${1:-$PWD}"
here="$(cd "$(dirname "$0")" && pwd)"

echo "== identity =="
git -C "$dir" remote -v 2>/dev/null | head -4
echo "branch: $(git -C "$dir" branch --show-current 2>/dev/null || echo unknown)"
echo "cwd:    $dir"

echo "== recent activity =="
git -C "$dir" log --oneline -10 2>/dev/null || echo "no git history"
echo "-- diff stat (unstaged) --"
git -C "$dir" diff --stat HEAD 2>/dev/null | tail -30
echo "-- diff stat (staged) --"
git -C "$dir" diff --staged --stat 2>/dev/null | tail -20

echo "== plans =="
plans="$(cd "$dir" && "$here/resolve-plans-dir.sh" 2>&1)"; rc=$?
if [ $rc -ne 0 ]; then
  echo "plans dir unresolved (exit $rc): $plans"
  [ $rc -eq 3 ] && echo "  -> unrecognized project: ask the user where plans live"
  [ $rc -eq 4 ] && echo "  -> docs repo not cloned: stop, don't create it"
  exit 0
fi
echo "PLANS_DIR=$plans"
echo "-- active scope folders --"
ls -d "$plans"/[0-9]*-*/ 2>/dev/null | sed "s|$plans/||" || echo "none"
idx="$plans/PLANS-INDEX.md"
if [ -f "$idx" ]; then
  echo "-- index sections --"
  grep -n '^## ' "$idx"
  echo "-- live index rows (first 20) --"
  grep -nE '^\| *[0-9]+(\.[0-9]+)? .*(Ready to execute|In progress|Active|Draft)' "$idx" | cut -c1-220 | head -20
  echo "-- index validation --"
  "$here/plans-index.py" validate "$idx" 2>&1 | tail -5
else
  echo "no PLANS-INDEX.md"
fi
# PRDs live in the plans dir AND elsewhere in the docs repo (PMG: development/prds/).
docs="$(git -C "$plans" rev-parse --show-toplevel 2>/dev/null || dirname "$plans")"
echo "-- PRDs in $(basename "$docs") (excluding archive/) --"
find "$docs" -maxdepth 4 -path '*/.git' -prune -o -path '*/archive/*' -prune -o \
  -type f \( -iname '*-PRD.md' -o -iname 'prd-*.md' -o -path '*/prds/*.md' \) -print 2>/dev/null \
  | sed "s|$docs/||" | head -20
exit 0
