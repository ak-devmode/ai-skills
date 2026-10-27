#!/usr/bin/env python3
"""verdict-gate.py — may this unit be marked Done? Reads the finish table, the verdict
log, the review log and the ledger's base SHAs; decides nothing a script can't.

Approach: for every finish-table row the unit owns, find the latest `final` verdict and
block on anything templates/verify-contracts.md §5.2 names — no verdict, an unfinished
newer run, fail / inconclusive, undeclared unreachable, under-rung, a table revision
change, or evidence whose SHA sits outside the unit's `base..HEAD` (base = the SHA
ledger-init.sh recorded at phase start; with no base, evidence must be at HEAD). Then
§5.2.1: every review finding carries a disposition. A non-codex judge on a deciding
verdict yields the `⚠ judge:` marker (§5.3). In advisory mode (§5.4) the same blocks are
reported with exit 0 and an advisory marker; `--skip-verify` bypasses loudly. A unit the
table lists under `**Predates gate:**` was Done before the gate existed: exempt, exit 0.
`--all` is /closeout's view: every gated unit in the table, and any block is a failure
whatever the mode — the scope cannot report HEALED on it (scope 5 §4.3).

Usage:  verdict-gate.py --scope DIR (--unit N.P | --all) [--advisory|--blocking]
                        [--skip-verify REASON] [--projects DIR] [--json]
        paths: DIR/finish-conditions.md · DIR/artifacts/verify-<unit>.jsonl ·
               DIR/artifacts/review-<unit>.jsonl (optional) · DIR/closeout-prep.md (bases)
Output: one line per owned check, a §10 message per block, then `verdict: …` and, when
        set, `marker: …` (the text plans-index.py appends to the index status).
Exit:   0 pass / advisory / skipped · 1 blocked · 2 usage · 3 could not evaluate
"""

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import landed_lib as ll  # noqa: E402
import verify_lib as vl  # noqa: E402

DOCS = f"{vl.CONTRACT} §5"


def git_ok(path, *args):
    return subprocess.run(["git", "-C", path, *args], capture_output=True, text=True).returncode == 0


def git_out(path, *args):
    p = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


class HistoryError(Exception):
    """A git query the coverage check depends on failed; the caller blocks, never guesses."""


def _git_list(path, *args):
    out = git_out(path, *args)
    if out is None:
        raise HistoryError("git " + " ".join(args))
    return out.split()


def is_ancestor(path, a, b):
    """git merge-base --is-ancestor a b: True / False, and HistoryError when git cannot answer
    (an unknown sha). Never negate git_ok for this — a git error would read as "not an ancestor"."""
    r = subprocess.run(["git", "-C", path, "merge-base", "--is-ancestor", a, b], capture_output=True, text=True)
    if r.returncode not in (0, 1):
        raise HistoryError(f"git merge-base --is-ancestor {a} {b}")
    return r.returncode == 0


def names_unit(path, sha, unit):
    """The commit's subject names the unit (`164.2` in `Merge pull request #514 from
    org/feature/164.2-etude-connector`, or in a squash merge's PR title). Branches carry the
    unit number by convention (/concurrency `concurrency/<scope>-<task>`, `fix/<N.P>-…`)."""
    if not unit:
        return False
    subject = git_out(path, "log", "-1", "--format=%s", sha)
    if subject is None:
        raise HistoryError(f"git log -1 {sha}")
    return re.search(rf"(?<![\d.]){re.escape(unit)}(?![\d])", subject) is not None


def first_unit_commit(path, b, tip, heads, unit=None):
    """The unit's oldest commit in b..tip, or None when no first-parent step is evidently the
    unit's (the caller then falls back to the oldest commit in b..tip, as before).

    On a shared trunk other units land between the unit's base and its own merge (164.2:
    backbone's oldest commit since the base was 163.2's, infra's 158.3's, so a reviewed unit read
    "never reviewed"). Git alone cannot tell this unit's PR from another's, so a first-parent step
    counts as the unit's only on evidence: its side holds one of the unit's reviewed heads, or its
    subject names the unit. On the lane (tip = HEAD) a non-merge first-parent commit is the unit's
    own. Residual: a unit PR whose name omits the unit number and whose side holds no reviewed
    head is not counted — the naming convention carries that case. A failed git query raises
    HistoryError; it is never read as "not a merge"."""
    for c in _git_list(path, "rev-list", "--first-parent", "--reverse", f"{b}..{tip}"):
        line = _git_list(path, "rev-list", "--parents", "-n1", c)
        parents = line[1:]
        if len(parents) <= 1:
            if tip == "HEAD" or names_unit(path, c, unit):
                return c
            continue
        holds = any(is_ancestor(path, h, side) for h in heads for side in parents[1:])
        if holds or names_unit(path, c, unit):
            # Not what the base already reaches: a lane whose base merged the trunk in lands
            # that trunk with it, older than the unit's own work (kalpa-iris 8.3).
            brought = _git_list(path, "rev-list", "--reverse", c, f"^{parents[0]}", f"^{b}")
            return brought[0] if brought else c
    return None


