# Are later-round findings about the fix, or about code the fix sat next to?
# For each finding, check whether its file:line falls inside a changed hunk of its own
# review's range (git diff -U0 in ~/Projects/<repo>). Lineage rounds via lineage.py's
# method (review.py rounds()/review_round()). Ranges whose commits are not in the local
# clone are counted as unresolved, not guessed.
import sys,glob,os,json,re,collections,io,contextlib,subprocess,importlib.util
AI=os.path.expanduser('~/Projects/ai-skills'); P=os.path.expanduser('~/Projects')
spec=importlib.util.spec_from_file_location('rv',AI+'/review/scripts/review.py'); rv=importlib.util.module_from_spec(spec); spec.loader.exec_module(rv)
files=glob.glob(os.path.expanduser('~/.cache/harness-logs/*-plans/**/review-*.jsonl'),recursive=True)
best={}
for f in files:
    m=re.search(r'/([^/]+)/artifacts/review-(.+)\.jsonl$',f)
    if not m: continue
    k=(m.group(1),m.group(2)); n=sum(1 for _ in open(f))
    if k not in best or n>best[k][1]: best[k]=(f,n)
fam=lambda r:('codex' if (r or '').startswith('codex') else 'fallback' if (r or '').startswith('claude-fallback') else 'lean' if (r or '').startswith('claude-lean') else 'other')
hunks_cache={}
def hunks(repo,rng):
    k=(repo,rng)
    if k in hunks_cache: return hunks_cache[k]
    d=os.path.join(P,repo); out=None
    if os.path.isdir(d):
        r=subprocess.run(['git','-C',d,'diff','-U0','--no-color',rng],capture_output=True,text=True)
        if r.returncode==0:
            out=collections.defaultdict(list); cur=None
            for l in r.stdout.splitlines():
                if l.startswith('+++ '): cur=l[6:] if l.startswith('+++ b/') else None
                elif l.startswith('@@') and cur:
                    m=re.search(r'\+(\d+)(?:,(\d+))?',l); s=int(m.group(1)); n=int(m.group(2) or 1)
                    out[cur].append((s,s+max(n,1)-1))
    hunks_cache[k]=out; return out
# per (family, round bucket): in-hunk / in-touched-file-outside-hunk / untouched-file / unresolved
C=collections.defaultdict(collections.Counter); revs_by=collections.Counter(); f_by=collections.Counter()
for i,((scope,unit),(f,_)) in enumerate(best.items()):
    print(f'[{i+1}/{len(best)}] {unit}',file=sys.stderr,flush=True)
    recs=[json.loads(l) for l in open(f) if l.strip()]
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            rs,lin=rv.rounds(recs,unit); rid2={e['id']:(e['repo'],lin[e['id']][1]) for e in rs}
    except Exception: continue
    meta={r['review_id']:r for r in recs if r.get('record')=='review'}
    # r2+ split: a fix-only range starts at an earlier review's head in the same repo; a wide
    # one re-reviews the original code too, so "in hunk" there does not mean "in the fix"
    heads=collections.defaultdict(set); kind={}
    for e in rs:
        kind[e['id']]='fix-range' if e['base'] in heads[e['repo']] else 'wide'
        heads[e['repo']].add(e['head'])
    for rid,(repo,rnd) in rid2.items():
        revs_by[(fam(meta.get(rid,{}).get('reviewer')),'r1' if rnd==1 else 'r2+ '+kind[rid])]+=1
    for x in recs:
        if x.get('record')!='finding' or x.get('review_id') not in rid2: continue
        repo,rnd=rid2[x['review_id']]; key=(fam(x.get('reviewer')),'r1' if rnd==1 else 'r2+ '+kind[x['review_id']])
        f_by[key]+=1
        rng=(meta.get(x['review_id'],{}).get('range') or {})
        rng=rng.get(repo) if isinstance(rng,dict) else None
        h=hunks(repo,rng) if rng else None
        try: line=int(x.get('line'))
        except Exception: line=None
        if h is None or line is None: C[key]['unresolved']+=1; continue
        fl=x.get('file') or ''
        if fl not in h: C[key]['untouched file']+=1
        elif any(a-3<=line<=b+3 for a,b in h[fl]): C[key]['in fix hunk (±3)']+=1
        else: C[key]['touched file, outside hunk']+=1
for key in sorted(C):
    tot=sum(v for k,v in C[key].items() if k!='unresolved')
    print(key,'reviews',revs_by[key],'findings/rev %.1f'%(f_by[key]/max(revs_by[key],1)),
          {k:f'{v} ({v/tot:.0%})' if k!='unresolved' and tot else v for k,v in C[key].items()})
