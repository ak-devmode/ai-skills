#!/usr/bin/env bash
# Snapshot every repo in the CROSS-REPO.md graph and emit /scope's `## Repo Graph` table.
#
# Approach: extract candidate repo names from CROSS-REPO.md, keep only the ones that
# resolve to a sibling checkout, then probe those in parallel. The emitted table is the
# freshness contract /plan §5.6.1 validates against later, so every SHA comes from one
# point in time rather than from a narrative walk.
#
# Portability notes, all learned the hard way on macOS bash 3.2:
#   - no `mapfile`; newline-delimited strings + IFS instead
#   - `local a=1 b=$a` expands $a before it is bound under `set -u`; split the statement
#   - background jobs started inside a `cmd | while read` run in a SUBSHELL, so the
#     parent's `wait` never sees them; iterate with `for` over an IFS-split string
#
# Usage:  repo-graph-snapshot.sh [repo-root]      # default: git toplevel of $PWD
# Output: markdown table on stdout; drift notes on stderr. Exit 3 if there is no graph.

set -uo pipefail

root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")}"
xrepo="$root/CROSS-REPO.md"
[ -f "$xrepo" ] || { echo "repo-graph-snapshot: no CROSS-REPO.md at $root" >&2; exit 3; }

group="$(dirname "$root")"          # e.g. ~/Projects/wellmed
this="$(basename "$root")"
NL='
'

probe() {                            # probe <name> -> one TSV row on stdout
  local name="$1"
  local path="$group/$name"
  local branch sha when pin dirty
  branch="$(git -C "$path" branch --show-current 2>/dev/null || echo '(detached)')"
  sha="$(git -C "$path" rev-parse --short HEAD 2>/dev/null || echo '?')"
  when="$(git -C "$path" log -1 --format=%cs 2>/dev/null || echo '?')"
  pin="$(grep -hoE '(wellmed-infrastructure|go-sdk)[^[:space:]]* v[0-9][^[:space:]]*' \
           "$path/go.mod" 2>/dev/null | head -1)"
  if [ -n "$(git -C "$path" status --porcelain 2>/dev/null | head -1)" ]; then
    dirty=yes
  else
    dirty=no
  fi
  # Trunk is PER-REPO. Read this repo's own CROSS-REPO.md first; fall back to the
  # group default (develop for wellmed/pmg, main elsewhere). Applying the primary's
  # trunk to every consumer mislabels a whole graph — kalpa-docs declares `main`
  # while every wellmed-* service it names is a `develop` repo.
  local trunk
  trunk="$(grep -oE 'trunk-branch: *[a-z0-9._/-]+' "$path/CROSS-REPO.md" 2>/dev/null \
             | head -1 | awk '{print $2}')"
  if [ -z "$trunk" ]; then
    if git -C "$path" show-ref --verify --quiet refs/remotes/origin/develop; then
      trunk=develop
    else
      trunk="$(git -C "$path" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null \
                 | sed 's|^origin/||')"
      trunk="${trunk:-main}"
    fi
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$name" "$branch" "$sha" "${pin:-—}" "$dirty" "$when" "$trunk"
}

# --- candidates -> resolved. CROSS-REPO.md prose is full of hyphenated tokens that
# look like repo names (`trunk-branch`, `max-depth-override`, `docs-only`), so
# resolving against disk before probing is what keeps the output signal.
candidates="$(grep -oE '[`"]?[a-z][a-z0-9]+(-[a-z0-9]+)+[`"]?' "$xrepo" \
                | tr -d '`"' | sort -u)"

resolved=""; missing=""
OLDIFS="$IFS"; IFS="$NL"
for n in $candidates; do
  [ -n "$n" ] || continue
  if [ -d "$group/$n/.git" ] || [ -f "$group/$n/.git" ]; then
    resolved="$resolved$n$NL"
  else
    # Report a miss only when the name looks like a real project repo, not prose.
    case "$n" in
      wellmed-*|pmg-*|kalpa-*|*-docs) missing="$missing$n$NL" ;;
    esac
  fi
done
IFS="$OLDIFS"

if [ -z "$resolved" ]; then
  echo "repo-graph-snapshot: no declared repo resolved to a checkout under $group" >&2
  exit 3
fi

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

OLDIFS="$IFS"; IFS="$NL"
for n in $resolved; do
  [ -n "$n" ] || continue
  probe "$n" > "$tmp/$n.row" &
done
IFS="$OLDIFS"
wait

echo "| Repo | Role | Trunk | Current Branch | HEAD SHA | SDK Pin | Dirty | Last commit |"
echo "|---|---|---|---|---|---|---|---|"

drift=0
for f in "$tmp"/*.row; do
  [ -s "$f" ] || continue
  IFS="$(printf '\t')" read -r name branch sha pin dirty when trunk < "$f"
  role="consumer"
  [ "$name" = "$this" ] && role="**primary**"
  printf '| %s | %s | %s | %s | %s | %s | %s | %s |\n' \
    "$name" "$role" "$trunk" "$branch" "$sha" "$pin" "$dirty" "$when"
  if [ "$name" != "$this" ] && [ "$branch" != "$trunk" ]; then
    echo "  drift: $name is on '$branch', declared trunk is '$trunk'" >&2
    drift=1
  fi
  if [ "$dirty" = yes ]; then
    echo "  drift: $name has uncommitted changes — someone may be mid-task there" >&2
    drift=1
  fi
done

# SDK-pin asymmetry across consumers is a flag, not a stop (/scope §0.5.2).
pinlist="$(cut -f1,4 "$tmp"/*.row 2>/dev/null | grep -v "$(printf '\t')—$" || true)"
pincount="$(printf '%s\n' "$pinlist" | grep -c . || true)"
distinct="$(printf '%s\n' "$pinlist" | cut -f2 | sort -u | grep -c . || true)"
if [ "${distinct:-0}" -gt 1 ]; then
  echo "  drift: SDK pins are asymmetric across $pincount repo(s):" >&2
  printf '%s\n' "$pinlist" | sed 's/^/    /' >&2
  drift=1
fi

# Declared members with no checkout: /plan §5.11 halts on these, because Pattern-First
# would otherwise return a false "no pattern found" indistinguishable from a real one.
if [ -n "$missing" ]; then
  OLDIFS="$IFS"; IFS="$NL"
  for n in $missing; do
    [ -n "$n" ] && echo "  note: '$n' named in CROSS-REPO.md, not cloned at $group/$n" >&2
  done
  IFS="$OLDIFS"
fi

echo "" >&2
[ "$drift" -eq 0 ] && echo "  no drift — every resolved repo is on its trunk and clean" >&2
echo "  snapshot taken: $(date +%F)" >&2