def coverage_blocks(review_log):
    """§6.3 / §5.2.1 — findings without a valid latest disposition."""
    recs = vl.read_jsonl(review_log)
    findings = [r for r in recs if r.get("record") == "finding"]
    latest = {}
    for r in recs:
        if r.get("record") == "disposition":
            latest[r.get("finding_id")] = r
    blocks = []
    ids = [f.get("finding_id") for f in findings]
    for fid in sorted({i for i in ids if ids.count(i) > 1}):
        # One disposition must never clear two findings (review 5.2-r1-04).
        blocks.append((fid, "duplicate finding ID", "one finding per finding_id",
                       f"{ids.count(fid)} findings share it", f"{review_log} · {fid}", "tooling"))
    for f in findings:
        fid, d = f.get("finding_id"), latest.get(f.get("finding_id"))
        where = f"{review_log} · {fid} ({f.get('file')}:{f.get('line')})"
        if d is None:
            blocks.append((fid, "review finding has no disposition", "`fixed <sha>`, `rejected <reason>`, "
                           "`deferred <TO-DO>`, `accepted <process nit>` or `reframed <what> --commit <sha>`",
                           "no disposition recorded", where, "code"))
        elif d.get("disposition") == "fixed" and not d.get("sha"):
            blocks.append((fid, "`fixed` disposition without a commit", "the fixing commit's SHA",
                           "sha missing", where, "code"))
        elif d.get("disposition") == "fixed" and d.get("via") == "off-anchor" and not str(d.get("reason") or "").strip():
            blocks.append((fid, "`fixed` off the anchor without a reason",
                           "how a commit that touches neither the file nor a test beside it fixes the finding",
                           "reason missing", where, "code"))
        elif d.get("disposition") == "rejected" and not str(d.get("reason") or "").strip():
            blocks.append((fid, "`rejected` disposition without a reason", "the reason the finding is wrong",
                           "reason missing", where, "code"))
        elif d.get("disposition") == "deferred" and (
                f.get("severity") == "blocking"
                or not str(d.get("reason") or "").strip()
                or not vl.todo_has_item(os.path.dirname(os.path.dirname(review_log)), fid, open_only=False)):
            blocks.append((fid, "`deferred` disposition on a blocking finding, or its TO-DO item is gone",
                           "a non-blocking finding whose TO-DO item exists (open, or closed into the archive)",
                           f"severity {f.get('severity')}, reason {d.get('reason')!r}", where, "code"))
        elif d.get("disposition") == "accepted" and (
                f.get("severity") == "blocking" or not str(d.get("reason") or "").strip()):
            # a process nit, noted (review/SKILL.md §5.1) — never a blocking finding, never unexplained
            blocks.append((fid, "`accepted` disposition on a blocking finding, or without a reason",
                           "a non-blocking process nit with the reason it stands",
                           f"severity {f.get('severity')}, reason {d.get('reason')!r}", where, "code"))
        elif d.get("disposition") == "reframed" and (
                not d.get("sha") or not str(d.get("reason") or "").strip()
                or not vl.REFRAMED_BY.match(str(d.get("by") or ""))):
            # an accepted reframe replaced the code (review/SKILL.md §5.1): counted like a deferral,
            # never audited as a rejection; its commit is wanted re-reviewed below
            blocks.append((fid, "`reframed` disposition without its commit, what changed, or who accepted it",
                           "`reframed \"<what changed>\" --commit <sha> --by judge|user`",
                           f"sha {d.get('sha')!r}, reason {d.get('reason')!r}, by {d.get('by')!r}", where, "code"))
        elif d.get("disposition") not in ("fixed", "rejected", "deferred", "accepted", "reframed"):
            blocks.append((fid, "unknown disposition", "`fixed`, `rejected`, `deferred`, `accepted` or `reframed`",
                           repr(d.get("disposition")), where, "tooling"))
    return blocks, len(findings)


def accepted_nits(review_log):
    """The finding IDs whose latest disposition is `accepted` — process nits, listed apart from
    rejections (review/SKILL.md §5.1); `/verify` never audits them as rejections."""
    return [d.get("finding_id") for _, d in vl.accepted_nits(vl.read_jsonl(review_log))]


def accepted(review_log):
    """§6.4: the log's last finding/disposition is followed by an `acceptance` record."""
    last = None
    for r in vl.read_jsonl(review_log):
        if r.get("record") in ("finding", "disposition"):
            last = "open"
        elif r.get("record") == "acceptance" and str(r.get("by") or "").strip():
            last = "accepted"
    return last == "accepted"


def fallback_markers(review_log, projects, scope=None):
    """`review <reviewer>` for each fallback review no later codex review covers (review/SKILL.md
    §3). Covered = same repo, codex base an ancestor of the fallback's base, fallback head an
    ancestor of codex head (review 5.2-r2-01). Records without resolved `shas` cannot prove
    coverage, so they keep the marker; logs predating `review` records use the latest
    finding's reviewer."""
    recs = vl.read_jsonl(review_log)
    reviews = [r for r in recs if r.get("record") == "review"]
    if not reviews:
        f = [r for r in recs if r.get("record") == "finding"]
        return [f"review {f[-1].get('reviewer', 'unrecorded')}"] if f and not \
            str(f[-1].get("reviewer", "")).startswith("codex ") else []

    def covers(c, f):
        (repo, _), = f["range"].items()
        cs, fs = c.get("shas") or {}, f.get("shas") or {}
        path = vl.repo_root(projects, repo, scope)
        return (repo in c.get("range", {}) and all(cs.get(k) and fs.get(k) for k in ("base", "head"))
                and git_ok(path, "merge-base", "--is-ancestor", cs["base"], fs["base"])
                and git_ok(path, "merge-base", "--is-ancestor", fs["head"], cs["head"]))

    out = []
    for i, f in enumerate(reviews):
        if str(f.get("reviewer", "")).startswith("codex "):
            continue
        if not any(str(c.get("reviewer", "")).startswith("codex ") and covers(c, f) for c in reviews[i + 1:]):
            out.append(f"review {f.get('reviewer', 'unrecorded')}")
    return out


