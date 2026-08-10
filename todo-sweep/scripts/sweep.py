#!/usr/bin/env python3
"""sweep.py — durable state + deterministic bookkeeping for /todo-sweep.

Approach: the sweep's JUDGEMENT (is this item still true? which bucket? what is the
evidence?) belongs to the agent reading actual code. Everything else — which items
remain, what was already decided, how owners are derived, how the proposal renders —
is deterministic, so it lives here rather than in prose. ai-skills CLAUDE.md §3.6.1:
prose asked to be a program fails differently every time and nobody notices.

WHAT THIS ENFORCES, AND WHY EACH ONE IS A REFUSAL RATHER THAN A WARNING

  Evidence or no verdict.   `record` REFUSES a done/moot verdict with no --evidence,
                            and refuses evidence that is just a TO-DO.md line
                            reference. The entire lesson of plan 114.1 is that the
                            doc was wrong 3 times in 8; a sweep that accepts the
                            doc as its own proof reproduces the bug it exists to
                            find. Verification is against code: a file:line, a
                            commit SHA, or an explicit "searched X, absent".
  Propose, never write.     No command mutates TO-DO.md except `apply --write`,
                            which a human runs after reading the proposal (A1).
                            An agent silently archiving a live item is the one
                            failure that would end trust in the mechanism, and
                            trust is the whole deliverable.
  Resumable by default.     Every verdict is fsync'd to state as it is recorded, not
                            batched at the end. 465 items will not fit one context,
                            and the failure this guards against is the one 114.1 kept
                            hitting: work that looks complete because the bookkeeping
                            was dropped.

A HIGH REMOVAL RATE IS SUCCESS. Three of the four buckets are removals. Deferring an
item lets someone else's in-flight work solve it, or render it moot by doing something
better — so a sweep that archives most of what it touches is the deferral system paying
off, not an indictment of the team. `status` and `report` say so in words, because the
first real run over ~470 items will otherwise read as a disaster.

State: ~/.claude/todo-sweep-state.json (override $TODO_SWEEP_STATE), keyed by the
absolute TO-DO.md path, so several plans dirs can be swept independently. Kept outside
any git repo on purpose — a half-finished multi-day sweep should not sit in a docs repo
as uncommitted noise. The durable RECORD lands in the repo when a human applies.

Item identity is a hash of the item's first line plus its section, which survives
annotation of the body but NOT a rewrite of the lead line. That is deliberate: a
rewritten item (bucket 4) is a different assertion and should be re-verified rather
than inheriting an old verdict. `status` reports keys it can no longer find instead
of failing, so an item edited by a teammate mid-sweep is visible, not silently lost.

Exit: 0 ok · 1 refused (bad verdict, missing evidence, nothing to do) · 2 bad usage.
Usage: sweep.py {next,record,status,report,owners,apply} <plans-dir> [...]
"""

import argparse
import hashlib
import importlib.util
import json
import os
import random
import re
import sys

BUCKETS = {
    "done": "Done elsewhere — someone shipped it; archive WITH the SHA that did it",
    "moot": "Rendered moot — a better design removed the need; archive WITH why",
    "true": "Still true — genuinely open; stamp VERIFIED and leave in place",
    "reframe": "Still true, wrong framing — premise drifted; rewrite the item, stamp it",
}
REMOVALS = ("done", "moot")
NEEDS_EVIDENCE = ("done", "moot", "true", "reframe")  # all of them, deliberately

# Evidence that is really just the TO-DO file talking about itself. Rejected: the doc
# is the thing under test.
SELF_REFERENTIAL = re.compile(r"TO-DO\.md|TO-DO-archive|\bthe (to-?do|doc|row)\b", re.I)
# Something that looks like real evidence: a path with a line, a SHA, or a stated absence.
EVIDENCE_OK = re.compile(
    r"[\w./-]+\.\w+:\d+"  # file.go:123
    r"|\b[0-9a-f]{7,40}\b"  # commit sha
    r"|\bPR\s*#\d+|#\d+\b"  # PR reference
    r"|\b(absent|no callers|not present|zero|removed|searched)\b",
    re.I,
)


