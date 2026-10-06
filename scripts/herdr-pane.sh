#!/usr/bin/env bash
# herdr pane identity + helper split — the `herdr` skill §2/§5 rules as one call.
#
# Approach: the naming rule needs TWO herdr calls to take effect (pane rename AND
# report-metadata --display-agent), and forgetting the second is the recurring
# miss. The name is the task only (`herdr` §2): the sidebar's row 2 already shows
# the model + account, so a seat suffix only costs row-1 width. `name` does both and reads the pane back. `helper` is the one sanctioned
# helper-pane geometry: split your OWN pane right at half size, no focus steal.
#
# Usage:
#   herdr-pane.sh name <pane-id> <name> [--source SKILL] [--machine HOST]
#                      (a legacy third <seat> argument is accepted and ignored)
#                      (default source: concurrency; --machine: a pane on a saved herdr
#                       machine, e.g. homelab2026 — pane ids are per server)
#   herdr-pane.sh helper [--cwd DIR]                               (prints the new pane id)
# Exit: 0 ok · 1 herdr call failed or label did not land · 2 usage · 3 not inside herdr / no server

set -uo pipefail

usage() { sed -n '10,16p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }
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
  *) usage ;;
esac