def round_no(review_id):
    """n of a `<unit>-r<n>` review ID; -1 when it has none (never later than anything)."""
    m = re.search(r"-r(\d+)$", str(review_id or ""))
    return int(m.group(1)) if m else -1


def known_shas(recs):
    """Every SHA a log names — the lane commits a squash-merged fix can ride in on (§5.2.2)."""
    return {s for r in recs for s in [*(r.get("shas") or {}).values(), r.get("sha")] if s}


def review_presence_blocks(review_log, base, projects, scope=None, unit=None):
    """§5.2.1 — a unit with commits must have been reviewed (review 5.3-r1-03).

    For every repo whose ledger base has commits in base..HEAD, some `review` record must
    name that repo and cover the unit's start: its base at or before the unit's base, its head
    after it AND on the current branch (a review of a discarded branch covers nothing —
    5.3-r2-03). Later commits (progress notes) don't force a re-review. The fix of every
    *blocking* finding must itself sit inside a later review's range, which is /plan §6.8's
    "review the fixes again" (5.3-r2-03) — and so must every `off-anchor` fix, whatever the
    severity: nothing but a reason ties that commit to the finding (review adhoc-03) — until the
    finding's review lineage reaches the round cap without SHIP and an acceptance follows the disposition
    (`stopped`).
    A git call that fails is a block, never a zero (5.3-r2-02)."""
    ll.reset()
    recs = vl.read_jsonl(review_log) if os.path.exists(review_log) else []
    reviews = [r for r in recs if r.get("record") == "review"]
    # Logs from before `review` records existed (§6.0) carry the range on each finding.
    for f in recs:
        if f.get("record") == "finding" and not any(r.get("review_id") == f.get("review_id") for r in reviews):
            for repo_, rng in (f.get("range") or {}).items():
                fb, _, fh = rng.partition("..")
                if fb and fh:
                    reviews.append({"review_id": f.get("review_id"), "range": {repo_: rng},
                                    "shas": {"base": fb, "head": fh}})
    blocks = []
    known = known_shas(recs)

    def canon(key):
        return vl.canonical_key(key, projects)

    def root(repo):  # the scope's own worktree when it is one (verify_lib.repo_root, §3.2.1)
        return vl.repo_root(projects, canon(repo), scope)

    def names(r, repo):  # the record's range names this repo, under any key for it
        return any(canon(k) == canon(repo) for k in r.get("range", {}))

    def inside(path, r, sha):
        """sha is in the range r.base..r.head as git reads one — reachable from the head, not
        from the base — and r.head landed: on the current branch or the trunk, an ancestor or
        squash/rebase-merged (§5.2.2). Not "base is an ancestor of sha": a review taken after the
        trunk was merged into the lane has that merge as its base, and the lane's commits from
        before it are in its range and were read (kalpa-iris 5.2)."""
        sh = r.get("shas") or {}
        return bool(sh.get("base") and sh.get("head")) and not sha.startswith(sh["base"]) \
            and not sh["base"].startswith(sha) \
            and not is_ancestor(path, sha, sh["base"]) \
            and is_ancestor(path, sha, sh["head"]) \
            and ll.landed(path, sh["head"], known) is not None

    def squash_covers(path, r, b, tip):
        """§5.2.2: the commit S on tip's first-parent line after the unit's base in which the
        review's net diff (base..head) arrived — S, not the lane commits, is what base..tip holds —
        or None."""
        sh = r.get("shas") or {}
        s = sh.get("base") and sh.get("head") and ll.arrival(path, sh["base"], sh["head"], tip)
        return s if s and not s.startswith(b) and is_ancestor(path, b, s) else None

    for repo, b in sorted(base.items()):
        path = root(repo)
        mine = [r for r in reviews if names(r, repo)]
        counted, covered = [], False
        # the unit's commits sit on HEAD while it is on its lane, on the trunk once merged (§5.2.2)
        for tip in ll.targets(path):
            n = git_out(path, "rev-list", "--count", f"{b}..{tip}")
            if n is None:
                blocks.append((f"review:{repo}", "cannot count the unit's commits", f"git rev-list {b[:10]}..{tip} "
                               f"in {repo}", "git failed", f"{path}", "environment"))
                covered = True  # reported; one block per repo
                break
            if n == "0":
                continue
            counted.append(f"{n} commit(s) in {b[:10]}..{tip}")
            # the unit's first commit must sit inside a review on this branch, or a squash
            # commit in the range must hold a review's net diff
            # On its lane the unit's own commits are HEAD's first-parent line: what a merge of
            # the trunk brought in is another unit's, reviewed there, and is not this unit's
            # first commit (kalpa-iris 5.2: scope 4's commits, merged in from develop, were).
            # On a shared trunk the same holds for other units' PR merges (first_unit_commit).
            # A squash landing covers only when it IS the unit's first landing: a later squash
            # reviewed from the unit's first merge on must not clear an unreviewed first PR.
            heads = [h for h in ((r.get("shas") or {}).get("head") for r in mine) if h]
            try:
                found = first_unit_commit(path, b, tip, heads, unit)
                first = found
                if first is None:
                    oldest = (git_out(path, "rev-list", "--reverse", f"{b}..{tip}") or "").splitlines()[:1]
                    first = oldest[0] if oldest else None
                landings = [s for s in (squash_covers(path, r, b, tip) for r in mine) if s]
                ok = any(first and inside(path, r, first) for r in mine) \
                    or any(found is None or s == found for s in landings)
            except HistoryError as e:
                blocks.append((f"review:{repo}", "cannot determine the unit's first commit", f"{e} in {repo}",
                               "git failed", f"{path}", "environment"))
                covered = True  # reported; one block per repo
                break
            if ok:
                covered = True
                break
        if counted and not covered:
            blocks.append((f"review:{repo}", "commits in range were never reviewed",
                           f"a /review record covering {b[:10]}.. in {repo}, on HEAD or the trunk",
                           f"{'; '.join(counted)}, {len(mine)} review record(s) for {repo}, none covering it",
                           f"{review_log} · {repo}", "code"))
    latest, at = {}, {}
    for i, r in enumerate(recs):
        if r.get("record") == "disposition":
            latest[r.get("finding_id")], at[r.get("finding_id")] = r, i

    # rounds count per review lineage, not per repo (verify_lib.review_lineage; WellMed 171.2)
    ordered = sorted(reviews, key=lambda r: round_no(r.get("review_id")))
    lineage = vl.review_lineage(
        [(r.get("review_id"), canon(next(iter(r.get("range") or {}), "")), (r.get("shas") or {}).get("base"),
          (r.get("shas") or {}).get("head")) for r in ordered], root, *vl.lineage_links(recs))
    rules = vl.lineage_rules(recs, lineage)

    def budgeted_note(f):
        """review/SKILL.md §5.1 findings budget (rules 2+): a note from round 2 of its lineage is
        logged with at most one batch fix and never re-reviewed. A lineage rooted before the
        cutover keeps the old rule (decision 65); an unknown round is not round 2+."""
        rid = f.get("review_id")
        return f.get("severity") == "note" and rules.get(rid, 1) >= 2 and (lineage.get(rid) or ("", 0))[1] >= 2

    def capped(review_id):
        """The finding's review lineage has reached ROUND_CAP rounds."""
        mine = lineage.get(review_id)
        return bool(mine) and max(rnd for rt, rnd in lineage.values() if rt == mine[0]) >= vl.ROUND_CAP

    def unshipped(review_id):
        """The latest review in the finding's lineage has a verdict other than SHIP."""
        mine = lineage.get(review_id)
        last = [r for r in ordered if mine and (lineage.get(r.get("review_id")) or ("",))[0] == mine[0]][-1:]
        return bool(last) and str(last[0].get("verdict") or "").strip() != "SHIP"

    def stopped(fid, review_id):
        """review/SKILL.md §5.1 stop: the finding's lineage reached ROUND_CAP rounds without SHIP
        and the loop stopped there — an `accept` recorded after this disposition stands in for the
        re-review (kalpa-iris 1.1: five rounds re-reviewing its own checkers). A SHIP's standing
        accept never does: SHIP proceeds only once nothing wants re-reviewing (§5.1)."""
        return capped(review_id) and unshipped(review_id) and any(
            r.get("record") == "acceptance" and str(r.get("by") or "").strip() for r in recs[at[fid] + 1:])

    for f in recs:
        d = latest.get(f.get("finding_id"))
        if f.get("record") != "finding" or not d or d.get("disposition") not in ("fixed", "reframed") \
                or not d.get("sha"):
            continue
        reframed = d["disposition"] == "reframed"
        who = vl.REFRAMED_BY.match(str(d.get("by") or "")) if reframed else None
        why_not = who and who.group(1) == "judge" and vl.judge_took(recs, f["finding_id"], lineage)
        if why_not:
            # `--by judge` is checked against the log, as dispose checks it: a hand-written
            # record, or one from before the check, never clears a finding on the driver's
            # word (review 10.2-r1-01); `--by user` is the user's call and stands as recorded
            blocks.append((f"reframe:{f['finding_id']}", "a `reframed --by judge` the judge never took",
                           "a reframe that vl.reframe_call says is the judge's to take, in the "
                           "finding's lineage that removes it", why_not, f"{review_log} · {f['finding_id']}",
                           "code"))
        # the reviewed code is never its own fix: the commit that introduced a finding touches
        # its file (review adhoc-01); dispose refuses it, a hand-written record blocks here
        own, rng = next(iter((f.get("range") or {}).items()), ("", ""))
        # a fix on a branch that never merged is not in what ships (review r2-04); a git
        # failure (repo gone, sha unknown) is a block too, never a pass
        # — squash and rebase merges count when the fix's change arrived (§5.2.2)
        hold = d.get("repo") or own
        if ll.landed(root(hold), d["sha"], known) is None:
            blocks.append((f"unmerged:{f['finding_id']}", f"a `{d['disposition']}` commit is not in what ships",
                           f"{d['sha'][:10]} on HEAD or the trunk in {hold}: an ancestor, the same patch-id, or "
                           "its change squash-merged",
                           "none of the three (or git cannot tell)", f"{review_log} · {f['finding_id']}", "code"))
        head = rng.partition("..")[2]  # the head this finding's reviewer saw
        if own and head and canon(d.get("repo", own)) == canon(own) \
                and git_ok(root(own), "merge-base", "--is-ancestor", d["sha"], head):
            blocks.append((f"predates:{f['finding_id']}", f"a `{d['disposition']}` commit predates the finding",
                           f"a commit made after {head[:10]}, the head {f.get('review_id')} reviewed",
                           f"{d['sha'][:10]} is an ancestor of it", f"{review_log} · {f['finding_id']}", "code"))
        # a scaffolding finding never forces another round, even fixed off-anchor (lenses §7)
        # a reframe's replacing commit, at any severity, is new code: a new lineage reviews it, and
        # the old lineage's round-cap stop never stands in for that review
        why = "a reframe's replacing commit" if reframed else \
            "a blocking finding's fix" if f.get("severity") == "blocking" else \
            "an off-anchor fix" if d.get("via") == "off-anchor" and f.get("target") != "scaffolding" \
            and not budgeted_note(f) else None
        if why is None:
            continue
        # a fix recorded in another repo (`dispose --fixed-in`) is re-reviewed THERE, by a review
        # minted after the finding's — an earlier one never saw the fix as a fix (review adhoc-05)
        later = [r for r in reviews if round_no(r.get("review_id")) > round_no(f.get("review_id")) >= 0]
        for repo in ([d["repo"]] if d.get("repo") else (f.get("range") or {})):
            path = root(repo)
            try:
                seen = any(inside(path, r, d["sha"]) for r in later if names(r, repo))
            except HistoryError as e:
                blocks.append((f"rereview:{f['finding_id']}", "cannot read the fix's history",
                               f"{e} in {repo}", "git failed", f"{path}", "environment"))
                continue
            if not seen and (reframed or not stopped(f["finding_id"], f.get("review_id"))):
                blocks.append((f"rereview:{f['finding_id']}", f"{why} was never reviewed",
                               f"a later /review whose range contains {d['sha'][:10]}" + (
                                   f" — or, its review lineage being at round {vl.ROUND_CAP}+ without SHIP, "
                                   "`review.py accept` to stop the loop here"
                                   if capped(f.get("review_id")) and unshipped(f.get("review_id"))
                                   and not reframed else ""),
                               f"no review record covers it", f"{review_log} · {f['finding_id']}", "code"))
    return blocks


