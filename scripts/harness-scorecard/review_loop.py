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


def review_logs(logs_root):
    """Every review log under `<logs_root>/*-plans/`. os.walk, not glob's `**`: glob skips hidden
    directories, and every worktree copy lives under `.herdr/worktrees/`."""
    out = []
    for top in sorted(glob.glob(os.path.join(logs_root, "*-plans"))):
        for d, _, fs in os.walk(top):
            out += [os.path.join(d, f) for f in fs if LOG_RE.search(os.path.join(d, f))]
    return sorted(out)


def load_logs(logs_root, until=None):
    """({(scope, unit): [records]}, {"files", "bad_lines", "dropped_after_until"}). Largest copy
    wins, counted after the `until` cut. A line that is not JSON is counted, never guessed at."""
    best, stats = {}, collections.Counter()
    for f in review_logs(logs_root):
        m = LOG_RE.search(f)
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
                # diffs carry file contents, which need not be UTF-8; only the ASCII hunk
                # headers and numstat counts are read, so a replaced byte changes no number
                p = subprocess.run(["git", "-C", d, *args], capture_output=True, text=True, errors="replace")
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

    def stat(self, repo, rng):
        """(files, changed lines) — verify_lib.diff_stat's shape, but None when git cannot read
        the range (diff_stat reads that as an empty diff, which effort_for calls `low`)."""
        out = self._run(repo, "diff", "--numstat", rng)
        if out is None:
            return None
        rows = [l.split("\t") for l in out.splitlines() if l.strip()]
        return len(rows), sum(int(r[0]) + int(r[1]) for r in rows if len(r) > 2 and r[0].isdigit() and r[1].isdigit())

    def changed(self, repo, rng):
        s = self.stat(repo, rng)
        return None if s is None else s[1]

    def commits(self, repo, rng):
        out = self._run(repo, "rev-list", rng)
        return None if out is None else out.split()


def _ratio(a, b):
    return round(a / b, 2) if b else None


def _pct(a, b):
    return round(100 * a / b, 1) if b else None


TIER_ORDER = ("low", "medium", "high", "xhigh")


def _trial_order(k):
    """Effort-trial row order: pre-trial before trial, base tiers lowest first (unstamped /
    unresolved last), round 1 before fix rounds."""
    b, t, *p = k
    return (b != "pre-trial", TIER_ORDER.index(t) if t in TIER_ORDER else len(TIER_ORDER), t, p != ["round 1"])


FOLLOW_UP_DAYS = 7


