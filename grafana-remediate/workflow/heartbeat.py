#!/usr/bin/env python3
# Workflow self-heartbeat (scope 146, Phase 2, Task 2.3b — autoplan finding).
#
# Approach: a dead cron produces NOTHING, and "nothing" is indistinguishable from a
# quiet, healthy night when zero alarms were actionable. So the workflow emits its own
# liveness signal on EVERY run, including zero-action nights: a timestamped line to a
# heartbeat log plus a one-line status suitable for the run digest. Phase 4 wires the
# absence-detector (a Grafana "no heartbeat by 06:00 WITA" rule) against this log — the
# detector is infra and out of Phase 2, but the emitter it watches is built here.
#
# The heartbeat records the run OUTCOME (processed/emailed/PRed/held/errored) so a run
# that ran-but-crashed-mid-pipeline is distinguishable from a clean quiet night.
#
# Stdlib only.

import json
import os
import subprocess
import time
from pathlib import Path

LOG = Path(os.environ.get("ALARM_HEARTBEAT_LOG",
                          Path(__file__).parent / "heartbeat.log"))
CW_NAMESPACE = os.environ.get("ALARM_CW_NAMESPACE", "Kalpa/AlarmRemediation")


def _emit_cloudwatch(ok):
    """Best-effort durable heartbeat for the cloud cron: a local log dies with the
    ephemeral sandbox, so the absence-detector watches a CloudWatch custom metric
    instead. The routine's OIDC role carries cloudwatch:PutMetricData. A failure here
    never fails the run (the run's real work already happened) — but it is logged.
    The matching CloudWatch alarm uses TreatMissingData=breaching (the CW analog of
    Grafana's noDataState:Alerting) so a DEAD cron alarms rather than going quiet."""
    if os.environ.get("ALARM_CW_HEARTBEAT", "0") != "1":
        return False  # off by default; the cloud routine sets it to 1
    try:
        p = subprocess.run(
            ["aws", "cloudwatch", "put-metric-data", "--namespace", CW_NAMESPACE,
             "--metric-name", "NightlyRun", "--value", "1" if ok else "0",
             "--unit", "Count"], capture_output=True, text=True, timeout=30)
        return p.returncode == 0
    except Exception:
        return False


def emit(summary, ok=True, log=LOG):
    """Append one JSON line with the run's outcome AND push the CloudWatch heartbeat
    (cloud only). Returns the record."""
    cw = _emit_cloudwatch(ok)
    rec = {"ts": int(time.time()),
           "iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "ok": bool(ok), "cw_heartbeat": cw, **summary}
    with open(log, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def status_line(rec):
    return (f"heartbeat {rec['iso']} ok={rec['ok']} "
            f"incidents={rec.get('incidents',0)} emails={rec.get('emails',0)} "
            f"prs={rec.get('prs',0)} held={rec.get('held',0)} errors={rec.get('errors',0)}")


def last(log=LOG):
    """Most recent heartbeat record, or None. Used by the Phase-4 absence detector."""
    try:
        lines = [l for l in Path(log).read_text().splitlines() if l.strip()]
        return json.loads(lines[-1]) if lines else None
    except (FileNotFoundError, json.JSONDecodeError, IndexError):
        return None
