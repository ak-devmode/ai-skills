# Review-loop shape across both hosts' scope artifacts, deduped across worktree copies.
# Per reviewer family: reviews, findings/review, round depth, disposition mix (rejection
# rate = noise proxy), and the decay of findings across rounds (flat = treadmill).
import json, glob, os, re, collections

files = glob.glob(os.path.expanduser('~/.cache/harness-logs/*-plans/**/review-*.jsonl'), recursive=True)
reviews, findings, disp = {}, {}, {}
for f in files:
    scope = re.search(r'plans/([^/]+)/artifacts', f)
    scope = scope.group(1) if scope else '?'
    for l in open(f):
        try: r = json.loads(l)
        except Exception: continue
        rt = r.get('record')
        if rt == 'review':
            k = (scope, r['review_id'], json.dumps(r.get('range'), sort_keys=True))
            reviews[k] = r | {'scope': scope}
        elif rt == 'finding':
            findings[(scope, r['finding_id'], json.dumps(r.get('range'), sort_keys=True))] = r | {'scope': scope}
        elif rt == 'disposition':
            disp[(scope, r['finding_id'])] = r  # latest wins (files are append-only, roughly ts ordered)

def fam(rev):
    rev = rev or ''
    if rev.startswith('codex'): return 'codex ' + rev.split()[1] if len(rev.split()) > 1 else 'codex'
    if rev.startswith('claude-fallback'): return 'claude-fallback'
    if rev.startswith('claude-lean'): return 'claude-lean'
    return rev[:20]

rnd = lambda rid: int(re.search(r'-r(\d+)$', rid).group(1))
print('unique reviews', len(reviews), 'findings', len(findings), 'dispositions', len(disp))
print('\n-- reviewer families --')
byfam = collections.defaultdict(list)
for k, r in reviews.items(): byfam[fam(r.get('reviewer'))].append(r)
for fa, rs in sorted(byfam.items(), key=lambda x: -len(x[1])):
    fs = [x for x in findings.values() if fam(x.get('reviewer')) == fa]
    d = collections.Counter((disp.get((x['scope'], x['finding_id'])) or {}).get('disposition', 'none') for x in fs)
    sev = collections.Counter(x.get('severity') for x in fs)
    tot = max(sum(d.values()), 1)
    print(f'{fa:28s} reviews {len(rs):4d}  findings {len(fs):5d} ({len(fs)/len(rs):.1f}/rev)  '
          f'fixed {d["fixed"]/tot:.0%} rej {d["rejected"]/tot:.0%} acc {d["accepted"]/tot:.0%} def {d["deferred"]/tot:.0%} none {d["none"]/tot:.0%}  '
          f'blocking {sev["blocking"]/max(len(fs),1):.0%}')
print('\nfallback reasons:', collections.Counter(re.sub(r'\(.*', '', r.get('reviewer', ''))[:70] for r in reviews.values() if fam(r.get('reviewer')) == 'claude-fallback').most_common(8))

print('\n-- round depth per unit (unit = scope + unit prefix) --')
units = collections.defaultdict(list)
for (scope, rid, _), r in reviews.items():
    units[(scope, rid.rsplit('-r', 1)[0])].append(rnd(rid))
depth = collections.Counter(min(max(v), 13) for v in units.values())
print('units', len(units), 'max-round histogram', sorted(depth.items()))
deep = sorted(units.items(), key=lambda x: -max(x[1]))[:15]
for (s, u), v in deep: print(f'   r{max(v):2d}  {s} {u}')

print('\n-- findings by round number (all units) --')
byr = collections.Counter(); revr = collections.Counter(); blk = collections.Counter()
for x in findings.values():
    byr[min(rnd(x['review_id']), 8)] += 1
for (s, rid, _), r in reviews.items(): revr[min(rnd(rid), 8)] += 1
for x in findings.values():
    if x.get('severity') == 'blocking': blk[min(rnd(x['review_id']), 8)] += 1
for n in sorted(revr): print(f'   r{n}: reviews {revr[n]:4d}  findings/review {byr[n]/revr[n]:.1f}  blocking/review {blk[n]/revr[n]:.2f}')

print('\n-- finding categories, and target --')
print(collections.Counter(x.get('category') for x in findings.values()).most_common(14))
print(collections.Counter(x.get('target') for x in findings.values()))
print('\n-- verdicts --', collections.Counter(r.get('verdict') for r in reviews.values()).most_common(8))
print('\n-- modes --', collections.Counter((r.get('mode') or '')[:22] for r in reviews.values()).most_common(6))
# rejection reasons that cite a user decision = design decision surfaced via review
rej = [d for d in disp.values() if d.get('disposition') == 'rejected']
alex = [d for d in rej if re.search(r'Alex|chosen|decid|option [A-D]|by design|deliberate', d.get('reason', ''), re.I)]
print(f'\nrejections {len(rej)}; citing a deliberate/Alex decision {len(alex)}')
json.dump(dict(rej=[d.get('reason') for d in rej]), open(os.path.join(os.path.dirname(__file__), 'rejections.json'), 'w'))

print('\n-- late rounds (r>=4): who reviews, and do findings land on already-hit files? --')
seen = collections.defaultdict(set)  # unit -> files hit in earlier rounds
late = collections.Counter(); rehit = collections.Counter(); latecat = collections.Counter()
for x in sorted(findings.values(), key=lambda x: (x['scope'], rnd(x['review_id']))):
    u = (x['scope'], x['review_id'].rsplit('-r', 1)[0]); r = rnd(x['review_id'])
    if r >= 4:
        fa = fam(x.get('reviewer')); late[fa] += 1
        if x.get('file') in seen[u]: rehit[fa] += 1
        latecat[(x.get('category'), x.get('target'))] += 1
    seen[u].add(x.get('file'))
for fa in late: print(f'   {fa:20s} late findings {late[fa]:5d}  on already-hit file {rehit[fa]/late[fa]:.0%}')
print('   late categories', latecat.most_common(10))
lr = collections.Counter(fam(r.get('reviewer')) for (s, rid, _), r in reviews.items() if rnd(rid) >= 4)
print('   late reviews by family', lr)
