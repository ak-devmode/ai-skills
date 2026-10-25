# Activity attribution by tool-call signature instead of slash-command: each assistant
# turn is tagged by what its tool calls touch (review.py, judge.py, gh pr, herdr...),
# sticky until a different signature appears. Reports cost share, API calls and mean
# context per activity, so "review is expensive" splits into turns x context.
import json, os, glob, re, time, sys, collections

ROOTS = {'mba': os.path.expanduser('~/.cache/harness-logs/mba/claude-projects'), 'homelab': os.path.expanduser('~/.cache/harness-logs/homelab/.claude/projects')}
CUT = time.time() - 21 * 86400
KALPA = re.compile(r'wellmed|kalpa|ai-skills|dev-workbench', re.I)
NOT = re.compile(r'/pmg|bernard|research-lanes', re.I)
W = dict(input_tokens=1, cache_creation_input_tokens=1.25, cache_read_input_tokens=0.1, output_tokens=5)
MM = lambda m: 1.67 if 'opus' in m else (0.33 if 'haiku' in m else 1.0)
SIG = [  # first match wins
    ('review', re.compile(r'review\.py|review/SKILL|review/rules|gstack/review|codex-exec\.py exec --prompt \S*review|review-\S+-r\d')),
    ('verify', re.compile(r'verify-run\.py|judge\.py|verify/SKILL|verdict-gate|finish-conditions|verify-\S+-report')),
    ('ready-to-clear', re.compile(r'ready-to-clear')),
    ('closeout', re.compile(r'closeout')),
    ('merge/pr', re.compile(r'gh pr (create|merge|ready|view|checks)|gh run (view|watch|list)|git push')),
    ('deploy/ops', re.compile(r'aws ssm|aws ecs|ssm send-command|docker (ps|logs)|curl -s')),
    ('herdr', re.compile(r'(^|[;&|(]\s*)herdr\s+\w|concurrency/SKILL|herdr/SKILL')),
    ('plan-bookkeeping', re.compile(r'progress\.md|PLANS-INDEX|plans-index\.py|closeout-prep|-PLAN\.md|scope\.md')),
]

def sig_of(blocks):
    s = ''
    for b in blocks or []:
        if isinstance(b, dict) and b.get('type') == 'tool_use':
            inp = b.get('input', {}) or {}
            # commands and file targets only, with worktree prefixes stripped so paths can't masquerade as activity
            s += ' ' + b.get('name', '') + ' ' + re.sub(r'\S*\.herdr/worktrees/\S*?/', '', str(inp.get('command') or inp.get('file_path') or inp.get('skill') or inp.get('pattern') or '')[:2000])
    if not s: return None
    for name, rx in SIG:
        if rx.search(s): return name
    if re.search(r'"name": ?"(Edit|Write)"| (Edit|Write) ', s): return 'build'
    return None

def cost(m):
    u = m.get('usage') or {}
    return sum(u.get(k, 0) * w for k, w in W.items()) * MM(m.get('model', '')), \
        u.get('input_tokens', 0) + u.get('cache_read_input_tokens', 0) + u.get('cache_creation_input_tokens', 0)

def run(files, sticky_start='explore'):
    agg = collections.defaultdict(lambda: [0.0, 0, 0])  # cost, calls, ctx-sum
    for f in files:
        cur = sticky_start
        for l in open(f):
            try: r = json.loads(l)
            except Exception: continue
            if r.get('type') != 'assistant': continue
            m = r.get('message') or {}
            s = sig_of(m.get('content'))
            if s: cur = s
            c, ctx = cost(m)
            a = agg[cur]; a[0] += c; a[1] += 1; a[2] += ctx
    return agg

mains, subs = [], []
HOST = {}
for f in [g for R in ROOTS.values() for g in glob.glob(f'{R}/*/*.jsonl')]:
    if os.path.getmtime(f) < CUT: continue
    with open(f) as fh:
        head = fh.read(20000)
    m = re.search(r'"cwd":"([^"]+)"', head)
    cwd = m.group(1) if m else ''
    if not KALPA.search(cwd) or NOT.search(cwd): continue
    mains.append(f); HOST[f] = 'homelab' if 'homelab' in f else 'mba'
    subs += glob.glob(f'{f[:-6]}/subagents/*.jsonl')

print('mains per host', collections.Counter(HOST.values()))
for label, files in (('MAIN', mains), ('SUBAGENTS', subs)):
    agg = run(files)
    T = sum(a[0] for a in agg.values())
    print(f'== {label} ({len(files)} files) ==')
    for k, (c, n, ctx) in sorted(agg.items(), key=lambda x: -x[1][0]):
        print(f'{c/T*100:5.1f}%  calls {n:6d}  mean ctx {ctx/max(n,1)/1000:6.0f}k  {k}')
