"""Session analyses for the harness scorecard (baseline §1 volume, §2 activity cost, §4 attention).

Approach: one pass per Claude Code transcript (`<logs>/mba/claude-projects/*/*.jsonl` and
`<logs>/homelab/.claude/projects/*/*.jsonl`) plus its `subagents/*.jsonl`. Kalpa work only (cwd
matching wellmed / kalpa / ai-skills / dev-workbench, not pmg). A record counts when its
timestamp falls in [since, until]; a session counts when any of its records does. Files last
written before `since` are skipped unread.

- Cost: relative weights (input 1, cache-write 1.25, cache-read 0.1, output 5; opus x1.67).
- Activity: each assistant turn is tagged by what its tool calls touch (mine2.py's signatures),
  sticky until another signature appears.
- Attention: a typed prompt is a human-origin user turn not starting with `<`. A prompt starting
  `[lane ` is a pasted decision-queue answer (the packet's prefilled reply, scope 10 §4.1); its
  latency is the wait since that session's last assistant message. Waits are capped at 2 h for
  the agent-hours total.

Prompt text is read only to classify it. Nothing here returns text — counts and durations only —
because the scorecard stores its numbers and transcripts can carry patient data.
"""

import collections
import glob
import json
import os
import re
from datetime import datetime, timezone

KALPA = re.compile(r"wellmed|kalpa|ai-skills|dev-workbench", re.I)
NOT = re.compile(r"/pmg|bernard|research-lanes", re.I)
W = dict(input_tokens=1, cache_creation_input_tokens=1.25, cache_read_input_tokens=0.1, output_tokens=5)
WAIT_CAP = 2 * 3600
QUEUE = re.compile(r"^\[lane ")
# Regex categories, first match wins (baseline §4: treat shares as ±5 points).
CATEGORIES = [
    ("queue answer", QUEUE),
    ("merge/push stamp", re.compile(r"^\W*(merge|push|land|ship|open (a |the )?pr|pr\b|commit)\b[^\n]{0,60}$", re.I)),
    ("status ping", re.compile(r"^\W*(status|where are we|what'?s (next|left|the status)|progress|continue|resume|go on)\b[^\n]{0,80}$", re.I)),
    ("redirect", re.compile(r"^\W*(no|stop|wait|actually|instead|don'?t|hold on|revert)\b", re.I)),
    ("other stamp", re.compile(r"^\W*(y|yes|yep|ok|okay|go|do it|approved?|lgtm|sure|agreed|proceed|\d+[a-d]?)\W*$", re.I)),
]
SIG = [  # first match wins (mine2.py)
    ("review", re.compile(r"review\.py|review/SKILL|review/rules|gstack/review|codex-exec\.py exec --prompt \S*review|review-\S+-r\d")),
    ("verify", re.compile(r"verify-run\.py|judge\.py|verify/SKILL|verdict-gate|finish-conditions|verify-\S+-report")),
    ("ready-to-clear", re.compile(r"ready-to-clear")),
    ("closeout", re.compile(r"closeout")),
    ("merge/pr", re.compile(r"gh pr (create|merge|ready|view|checks)|gh run (view|watch|list)|git push")),
    ("deploy/ops", re.compile(r"aws ssm|aws ecs|ssm send-command|docker (ps|logs)|curl -s")),
    ("herdr", re.compile(r"(^|[;&|(]\s*)herdr\s+\w|concurrency/SKILL|herdr/SKILL")),
    ("plan bookkeeping", re.compile(r"progress\.md|PLANS-INDEX|plans-index\.py|closeout-prep|-PLAN\.md|scope\.md")),
]


def parse_ts(s):
    if not isinstance(s, str) or not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def category(text):
    """Category of a typed prompt; `substantive` when no stamp/ping/redirect pattern matches."""
    t = (text or "").strip()
    if QUEUE.match(t):
        return "queue answer"
    if t.count("\n") >= 4 and re.search(r"^\s*(\$ |[\w.-]+@[\w.-]+:|Traceback|\{|\[\d|\d{4}-\d\d-\d\d)", t, re.M):
        return "pasted output"
    for name, rx in CATEGORIES[1:]:
        if rx.search(t):
            return name
    return "substantive"


