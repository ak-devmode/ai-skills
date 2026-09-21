#!/usr/bin/env bash
# Thin token-bearing fetch: pull a day's Grafana alert annotations to a JSON file.
# Deliberately separate from classify.py so the classifier stays pure/offline-testable.
# Default window = previous full day (the 05:00 WITA cron's target). Override with
# FROM/TO epoch-ms env vars for backfill. Token is read from SSM, never printed.
#
# Usage: ./fetch.sh [out.json]            # yesterday
#        FROM=.. TO=.. ./fetch.sh out.json # explicit window (backfill)
set -euo pipefail

SSM_PARAM="${GRAFANA_TOKEN_SSM:-/wellmed/prod/grafana/ro-token}"
BASE="${GRAFANA_BASE:-https://dashboard.kalpahealth.com}"
OUT="${1:-september-alarms.json}"

# previous full day in ms unless FROM/TO given (macOS + GNU date compatible)
if [ -z "${FROM:-}" ]; then
  if date -v-1d >/dev/null 2>&1; then            # BSD/macOS
    FROM=$(( $(date -v-1d -v0H -v0M -v0S +%s) * 1000 ))
    TO=$((   $(date -v0H -v0M -v0S +%s) * 1000 ))
  else                                            # GNU
    FROM=$(( $(date -d 'yesterday 00:00' +%s) * 1000 ))
    TO=$((   $(date -d 'today 00:00' +%s) * 1000 ))
  fi
fi

TOKEN=$(aws ssm get-parameter --name "$SSM_PARAM" --with-decryption \
          --query Parameter.Value --output text)
curl -sS -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/annotations?type=alert&from=$FROM&to=$TO&limit=5000" | jq '.' > "$OUT"
echo "wrote $(jq length "$OUT") annotations to $OUT (from=$FROM to=$TO)"