def load_todo_stats():
    """Reuse the shared parser rather than growing a second, competing one."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.normpath(os.path.join(here, "..", "..", "scripts", "todo-stats.py"))
    spec = importlib.util.spec_from_file_location("todo_stats", path)
    if spec is None or spec.loader is None:
        sys.exit(f"sweep: cannot load the shared parser at {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TS = load_todo_stats()


def state_path():
    return os.environ.get(
        "TODO_SWEEP_STATE",
        os.path.join(os.path.expanduser("~"), ".claude", "todo-sweep-state.json"),
    )


def read_state():
    try:
        with open(state_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(data):
    """Write durably. A sweep that loses the last verdict on a crash is the exact
    dropped-bookkeeping failure this is built to prevent, so fsync rather than trust
    the page cache."""
    path = state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def todo_file(plans_dir):
    return os.path.abspath(os.path.join(plans_dir, "TO-DO.md"))


# A verification stamp is metadata ABOUT the claim, not part of it, so it must not change the
# item's identity. Stripping it before hashing is what makes `apply` key-stable: without this,
# stamping an item rewrites its lead line, changes its key, and orphans the very verdict just
# applied -- which is how the first real run ended with `triaged: 0` and all 18 verdicts
# reported as orphans (plan 114.3 T3, 2026-08-10). A REWRITE (bucket `reframe`) still re-keys
# on purpose: that one genuinely changes the assertion and should be re-verified.
KEY_STRIP = re.compile(r"^- \[[ xX]\]\s*\**\s*VERIFIED(?:\s+STILL\s+TRUE)?[^:]*:\**\s*", re.I)
# A date added to a section heading is metadata about the SECTION, not a change to any item's
# claim, so it must not re-key the items beneath it. Found the same way as the stamp problem:
# dating 40 headings re-keyed every item under them (plan 114.3 T4 -> T3, 2026-08-10).
SEC_STRIP = re.compile(r"\s*\((?:20\d\d-\d\d-\d\d)\)\s*$")


def item_key(it):
    lead = " ".join(it["body"][0].split())
    lead = KEY_STRIP.sub("- [ ] ", lead)
    section = SEC_STRIP.sub("", it.get("section") or "")
    basis = f"{section}␟{lead}"
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]


def load_items(plans_dir, open_only=True):
    path = todo_file(plans_dir)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        sys.exit(f"sweep: cannot read {path}: {exc}")
    items = TS.parse_items(text)
    for it in items:
        it["key"] = item_key(it)
    return [i for i in items if i["open"]] if open_only else items


# ---------------------------------------------------------------- owner derivation (T4)

SOURCE_SCOPE = re.compile(r"Source:.*?\b(?:scope|plan)[ -]?(\d+)", re.I)
ANY_SCOPE = re.compile(r"\b(?:scope|plan)[ -]?(\d+)", re.I)
INLINE_OWNER = re.compile(r"Owner:\s*([^.,;|\n]{1,40})", re.I)
# Only WHOLE-NUMBER scope rows carry `Created by`, and only in the canonical 5-column
# shape `| # | Status | Folder | Description | Created by |`. Per-plan `{N}.{P}` rows are
# a different table shape (4 or 7 cells) whose last cell is a Phase description -- reading
# those as creators produced owners like "Phase 0 - Discovery & Architecture Decision...",
# which is how this bug announced itself. Cell count is checked, not assumed.
SCOPE_NUM = re.compile(r"^\d+$")
PLACEHOLDER_CREATOR = {"created by", "---", "", "-", "\u2014", "tbd", "n/a"}


def index_creators(plans_dir):
    """scope number -> `Created by`, from PLANS-INDEX.md's canonical 5-column rows."""
    path = os.path.join(plans_dir, "PLANS-INDEX.md")
    out = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.startswith("|"):
                    continue
                cells = line.rstrip("\n").split("|")[1:-1]
                if len(cells) != 5:
                    continue
                num = cells[0].strip()
                creator = cells[4].strip().strip("*_` ")
                if not SCOPE_NUM.match(num):
                    continue
                if creator.lower() in PLACEHOLDER_CREATOR:
                    continue
                out.setdefault(num, creator)
    except OSError:
        pass
    return out


