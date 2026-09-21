---
name: grafana-remediate
description: "Nightly Grafana alarm auto-remediation workflow for WellMed/Kalpa. Pulls the previous day's alarms, routes each through logic gates (dedup → classify → root-cause → repro → fix → verify), and either opens a PR (a code defect proven under a reproduction) or emails an executive-summary proposal. Never merges, never deploys, never silences. Use to run the workflow by hand, understand its gates, or (re)deploy the 05:00 WITA cron."
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
---

# grafana-remediate

Graduated from WellMed scope 146 (`kalpa-docs/plans/146-grafana-alarm-remediation/`).
The build history + calibration evidence live there; this is the runnable home.

## What it does

At 05:00 WITA a CC cloud routine pulls the previous day's Grafana alarms from the
alert-state-history/annotations API over the public ALB (`dashboard.kalpahealth.com`,
read-only SA token in SSM) and routes each incident:

```
fetch → collapse to incidents → dedup → classify → route:
  DROP        noise / known-issue / already-handled
  PROPOSE     infra/ops, hygiene, or a code-defect that is not a mechanical diff → ES email
  INVESTIGATE fault-rate that needs a human look → ES email
  PIPELINE    code-defect → root-cause → repro gate (fail-closed) → fix → verify oracle
              → PR (never merged) ; degrades to PROPOSE on any repro/verify failure
```

Every egress (email body + PR diff/description) passes a deterministic **PHI/governance
gate** first. The workflow **never merges, never deploys, never silences** — promotion is
always a human call. See `workflow/README.md` for the module map + safety floor.

## Run it

```bash
cd workflow
python3 remediate.py --no-gh                       # read-only dry-run (no LLM, no egress)
python3 remediate.py --once yesterday.json         # live pipeline; egress still dry
python3 remediate.py --once yesterday.json --send   # + real SES email
python3 remediate.py --once yesterday.json --allow-pr --send  # + live PR (blast-radius repo)
python3 remediate.py --once y.json --only HPACK     # a single alarm by name substring
python3 tests/test_workflow.py                      # 21 offline tests (no token/LLM)
```

## Deploy / schedule

The 05:00 WITA cron, the OIDC IAM role the routine assumes, and the CloudWatch
heartbeat alarm are specified in [`DEPLOY.md`](DEPLOY.md). Runtime state (dedup handled
store, heartbeat log, day pulls) is git-ignored.

## Scope of autonomy (locked)

- Blast radius for auto-PR is **`wellmed-gateway-go` only** at t0 (`gh` scoped to it).
- The September corpus had **0 auto-PR-eligible defects**; the first real PR-path input
  is expected from the go-forward Sentry/E2E stream. The PR path was validated end-to-end
  against a synthetic seed (see scope 146 `pr-path-validation.md`).
