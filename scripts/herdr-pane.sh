#!/usr/bin/env bash
# herdr pane identity + helper split — the `herdr` skill §2/§5 rules as one call.
#
# Approach: the naming rule needs TWO herdr calls to take effect (pane rename AND
# report-metadata --display-agent), and forgetting the second is the recurring
# miss. The name is the task only (`herdr` §2): the sidebar's row 2 already shows
# the model + account, so a seat suffix only costs row-1 width. `name` does both and reads the pane back. `helper` is the one sanctioned
# helper-pane geometry: split your OWN pane right at half size, no focus steal. `grid` builds
# the `herdr` §5 lanes tab: a new tab of six equal panes, columns first then rows (splitting a1
# down before cutting the columns gives a2 the full width — hit 2026-11-15), and prints the six
# pane ids in slot order a1..a6 (a1/a2 left, a3/a4 middle, a5/a6 right).
#
# Usage:
#   herdr-pane.sh name <pane-id> <name> [--source SKILL] [--machine HOST]
#                      (a legacy third <seat> argument is accepted and ignored)
#                      (default source: concurrency; --machine: a pane on a saved herdr
#                       machine, e.g. homelab2026 — pane ids are per server)
#   herdr-pane.sh helper [--cwd DIR]                               (prints the new pane id)
#   herdr-pane.sh grid <tab-label> [--workspace ID] [--cwd DIR] [--machine HOST]
#                      (prints "a1 a2 a3 a4 a5 a6"; --workspace defaults to $HERDR_WORKSPACE_ID)
# Exit: 0 ok · 1 herdr call failed or label did not land · 2 usage · 3 not inside herdr / no server

set -uo pipefail

usage() { sed -n '13,22p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }
command -v herdr >/dev/null || { echo "herdr-pane: herdr not installed" >&2; exit 3; }

cmd="${1:-}"; shift || true
H=(herdr)
case "$cmd" in
  name)
    [ $# -ge 2 ] || usage
    pane="$1"; label="$2"; shift 2; source=concurrency
    case "${1:-}" in --*|"") ;; *) shift ;; esac   # legacy <seat> positional
    while [ $# -gt 0 ]; do
      case "$1" in
        --source)  source="${2:?--source needs a value}"; shift 2 ;;
        --machine) H=(herdr --machine "${2:?--machine needs a value}"); shift 2 ;;
        *) usage ;;
      esac
    done
    "${H[@]}" workspace list >/dev/null 2>&1 \
      || { echo "herdr-pane: ${H[*]} server not answering — report and stop (never start it mid-skill)" >&2; exit 3; }
    "${H[@]}" pane rename "$pane" "$label" >/dev/null || { echo "herdr-pane: rename failed for $pane" >&2; exit 1; }
    "${H[@]}" pane report-metadata "$pane" --source "$source" --display-agent "$label" >/dev/null \
      || { echo "herdr-pane: report-metadata failed for $pane" >&2; exit 1; }
    "${H[@]}" pane get "$pane" 2>/dev/null | grep -qF "$label" \
      || { echo "herdr-pane: label '$label' not visible on $pane after rename" >&2; exit 1; }
    echo "named $pane: $label (source $source${H[2]:+, machine ${H[2]}})"
    ;;
  helper)
    herdr workspace list >/dev/null 2>&1 || { echo "herdr-pane: herdr server not answering — report and stop (never start it mid-skill)" >&2; exit 3; }
    [ "${HERDR_ENV:-}" = 1 ] || { echo "herdr-pane: helper must run inside a herdr pane" >&2; exit 3; }
    cwd="$PWD"; [ "${1:-}" = "--cwd" ] && cwd="${2:?--cwd needs a dir}"
    out="$(herdr pane split --current --direction right --ratio 0.5 --cwd "$cwd" --no-focus 2>&1)" \
      || { echo "herdr-pane: split failed: $out" >&2; exit 1; }
    id="$(printf '%s' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); r=d.get("result",d); p=r.get("pane",r); print(p.get("pane_id") or p.get("id") or "")' 2>/dev/null)"
    [ -n "$id" ] || { echo "herdr-pane: split returned no pane id: $out" >&2; exit 1; }
    echo "$id"
    ;;
  grid)
    [ $# -ge 1 ] || usage
    label="$1"; shift; ws="${HERDR_WORKSPACE_ID:-}"; cwd="$PWD"
    while [ $# -gt 0 ]; do
      case "$1" in
        --workspace) ws="${2:?--workspace needs an id}"; shift 2 ;;
        --cwd)       cwd="${2:?--cwd needs a dir}"; shift 2 ;;
        --machine)   H=(herdr --machine "${2:?--machine needs a value}"); shift 2 ;;
        *) usage ;;
      esac
    done
    [ -n "$ws" ] || { echo "herdr-pane: grid needs --workspace (no \$HERDR_WORKSPACE_ID here)" >&2; exit 2; }
    "${H[@]}" workspace list >/dev/null 2>&1 \
      || { echo "herdr-pane: ${H[*]} server not answering — report and stop (never start it mid-skill)" >&2; exit 3; }
    pid() { python3 -c 'import json,sys; d=json.load(sys.stdin)["result"]; print((d.get("root_pane") or d.get("pane"))["pane_id"])' 2>/dev/null; }
    split() {  # $1 pane, $2 direction, $3 ratio -> new pane id
      local out id
      out="$("${H[@]}" pane split "$1" --direction "$2" --ratio "$3" --cwd "$cwd" --no-focus 2>&1)" || { echo "herdr-pane: split $2 of $1 failed: $out" >&2; return 1; }
      id="$(printf '%s' "$out" | pid)"; [ -n "$id" ] || { echo "herdr-pane: split returned no pane id: $out" >&2; return 1; }
      echo "$id"
    }
    a1="$("${H[@]}" tab create --workspace "$ws" --cwd "$cwd" --label "$label" --no-focus | pid)" \
      && [ -n "$a1" ] || { echo "herdr-pane: tab create failed in $ws" >&2; exit 1; }
    a3="$(split "$a1" right 0.333)" || exit 1      # columns first: a1 keeps 1/3
    a5="$(split "$a3" right 0.5)"   || exit 1      # a3 keeps half of the remaining 2/3
    a2="$(split "$a1" down 0.5)"    || exit 1      # then halve each column
    a4="$(split "$a3" down 0.5)"    || exit 1
    a6="$(split "$a5" down 0.5)"    || exit 1
    echo "$a1 $a2 $a3 $a4 $a5 $a6"
    ;;
  *) usage ;;
esac
