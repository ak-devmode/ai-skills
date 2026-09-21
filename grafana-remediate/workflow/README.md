# Grafana alarm auto-remediation workflow

Nightly agent-in-series workflow (scope 146). At 05:00 WITA it pulls the previous day's
Grafana alarms, routes each through logic gates, and either opens a **PR** (a code
defect proven under a reproduction) or emails a **proposal** — every output an
executive-summary email to `alex@kalpahealth.com`. **It never merges, never deploys,
never silences.** Promotion is always a human call.

## Layout — one substrate-agnostic artifact

Chosen 2026-09-21 (decision 1a): a portable orchestrator + a versioned prompt library
invoking `claude -p` per stage. The dev-time run and the Phase-4 cloud routine are the
**same code** — Phase 4 swaps the scheduler, not the logic.

```
fetch.sh            token-bearing day pull (SSM RO token, never printed)   [deterministic]
classify.py         collapse annotations -> incidents, dedup, classify, route [deterministic]
known_issues.json   static dedup seeds (HPACK, Saga DLQ)                    [data]
phi_scrub.py        PHI/tenant egress detector+redactor                     [deterministic]
--- agentic stages ---
agent.py            ONE run_agent(stage, ctx) -> validated JSON; claude -p
prompts/*.md        versioned stage prompts (root_cause, repro, fix, verify, email)
gates.py            phi_gate · repro_gate (fail-closed) · verify_gate (oracle) · honesty gate
worktree.py         per-alarm throwaway worktree: create at repro entry, prune except verify-fail, age-sweep
dedup.py            signature key · linked-PR check · handled store · reopen-on-worsening
email_ses.py        ES-email composer (2-sentence lead) + SES send (reuses PR summary)
heartbeat.py        liveness emit every run (dead cron != handled)
remediate.py        the spine / state machine + CLI
tests/              offline suite (fake agent runner + fake worktree; no token, no LLM)
```

## Run

```bash
# Read-only calibration over the September corpus (NO LLM, NO egress) — the default:
python3 remediate.py --no-gh

# Live over yesterday's alarms (LLM stages run; email/PR still DRY unless flagged):
FROM= TO= ./fetch.sh today.json && python3 remediate.py --once today.json

# Enable real egress (Phase 3+ only, human-supervised):
python3 remediate.py --once today.json --send            # actually send SES
python3 remediate.py --once today.json --allow-pr        # allow live PR creation

# Tests (offline, no token):
python3 tests/test_workflow.py
```

## Safety floor (structural, not a prompt hope)

- No function merges, deploys, or silences. The only writes are "send email" and "open
  PR". Every egress passes `phi_gate` first, and `email_ses.send()` re-checks — no
  unredacted egress even on a caller bug.
- **Repro-or-nothing:** a defect reaches a PR only through the fail-closed repro gate
  (must reproduce the original signal pre-fix) + the verify oracle (must stop
  reproducing it post-fix, tied to that signal). Anything short degrades to a proposal.
- **Honesty gate:** root-cause reading the firing rule's annotation can abort a PIPELINE
  incident to PROPOSE — the HPACK case is the negative test (never a dep-bump PR).
- Alarm text is untrusted data, rendered into a fenced region the prompts treat as data.

## Evidence-access constraint

The cloud agent reaches Grafana's API over the public ALB but **not** loopback
Prometheus (`127.0.0.1:9091`) or host logs. Root-cause is bounded to what the Grafana
annotation + labels expose plus what a repro can surface in-sandbox. An on-host
evidence collector is a Phase-4 substrate item.

## Graduation

Phase 4 packages this directory into `ai-skills/` and schedules `remediate.py --once`
as a CC cloud routine at 05:00 WITA, token injected as a secret from SSM. A thin
pointer/runbook stays in `wellmed-infrastructure/observability/`.