def text_of(content):
    if isinstance(content, str):
        return content
    return "\n".join(c.get("text", "") for c in content or [] if isinstance(c, dict) and c.get("type") == "text")


def model_mult(m):
    return 1.67 if "opus" in m else (0.33 if "haiku" in m else 1.0)


def cost(msg):
    u = msg.get("usage") or {}
    c = sum((u.get(k) or 0) * w for k, w in W.items()) * model_mult(msg.get("model") or "")
    ctx = sum(u.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    return c, ctx


def signature(blocks):
    s = ""
    for b in blocks or []:
        if isinstance(b, dict) and b.get("type") == "tool_use":
            inp = b.get("input") or {}
            target = str(inp.get("command") or inp.get("file_path") or inp.get("skill") or inp.get("pattern") or "")[:2000]
            s += " " + (b.get("name") or "") + " " + re.sub(r"\S*\.herdr/worktrees/\S*?/", "", target)
    if not s:
        return None
    for name, rx in SIG:
        if rx.search(s):
            return name
    return "build" if re.search(r" (Edit|Write) ", s) else None


def _records(path, stats):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except ValueError:
                stats["bad_lines"] += 1


def roots(logs_root):
    return {"mba": os.path.join(logs_root, "mba", "claude-projects"),
            "homelab": os.path.join(logs_root, "homelab", ".claude", "projects")}


def scan(logs_root, since, until):
    """Aggregates over every Kalpa session in the window: {"sessions": [...], "prompts": [...],
    "activity": {...}, ...}. Prompt entries carry ts / wait / category / host only."""
    stats = collections.Counter()
    sessions, prompts = [], []
    act = {"main": collections.defaultdict(lambda: [0.0, 0, 0]), "sub": collections.defaultdict(lambda: [0.0, 0, 0])}
    model_cost = collections.Counter()
    inwin = lambda t: t is not None and (since is None or t >= since) and (until is None or t <= until)
    for host, root in roots(logs_root).items():
        for f in sorted(glob.glob(os.path.join(root, "*", "*.jsonl"))):
            if since is not None and os.path.getmtime(f) < since:
                continue
            stats["files_read"] += 1
            recs = list(_records(f, stats))
            cwd = next((r.get("cwd") for r in recs if r.get("cwd")), "") or ""
            if not KALPA.search(cwd) or NOT.search(cwd):
                continue
            s = dict(host=host, pmode=None, cost=0.0, usd=None, compactions=0, active=False)
            cur, last_asst = "explore", None
            for r in recs:
                t, ts = r.get("type"), parse_ts(r.get("timestamp"))
                if t == "permission-mode" and s["pmode"] is None:
                    s["pmode"] = r.get("permissionMode")
                if t == "cost-state":
                    s["usd"] = r.get("totalCostUSD")
                if t == "assistant":
                    m = r.get("message") or {}
                    sig = signature(m.get("content"))
                    cur = sig or cur
                    if inwin(ts):
                        c, ctx = cost(m)
                        a = act["main"][cur]; a[0] += c; a[1] += 1; a[2] += ctx
                        s["cost"] += c; s["active"] = True
                        model_cost[m.get("model") or "?"] += c
                    last_asst = ts if ts is not None else last_asst
                elif t == "user":
                    if not inwin(ts):
                        continue
                    s["active"] = True
                    if r.get("isCompactSummary"):
                        s["compactions"] += 1
                        continue
                    human = r.get("turnOrigin") == "human" or (r.get("origin") or {}).get("kind") == "human"
                    txt = text_of((r.get("message") or {}).get("content"))
                    if human and txt and not txt.lstrip().startswith("<"):
                        wait = ts - last_asst if last_asst is not None and ts >= last_asst else None
                        prompts.append(dict(host=host, sid=os.path.basename(f)[:-6], ts=ts, wait=wait, category=category(txt)))
            for sf in glob.glob(os.path.join(f[:-6], "subagents", "*.jsonl")):
                scur = "explore"
                for r in _records(sf, stats):
                    if r.get("type") != "assistant" or not inwin(parse_ts(r.get("timestamp"))):
                        continue
                    m = r.get("message") or {}
                    scur = signature(m.get("content")) or scur
                    c, ctx = cost(m)
                    a = act["sub"][scur]; a[0] += c; a[1] += 1; a[2] += ctx
                    model_cost[m.get("model") or "?"] += c
            if s["active"]:
                sessions.append(s)
    return dict(sessions=sessions, prompts=prompts, activity=act, model_cost=model_cost, stats=dict(stats))


def _q(vals, q):
    v = sorted(vals)
    return v[min(int(q * len(v)), len(v) - 1)] if v else None


def _pct(a, b):
    return round(100 * a / b, 1) if b else None


def tables(scan_out):
    """The §1 / §2 / §4 tables (numbers only) from a scan()."""
    ss, ps, mc = scan_out["sessions"], scan_out["prompts"], scan_out["model_cost"]
    hosts = collections.Counter(s["host"] for s in ss)
    MT = sum(mc.values())
    fam = collections.Counter()
    for m, v in mc.items():
        fam["opus" if "opus" in m else "sonnet" if "sonnet" in m else "haiku" if "haiku" in m else "other"] += v
    pm = collections.Counter(s["pmode"] or "unset" for s in ss)
    out = collections.OrderedDict()
    out["1 Volume"] = {"cols": ["Value"], "rows": {
        "sessions": [len(ss)], **{f"sessions {h}": [hosts[h]] for h in sorted(hosts)},
        "usd (cost-state)": [round(sum(s["usd"] or 0 for s in ss))],
        **{f"model share {k} %": [_pct(v, MT)] for k, v in fam.most_common()},
        "compaction resumes": [sum(s["compactions"] for s in ss)],
        **{f"permission {k}": [v] for k, v in pm.most_common()}}}
    for label, key in (("2 Activity cost (driver)", "main"), ("2 Activity cost (subagents)", "sub")):
        agg = scan_out["activity"][key]
        T = sum(a[0] for a in agg.values())
        out[label] = {"cols": ["Share %", "Calls", "Mean ctx k"], "rows": {
            k: [_pct(c, T), n, round(ctx / max(n, 1) / 1000)] for k, (c, n, ctx) in sorted(agg.items(), key=lambda x: -x[1][0])}}
    day = collections.Counter(datetime.fromtimestamp(p["ts"], timezone.utc).strftime("%Y-%m-%d") for p in ps)
    hour = collections.defaultdict(set)
    for p in ps:
        hour[int(p["ts"] // 3600)].add((p["host"], p["sid"]))
    waits = [p["wait"] for p in ps if p["wait"] is not None]
    qa = [p for p in ps if p["category"] == "queue answer"]
    qw = [p["wait"] for p in qa if p["wait"] is not None]
    mins = lambda v: round(v / 60, 1) if v is not None else None
    out["4 Attention"] = {"cols": ["Value"], "rows": {
        "typed prompts": [len(ps)], "prompts/day median": [_q(list(day.values()), 0.5)],
        "prompts/day max": [max(day.values()) if day else None],
        "sessions prompted per active hour median": [_q([len(v) for v in hour.values()], 0.5)],
        "sessions prompted per active hour p90": [_q([len(v) for v in hour.values()], 0.9)],
        "wait median min": [mins(_q(waits, 0.5))], "wait p90 min": [mins(_q(waits, 0.9))],
        "agent-hours waited (2h cap)": [round(sum(min(w, WAIT_CAP) for w in waits) / 3600)],
        "queue answers": [len(qa)], "queue answer share %": [_pct(len(qa), len(ps))],
        "queue answer latency median min": [mins(_q(qw, 0.5))],
        "queue answer latency p90 min": [mins(_q(qw, 0.9))]}}
    cats = collections.Counter(p["category"] for p in ps)
    out["4 Prompt categories"] = {"cols": ["Prompts", "Share %"], "rows": {
        k: [v, _pct(v, len(ps))] for k, v in cats.most_common()}}
    return out
