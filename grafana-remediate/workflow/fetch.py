#!/usr/bin/env python3
# Stdlib Grafana fetch for the CLOUD routine (scope 146, Phase 4, path B).
#
# Why a Python twin of fetch.sh: the CC cloud sandbox is a Claude session with git +
# MCP, not a general box — it has no `aws` creds (no OIDC provider for it) and may lack
# `jq`/`curl`. So the cloud path reads the Grafana token from an ENV VAR (GRAFANA_TOKEN,
# set on the cloud environment by Alex — the one unavoidable manual step) and pulls the
# annotations with stdlib urllib only. No aws, no jq, no curl. fetch.sh stays the local/
# dev path (SSM token). Default window = previous full UTC day (the 05:00 WITA target).
#
# Usage (cloud): GRAFANA_TOKEN=... python3 fetch.py day.json
#        (backfill): GRAFANA_FROM=<ms> GRAFANA_TO=<ms> python3 fetch.py out.json
# The token is read from env and never printed.

import json
import os
import sys
import time
import urllib.request

BASE = os.environ.get("GRAFANA_BASE", "https://dashboard.kalpahealth.com")


def window():
    if os.environ.get("GRAFANA_FROM"):
        return int(os.environ["GRAFANA_FROM"]), int(os.environ["GRAFANA_TO"])
    now = time.time()
    midnight = int(now - (now % 86400))          # today 00:00 UTC
    return (midnight - 86400) * 1000, midnight * 1000  # previous full UTC day, in ms


def main(out):
    token = os.environ.get("GRAFANA_TOKEN")
    if not token:
        sys.exit("GRAFANA_TOKEN not set — set it on the cloud environment (path B).")
    frm, to = window()
    url = f"{BASE}/api/annotations?type=alert&from={frm}&to={to}&limit=5000"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    with open(out, "w") as f:
        json.dump(data, f)
    print(f"wrote {len(data)} annotations to {out} (from={frm} to={to})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "day.json")
