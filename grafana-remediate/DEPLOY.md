# grafana-remediate — deploy (LIVE, path B: CC cloud routine + Gmail MCP)

**Status: LIVE as of 2026-09-22.** Routine `trig_01CPn57nuDtajuxb2YgsxbVx`
(`grafana-remediate-nightly`), cron `0 21 * * *` UTC (= 05:00 WITA), enabled.
Manage at https://claude.ai/code/routines .

This is the as-built record. The cloud sandbox is a Claude Code session with a git
checkout + MCP connectors — **not** a general compute box: no OIDC provider exists for it
and the routine API has no secret field, so there is **no AWS in the sandbox**. Egress is
the **Gmail MCP connector**; the Grafana token is a cloud-environment **env var**. (The
original OIDC/SES/CloudWatch plan was abandoned once that substrate was verified — it only
applies to the local/dev path below.)

## 1. The environment — `cloud-agents` (NOT Default)

The routine runs on a **dedicated** environment: **`cloud-agents`**
(`env_01F8iRkkm17w77iTbZWLPJ9q`, kind anthropic_cloud). The shared **Default** env
(`env_013Pof…`) could NOT hold custom env vars — that was the multi-hour red herring.
Three things must be configured on the `cloud-agents` environment (claude.ai/code → open
the environment's **Update cloud environment** dialog):

1. **Environment variable** — `GRAFANA_TOKEN=<glsa_… value>` (from SSM
   `/wellmed/prod/grafana/ro-token`), `.env` format, no quotes. Read by `fetch.py` as
   `os.environ["GRAFANA_TOKEN"]`. **Confirm the routine's environment is `cloud-agents`,
   not Default** — a mismatch here is why it silently read UNSET.
2. **Network access → allowed domain** — `dashboard.kalpahealth.com` (no scheme/port).
   The sandbox egress proxy 403-denies any host not on the allowlist; without this the
   fetch fails `Tunnel connection failed: 403 Forbidden`.
3. **Gmail connector with SEND scope** — the routine's Gmail MCP connection must expose
   `send_message` (org + personal send enabled at claude.ai/customize/connectors). With
   only compose scope it can `create_draft` but not send.

No setup script is needed — the workflow is **stdlib Python only** (no pip).

## 2. What runs
The routine prompt tells the session to read `workflow/cloud-routine.md` and follow it:
`fetch.py` (env-token pull) → `classify.py --json` → the session root-causes each
PROPOSE/INVESTIGATE incident, composes an ES email (problem+solution in the first two
sentences), runs `phi_scrub.py` on the body, and **sends via Gmail `send_message`** →
then a run-summary email + a `PushNotification` (the heartbeat — its absence = dead cron).
Hard floor: only ever emails; never merges/deploys/silences/PRs. PIPELINE (code-defect)
incidents are emailed as proposals — the auto-PR path is **not** enabled in the cloud
routine (it would need a gateway-go checkout + Go + `gh` in the environment; local path
only for now).

## 3. Verified end-to-end (2026-09-22)
A manual `RemoteTrigger run` fetched 24 real Sept-21 annotations, classified 1 PROPOSE
incident ("Deploy rolled back or failed", dev/fe), root-caused it, passed the PHI gate,
and sent the proposal + summary via Gmail. Egress, token, allowlist, PHI, fail-closed and
heartbeat all confirmed.

## 4. Operate
- Pause: disable the routine (claude.ai/code/routines) or `RemoteTrigger update {enabled:false}`.
- Test now: `RemoteTrigger run`, then `list_runs` → `get_run_log`.
- Rotate the token: mint a new Grafana SA token, update BOTH SSM (local path) and the
  `cloud-agents` `GRAFANA_TOKEN` env var (cloud path).
- Promote auto-PR later: add a gateway-go checkout + gateway-go-scoped `gh` to the env and
  switch the routine to the full pipeline (`--allow-pr`).

## Local / dev path (unchanged)
Local runs use `fetch.sh` (SSM token) + `remediate.py` (SES egress, `claude -p` stages,
real worktree/PR). See `workflow/README.md`. SES/worktree/PR are the local substrate; the
cloud routine deliberately uses none of them.
