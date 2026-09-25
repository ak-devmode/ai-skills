#!/usr/bin/env bash
# herdr pane identity + helper split — the `herdr` skill §2/§5 rules as one call.
#
# Approach: the naming rule needs TWO herdr calls to take effect (pane rename AND
# report-metadata --display-agent — without the metadata the sidebar shows the
# workspace label for every agent), and forgetting the second is the recurring
# miss. `name` does both and reads the pane back. `helper` is the one sanctioned
# helper-pane geometry: split your OWN pane right at half size, no focus steal.
#
# Usage:
#   herdr-pane.sh name <pane-id> <task> <seat> [--source SKILL]   (default source: concurrency)
#   herdr-pane.sh helper [--cwd DIR]                               (prints the new pane id)
# Exit: 0 ok · 1 herdr call failed or label did not land · 2 usage · 3 not inside herdr / no server

set -uo pipefail

usage() { sed -n '9,12p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }
command -v herdr >/dev/null || { echo "herdr-pane: herdr not installed" >&2; exit 3; }
herdr workspace list >/dev/null 2>&1 || { echo "herdr-pane: herdr server not answering — report and stop (never start it mid-skill)" >&2; exit 3; }

cmd="${1:-}"; shift || true
case "$cmd" in
  name)
    [ $# -ge 3 ] || usage
    pane="$1"; task="$2"; seat="$3"; shift 3; source=concurrency
    [ "${1:-}" = "--source" ] && source="${2:?--source needs a value}"
    label="$task @$seat"
    herdr pane rename "$pane" "$label" >/dev/null || { echo "herdr-pane: rename failed for $pane" >&2; exit 1; }
    herdr pane report-metadata "$pane" --source "$source" --display-agent "$label" >/dev/null \
      || { echo "herdr-pane: report-metadata failed for $pane" >&2; exit 1; }
    herdr pane get "$pane" 2>/dev/null | grep -qF "$label" \
      || { echo "herdr-pane: label '$label' not visible on $pane after rename" >&2; exit 1; }
    echo "named $pane: $label (source $source)"
    ;;
  helper)
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
