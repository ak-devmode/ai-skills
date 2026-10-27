"""Review-loop analyses for the harness scorecard (baseline §3, §3.1–§3.3, plus the effort trial).

Approach: the review logs (`<logs>/*-plans/**/artifacts/review-<unit>.jsonl`, both hosts' copies)
are read once, deduped across worktree copies by keeping the largest log per (scope, unit), and
cut at `until` (a record stamped later is dropped, so a past window sees the logs as they were).
Rounds are the gate's own: review.py `rounds()` is called ONCE per unit — never `review_round()`
per id, which re-runs it (quadratic) — and never the unit's `r<n>`. The lineage needs the whole
history, so every record up to `until` feeds `rounds()`; only reviews stamped at or after `since`
are counted. review.py's lineage rule is versioned (decision 65): an unstamped (pre-cutover)
lineage keeps the old rule, which is why a re-run on the baseline window reproduces it.

Every function returns aggregates only — counts and ratios, never finding text — because the
scorecard stores its numbers on disk and logs can carry patient data.
"""

import collections
import contextlib
import glob
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_RE = re.compile(r"/([^/]+)/artifacts/review-(.+)\.jsonl$")
ALEX_DECISION = re.compile(r"Alex|chosen|decid|option [A-D]|by design|deliberate", re.I)


