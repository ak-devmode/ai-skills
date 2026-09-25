#!/usr/bin/env bash
# Create a plan/scope folder and sweep its related working files into it.
#
# Approach: derive nothing — the caller passes the plans dir, the folder name and
# the slug. Create <folder>/artifacts/, move any explicitly named files, then sweep
# top-level plans-dir markdown whose name contains the slug. Never clobber: a
# destination that already exists is a refusal, not an overwrite. Every move is
# read back from the destination before the script reports success.
#
# Why this exists: /plan §2.5 and /scope §5.6–5.7 each carried their own copy of
# this mkdir/mv sweep as prose (the linter's cross-skill-duplicate hit). Two copies
# of a file-moving procedure is two chances to glob the wrong thing.
#
# Usage:  plans-folder.sh <plans-dir> <folder-name> [--slug S] [--move FILE]... [--dry-run]
#   <folder-name>  e.g. 39-cashier-settlement  or  ci-hardening
#   --slug S       sweep <plans-dir>/*S*.md (default: folder-name minus a leading N-)
#   --move FILE    also move this file (e.g. a raw ci-hardening-PLAN.md) into the folder
# Output: one line per action on stdout.
# Exit:   0 ok · 1 a move was refused or failed to land · 2 usage

set -uo pipefail

usage() { echo "usage: plans-folder.sh <plans-dir> <folder-name> [--slug S] [--move FILE]... [--dry-run]" >&2; exit 2; }
[ $# -ge 2 ] || usage
plans="$1"; name="$2"; shift 2
[ -d "$plans" ] || { echo "plans-folder: no such plans dir: $plans" >&2; exit 2; }
case "$name" in */*|"") echo "plans-folder: folder name must be a single path segment" >&2; exit 2 ;; esac

slug="$(printf '%s' "$name" | sed -E 's/^[0-9]+(\.[0-9]+)?-//')"
moves=""; dry=0
NL='
'
while [ $# -gt 0 ]; do
  case "$1" in
    --slug) [ $# -ge 2 ] || usage; slug="$2"; shift 2 ;;
    --move) [ $# -ge 2 ] || usage; moves="$moves$2$NL"; shift 2 ;;
    --dry-run) dry=1; shift ;;
    *) usage ;;
  esac
done
[ -n "$slug" ] || { echo "plans-folder: empty slug" >&2; exit 2; }

dest="$plans/$name"

if [ -d "$dest/artifacts" ]; then
  echo "exists  $dest/artifacts/"
elif [ "$dry" -eq 1 ]; then
  echo "would create $dest/artifacts/"
else
  mkdir -p "$dest/artifacts" && echo "created $dest/artifacts/"
fi

fail=0
move_one() {                          # move_one <src>
  local src="$1" base target
  base="$(basename "$src")"
  target="$dest/$base"
  if [ -e "$target" ]; then
    echo "REFUSED $src -> $target (destination exists)" >&2; fail=1; return
  fi
  case "$done_list" in *"$NL$src$NL"*) return ;; esac     # --move'd and swept: once only
  done_list="$done_list$src$NL"
  if [ "$dry" -eq 1 ]; then echo "would move $src -> $target"; return; fi
  mv "$src" "$target" || { echo "FAILED  mv $src" >&2; fail=1; return; }
  [ -e "$target" ] || { echo "FAILED  $target not present after mv" >&2; fail=1; return; }
  echo "moved   $src -> $target"
}
done_list="$NL"

OLDIFS="$IFS"; IFS="$NL"; set -f
movelist=""; for f in $moves; do [ -n "$f" ] && movelist="$movelist$f$NL"; done
set +f; IFS="$OLDIFS"
while IFS= read -r f; do
  [ -n "$f" ] || continue
  [ -f "$f" ] || { echo "REFUSED --move $f (no such file)" >&2; fail=1; continue; }
  move_one "$f"
done <<EOF_MOVES
$movelist
EOF_MOVES

# Sweep: top level only, markdown only, never the index or the TO-DO file.
for f in "$plans"/*"$slug"*.md; do
  [ -f "$f" ] || continue
  case "$(basename "$f")" in PLANS-INDEX.md|TO-DO.md) continue ;; esac
  move_one "$f"
done

exit "$fail"