def row_unchanged(row, pend):
    """The table row is still the one the run checked: same deliverable, check, class, rung,
    repo and dir as the run's pending record. A runner-decided judge row is recorded as
    `auto: …` and counts as `judge`. No record to compare is never unchanged."""
    if not pend:
        return False
    ran = pend.get("command") or ""
    if ran.startswith(vl.AUTO_PREFIX):
        ran = "judge"
    return (pend.get("deliverable"), ran, pend.get("class"), pend.get("rung_required"),
            pend.get("dir")) == (row["deliverable"], row["check"], row["class"], row["rung"],
                                 row["dir"]) and vl.canonical_key(pend.get("repo") or "", None) \
        == vl.canonical_key(row["repo"], None)


def evidence_line(pend):
    """The one output line that says why: the first [FAIL]/[BLOCK]/[ERROR] line, else the last
    non-empty line of the runner's output_tail (§10: actual values, not adjectives)."""
    lines = [x.strip() for x in ((pend or {}).get("output_tail") or "").splitlines() if x.strip()]
    flagged = [x for x in lines if re.match(r"^\[(FAIL|BLOCK|ERROR)\]", x)]
    line = (flagged or lines or [""])[0 if flagged else -1]
    return f" — output: {line[:200]}" if line else ""


def evaluate(scope, unit, projects):
    """Return (rows_report, blocks, judge_lines). Raises vl.ContractError."""
    ll.reset()
    table = vl.parse_table(os.path.join(scope, "finish-conditions.md"))
    owned = vl.select(table["rows"], unit)
    log = os.path.join(scope, "artifacts", f"verify-{unit}.jsonl")
    recs = vl.read_jsonl(log)
    base = vl.bases(os.path.join(scope, "closeout-prep.md"), unit)
    review = os.path.join(scope, "artifacts", f"review-{unit}.jsonl")
    known = known_shas([*recs, *(vl.read_jsonl(review) if os.path.exists(review) else [])])
    report, blocks, judges = [], [], set()
    if not owned:
        raise vl.ContractError(vl.message("ERROR", f"no finish-table rows owned by {unit}",
                                          f"at least one row whose owner is {unit} or {unit}/…", "0 rows",
                                          table["path"], "code", "add the unit's rows, bump Revision",
                                          f"{vl.CONTRACT} §3.4"))
    appr = table.get("approval")
    if appr is not None and appr != table["revision"]:
        found = "pending" if appr == "pending" else f"rev {appr} approved, table is rev {table['revision']}"
        blocks.append(("table-approval", "the finish table's current revision is not approved by a human",
                       f"**Approved:** rev {table['revision']} — <who>, <date>", found, table["path"], "code",
                       f"show the user the rows; on their yes: finish-table.py approve --scope {scope} --by <name>"))
        report.append("BLOCK  table-approval  finish table not approved")
    heads = {}
    for row in owned:
        cid = row["check_id"]
        run_cmd = (f"verify-run.py run --table {table['path']} --log {log} --owner {unit}")

        def block(what, expected, found, cause, nxt=run_cmd):
            blocks.append((cid, what, expected, found, f"{cid} · {log}", cause, nxt))
            report.append(f"BLOCK  {cid}  {what}")

        finals = [(i, r) for i, r in enumerate(recs) if r.get("run_state") == "final" and cid in r.get("results", {})]
        if not finals:
            block("no final verdict", "a finalized run covering this check", "none in the verdict log", "tooling")
            continue
        fi, final = finals[-1]
        newer = [r for r in recs[fi + 1:] if r.get("run_state") == "pending" and r.get("check_id") == cid]
        if newer:
            block("an unfinished run is newer than the verdict", "every run judged and finalized",
                  f"pending run {newer[-1]['run_id']}", "tooling",
                  f"verify-run.py finalize --log {log} --run-id {newer[-1]['run_id']} ...")
            continue
        res = final["results"][cid]
        pend = next((r for r in recs if r.get("run_state") == "pending" and r.get("run_id") == final["run_id"]
                     and r.get("check_id") == cid), None)
        judges.add(final.get("judge", ""))
        # §5.1 re-check: the final result must follow from its own evidence. A final record
        # edited by hand (or written by anything but verify-run.py) is caught here.
        if pend is not None:
            jud = [r for r in recs if r.get("run_state") == "judged" and r.get("run_id") == final["run_id"]
                   and r.get("check_id") == cid]
            want = vl.authority(pend, jud[-1] if jud else None)
            if (want["result"], want["rung_reached"]) != (res["result"], res["rung_reached"]):
                block("final verdict contradicts its own evidence",
                      f"{want['result']} · rung {want['rung_reached']} (authority rule over run {final['run_id']})",
                      f"{res['result']} · rung {res['rung_reached']} in the final record", "tooling",
                      "re-run the checks; never edit a final record")
                continue
        # A revision expires a verdict only when it changed the row that verdict checked. The
        # run's own record holds the row as it ran it; a bump for another unit's rows leaves
        # it standing (kalpa-iris 6: rev 16–17 changed 6.4's rows and expired 6.1–6.3's 91).
        if final.get("table_rev") != table["revision"] and not row_unchanged(row, pend):
            block("verdict predates the current finish table", f"table_rev {table['revision']}",
                  f"table_rev {final.get('table_rev')}", "code")
            continue
        if res["result"] == "inconclusive" and row["is_judge"] and str(final.get("judge", "")).startswith("none "):
            # nobody judged the work: a tooling failure, not a finding about it (Alex, 2026-10-02)
            blocks.append((cid, "not judged — the judge did not run or its answer was refused", "a judge verdict",
                           f"judge line `{final.get('judge')}`", f"{cid} · {log}", NOT_JUDGED,
                           "re-run /verify's judge step (verify/SKILL.md §3.6 retry)"))
            report.append(f"NOT-JUDGED  {cid}  {final.get('judge')}")
            continue
        if res["result"] in ("fail", "inconclusive"):
            block(f"verdict is {res['result']}", "pass", f"{res['result']}: {res['reason']}{evidence_line(pend)}",
                  "code" if res["result"] == "fail" else "environment")
            continue
        if res["result"] == "verified-unreachable" and not row["unreachable_ok"]:
            block("unreachable, and the table does not allow it", "pass (unreachable_ok is `no`)",
                  f"verified-unreachable: {res['reason']}", "environment")
            continue
        if res["rung_reached"] < row["rung"]:
            block("verdict is under the required rung", f"rung ≥ {row['rung']}", f"rung {res['rung_reached']}", "code")
            continue
        if pend is None or not pend.get("sha"):
            block("verdict has no evidence SHA", "the pending record with the tested SHA", "none", "tooling")
            continue
        repo, sha = pend["repo"], pend["sha"]
        repo_path = vl.repo_root(projects, repo, scope)
        if repo not in heads:
            heads[repo] = git_out(repo_path, "rev-parse", "HEAD")
        head = heads[repo]
        if head is None:
            block("cannot read the evidence repo", f"a git repo at {repo_path}", "not readable", "environment",
                  f"git -C {repo_path} status")
            continue
        if repo in base:
            b = base[repo]
            # after the base, and on HEAD — or landed on the trunk with the lane (§5.2.2)
            inside = git_ok(repo_path, "merge-base", "--is-ancestor", b, sha) and (
                git_ok(repo_path, "merge-base", "--is-ancestor", sha, head)
                or ll.landed(repo_path, sha, known) is not None)
            if not inside:
                block("evidence SHA is outside the unit's range", f"{b[:10]}..{head[:10]} in {repo}, or landed "
                      "on its trunk", f"evidence at {sha[:10]}", "code")
                continue
        elif sha != head:
            block("evidence is stale and no base SHA is recorded", f"evidence at HEAD {head[:10]} of {repo}",
                  f"evidence at {sha[:10]}", "code")
            continue
        report.append(f"pass   {cid}  {res['result']} · rung {res['rung_reached']}/{row['rung']} · "
                      f"{final.get('judge')}")
    for bid, what, exp, found, where, cause in review_presence_blocks(review, base, projects, scope, unit):
        blocks.append((bid, what, exp, found, where, cause,
                       f"/review --scope {scope} --unit {unit} on the unit's base..HEAD"))
        report.append(f"BLOCK  {bid}  {what}")
    if os.path.exists(review):
        cov, n = coverage_blocks(review)
        for fid, what, exp, found, where, cause in cov:
            blocks.append((fid, what, exp, found, where, cause, "record the disposition through /review's log writer"))
            report.append(f"BLOCK  {fid}  {what}")
        if appr is not None and n and not cov and not accepted(review):
            # §6.4 — a table under the human checkpoint wants review outcomes recorded too: by the
            # session on a SHIP (standing policy), by the user's answer at a /review §5.1 stop
            blocks.append(("review-acceptance", "review outcomes not accepted since the last "
                           "finding or disposition", "an `acceptance` record after every finding and disposition",
                           "none, or an older one", review, "code",
                           f"on a SHIP: review.py accept --scope {scope} --unit {unit} --by \"<owner> (standing "
                           f"policy)\"; at a /review §5.1 stop, on the user's answer: --by <name>"))
            report.append("BLOCK  review-acceptance  review outcomes not accepted")
        report.append(f"review {n} finding(s), {n - len(cov)} dispositioned")
        nits = accepted_nits(review)
        if nits:
            report.append(f"review accepted as process nits ({len(nits)}): {', '.join(nits)}")
        for line in fallback_markers(review, projects, scope):
            judges.add(line)
    return report, blocks, sorted(j for j in judges if j)


