# Why do fixes draw findings? Two outputs:
# 1. Findings per 100 changed lines: codex round 1 vs codex fix-only ranges (git diff --numstat).
# 2. A seeded sample of codex fix-only findings that sit on the fix's own lines, each paired
#    with the previous review's findings on the same file and their dispositions, for reading:
#    is it the original defect not fully fixed, or a new defect the fix introduced?
# Lineage as in lineage.py (one review.py rounds() call per unit).
import sys,glob,os,json,re,collections,io,contextlib,subprocess,random,importlib.util
AI=os.path.expanduser('~/Projects/ai-skills'); P=os.path.expanduser('~/Projects')
spec=importlib.util.spec_from_file_location('rv',AI+'/review/scripts/review.py'); rv=importlib.util.module_from_spec(spec); spec.loader.exec_module(rv)
N=int(sys.argv[1]) if len(sys.argv)>1 else 40
files=glob.glob(os.path.expanduser('~/.cache/harness-logs/*-plans/**/review-*.jsonl'),recursive=True)
best={}
for f in files:
    m=re.search(r'/([^/]+)/artifacts/review-(.+)\.jsonl$',f)
    if not m: continue
    k=(m.group(1),m.group(2)); n=sum(1 for _ in open(f))
    if k not in best or n>best[k][1]: best[k]=(f,n)
def git(repo,*a):
    r=subprocess.run(['git','-C',os.path.join(P,repo),*a],capture_output=True,text=True)
    return r.stdout if r.returncode==0 else None
def hunks(repo,rng):
    out=git(repo,'diff','-U0','--no-color',rng)
    if out is None: return None
    h=collections.defaultdict(list); cur=None
    for l in out.splitlines():
        if l.startswith('+++ '): cur=l[6:] if l.startswith('+++ b/') else None
        elif l.startswith('@@') and cur:
            m=re.search(r'\+(\d+)(?:,(\d+))?',l); s=int(m.group(1)); n=int(m.group(2) or 1)
            h[cur].append((s,s+max(n,1)-1))
    return h
def changed(repo,rng):
    out=git(repo,'diff','--numstat',rng)
    if out is None: return None
    return sum(int(a)+int(b) for a,b,*_ in (l.split('\t') for l in out.splitlines()) if a.isdigit() and b.isdigit())
nrev=collections.Counter(); lines=collections.Counter(); finds=collections.Counter(); pool=[]
for (scope,unit),(f,_) in best.items():
    recs=[json.loads(l) for l in open(f) if l.strip()]
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            rs,lin=rv.rounds(recs,unit)
    except Exception: continue
    meta={r['review_id']:r for r in recs if r.get('record')=='review'}
    disp={}
    for r in recs:
        if r.get('record')=='disposition': disp[r['finding_id']]=r
    fixshas={r.get('sha') for r in recs if r.get('record')=='disposition' and r.get('disposition')=='fixed' and r.get('sha')}
    byhead={}; kind={}
    for e in rs:
        prev=byhead.get((e['repo'],e['base']))
        kind[e['id']]=('r1' if lin[e['id']][1]==1 else 'fix' if prev else 'wide',prev)
        byhead[(e['repo'],e['head'])]=e['id']
    fnd=collections.defaultdict(list)
    for x in recs:
        if x.get('record')=='finding': fnd[x['review_id']].append(x)
    for e in rs:
        k,prev=kind[e['id']]
        if not (meta.get(e['id'],{}).get('reviewer') or '').startswith('codex') or k=='wide': continue
        rng=(meta[e['id']].get('range') or {}); rng=rng.get(e['repo']) if isinstance(rng,dict) else None
        if not rng: continue
        c=changed(e['repo'],rng)
        if c is None: continue
        if k=='fix':
            # pure fix = every commit in the range is a sha some earlier finding was disposed `fixed` to;
            # otherwise the range also carries new work (a later task in the same lineage)
            cs=(git(e['repo'],'rev-list',rng) or '').split()
            k='fix' if cs and all(sh in fixshas for sh in cs) else 'fix+new'
        lines[k]+=c; finds[k]+=len(fnd[e['id']]); nrev[k]+=1
        if k!='fix': continue
        h=hunks(e['repo'],rng) or {}
        for x in fnd[e['id']]:
            try: ln=int(x.get('line'))
            except Exception: continue
            if any(a-3<=ln<=b+3 for a,b in h.get(x.get('file'),[])):
                before=[(p['finding_id'],p.get('severity'),(disp.get(p['finding_id']) or {}).get('disposition'),p.get('text','')[:170])
                        for p in fnd[prev] if p.get('file')==x.get('file')]
                pool.append((unit,e['repo'],x['finding_id'],x.get('severity'),x.get('file'),ln,x.get('text','')[:260],before))
for k in ('r1','fix','fix+new'):
    print(f'codex {k}: {nrev[k]} reviews, {finds[k]} findings over {lines[k]} changed lines = {100*finds[k]/max(lines[k],1):.2f} per 100 lines, {finds[k]/max(nrev[k],1):.1f}/review')
print('fix-line findings in pool:',len(pool),' with a prior finding on the same file:',sum(1 for p in pool if p[7]))
random.seed(10);
for p in random.sample(pool,min(N,len(pool))):
    unit,repo,fid,sev,fl,ln,txt,before=p
    print(f'\n### {fid} [{sev}] {repo} {fl}:{ln}\n  NOW: {txt}')
    for b in before[:3]: print(f'  PREV {b[0]} [{b[1]}] {b[2]}: {b[3]}')
    if not before: print('  PREV: (no prior finding on this file)')