def analyze(units, rv, since=None, git=None, until=None, follow_up=FOLLOW_UP_DAYS * 86400):
    """All review-loop tables for `units` (from load_logs). `rv` is the loaded review.py;
    `git` a Git (None = no hunk/line analyses); `until` the cut the logs were read at (None =
    the latest stamp in them); `follow_up` the effort trial's fixed follow-up, in seconds.
    Returns {"tables": {...}, "notes": {...}}."""
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
    trial_lin = {}   # (scope, unit, root) → the lineage's facts; bucketed after every unit is read
    tiers, round_mismatch = collections.Counter(), 0
    fallback_credit, fallback_total, rejections, rej_alex = 0, 0, 0, 0

    # review_lineage's stderr is captured to keep the report readable, but never dropped: each
    # `[WARN] lineage of` is a review git could not place, continued rather than restarted at
    # round 1 — the case that inflates §3.1's late rounds. Counted per unit; any other stderr line
    # is counted apart, so nothing it said is lost without a number.
    lin_warns, other_err = collections.Counter(), collections.Counter()

    for (scope, unit), recs in sorted(units.items()):
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                revs, lin = rv.rounds(recs, unit)  # once per unit: review_round() per id re-runs this
                rules = rv.vl.lineage_rules(recs, lin)
            rounds_calls += 1
        except Exception as exc:  # one unreadable unit is reported, never silently dropped
            fails.append(f"{scope}/{unit}: {type(exc).__name__}")
            continue
        finally:
            for line in err.getvalue().splitlines():
                if line.startswith("[WARN] lineage of"):
                    lin_warns[f"{scope}/{unit}"] += 1
                elif line.strip():
                    other_err[f"{scope}/{unit}"] += 1
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

        def reviewer_of(rid):
            return (meta.get(rid) or {}).get("reviewer") or next((x.get("reviewer") for x in fnd.get(rid, [])), "")

        def base_of(e):
            """effort_for's tier for review `e` — the trial's bucket key (it decides per base tier
            whether the bump pays). ONE rule for trial and pre-trial alike: review.py's stamped
            `effort_base` when present, else effort_for on the review's own range (`unresolved`
            when git cannot read it). review.py stamps only codex reviews, so a fallback or lean
            review on either side is recomputed. `unstamped` is kept for the one review that
            should have carried a stamp and did not: a codex review under the trial's rules."""
            m = meta.get(e["id"]) or {}
            if m.get("effort_base"):
                return m["effort_base"]
            if rules.get(e["id"], 1) >= 2 and family(reviewer_of(e["id"])) == "codex":
                return "unstamped"
            st = git.stat(e["repo"], f"{e['base']}..{e['head']}") if e.get("base") and e.get("head") else None
            return rv.vl.effort_for([st])[0] if st is not None else "unresolved"

        ev_of = {e["id"]: e for e in revs}
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
            reviewer = reviewer_of(rid)
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

            # effort trial — trial (lineage rules 2+) vs pre-trial, per base tier, then round 1 vs
            # fix rounds. A codex row takes its own review's base; a lineage its root's.
            bucket = "trial" if rules.get(rid, 1) >= 2 else "pre-trial"
            phase = "round 1" if rnd == 1 else "fix rounds"
            lk = (bucket, base_of(ev_of[root]) if root in ev_of else "unresolved")
            L = trial_lin.get((scope, unit, root))
            if L is None:
                L = trial_lin[(scope, unit, root)] = {"lk": lk, "root_ts": ts_of(root), "in_window": counted(root),
                                                      "maxr": 0, "all": 0, "out": 0, "ship": False, "unplaced": 0}
            # the outcome is read over the fixed follow-up only: reviews within `follow_up` of the
            # root. A review with no stamp cannot be placed in it, so it is left out (fail closed:
            # counting it would let an unbounded tail back in) and counted under the notes.
            t, rt = ts_of(rid), L["root_ts"]
            if t is None or rt is None:
                L["unplaced"] += rt is not None
            elif t - rt <= follow_up:
                L["maxr"] = max(L["maxr"], rnd)
                L["all"] += 1
                L["out"] += fa == "fallback" and "out of credits" in reviewer
                L["ship"] |= m.get("verdict") == "SHIP"
            if fa == "codex":
                ck = (bucket, base_of(e), phase)
                tr_rev[ck] += 1; tr_find[ck] += len(fs); tr_blk[ck] += nblk
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
        "rows": {f"{b} · base {t} · {p}": [tr_rev[k], _ratio(tr_find[k], tr_rev[k]), _ratio(tr_blk[k], tr_rev[k])]
                 for k in sorted(tr_rev, key=_trial_order) for b, t, p in [k]}}
    # Fixed follow-up: a lineage counts when its root is in the window and at least `follow_up`
    # before the cut, and its outcome (fix rounds, credit-outs, SHIP) is read only from reviews
    # within `follow_up` of its root — the same for every bucket, nothing estimated from the data,
    # nothing depending on whether it closed. Every counted lineage is then observed for the full
    # follow-up, so the newest (trial) lineages are not cut short at `until` (right-censoring).
    # With no cut at all (no stamp anywhere) none can be placed, so none is counted (fail closed).
    lin_list = list(trial_lin.values())
    cut = until if until is not None else max((t for recs in units.values() for t in (parse_ts(r.get("ts")) for r in recs)
                                                if t is not None), default=None)
    lin_by, tr_all, tr_out, tr_ship = (collections.defaultdict(list), collections.Counter(),
                                       collections.Counter(), collections.Counter())
    tr_young, tr_before, tr_nots = (collections.Counter() for _ in range(3))
    unplaced = 0
    for L in lin_list:
        lk = L["lk"]
        if L["root_ts"] is None:
            tr_nots[lk] += 1     # no stamp: neither the window nor the follow-up can place it
        elif not L["in_window"]:
            tr_before[lk] += 1   # its round 1 predates the window
        elif cut is None or L["root_ts"] > cut - follow_up:
            tr_young[lk] += 1    # rooted after until − F: its follow-up is not over
        else:
            lin_by[lk].append(L["maxr"])
            tr_all[lk] += L["all"]; tr_out[lk] += L["out"]; tr_ship[lk] += L["ship"]
            unplaced += L["unplaced"]
    tables["Effort trial lineages"] = {
        "cols": ["Lineages", "Fix rounds/lineage", "Credit-outs %", "SHIP within follow-up %",
                 "Too young (rooted after until − F)", "Rooted before window (excluded)", "Unstamped root (excluded)"],
        "rows": {f"{b} · base {t}": [len(lin_by[(b, t)]), _ratio(sum(x - 1 for x in lin_by[(b, t)]), len(lin_by[(b, t)])),
                                     _pct(tr_out[(b, t)], tr_all[(b, t)]), _pct(tr_ship[(b, t)], len(lin_by[(b, t)])),
                                     tr_young[(b, t)], tr_before[(b, t)], tr_nots[(b, t)]]
                 for b, t in sorted({L["lk"] for L in lin_list}, key=_trial_order)}}
    notes = {"rounds_calls": rounds_calls, "failed_units": fails, "trial_effort_tiers": dict(tiers),
             "trial_follow_up": {"days": round(follow_up / 86400, 2), "unplaced_reviews": unplaced},
             "stamped_round_mismatches": round_mismatch,
             "lineage_warns": {"total": sum(lin_warns.values()), "units": dict(sorted(lin_warns.items()))},
             "other_stderr_lines": {"total": sum(other_err.values()), "units": dict(sorted(other_err.items()))}}
    return {"tables": tables, "notes": notes}