def derive_owner(it, creators):
    """Fallback chain, most-specific first. Returns (owner, basis).

    The plan assumed `Source: scope N` was near-universal. Measured on kalpa: 79 of 133
    sections carry an explicit `Source:`, 122 carry a scope reference somewhere. So this
    is a ranked chain, not a single join, and `unattributed` is a real outcome that gets
    reported rather than hidden.
    """
    blob = it["text"]
    m = INLINE_OWNER.search(blob)
    if m:
        raw = m.group(1).strip().rstrip("*_` ")
        # Inline owners are free text ("backbone/cashier seeds", "whoever owns the hq
        # cutover"), so a hard 40-char cut lands mid-word and reads as corruption. Trim to
        # a word boundary and drop an unclosed paren. Not normalised further on purpose:
        # the plan says inline Owner always wins and Alex corrects it, so silently
        # rewriting what he typed would be the wrong direction.
        if raw.count("(") > raw.count(")"):
            raw = raw.split("(")[0].strip()
        if len(raw) > 32:
            raw = raw[:32].rsplit(" ", 1)[0] + "\u2026"
        return raw, "inline Owner:"
    m = SOURCE_SCOPE.search(blob)
    if m and m.group(1) in creators:
        return creators[m.group(1)], f"Source: scope {m.group(1)}"
    if m:
        return "unattributed", f"Source: scope {m.group(1)} (not in index)"
    m = ANY_SCOPE.search(blob) or (
        ANY_SCOPE.search(it.get("section") or "") if it.get("section") else None
    )
    if m and m.group(1) in creators:
        return creators[m.group(1)], f"scope {m.group(1)} mentioned"
    return "unattributed", "no owner, no scope reference"


# ------------------------------------------------------------------------- subcommands


def cmd_next(args):
    items = load_items(args.plans_dir)
    st = read_state().get(todo_file(args.plans_dir), {})
    done = st.get("verdicts", {})
    creators = index_creators(args.plans_dir)

    pending = [i for i in items if i["key"] not in done]
    if args.priority:
        pending.sort(key=lambda i: (i["priority"] is None, i["priority"] or 9))
    elif args.random:
        # Document order is NOT a neutral sample: sections are appended, so reading top-down
        # is biased toward recent items, and `--priority` is biased the opposite way (the
        # oldest audit items carry the P1s, and those are the ones most likely already
        # fixed). Measuring a drift RATE needs neither bias. Seeded so a quoted rate can be
        # re-drawn and checked by someone else -- an unreproducible sample is an anecdote.
        random.Random(args.seed).shuffle(pending)
    batch = pending[: args.batch]

    out = []
    for it in batch:
        owner, basis = derive_owner(it, creators)
        out.append(
            {
                "key": it["key"],
                "section": it["section"],
                "priority": it["priority"],
                "owner": owner,
                "owner_basis": basis,
                "stamped": str(it["stamped"]) if it["stamped"] else None,
                "text": it["text"],
            }
        )
    print(
        json.dumps(
            {
                "remaining_before_batch": len(pending),
                "total_open": len(items),
                "batch": out,
            },
            indent=2,
        )
    )
    return 0


