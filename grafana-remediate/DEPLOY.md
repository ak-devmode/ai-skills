# grafana-remediate — deploy (Phase 4, Gate D)

The workflow runs as a **CC cloud routine** at 05:00 WITA. This doc is the go-live spec:
the schedule, the OIDC IAM role the routine assumes (no long-lived keys in the sandbox),
and the CloudWatch heartbeat alarm (dead-cron guard). Items marked **[infra — Alex]** are
gated (IAM/SSM value writes, alarm creation) and are handed off as commands, not applied
by the agent.

## 1. Schedule

- **05:00 WITA = 21:00 UTC the previous day.** Cron (UTC): `0 21 * * *`.
- Command: `python3 workflow/remediate.py --once "$(workflow/fetch.sh yesterday.json && echo yesterday.json)"`
  — in one step: `./workflow/fetch.sh day.json && python3 workflow/remediate.py --once day.json --send`.
- **First cron scope (decided):** classify + PROPOSE/INVESTIGATE path only (`--send`, no
  `--allow-pr`). This needs only Grafana + SES + Claude in the sandbox — no gateway-go
  checkout, Go toolchain, or `gh`. The auto-PR path stays degraded to
  propose+candidate-diff until in-cloud sandbox-buildability for gateway-go is set up and
  proven; promote by adding `--allow-pr` then.

## 2. Credentials — OIDC assume-role, not static keys

The routine authenticates to AWS by assuming a least-privilege role via OIDC federation.
The Grafana token stays in SSM and is fetched at runtime through that role — it is never
injected as a static secret.

**Trust policy** (federate the CC cloud routine's OIDC provider — substitute the real
provider ARN + `sub`/`aud` the routine presents):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::114729078544:oidc-provider/<CC_OIDC_PROVIDER>" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": { "StringEquals": { "<CC_OIDC_PROVIDER>:aud": "<audience>",
                                     "<CC_OIDC_PROVIDER>:sub": "<routine-subject>" } }
  }]
}
```

**Permission policy** (least privilege — the one token, decrypt it, send mail, heartbeat):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "ssm:GetParameter",
      "Resource": "arn:aws:ssm:ap-southeast-1:114729078544:parameter/wellmed/prod/grafana/ro-token" },
    { "Effect": "Allow", "Action": "kms:Decrypt",
      "Resource": "arn:aws:kms:ap-southeast-1:114729078544:key/<ssm-securestring-cmk>" },
    { "Effect": "Allow", "Action": "ses:SendEmail",
      "Resource": "*",
      "Condition": { "StringEquals": { "ses:FromAddress": "alerts@kalpahealth.com" } } },
    { "Effect": "Allow", "Action": "cloudwatch:PutMetricData",
      "Resource": "*",
      "Condition": { "StringEquals": { "cloudwatch:namespace": "Kalpa/AlarmRemediation" } } }
  ]
}
```

When the auto-PR path is promoted, add a `gh` token scoped to `wellmed-gateway-go` only
(a fine-grained PAT with Contents+PullRequests write on that one repo) as a routine
secret — the ONE credential that is a secret rather than an assumed grant, because GitHub
is not in the AWS trust domain.

**[infra — Alex]** create the role + policies (Terraform under
`wellmed-infrastructure/terraform/`), then set `ALARM_CW_HEARTBEAT=1` in the routine env.

## 3. Heartbeat / dead-cron guard

A local `heartbeat.log` dies with the ephemeral sandbox, so `heartbeat.py` also pushes a
CloudWatch metric `Kalpa/AlarmRemediation NightlyRun=1` each run (gated on
`ALARM_CW_HEARTBEAT=1`). The absence detector is a **CloudWatch alarm** — the AWS analog
of the `deploy-hygiene.yaml` lesson (`noDataState: Alerting`): a dead cron must ALARM,
not go quiet.

**[infra — Alex]** create the alarm (missing data = breaching, 26h window so a single
missed night trips it):

```bash
aws cloudwatch put-metric-alarm --alarm-name alarm-remediation-no-heartbeat \
  --namespace Kalpa/AlarmRemediation --metric-name NightlyRun \
  --statistic Sum --period 93600 --evaluation-periods 1 --threshold 1 \
  --comparison-operator LessThanThreshold --treat-missing-data breaching \
  --alarm-actions <SNS-topic-that-emails-alex> \
  --alarm-description "grafana-remediate nightly routine did not run (05:00 WITA)"
```

## 4. Backlog drain (one-time, Task 4.2)

Run the workflow over the triaged September corpus to clear the backlog before leaving
the cron running. Unresolved = P1 (full pipeline), resolved = P2 (root-cause note). HPACK
is already in the handled store and will not re-send. This was run from
`kalpa-docs/.../artifacts/september-alarms.json` at graduation; nightly runs continue
from live pulls.

## 5. Go-live checklist

- [ ] **[infra — Alex]** OIDC role + policies applied; role ARN recorded.
- [ ] **[infra — Alex]** CloudWatch no-heartbeat alarm created → SNS→email.
- [ ] Routine created via `/schedule` at `0 21 * * *` UTC, env `ALARM_CW_HEARTBEAT=1`
      (+ role ARN), command per §1, classify+PROPOSE scope (no `--allow-pr`).
- [ ] First nightly run observed: heartbeat metric present, emails correct, nothing merged/deployed.
- [ ] Promote auto-PR (add gateway-go `gh` token + `--allow-pr`) only after in-cloud
      gateway-go build+test is proven.