# Blocks that mean "no complete verdict yet" — /closeout runs /verify for these, and only these.
NEEDS_VERIFY = ("no final verdict", "an unfinished run is newer than the verdict")
NOT_JUDGED = "not-judged"  # the cause on a judge row nobody judged: reported apart from blocks


def closeout_view(a, table):
    """Every gated unit, blocks as failures. Output ends `verdict: PASS|FAILED …` and, when
    anything is off, `marker: ⚠ verify failed <ids>` (+ judge markers) — the text /closeout
    puts on the archived index row."""
    units = sorted({r["owner"].split("/")[0] for r in table["rows"]}, key=lambda u: [int(x) for x in u.split(".")])
    per, failed, judges, msgs, unjudged = [], [], set(), [], []
    for u in units:
        report, blocks, js = evaluate(a.scope, u, a.projects)
        judges.update(js)
        unjudged += [b[0] for b in blocks if b[5] == NOT_JUDGED]
        failed += [b[0] for b in blocks if b[5] != NOT_JUDGED]
        # a not-judged row is a tooling WARN, never a FAIL (and `not-judged` is not a §10 cause — 7.1-r4-01)
        msgs += [vl.message("WARN", f"{u}: {what}", exp, found, where, "tooling", nxt, DOCS) if cause == NOT_JUDGED
                 else vl.message("FAIL", f"{u}: {what}", exp, found, where, cause, nxt, DOCS)
                 for _, what, exp, found, where, cause, nxt in blocks]
        per.append({"unit": u, "blocks": [{"id": b[0], "what": b[1], "cause": b[5]} for b in blocks],
                    "needs_verify": any(b[1] in NEEDS_VERIFY or b[5] == NOT_JUDGED for b in blocks)})
    markers = [f"⚠ judge: {j}" for j in sorted(judges) if not j.startswith("codex ")]
    if not units:
        # Every phase predates the gate: nothing was verified, so this is not a pass
        # (it must never count toward the blocking flip — review 5.3-r1-05).
        doc = {"verdict": "ungated", "units": [], "predates": table["predates"], "failed": [], "marker": "",
               "messages": []}
        print(json.dumps(doc) if a.json else f"verdict: UNGATED (every phase predates the gate: "
                                             f"{', '.join(table['predates']) or 'no rows'})")
        return vl.EXIT_PASS
    if unjudged:
        markers.insert(0, f"⚠ verify not judged {', '.join(unjudged)}")
    if failed:
        markers.insert(0, f"⚠ verify failed {', '.join(failed)}")
    marker = " ".join(markers)
    # not-judged is not failed, and not pass either: it never counts toward the blocking flip
    verdict = "failed" if failed else "not-judged" if unjudged else "pass"
    if a.json:
        print(json.dumps({"verdict": verdict, "units": per, "predates": table["predates"],
                          "failed": failed, "marker": marker, "messages": msgs}))
    else:
        for p in per:
            print(f"{'FAIL' if p['blocks'] else 'pass'}  {p['unit']}  "
                  f"{', '.join(b['id'] for b in p['blocks']) if p['blocks'] else 'every owned check passes'}"
                  + ("  (verdict missing or unfinished — run /verify)" if p["needs_verify"] else ""))
        for u in table["predates"]:
            print(f"n/a   {u}  predates the gate")
        for m in msgs:
            print(m)
        print(f"verdict: {verdict.upper()} (scope, {len(units)} gated unit(s), {len(failed)} failed check(s))")
        if marker:
            print(f"marker: {marker}")
    return vl.EXIT_FAIL if failed else vl.EXIT_PASS