def cmd_record(args):
    if args.bucket not in BUCKETS:
        print(
            f"sweep: unknown bucket {args.bucket!r}. One of: {', '.join(BUCKETS)}",
            file=sys.stderr,
        )
        return 1

    ev = (args.evidence or "").strip()
    if args.bucket in NEEDS_EVIDENCE:
        if not ev:
            print(
                f"sweep: bucket {args.bucket!r} requires --evidence (a file:line, a commit "
                f"SHA, a PR, or a stated absence). Verification is against the CODE — the "
                f"doc is the thing under test.",
                file=sys.stderr,
            )
            return 1
        if SELF_REFERENTIAL.search(ev) and not EVIDENCE_OK.search(ev):
            print(
                f"sweep: refusing evidence that only cites the TO-DO file itself: {ev!r}. "
                f"Plan 114.1 found the doc wrong 3 times in 8 — it cannot be its own proof.",
                file=sys.stderr,
            )
            return 1
        if not EVIDENCE_OK.search(ev):
            print(
                f"sweep: {ev!r} does not look like code evidence. Expected a file:line, a "
                f"commit SHA, a PR reference, or an explicit statement of absence "
                f"(\"searched X, no callers\").",
                file=sys.stderr,
            )
            return 1

    items = {i["key"]: i for i in load_items(args.plans_dir)}
    if args.key not in items:
        print(
            f"sweep: no open item with key {args.key!r} in {todo_file(args.plans_dir)}. "
            f"Run `next` again — the file may have changed under the sweep.",
            file=sys.stderr,
        )
        return 1

    data = read_state()
    entry = data.setdefault(todo_file(args.plans_dir), {})
    verdicts = entry.setdefault("verdicts", {})
    if args.key in verdicts and not args.force:
        prior = verdicts[args.key]
        print(
            f"sweep: {args.key} already recorded as {prior['bucket']!r}. Pass --force to "
            f"overwrite (and say why in --why).",
            file=sys.stderr,
        )
        return 1

    it = items[args.key]
    owner, basis = derive_owner(it, index_creators(args.plans_dir))
    verdicts[args.key] = {
        "bucket": args.bucket,
        "why": args.why,
        "evidence": ev,
        "section": it["section"],
        "priority": it["priority"],
        "owner": owner,
        "owner_basis": basis,
        "lead": " ".join(it["body"][0].split())[:200],
        "rewrite": args.rewrite,
    }
    write_state(data)
    print(f"recorded {args.key} -> {args.bucket}  ({len(verdicts)} verdicts on file)")
    return 0


def _tally(verdicts):
    by_bucket = {}
    by_owner = {}
    for v in verdicts.values():
        by_bucket[v["bucket"]] = by_bucket.get(v["bucket"], 0) + 1
        by_owner[v["owner"]] = by_owner.get(v["owner"], 0) + 1
    return by_bucket, by_owner


