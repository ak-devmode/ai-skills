# grafana-remediate — deploy (Phase 4, Gate D) · path B (Gmail MCP, creds-free)

The workflow runs as a **CC cloud routine** (`/schedule`) at 05:00 WITA. The cloud
sandbox is a Claude session with a git checkout + MCP connectors — **not** a general box:
there is **no OIDC provider** for it and **no secret-injection field** in the routine API,
so it cannot assume an AWS role or be handed secrets programmatically. Path B therefore
uses **no AWS in the sandbox**: egress via the **Gmail MCP connector**, and the Grafana
token as a single **environment variable** on the cloud environment.

## 1. Schedule + shape
- **05:00 WITA = 21:00 UTC prior day.** Cron (UTC): `0 21 * * *`.
- The routine runs the prompt in `workflow/cloud-routine.md`: `fetch.py` → `classify.py --json`
  → the session root-causes + composes an ES email per actionable incident → `phi_scrub.py`
  gate → **send via Gmail connector** → one run-summary email (the heartbeat).
- Egress is Gmail (from the connected account), **not** SES — a deliberate substrate
  deviation from the scope's "SES not Gmail MCP" line, which assumed a compute cron.
- **Scope:** classify + PROPOSE/INVESTIGATE only. PIPELINE is emailed as a proposal; the
  auto-PR path is **not** enabled in the cloud routine (it needs a gateway-go checkout +
  Go + `gh` in the sandbox — a later promotion).

## 2. The ONE manual step (Alex — only you can do it)
Set the Grafana read-only token as an env var on the cloud environment
(`env_013Pof1Kao9aEawkJPoJ2K3T`) via claude.ai:

- `GRAFANA_TOKEN` = the value of SSM `/wellmed/prod/grafana/ro-token`
  (read it once with `aws ssm get-parameter --name /wellmed/prod/grafana/ro-token --with-decryption --query Parameter.Value --output text`).

Nothing else — no AWS keys, no IAM role, no SSM-in-sandbox. If you would rather not put
the token in the environment, it can instead be pasted into the routine prompt, but the
env var keeps it out of the routine definition.

## 3. Connector
The routine attaches the **Gmail** claude.ai connector
(`connector_uuid 78e49e8c-20d5-4690-b0ef-5707ad1016e0`). It must stay connected at
https://claude.ai/customize/connectors.

## 4. Heartbeat / dead-cron guard
The routine always sends a **run-summary email** (step 6 of the prompt), even on a
zero-actionable night. Its **absence** is the dead-cron signal. (A metric-based
absence-detector was the compute-cron design; on this substrate the daily email is the
v1 dead-man's switch — upgrade later if warranted.)

## 5. Go-live checklist
- [ ] **[Alex]** set `GRAFANA_TOKEN` env var on `env_013Pof…` (§2).
- [ ] Routine created via `/schedule` (`RemoteTrigger create`) — cron `0 21 * * *`, repo
      `ai-skills`, Gmail connector attached, prompt = `workflow/cloud-routine.md`. Created
      **disabled** until the token is set.
- [ ] Enable it; `RemoteTrigger run` once to test; confirm: emails land via Gmail, the
      run-summary arrives, nothing merged/deployed.
- [ ] (Later) promote auto-PR: add a gateway-go-scoped `gh` token + gateway-go checkout
      to the environment and switch the routine to the full pipeline.

## Local / dev path (unchanged)
Local runs still use `fetch.sh` (SSM token) + `remediate.py` (SES egress, `claude -p`
stages). See `workflow/README.md`. That path keeps SES/CloudWatch; only the CLOUD routine
uses Gmail MCP.
