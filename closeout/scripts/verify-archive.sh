#!/usr/bin/env bash
# verify-archive.sh — the deterministic completion gate for /closeout.
#
# Approach: /closeout's final step is "the scope is archived." Prose in a SKILL.md
# is advisory — an agent can believe it archived and be wrong, or halt early and
# never reach the step at all. Both happened (scopes 57 and 99, 2026-07). So the
# gate is a script that ASSERTS the end state and exits non-zero when it is not
# met. /closeout must run this last and MUST NOT report success if it fails.
#
# Checks, in order:
#   1. the live scope folder no longer sits outside archive/
#   2. the archived folder exists at archive/<N>-<slug>/ (or a program archive)
#   3. the PLANS-INDEX row for <N> reads as done AND points into archive/
#   4. no closeout-prep.md is left behind outside archive/
#
# Usage: verify-archive.sh <plans-dir> <scope-number>
#   e.g. verify-archive.sh ~/Projects/wellmed/kalpa-docs/plans 57
# Exit: 0 = archived and consistent · 1 = not complete (message says what) · 2 = bad args

set -uo pipefail

PLANS_DIR="${1:-}"
SCOPE_NUM="${2:-}"

if [ -z "$PLANS_DIR" ] || [ -z "$SCOPE_NUM" ]; then
  echo "usage: verify-archive.sh <plans-dir> <scope-number>" >&2
  exit 2
fi
if [ ! -d "$PLANS_DIR" ]; then
  echo "verify-archive: plans dir not found: $PLANS_DIR" >&2
  exit 2
fi

INDEX="$PLANS_DIR/PLANS-INDEX.md"
fail=0
note() { printf '  %s\n' "$1"; }

echo "verify-archive: scope $SCOPE_NUM in $PLANS_DIR"

# --- 1. no live scope folder outside archive/ -------------------------------
# Match <N>-<slug>/ at the plans root, and the legacy scope-<slug>/ shape.
live=""
for d in "$PLANS_DIR"/"$SCOPE_NUM"-*/ ; do
  [ -d "$d" ] && live="$live$d"$'\n'
done
if [ -n "$live" ]; then
  fail=1
  echo "NOT ARCHIVED — live scope folder still at the plans root:"
  while IFS= read -r d; do [ -n "$d" ] && note "$d"; done <<< "$live"
  note "fix: move it to $PLANS_DIR/archive/ (or the program's archive/ for a program member)"
fi

# --- 2. an archived folder exists ------------------------------------------
archived=""
for d in "$PLANS_DIR"/archive/"$SCOPE_NUM"-*/ "$PLANS_DIR"/*-program/archive/"$SCOPE_NUM"-*/ ; do
  [ -d "$d" ] && archived="$archived$d"$'\n'
done
if [ -z "$archived" ]; then
  fail=1
  echo "NOT ARCHIVED — no archive/$SCOPE_NUM-*/ folder found"
  note "expected $PLANS_DIR/archive/$SCOPE_NUM-<slug>/"
  note "or, for a program member, $PLANS_DIR/<program>/archive/$SCOPE_NUM-<slug>/"
fi

# --- 3. PLANS-INDEX row is done AND repointed ------------------------------
if [ ! -f "$INDEX" ]; then
  fail=1
  echo "NO INDEX — $INDEX not found"
else
  # The scope's own row: a table row whose first cell is exactly the scope number.
  row=$(grep -n "^|[[:space:]]*$SCOPE_NUM[[:space:]]*|" "$INDEX" | head -1)
  if [ -z "$row" ]; then
    fail=1
    echo "NO INDEX ROW — PLANS-INDEX.md has no row for scope $SCOPE_NUM"
    note "fix: add a row, or check the number is right"
  else
    lineno="${row%%:*}"
    body="${row#*:}"
    # Done marker: the tick, or an explicit Done/Archived word.
    if ! printf '%s' "$body" | grep -qi '✅\|done\|archived'; then
      fail=1
      echo "INDEX ROW NOT DONE — line $lineno still reads as active"
      note "$(printf '%s' "$body" | cut -c1-120)"
      note "fix: set the status cell to '✅ Done / archived <date>'"
    fi
    # Folder cell must point into an archive/ path, not the live folder.
    if ! printf '%s' "$body" | grep -q 'archive/'; then
      fail=1
      echo "INDEX ROW NOT REPOINTED — line $lineno does not reference an archive/ path"
      note "fix: repoint the Folder column to archive/$SCOPE_NUM-<slug>/"
    fi
    # Child plan rows (<N>.<P>) should be repointed too — warn only, not fatal.
    stale_children=$(grep -c "^|[[:space:]]*$SCOPE_NUM\.[0-9]" "$INDEX" 2>/dev/null || true)
    if [ "${stale_children:-0}" != "0" ]; then
      unrepointed=$(grep "^|[[:space:]]*$SCOPE_NUM\.[0-9]" "$INDEX" | grep -vc 'archive/' || true)
      if [ "${unrepointed:-0}" != "0" ]; then
        note "warn: $unrepointed child-plan row(s) for $SCOPE_NUM.* not repointed to archive/ (not fatal)"
      fi
    fi
  fi
fi

# --- 4. no ledger left outside archive/ ------------------------------------
for d in "$PLANS_DIR"/"$SCOPE_NUM"-*/ ; do
  if [ -f "$d/closeout-prep.md" ]; then
    fail=1
    echo "LEDGER STRANDED — $d/closeout-prep.md is outside archive/"
    note "the ledger travels with the scope; move the whole folder"
  fi
done

echo
if [ "$fail" != "0" ]; then
  echo "verify-archive: FAIL — scope $SCOPE_NUM is NOT fully archived."
  echo "/closeout MUST NOT report success. Fix the items above, then re-run this check."
  exit 1
fi

echo "verify-archive: PASS — scope $SCOPE_NUM archived, index row done + repointed."
exit 0