def cmd_rekey(args):
    """Re-attach verdicts whose key changed, by matching on the recorded lead line.

    Why this has to exist: the key is a hash of (section, lead), so ANY change to the key
    function -- or to a heading, or a stamp -- detaches some subset of existing verdicts. That
    happened twice in one session (a stamp re-keyed 11 items, then dating 40 headings re-keyed
    the rest), and each time the verdicts were intact while the pointers were not. Losing
    verified work to a hash change is exactly the dropped-bookkeeping failure this tool exists
    to prevent, so recovery is a command rather than a manual JSON edit.

    Matches on the recorded `lead`, normalised the same way item_key normalises, because that
    is the one field that survives re-keying. Never guesses: an unmatched verdict is reported,
    not deleted.
    """
    items = load_items(args.plans_dir)
    # `record` stores `lead` truncated to 200 chars, so the comparison has to be made on the
    # same prefix or every long item fails to match. Missing this made the first rekey run
    # re-attach 1 of 14.
    by_lead = {}
    for it in items:
        norm = KEY_STRIP.sub("- [ ] ", " ".join(it["body"][0].split()))
        by_lead.setdefault(norm[:200], it["key"])

    data = read_state()
    path = todo_file(args.plans_dir)
    verdicts = data.setdefault(path, {}).setdefault("verdicts", {})
    live = {i["key"] for i in items}

    moved, unmatched = [], []
    for k in list(verdicts):
        if k in live:
            continue
        v = verdicts[k]
        norm = KEY_STRIP.sub("- [ ] ", " ".join((v.get("lead") or "").split()))
        new = by_lead.get(norm[:200])
        if new and new not in verdicts:
            v["rekeyed_from"] = k
            verdicts[new] = v
            del verdicts[k]
            moved.append((k, new))
        else:
            unmatched.append(k)

    if moved and not args.dry_run:
        write_state(data)
    verb = "would re-attach" if args.dry_run else "re-attached"
    print(f"{verb} {len(moved)} verdict(s):")
    for old, new in moved:
        print(f"  {old} -> {new}  {verdicts.get(new, {}).get('lead', '')[:62]}")
    if unmatched:
        print(
            f"\n{len(unmatched)} verdict(s) could not be matched to a live open item. That is"
            f"\nexpected for anything already archived or rewritten — mark those with"
            f"\n`apply --write`, which records what it applied. Left untouched, never deleted:"
        )
        for k in unmatched:
            print(f"  {k}  [{verdicts[k]['bucket']}] {verdicts[k]['lead'][:58]}")
    return 0


def cmd_status(args):
    items = load_items(args.plans_dir)
    keys = {i["key"] for i in items}
    entry = read_state().get(todo_file(args.plans_dir), {})
    verdicts = entry.get("verdicts", {})
    # An orphan whose verdict was already APPLIED is history, not a loss: the item was
    # archived or rewritten on purpose. Only an unapplied orphan means the file moved under
    # the sweep. Reporting both as one number made a successful run look like a failure.
    orphans = [k for k in verdicts if k not in keys and not verdicts[k].get("applied")]
    applied_gone = [k for k in verdicts if k not in keys and verdicts[k].get("applied")]
    # Tally only what is still live, or the removal rate divides by the wrong denominator and
    # prints things like "7/4 (175%)".
    live = {k: v for k, v in verdicts.items() if k in keys}
    by_bucket, _ = _tally(live)

    triaged = len(live)
    print(f"open items:      {len(items)}")
    print(f"triaged:         {triaged}")
    print(f"remaining:       {len(items) - triaged}")
    if by_bucket:
        print("\nbuckets:")
        for b in BUCKETS:
            if by_bucket.get(b):
                print(f"  {b:8s} {by_bucket[b]:4d}   {BUCKETS[b]}")
        removals = sum(by_bucket.get(b, 0) for b in REMOVALS)
        if triaged:
            pct = round(100 * removals / triaged)
            print(
                f"\nremoval rate: {removals}/{triaged} ({pct}%). A HIGH RATE IS SUCCESS —"
                f"\n  three of the four buckets are removals, and an item that someone else's"
                f"\n  work already solved (or rendered moot by doing something better) is the"
                f"\n  deferral system paying off, not a backlog failure."
            )
    if applied_gone:
        print(
            f"\napplied and retired: {len(applied_gone)} — archived or rewritten by an earlier"
            f"\n  `apply` run. Expected, not a loss."
        )
    if orphans:
        print(
            f"\n⚠ {len(orphans)} recorded verdict(s) no longer match an open item AND were never"
            f"\n  applied — the file changed under the sweep (edited or rewritten by someone else):"
        )
        for k in orphans[:10]:
            print(f"    {k}  was: {verdicts[k]['lead'][:70]}")
    return 0


