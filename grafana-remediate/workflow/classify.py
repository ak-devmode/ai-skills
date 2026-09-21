#!/usr/bin/env python3
# Deterministic front-end of the alarm-remediation workflow (scope 146, Phase 2).
#
# Approach: the fetch/normalize/classify/dedup stages are pure and deterministic —
# they must NOT be an LLM's job (an LLM classifier drifts and can't be diffed against
# a signed-off bucket set). This script turns raw Grafana alert annotations into
# routed *incidents*, so the agentic stages downstream (root-cause -> repro -> fix ->
# verify -> PHI -> email) only ever run on the small `PIPELINE`/`INVESTIGATE` residue.
#
# Pipeline position:
#   [fetch] -> collapse annotations to incidents -> dedup (known_issues.json) ->
#   classify (taxonomy) -> route -> (LLM stages handle PIPELINE/INVESTIGATE only)
#
# Routes: DROP (noise/known) · PROPOSE (email, no PR) · INVESTIGATE (human/agent look) ·
#         PIPELINE (full repro->fix->verify->PR, code-defect with an available fix).
#
# Stdlib only. Operates on a JSON file so it is testable offline against the
# September corpus (artifacts/september-alarms.json) without a Grafana token.
# `fetch.sh` (sibling) is the thin token-bearing wrapper that produces that JSON.

import json, sys, re
from collections import defaultdict
from pathlib import Path

KNOWN = json.loads((Path(__file__).parent / "known_issues.json").read_text())["known"]

def tags_to_dict(ann):
    d = {}
    for t in ann.get("tags", []):
        if ":" in t:
            k, v = t.split(":", 1)
            d[k] = v
    return d

def collapse_to_incidents(annotations):
    # An incident = one alert on one instance. Firings = count of transitions INTO
    # Alerting. The 522 annotations (Pending/Alerting/Normal transitions) collapse to
    # ~one row per (alertName, instance) carrying its firing count + latest labels.
    groups = defaultdict(lambda: {"firings": 0, "labels": {}, "alertName": None, "last": 0})
    for a in annotations:
        tg = tags_to_dict(a)
        # Key on env too: env-less alarms (e.g. "No deploy in 30 days" has no instance)
        # otherwise collapse prod+staging+dev into one group and mislabel by last-seen,
        # hiding the prod signal that must PROPOSE while non-prod DROPs.
        key = (a.get("alertName"), tg.get("instance", ""), tg.get("env", ""))
        g = groups[key]
        g["alertName"] = a.get("alertName")
        if a.get("time", 0) >= g["last"]:
            g["last"], g["labels"] = a.get("time", 0), tg
        if a.get("newState") == "Alerting":
            g["firings"] += 1
    # keep only groups that actually fired (had an Alerting transition)
    return [g for g in groups.values() if g["firings"] > 0]

CAP_RE = re.compile(r"\b(cpu|mem(ory)?|disk|swap|credit|ilm|es colour|es color)\b", re.I)
HYG_RE = re.compile(r"no deploy|deploy.*days|deploy hygiene", re.I)
DEFECT_RE = re.compile(r"panic|crash|restart storm|fatal|oom", re.I)
FAULT_RE = re.compile(r"server-fault|fault rate|error rate|5xx", re.I)

def classify(inc):
    name = inc["alertName"] or ""
    lab = inc["labels"]
    env = lab.get("env", "?")
    control = lab.get("control", "")
    prod = env == "prod"

    # 1) dedup / known-issues short-circuit
    for k in KNOWN:
        if k["match"].lower() in name.lower():
            return (k["class"], k["route"], f"known-issue: {k['note'][:80]}")

    # 2) capacity (host/container resource)
    if control == "host-resource" or CAP_RE.search(name):
        return ("infra-capacity", "PROPOSE" if prod else "DROP",
                f"capacity ({env}); prod->propose, non-prod->drop")

    # 3) deploy hygiene
    if HYG_RE.search(name):
        return ("deploy-hygiene", "PROPOSE" if prod else "DROP",
                f"hygiene ({env}); not a code fix")

    # 4) code-defect (panic/crash) -> full pipeline (unless a known-issue caught it above)
    if DEFECT_RE.search(name):
        return ("code-defect", "PIPELINE",
                "crash/panic signature; repro->fix->verify->PR (gate refuses if no fix)")

    # 5) fault-rate -> investigate (may be our code or downstream)
    if FAULT_RE.search(name):
        return ("maybe-defect", "INVESTIGATE", "fault/error-rate; needs a look before fix-eligible")

    # 6) default: surface, don't drop
    return ("unclassified", "PROPOSE", "no rule matched; surface for a human")

def route_all(path):
    """Deterministic front-end: annotations file -> routed incidents (list of dicts).
    Shared by the human table (main) and the machine-readable --json mode the cloud
    routine parses."""
    anns = json.loads(Path(path).read_text())
    routed = []
    for inc in collapse_to_incidents(anns):
        cls, route, why = classify(inc)
        routed.append({**inc, "class": cls, "route": route, "why": why})
    return anns, routed


def main(path):
    anns, routed = route_all(path)

    by_route = defaultdict(int)
    for r in routed:
        by_route[r["route"]] += 1
    print(f"annotations={len(anns)}  incidents={len(incidents)}  "
          f"firings={sum(r['firings'] for r in routed)}")
    print("routes:", dict(by_route))
    print("-" * 70)
    for r in sorted(routed, key=lambda x: -x["firings"]):
        lab = r["labels"]
        print(f"{r['firings']:>3}x  [{r['route']:<10}] {r['class']:<32} "
              f"{r['alertName']}  ({lab.get('env','?')}/{lab.get('tier','?')})")
    return routed

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--json"]
    src = args[0] if args else str(Path(__file__).parents[1] / "september-alarms.json")
    if "--json" in sys.argv:
        # Machine-readable routed incidents for the cloud routine session to consume.
        _, routed = route_all(src)
        print(json.dumps([{k: r[k] for k in ("alertName", "class", "route", "why",
              "firings", "labels")} for r in routed], ensure_ascii=False))
    else:
        main(src)