def main(argv):
    ap = argparse.ArgumentParser(description="Verification gate (templates/verify-contracts.md §5).")
    ap.add_argument("--scope", required=True)
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument("--unit")
    target.add_argument("--all", action="store_true")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--advisory", dest="mode", action="store_const", const="advisory")
    mode.add_argument("--blocking", dest="mode", action="store_const", const="blocking")
    ap.add_argument("--skip-verify", metavar="REASON")
    ap.add_argument("--projects", default=vl.PROJECTS)
    ap.add_argument("--json", action="store_true")
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return vl.EXIT_USAGE if exc.code else vl.EXIT_PASS
    try:
        a.mode = a.mode or vl.gate_mode(a.scope)
    except vl.ContractError as exc:
        print(exc.msg, file=sys.stderr)
        return vl.EXIT_EVAL

    if a.skip_verify is not None:
        if not a.skip_verify.strip():
            print(vl.message("ERROR", "--skip-verify needs a reason", "a reason a reader can judge", "empty",
                             "--skip-verify", "tooling", '--skip-verify "<why verification cannot run>"',
                             f"{vl.CONTRACT} §5.4"), file=sys.stderr)
            return vl.EXIT_USAGE
        marker = f"⚠ verify skipped: {a.skip_verify.strip()}"
        out = {"verdict": "skipped", "unit": a.unit, "blocks": [], "marker": marker}
        print(json.dumps(out) if a.json else f"verdict: SKIPPED ({a.unit})\nmarker: {marker}")
        return vl.EXIT_PASS

    try:
        table = vl.parse_table(os.path.join(a.scope, "finish-conditions.md"))
        if a.all:
            return closeout_view(a, table)
        if a.unit in table["predates"]:
            msg = f"{a.unit} predates the gate (finish-conditions.md **Predates gate:**) — exempt"
            print(json.dumps({"verdict": "predates-gate", "unit": a.unit, "blocks": [], "marker": ""})
                  if a.json else f"verdict: PREDATES GATE ({msg})")
            return vl.EXIT_PASS
        report, blocks, judges = evaluate(a.scope, a.unit, a.projects)
    except vl.ContractError as exc:
        if a.json:
            print(json.dumps({"verdict": "error", "unit": a.unit or "all", "error": exc.msg}))
        print(exc.msg, file=sys.stderr)
        return vl.EXIT_EVAL

    markers = [f"⚠ judge: {j}" for j in judges if not j.startswith("codex ")]
    nj = [b for b in blocks if b[5] == NOT_JUDGED]
    blocks = [b for b in blocks if b[5] != NOT_JUDGED]
    if blocks and a.mode == "advisory":
        # a count and where the list lives — never the IDs: 149.2's 369 put 9,400 characters
        # into one PLANS-INDEX cell (§5.4)
        rep = os.path.join("artifacts", f"verify-{a.unit}-report.md")
        where = rep if os.path.exists(os.path.join(a.scope, rep)) else f"verdict-gate.py --unit {a.unit}"
        markers.append(f"⚠ verify advisory: {len(blocks)} blocked — see {where}")
    if nj:
        markers.append(f"⚠ verify not judged: {len(nj)} ({', '.join(b[0] for b in nj)})")
    # a real block wins; otherwise nobody judging is NOT-JUDGED — never a block. In blocking
    # mode it still refuses Done: an unjudged unit is not a verified one (Alex, 2026-10-02)
    verdict = ("advisory" if a.mode == "advisory" else "blocked") if blocks else "not-judged" if nj else "pass"
    marker = " ".join(markers)
    level = "WARN" if a.mode == "advisory" else "BLOCK"
    msgs = [vl.message(level, what, exp, found, where, cause, nxt, DOCS)
            for _, what, exp, found, where, cause, nxt in blocks] + \
        [vl.message("WARN", what, exp, found, where, "tooling", nxt, DOCS) for _, what, exp, found, where, _, nxt in nj]
    if a.json:
        print(json.dumps({"verdict": verdict, "unit": a.unit, "marker": marker, "report": report,
                          "blocks": [{"id": b[0], "what": b[1], "cause": b[5]} for b in blocks],
                          "not_judged": [b[0] for b in nj], "messages": msgs}))
    else:
        print("\n".join(report))
        for m in msgs:
            print(m)
        label = {"pass": "PASS", "advisory": "ADVISORY — would block", "blocked": "BLOCKED",
                 "not-judged": "NOT-JUDGED" + (" — refuses Done" if a.mode == "blocking" else "")}[verdict]
        print(f"verdict: {label} ({a.unit}, {len(blocks)} block(s), {len(nj)} not judged, mode {a.mode})")
        if marker:
            print(f"marker: {marker}")
    refuse = verdict == "blocked" or (verdict == "not-judged" and a.mode == "blocking")
    return vl.EXIT_FAIL if refuse else vl.EXIT_PASS


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