def cmd_owners(args):
    """T4 — display a derived owner distribution. Reporting the distribution IS the
    deliverable; it is the input to any future ownership conversation."""
    items = load_items(args.plans_dir)
    creators = index_creators(args.plans_dir)
    dist = {}
    bases = {}
    for it in items:
        owner, basis = derive_owner(it, creators)
        dist[owner] = dist.get(owner, 0) + 1
        bases[basis.split(":")[0].split("(")[0].strip()] = (
            bases.get(basis.split(":")[0].split("(")[0].strip(), 0) + 1
        )
    total = len(items)
    print(f"| Derived owner | Open items | Share |")
    print(f"|---|---|---|")
    for owner, n in sorted(dist.items(), key=lambda kv: -kv[1]):
        print(f"| {owner} | {n} | {round(100 * n / total)}% |")
    print(f"\n| Derivation basis | Items |")
    print(f"|---|---|")
    for basis, n in sorted(bases.items(), key=lambda kv: -kv[1]):
        print(f"| {basis} | {n} |")
    print(
        f"\n{total} open items. `unattributed` is a real outcome, not an error: the owner"
        f"\njoin is a ranked chain (inline Owner: > Source: scope N > any scope mention),"
        f"\nand items with none of those cannot be attributed from the file alone."
        f"\nAn inline `Owner:` always wins over the derived value."
    )
    return 0


def cmd_report(args):
    """A1 — render a PROPOSAL. Writes no TO-DO.md changes."""
    items = {i["key"]: i for i in load_items(args.plans_dir)}
    entry = read_state().get(todo_file(args.plans_dir), {})
    verdicts = entry.get("verdicts", {})
    live = {k: v for k, v in verdicts.items() if k in items}
    if not live:
        print("sweep: no verdicts recorded yet — nothing to propose.", file=sys.stderr)
        return 1

    by_bucket, by_owner = _tally(live)
    removals = sum(by_bucket.get(b, 0) for b in REMOVALS)
    lines = []
    add = lines.append
    add("# /todo-sweep proposal — NOTHING HAS BEEN WRITTEN")
    add("")
    add(
        f"{len(live)} of {len(items)} open items triaged. "
        f"Proposed removals: **{removals}** ({round(100 * removals / len(live))}%)."
    )
    add("")
    add(
        "> A high removal rate is **success**. Three of the four buckets are removals, and"
    )
    add(
        "> an item another person's work already solved — or rendered moot by doing"
    )
    add(
        "> something better — is the deferral system paying off, not a backlog failure."
    )
    add("")
    add("Review each block, then apply with:")
    add("")
    add(f"    sweep.py apply {args.plans_dir} --write")
    add("")
    for b, label in BUCKETS.items():
        rows = [(k, v) for k, v in live.items() if v["bucket"] == b]
        if not rows:
            continue
        add(f"## {b} — {label}  ({len(rows)})")
        add("")
        for k, v in rows:
            add(f"- **`{k}`** · {v['owner']} · {v['section'] or '(no section)'}")
            add(f"  - item: {v['lead']}")
            add(f"  - why: {v['why']}")
            add(f"  - evidence: `{v['evidence']}`")
            if v.get("rewrite"):
                add(f"  - proposed rewrite: {v['rewrite']}")
            add("")
    out = "\n".join(lines) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out)
        print(f"proposal written to {args.out} ({len(live)} verdicts). Nothing applied.")
    else:
        print(out, end="")
    return 0