def load_review_module():
    """review/scripts/review.py loaded by path (it puts scripts/ on sys.path for verify_lib)."""
    spec = importlib.util.spec_from_file_location("hs_review", os.path.join(REPO, "review", "scripts", "review.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_ts(s):
    """ISO-8601 (`Z` or offset) → epoch seconds; None when absent or unreadable."""
    if not isinstance(s, str) or not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def family(reviewer):
    r = reviewer or ""
    return ("codex" if r.startswith("codex") else "fallback" if r.startswith("claude-fallback")
            else "lean" if r.startswith("claude-lean") else "other")


def family_detail(reviewer):
    """codex split by model (`codex gpt-6.1-sol`), as baseline §3's reviewer table."""
    r = reviewer or ""
    if r.startswith("codex"):
        parts = r.split()
        return "codex " + parts[1] if len(parts) > 1 else "codex"
    return {"fallback": "claude-fallback", "lean": "claude-lean"}.get(family(r), r[:20] or "unknown")


def load_logs(logs_root, until=None):
    """({(scope, unit): [records]}, {"files", "bad_lines", "dropped_after_until"}). Largest copy
    wins, counted after the `until` cut. A line that is not JSON is counted, never guessed at."""
    best, stats = {}, collections.Counter()
    for f in glob.glob(os.path.join(logs_root, "*-plans", "**", "review-*.jsonl"), recursive=True):
        m = LOG_RE.search(f)
        if not m:
            continue
        stats["files"] += 1
        recs = []
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    stats["bad_lines"] += 1
                    continue
                t = parse_ts(r.get("ts"))
                if until is not None and t is not None and t > until:
                    stats["dropped_after_until"] += 1
                    continue
                recs.append(r)
        k = (m.group(1), m.group(2))
        if recs and (k not in best or len(recs) > len(best[k])):
            best[k] = recs
    return best, dict(stats)


class Git:
    """Diff hunks and changed-line counts per (repo, range), cached; None when git cannot read it
    (the range's commits are not in the local clone) — counted as unresolved, never guessed."""

    def __init__(self, projects, enabled=True):
        self.projects, self.enabled, self.cache = projects, enabled, {}

    def _run(self, repo, *args):
        if not self.enabled:
            return None
        k = (repo, args)
        if k not in self.cache:
            d = os.path.join(self.projects, repo)
            out = None
            if os.path.isdir(d):
                p = subprocess.run(["git", "-C", d, *args], capture_output=True, text=True)
                out = p.stdout if p.returncode == 0 else None
            self.cache[k] = out
        return self.cache[k]

    def hunks(self, repo, rng):
        out = self._run(repo, "diff", "-U0", "--no-color", rng)
        if out is None:
            return None
        h, cur = collections.defaultdict(list), None
        for line in out.splitlines():
            if line.startswith("+++ "):
                cur = line[6:] if line.startswith("+++ b/") else None
            elif line.startswith("@@") and cur:
                m = re.search(r"\+(\d+)(?:,(\d+))?", line)
                s, n = int(m.group(1)), int(m.group(2) or 1)
                h[cur].append((s, s + max(n, 1) - 1))
        return h

    def changed(self, repo, rng):
        out = self._run(repo, "diff", "--numstat", rng)
        if out is None:
            return None
        return sum(int(a) + int(b) for a, b, *_ in (l.split("\t") for l in out.splitlines())
                   if a.isdigit() and b.isdigit())

    def commits(self, repo, rng):
        out = self._run(repo, "rev-list", rng)
        return None if out is None else out.split()


def _ratio(a, b):
    return round(a / b, 2) if b else None


def _pct(a, b):
    return round(100 * a / b, 1) if b else None


def analyze(units, rv, since=None, git=None):
    """All review-loop tables for `units` (from load_logs). `rv` is the loaded review.py;
    `git` a Git (None = no hunk/line analyses). Returns {"tables": {...}, "notes": {...}}."""
    git = git or Git("", enabled=False)
    rounds_calls = 0
    fails = []
    # accumulators
    fam_rev, fam_find, fam_blk, fam_disp = (collections.Counter(), collections.Counter(),
                                            collections.Counter(), collections.defaultdict(collections.Counter))
    byr, fbyr, bbyr = collections.Counter(), collections.Counter(), collections.Counter()
    late, rehit, lm, lm_after = collections.Counter(), collections.Counter(), collections.Counter(), []
    lineages = set()
    infix_rev, infix_find, infix = collections.Counter(), collections.Counter(), collections.defaultdict(collections.Counter)
    fp_rev, fp_find, fp_lines = collections.Counter(), collections.Counter(), collections.Counter()
    tr_rev, tr_find, tr_blk = collections.Counter(), collections.Counter(), collections.Counter()
    tr_lin_max, tr_all, tr_out = {}, collections.Counter(), collections.Counter()
    tiers, round_mismatch = collections.Counter(), 0
    fallback_credit, fallback_total, rejections, rej_alex = 0, 0, 0, 0

    for (scope, unit), recs in sorted(units.items()):
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                revs, lin = rv.rounds(recs, unit)  # once per unit: review_round() per id re-runs this
                rules = rv.vl.lineage_rules(recs, lin)
            rounds_calls += 1
        except Exception as exc:  # one unreadable unit is reported, never silently dropped
            fails.append(f"{scope}/{unit}: {type(exc).__name__}")
            continue
        meta = {r.get("review_id"): r for r in recs if r.get("record") == "review"}
        fnd = collections.defaultdict(list)
        for r in recs:
            if r.get("record") == "finding":
                fnd[r.get("review_id")].append(r)
        disp = {}
        for r in recs:
            if r.get("record") == "disposition":
                disp[r.get("finding_id")] = r  # append-only log: latest wins
        fixshas = {r.get("sha") for r in disp.values() if r.get("disposition") == "fixed" and r.get("sha")}

        def ts_of(rid):
            t = parse_ts((meta.get(rid) or {}).get("ts"))
            if t is None:
                ts = [parse_ts(x.get("ts")) for x in fnd.get(rid, [])]
                ts = [t for t in ts if t is not None]
                t = min(ts) if ts else None
            return t

        def counted(rid):
            # a review with no timestamp at all is kept only when no lower bound is asked for
            t = ts_of(rid)
            return since is None or (t is not None and t >= since)

        heads, byhead, kind, maxr = collections.defaultdict(set), {}, {}, {}
        for e in revs:
            rid, repo = e["id"], e["repo"]
            rnd = lin[rid][1]
            prev = byhead.get((repo, e["base"]))
            kind[rid] = ("r1" if rnd == 1 else "fix" if e["base"] in heads[repo] else "wide", prev)
            heads[repo].add(e["head"])
            byhead[(repo, e["head"])] = rid
            maxr[lin[rid][0]] = max(maxr.get(lin[rid][0], 0), rnd)

        seen = collections.defaultdict(set)
        for e in revs:
            rid, repo = e["id"], e["repo"]
            root, rnd = lin[rid]
            m = meta.get(rid) or {}
            reviewer = m.get("reviewer") or next((x.get("reviewer") for x in fnd.get(rid, [])), "")
            fa, fs = family(reviewer), fnd.get(rid, [])
            nblk = sum(1 for x in fs if x.get("severity") == "blocking")
            inwin = counted(rid)
            if inwin:
                R = min(rnd, 6)
                byr[R] += 1; fbyr[R] += len(fs); bbyr[R] += nblk
                if rnd == 1:
                    lineages.add((scope, unit, root))
                fd = family_detail(reviewer)
                fam_rev[fd] += 1; fam_find[fd] += len(fs); fam_blk[fd] += nblk
                for x in fs:
                    fam_disp[fd][(disp.get(x.get("finding_id")) or {}).get("disposition", "none")] += 1
                if fa == "fallback":
                    fallback_total += 1
                    fallback_credit += "out of credits" in reviewer
            for x in fs:
                if inwin and rnd >= 4:
                    late[fa] += 1
                    rehit[fa] += x.get("file") in seen[repo]
                if inwin and x.get("category") == "local-maxima":
                    lm[fa] += 1
                    lm_after.append(maxr[root] - rnd)
                seen[repo].add(x.get("file"))
            if not inwin:
                continue

            # §3.2 — finding file:line against its own review's diff hunks
            k, prev = kind[rid]
            ikey = f"{fa} {'r1' if k == 'r1' else 'r2+ ' + ('fix-only' if k == 'fix' else 'wide')}"
            infix_rev[ikey] += 1; infix_find[ikey] += len(fs)
            rng = (m.get("range") or {})
            rng = rng.get(next(iter(rng), None)) if isinstance(rng, dict) and rng else None
            h = git.hunks(repo, rng) if rng else None
            for x in fs:
                try:
                    line = int(x.get("line"))
                except (TypeError, ValueError):
                    line = None
                if h is None or line is None:
                    infix[ikey]["unresolved"] += 1
                elif (x.get("file") or "") not in h:
                    infix[ikey]["other file"] += 1
                elif any(a - 3 <= line <= b + 3 for a, b in h[x.get("file")]):
                    infix[ikey]["in hunks"] += 1
                else:
                    infix[ikey]["same file, outside"] += 1

            # §3.3 — codex findings per 100 changed lines: round 1, pure fix, fix + new
            if fa == "codex" and k != "wide" and rng:
                c = git.changed(repo, rng)
                if c is not None:
                    fk = "round 1" if k == "r1" else "pure fix"
                    if k == "fix":
                        cs = git.commits(repo, rng) or []
                        fk = "pure fix" if cs and all(sh in fixshas for sh in cs) else "fix + new"
                    fp_rev[fk] += 1; fp_find[fk] += len(fs); fp_lines[fk] += c

            # effort trial — round 1 vs fix rounds, trial (lineage rules 2+) vs pre-trial
            bucket = "trial" if rules.get(rid, 1) >= 2 else "pre-trial"
            phase = "round 1" if rnd == 1 else "fix rounds"
            tr_all[bucket] += 1
            tr_out[bucket] += fa == "fallback" and "out of credits" in reviewer
            tr_lin_max[(scope, unit, root, bucket)] = max(tr_lin_max.get((scope, unit, root, bucket), 0), rnd)
            if fa == "codex":
                tr_rev[(bucket, phase)] += 1; tr_find[(bucket, phase)] += len(fs); tr_blk[(bucket, phase)] += nblk
                if bucket == "trial":
                    tiers[m.get("effort") or "unstamped"] += 1
            if isinstance(m.get("round"), int) and m["round"] != rnd:
                round_mismatch += 1

        rid_of = {f.get("finding_id"): rid for rid, fl in fnd.items() for f in fl}
        for x in disp.values():
            if x.get("disposition") == "rejected" and x.get("finding_id") in rid_of and counted(rid_of[x["finding_id"]]):
                rejections += 1
                rej_alex += bool(ALEX_DECISION.search(x.get("reason") or ""))

    T = sum(byr.values())
    tables = collections.OrderedDict()
    tables["3 Reviewers"] = {
        "cols": ["Reviews", "Findings/review", "Blocking %", "Fixed %", "Rejected %"],
        "rows": {fd: [fam_rev[fd], _ratio(fam_find[fd], fam_rev[fd]), _pct(fam_blk[fd], fam_find[fd]),
                      _pct(fam_disp[fd]["fixed"], sum(fam_disp[fd].values())),
                      _pct(fam_disp[fd]["rejected"], sum(fam_disp[fd].values()))]
                 for fd in sorted(fam_rev, key=lambda k: -fam_rev[k])}}
    tables["3.1 Lineage rounds"] = {
        "cols": ["Reviews", "Share %", "Findings/rev", "Blocking/rev"],
        "rows": {f"r{r}{'+' if r == 6 else ''}": [byr[r], _pct(byr[r], T), _ratio(fbyr[r], byr[r]), _ratio(bbyr[r], byr[r])]
                 for r in sorted(byr)}}
    tables["3.1 Lineage summary"] = {
        "cols": ["Value"],
        "rows": {"units": [len(units) - len(fails)], "reviews": [T], "lineages (r1 reviews)": [len(lineages)],
                 "reviews per lineage": [_ratio(T, len(lineages))],
                 "share at round >=4 %": [_pct(sum(v for k, v in byr.items() if k >= 4), T)],
                 "median rounds after local-maxima": [sorted(lm_after)[len(lm_after) // 2] if lm_after else None],
                 **{f"local-maxima {k}": [lm[k]] for k in sorted(lm)},
                 **{f"late re-hit % {k}": [_pct(rehit[k], late[k])] for k in sorted(late)},
                 "fallback out of credits": [fallback_credit], "fallback reviews": [fallback_total],
                 "rejections": [rejections], "rejections citing a decision": [rej_alex]}}
    tables["3.2 Where findings land"] = {
        "cols": ["Reviews", "Findings/rev", "In hunks %", "Same file, outside %", "Other file %", "Unresolved"],
        "rows": {}}
    for k in sorted(infix_rev):
        c = infix[k]; tot = c["in hunks"] + c["same file, outside"] + c["other file"]
        tables["3.2 Where findings land"]["rows"][k] = [
            infix_rev[k], _ratio(infix_find[k], infix_rev[k]), _pct(c["in hunks"], tot),
            _pct(c["same file, outside"], tot), _pct(c["other file"], tot), c["unresolved"]]
    tables["3.3 Codex findings per changed line"] = {
        "cols": ["Reviews", "Findings/rev", "Per 100 lines"],
        "rows": {k: [fp_rev[k], _ratio(fp_find[k], fp_rev[k]), _ratio(100 * fp_find[k], fp_lines[k])]
                 for k in ("round 1", "pure fix", "fix + new") if fp_rev[k]}}
    tables["Effort trial (codex)"] = {
        "cols": ["Reviews", "Findings/rev", "Blocking/rev"],
        "rows": {f"{b} · {p}": [tr_rev[(b, p)], _ratio(tr_find[(b, p)], tr_rev[(b, p)]), _ratio(tr_blk[(b, p)], tr_rev[(b, p)])]
                 for b in ("pre-trial", "trial") for p in ("round 1", "fix rounds") if tr_rev[(b, p)]}}
    lin_by = collections.defaultdict(list)
    for (_, _, _, b), mx in tr_lin_max.items():
        lin_by[b].append(mx)
    tables["Effort trial lineages"] = {
        "cols": ["Lineages", "Fix rounds/lineage", "Credit-outs %"],
        "rows": {b: [len(lin_by[b]), _ratio(sum(v - 1 for v in lin_by[b]), len(lin_by[b])), _pct(tr_out[b], tr_all[b])]
                 for b in ("pre-trial", "trial") if lin_by[b]}}
    notes = {"rounds_calls": rounds_calls, "failed_units": fails, "trial_effort_tiers": dict(tiers),
             "stamped_round_mismatches": round_mismatch}
    return {"tables": tables, "notes": notes}
