# Mine 21 days of Kalpa Claude Code sessions: weighted token cost per skill
# (main + subagent files, attributed to the skill active when they ran), and the
# human-attention surface (each typed prompt, the agent text that preceded it,
# and how long the agent sat waiting). Writes JSON for follow-up queries.
import json, os, glob, re, time, sys, collections

ROOT = os.path.expanduser('~/.claude/projects')
DAYS = 21
CUT = time.time() - DAYS * 86400
KALPA = re.compile(r'wellmed|kalpa|ai-skills|dev-workbench', re.I)
NOT = re.compile(r'/pmg|bernard|research-lanes', re.I)
# relative price weights (input=1); model multiplier vs sonnet
W = dict(input_tokens=1, cache_creation_input_tokens=1.25, cache_read_input_tokens=0.1, output_tokens=5)
MM = lambda m: 1.67 if 'opus' in m else (0.33 if 'haiku' in m else 1.0)
CMD = re.compile(r'<command-name>/?([\w:-]+)</command-name>')

def wcost(msg):
    u = msg.get('usage') or {}
    return sum(u.get(k, 0) * w for k, w in W.items()) * MM(msg.get('model', ''))

def text_of(content):
    if isinstance(content, str): return content
    out = []
    for c in content or []:
        if isinstance(c, dict) and c.get('type') == 'text': out.append(c['text'])
    return '\n'.join(out)

def load(f):
    try:
        return [json.loads(l) for l in open(f)]
    except Exception:
        return []

sessions, prompts = [], []
skill_cost = collections.Counter(); skill_n = collections.Counter(); skill_sub = collections.Counter()
model_cost = collections.Counter()
ROOTS=[os.path.expanduser('~/.cache/harness-logs/mba/claude-projects'), os.path.expanduser('~/.cache/harness-logs/homelab/.claude/projects')]
for f in [g for R in ROOTS for g in glob.glob(f'{R}/*/*.jsonl')]:
    if os.path.getmtime(f) < CUT: continue
    recs = load(f)
    cwd = next((r.get('cwd') for r in recs if r.get('cwd')), '') or ''
    if not KALPA.search(cwd) or NOT.search(cwd): continue
    sid = os.path.basename(f)[:-6]
    pmode = next((r.get('permissionMode') for r in recs if r.get('type') == 'permission-mode'), None)
    timeline = []  # (ts, skill) switches
    cur = 'none'; last_asst_ts = None; last_asst_text = ''; tot = 0.0
    for r in recs:
        t = r.get('type'); ts = r.get('timestamp')
        if t == 'user':
            m = r.get('message') or {}
            txt = text_of(m.get('content'))
            cm = CMD.search(txt or '')
            human = r.get('turnOrigin') == 'human' or (r.get('origin') or {}).get('kind') == 'human'
            if cm:
                cur = cm.group(1); skill_n[cur] += 1; timeline.append((ts, cur))
            elif human:
                if txt and not txt.lstrip().startswith('<'):
                    wait = None
                    if last_asst_ts and ts:
                        from datetime import datetime
                        p = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
                        wait = p(ts) - p(last_asst_ts)
                    prompts.append(dict(host='homelab' if 'homelab' in f else 'mba', sid=sid, cwd=cwd, ts=ts, skill=cur, wait=wait,
                                        ask=last_asst_text[-700:], reply=txt[:700]))
                    cur = 'none' if not cm else cur; timeline.append((ts, cur))
        elif t == 'assistant':
            m = r.get('message') or {}
            c = wcost(m); tot += c; skill_cost[cur] += c; model_cost[m.get('model', '?')] += c
            for blk in m.get('content') or []:
                if isinstance(blk, dict) and blk.get('type') == 'tool_use' and blk.get('name') == 'Skill':
                    cur = (blk.get('input') or {}).get('skill', '?'); skill_n[cur] += 1; timeline.append((ts, cur))
            tx = text_of(m.get('content'))
            if tx: last_asst_text = tx
            last_asst_ts = ts
    sub = 0.0
    for sf in glob.glob(f'{f[:-6]}/subagents/*.jsonl'):
        srecs = load(sf)
        st = next((r.get('timestamp') for r in srecs if r.get('timestamp')), '')
        sk = 'none'
        for ts, s in timeline:
            if ts and st and ts <= st: sk = s
        for r in srecs:
            if r.get('type') == 'assistant':
                m = r.get('message') or {}; c = wcost(m)
                sub += c; skill_cost[sk] += c; skill_sub[sk] += c; model_cost[m.get('model', '?')] += c
    cost_usd = None
    for r in recs:
        if r.get('type') == 'cost-state': cost_usd = r.get('totalCostUSD')
    sessions.append(dict(host='homelab' if 'homelab' in f else 'mba', sid=sid, cwd=cwd, pmode=pmode, main=tot, sub=sub, usd=cost_usd,
                         start=next((r.get('timestamp') for r in recs if r.get('timestamp')), '')))

out = dict(sessions=sessions, prompts=prompts, skill_cost=skill_cost, skill_n=skill_n,
           skill_sub=skill_sub, model_cost=model_cost)
json.dump(out, open(sys.argv[1], 'w'))
T = sum(skill_cost.values())
print('sessions', len(sessions), 'prompts', len(prompts), 'total units %.0f' % T)
print('usd (cost-state, sessions that have it):', round(sum(s['usd'] or 0 for s in sessions)), 'of', sum(1 for s in sessions if s['usd']))
print('main vs sub units: %.0f / %.0f' % (sum(s['main'] for s in sessions), sum(s['sub'] for s in sessions)))
print('\n-- cost share by active skill (incl. subagents) --')
for k, v in skill_cost.most_common(25):
    print(f'{v/T*100:5.1f}%  sub {skill_sub[k]/max(v,1)*100:4.0f}%  n={skill_n[k]:4d}  {k}')
print('\n-- by model --')
for k, v in model_cost.most_common(): print(f'{v/T*100:5.1f}%  {k}')
print('\n-- permission modes --', collections.Counter(s['pmode'] for s in sessions))