def cmd_apply(args):
    """The only mutating command, and it needs --write plus a human running it (A1).

    Scope is deliberately narrow: it stamps `true` items in place, and for removals it
    prints the exact archive moves for a human to make. Auto-moving sections between two
    files is where an unattended agent could destroy a live item, which is the one
    failure that would end trust in the mechanism.
    """
    path = todo_file(args.plans_dir)
    items = {i["key"]: i for i in load_items(args.plans_dir)}
    entry = read_state().get(path, {})
    verdicts = {k: v for k, v in entry.get("verdicts", {}).items() if k in items}
    if not verdicts:
        print("sweep: nothing to apply.", file=sys.stderr)
        return 1

    stamp_targets = [(k, v) for k, v in verdicts.items() if v["bucket"] == "true"]
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    stamped = 0
    for k, _v in stamp_targets:
        it = items[k]
        if it["stamped"]:
            continue
        lead = it["body"][0]
        if lead not in text:
            print(f"  SKIP {k}: lead line no longer matches", file=sys.stderr)
            continue
        new_lead = re.sub(
            r"^- \[ \]\s*", f"- [ ] **VERIFIED STILL TRUE {args.date}:** ", lead, count=1
        )
        text = text.replace(lead, new_lead, 1)
        stamped += 1

    if not args.write:
        print(f"DRY RUN — would stamp {stamped} item(s). Nothing written.")
    elif stamped:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"stamped {stamped} item(s) in {path}")

    if args.write:
        # Record WHAT was applied, so a later `status` can tell "retired on purpose" from
        # "lost track of". Without this, a wholly successful apply reads as N orphans.
        data = read_state()
        entry_w = data.setdefault(path, {}).setdefault("verdicts", {})
        for k in verdicts:
            if k in entry_w:
                entry_w[k]["applied"] = args.date
        write_state(data)
    else:
        print("no stamps to apply")

    moves = [(k, v) for k, v in verdicts.items() if v["bucket"] in REMOVALS]
    reframes = [(k, v) for k, v in verdicts.items() if v["bucket"] == "reframe"]
    if moves:
        print(
            f"\n{len(moves)} item(s) to ARCHIVE by hand — move each to "
            f"archive/TO-DO-archive.md with its section heading, per TO-DO.md's own\n"
            f"convention, keeping the evidence line:"
        )
        for k, v in moves:
            print(f"  [{v['bucket']}] {k}  {v['lead'][:70]}")
            print(f"        evidence: {v['evidence']}")
    if reframes:
        print(f"\n{len(reframes)} item(s) to REWRITE by hand:")
        for k, v in reframes:
            print(f"  {k}  {v['lead'][:70]}")
            print(f"        -> {v.get('rewrite') or '(no rewrite text recorded)'}")
    return 0


def main():
    ap = argparse.ArgumentParser(prog="sweep.py", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("next", help="emit the next un-triaged items as JSON")
    p.add_argument("plans_dir")
    p.add_argument("--batch", type=int, default=10)
    p.add_argument("--priority", action="store_true", help="most severe P first")
    p.add_argument(
        "--random", action="store_true", help="unbiased sample (for measuring a drift rate)"
    )
    p.add_argument("--seed", type=int, default=0, help="seed for --random, so it re-draws")
    p.set_defaults(fn=cmd_next)

    p = sub.add_parser("record", help="record one verdict (evidence enforced)")
    p.add_argument("plans_dir")
    p.add_argument("--key", required=True)
    p.add_argument("--bucket", required=True, choices=sorted(BUCKETS))
    p.add_argument("--why", required=True)
    p.add_argument("--evidence", default="")
    p.add_argument("--rewrite", default="", help="new item text, for bucket `reframe`")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_record)

    p = sub.add_parser("rekey", help="re-attach verdicts whose key changed")
    p.add_argument("plans_dir")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_rekey)

    p = sub.add_parser("status", help="progress + bucket distribution")
    p.add_argument("plans_dir")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("owners", help="T4 — derived owner distribution")
    p.add_argument("plans_dir")
    p.set_defaults(fn=cmd_owners)

    p = sub.add_parser("report", help="render the proposal (writes no TO-DO.md changes)")
    p.add_argument("plans_dir")
    p.add_argument("--out")
    p.set_defaults(fn=cmd_report)

    p = sub.add_parser("apply", help="stamp `true` items; print archive moves")
    p.add_argument("plans_dir")
    p.add_argument("--write", action="store_true")
    p.add_argument("--date", required=True, help="ISO date for the VERIFIED stamp")
    p.set_defaults(fn=cmd_apply)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
