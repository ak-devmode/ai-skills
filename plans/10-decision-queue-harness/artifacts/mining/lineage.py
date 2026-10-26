# Review rounds counted the way the gate counts them: per lineage, via review.py's own
# rounds()/review_round() (a fix re-review continues its lineage, new code starts at r1).
# Replaces reviews.py's round analysis, which used the unit's r<n> and overstated depth.
# Dedupes worktree copies by keeping the largest file per (scope, unit). Slow: lineage
# resolution checks git ancestry in ~/Projects (~10+ min over 86 units).
import sys,glob,os,json,re,collections,io,contextlib
AI=os.path.expanduser('~/Projects/ai-skills'); sys.path.insert(0,AI+'/review/scripts'); sys.path.insert(0,AI+'/scripts')
import importlib.util
spec=importlib.util.spec_from_file_location('rv',AI+'/review/scripts/review.py'); rv=importlib.util.module_from_spec(spec); spec.loader.exec_module(rv)
files=glob.glob(os.path.expanduser('~/.cache/harness-logs/*-plans/**/review-*.jsonl'),recursive=True)
best={}
for f in files:
    m=re.search(r'/([^/]+)/artifacts/review-(.+)\.jsonl$',f)
    if not m: continue
    k=(m.group(1),m.group(2)); n=sum(1 for _ in open(f))
    if k not in best or n>best[k][1]: best[k]=(f,n)
fam=lambda r:('codex' if (r or '').startswith('codex') else 'fallback' if (r or '').startswith('claude-fallback') else 'lean' if (r or '').startswith('claude-lean') else 'other')
byr=collections.Counter(); fbyr=collections.Counter(); bbyr=collections.Counter(); rehit=collections.Counter(); late=collections.Counter()
lm=collections.Counter(); revfam=collections.Counter(); fails=0; maxr={}; lmafter=[]
for (scope,unit),(f,_) in best.items():
    recs=[json.loads(l) for l in open(f) if l.strip()]
    rid2={}
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            revs,lin=rv.rounds(recs,unit)
            for e in revs: rid2[e['id']]=(e['repo'],lin[e['id']][1])  # one rounds() call; review_round() per id re-runs it
    except Exception as e:
        fails+=1; continue
    revmeta={r['review_id']:r for r in recs if r.get('record')=='review'}
    for rid,(repo,rnd) in rid2.items():
        byr[min(rnd,6)]+=1; revfam[fam(revmeta.get(rid,{}).get('reviewer'))]+=1
        k=(scope,unit,repo); maxr[k]=max(maxr.get(k,0),rnd)
    seen=collections.defaultdict(set)
    for x in sorted([r for r in recs if r.get('record')=='finding'],key=lambda r:r['review_id']):
        if x['review_id'] not in rid2: continue
        repo,rnd=rid2[x['review_id']]; R=min(rnd,6)
        fbyr[R]+=1
        if x.get('severity')=='blocking': bbyr[R]+=1
        if rnd>=4:
            late[fam(x.get('reviewer'))]+=1
            if x.get('file') in seen[repo]: rehit[fam(x.get('reviewer'))]+=1
        seen[repo].add(x.get('file'))
        if x.get('category')=='local-maxima':
            lm[fam(x.get('reviewer'))]+=1; pass
    for x in [r for r in recs if r.get('record')=='finding' and r.get('category')=='local-maxima' and r['review_id'] in rid2]:
        repo,rnd=rid2[x['review_id']]; lmafter.append(maxr[(scope,unit,repo)]-rnd)
print('units',len(best),'failed',fails)
for r in sorted(byr): print(f' lineage r{r}{"+" if r==6 else ""}: reviews {byr[r]:4d} findings/rev {fbyr[r]/byr[r]:.1f} blocking/rev {bbyr[r]/byr[r]:.2f}')
T=sum(byr.values()); print(' reviews',T,'share at lineage round >=4: %.0f%%'%(100*sum(v for k,v in byr.items() if k>=4)/T))
print(' unit-repos',len(maxr),'(lineages = r1 reviews) reaching r4+:',sum(1 for v in maxr.values() if v>=4),' r6+:',sum(1 for v in maxr.values() if v>=6))
for k in late: print(f' late findings {k}: {late[k]}, re-hit within lineage repo {rehit[k]/late[k]:.0%}')
print(' local-maxima by family:',dict(lm),' reviews by family:',dict(revfam))
la=sorted(lmafter); print(' rounds in same lineage after a local-maxima flag: median',la[len(la)//2] if la else None)
