"""verify_lib.py — shared by verify-run.py and verdict-gate.py (and resolve-identifiers.py
for messages). Not a CLI.

Approach: one parser for finish-conditions.md, one message formatter, one verified JSONL
appender — so the runner and the gate cannot disagree about what a row or a record is.
Every rule here is from templates/verify-contracts.md; section numbers are cited inline.
"""

import json
import os
import re
import shlex
import sys

SCHEMA = "verify/1"
CONTRACT = "templates/verify-contracts.md"
COLUMNS = ("check_id", "deliverable", "owner", "class", "check", "repo", "dir", "env",
           "timeout", "rung", "unreachable_ok", "evidence")
DEFAULT_TIMEOUT = 120
RESULTS = ("pass", "fail", "inconclusive", "verified-unreachable")
ORDER = {"fail": 0, "inconclusive": 1, "verified-unreachable": 2, "pass": 3}  # §5.1
EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_EVAL = 0, 1, 2, 3                     # §5.5
JUDGE_LINE = re.compile(r"^(codex|claude-fallback|claude-lean|none) \S.*$")               # §4.6
# §5.4: advisory until BLOCKING_AFTER real scopes pass cleanly — then Alex flips this to
# "blocking". `plans-index.py gate-count` (printed by /closeout) is the reminder.
GATE_MODE = "advisory"
BLOCKING_AFTER = 5
# §5.4.2: a graph can run blocking ahead of the fleet flip with a `**Gate mode:** blocking`
# line in its plans/README.md or PLANS-INDEX.md (kalpa-iris, 2026-09-29 — code nobody reads
# needs a gate that stops).
GATE_MODE_LINE = re.compile(r"^\*\*Gate mode:\*\*[ \t]*(.*?)[ \t]*$", re.M)
# Finish-table `repo` cells are paths under this root (§3.2). Tests point it elsewhere.
PROJECTS = os.environ.get("VERIFY_PROJECTS", os.path.expanduser("~/Projects"))


def _git_lines(path, *args):
    import subprocess
    p = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True)
    return p.stdout.splitlines() if p.returncode == 0 else []


# a worktree beside its repo: `<repo>.worktrees/<name>` (149.2 logged supply-chain's 4 rounds so)
WORKTREE_KEY = re.compile(r"\.worktrees/.+$")


def canonical_key(key, projects=None):
    """A logged repo key as its primary checkout's key, so one repo's records count together
    however a review reached it (review adhoc-06). A live path resolves through git (its common
    dir's owner); a gone worktree by its `<repo>.worktrees/<name>` name. Older logs keyed a
    worktree by its path. Shared by review.py and verdict-gate.py."""
    if not key:
        return key
    projects = projects or PROJECTS
    path = os.path.join(projects, key)
    if not os.path.isdir(path):
        return WORKTREE_KEY.sub("", key)
    common = _git_lines(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    main = os.path.dirname(common[0]) if common else path
    rel = os.path.relpath(os.path.realpath(main), os.path.realpath(projects))
    return os.path.basename(os.path.realpath(main)) if rel.startswith("..") else rel


def repo_root(projects, repo, scope=None):
    """Where a finish-table `repo` cell is checked (§3.2.1): `<projects>/<repo>`, unless the
    scope folder sits in a linked git worktree of that same repo — then that worktree. A
    herdr scope lives under ~/.herdr/worktrees/, and its main checkout is usually on another
    branch (kalpa-iris scope 1: an empty range and 45 phantom blocks). Matched by git
    identity (the worktree's common dir), never by name."""
    main = os.path.join(projects, repo)
    if not scope:
        return main
    d = os.path.abspath(scope)
    while not os.path.isdir(d):
        d = os.path.dirname(d)
    out = _git_lines(d, "rev-parse", "--path-format=absolute", "--show-toplevel", "--git-common-dir")
    if len(out) != 2:
        return main
    top, common = os.path.realpath(out[0]), os.path.realpath(out[1])
    owner = os.path.dirname(common) if os.path.basename(common) == ".git" else None
    if owner and owner != top and owner == os.path.realpath(main):
        return top
    return main


def gate_mode(scope_dir):
    """The mode the gate runs in for this scope: the nearest plans dir's `**Gate mode:**`
    line — in plans/README.md (where graph prose lives once the index is generated, scope
    9), else in PLANS-INDEX.md — else GATE_MODE. Walks up at most three levels, which covers
    plans/{N}/, plans/archive/{N}/ and plans/{program}/archive/{N}/. A plans dir is one with
    a PLANS-INDEX.md or a README.md declaring `**Index render:**`."""
    d = os.path.realpath(scope_dir)
    for _ in range(3):
        d = os.path.dirname(d)
        texts = {}
        for name in ("README.md", "PLANS-INDEX.md"):
            path = os.path.join(d, name)
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as fh:
                    texts[path] = fh.read()
        readme = texts.get(os.path.join(d, "README.md"), "")
        if os.path.join(d, "PLANS-INDEX.md") not in texts and "**Index render:**" not in readme:
            continue
        for path, text in texts.items():
            m = GATE_MODE_LINE.search(text)
            if m is None:
                continue
            if m.group(1) not in ("blocking", "advisory"):
                # a typo must never quietly downgrade a blocking graph (review adhoc-02)
                raise ContractError(message(
                    "ERROR", "the plans dir declares an unknown gate mode", "**Gate mode:** blocking | advisory",
                    repr(m.group(1)), path, "code", "fix the **Gate mode:** line", f"{CONTRACT} §5.4.2"))
            return m.group(1)
        return GATE_MODE
    return GATE_MODE


def todo_has_item(scope, finding_id, open_only):
    """True when a TO-DO item line (`- [ ] …`, or also `- [x] …` unless open_only) opens
    with the marker `[review <finding_id>]` followed by the work left, in the project's TO-DO.md — or, when not open_only, its
    archive, where a closed item moves. The file is beside PLANS-INDEX.md, at most three
    levels above the scope. The ID is the link: free text can't tie an item to a finding,
    a substring matched an unrelated task and prose matched nothing real (review adhoc
    r1-03 → r2-01 → r3-01, the §5.1 three-rounds stop — Alex chose the ID link)."""
    finding_id = finding_id.strip()
    if not finding_id:
        return False
    box = r"\[ \]" if open_only else r"\[[ xX]\]"
    # the marker leads the item and text follows it: an ID merely mentioned in another
    # task, or a bare marker with no work described, is not a follow-up (review adhoc-r4-01)
    item = re.compile(rf"^\s*[-*] {box} (?:\*\*)?\[review {re.escape(finding_id)}\](?:\*\*)?[ \t]+\S", re.M)
    d = os.path.realpath(scope)
    for _ in range(3):
        d = os.path.dirname(d)
        todo = os.path.join(d, "TO-DO.md")
        if os.path.isfile(todo):
            files = [todo] + ([] if open_only else [os.path.join(d, "archive", "TO-DO-archive.md")])
            for f in files:
                if os.path.isfile(f):
                    with open(f, encoding="utf-8") as fh:
                        if item.search(fh.read()):
                            return True
            return False
    return False


# ---------- §10 message contract ---------------------------------------------------

def message(level, what, expected, found, where, cause, nxt, docs):
    assert cause in ("code", "environment", "tooling"), cause
    return (f"  [{level}] {what}\n"
            f"      expected · {expected}\n"
            f"      found    · {found}\n"
            f"      where    · {where}\n"
            f"      cause    · {cause}\n"
            f"      next     · {nxt}\n"
            f"      docs     · {docs}")


class ContractError(Exception):
    """A malformed contract file or record: exit 3, cause tooling (or code, if the
    author's table is wrong). Carries a ready §10 message."""

    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg


# ---------- answer schemas -----------------------------------------------------------

_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool}


def schema_problems(doc, schema, path="answer"):
    """Problems with `doc` against the JSON Schema subset our answer schemas use — type (one, or
    one plus "null"), required, additionalProperties: false, enum, items. A type outside the
    subset is a problem, never a pass: an unchecked field would be fail-open. Both answer writers (review.py,
    judge.py) run this before any semantic check, so a wrong container or a missing field
    is exit 3 and never a crash or a partial write (review 5.2-r1-06)."""
    t = schema.get("type")
    if isinstance(t, list):
        # a nullable field (`["string", "null"]`): codex's strict output schemas require every
        # property, so an optional one is written as required-or-null (review-output `reopens`)
        if doc is None and "null" in t:
            return []
        rest = [x for x in t if x != "null"]
        if len(rest) != 1:
            return [f"{path}: schema type {t!r} is not supported"]  # fail closed on a schema we can't read
        return schema_problems(doc, dict(schema, type=rest[0]), path)
    if t is not None and t != "integer" and t not in _TYPES:
        return [f"{path}: schema type {t!r} is not supported"]
    if t == "integer":
        if not isinstance(doc, int) or isinstance(doc, bool):
            return [f"{path} is not an integer"]
    elif t in _TYPES and not isinstance(doc, _TYPES[t]):
        return [f"{path} is not a{'n' if t[0] in 'ao' else ''} {t}"]
    if "enum" in schema and doc not in schema["enum"]:
        return [f"{path} {doc!r} is not one of {schema['enum']}"]
    out = []
    if t == "object":
        props = schema.get("properties", {})
        out += [f"{path} is missing `{k}`" for k in schema.get("required", []) if k not in doc]
        if schema.get("additionalProperties") is False:
            out += [f"{path} has unknown field `{k}`" for k in doc if k not in props]
        for k, sub in props.items():
            if k in doc:
                out += schema_problems(doc[k], sub, f"{path}.{k}")
    elif t == "array" and "items" in schema:
        for i, item in enumerate(doc):
            out += schema_problems(item, schema["items"], f"{path}[{i}]")
    return out


# ---------- §3 finish-condition table ----------------------------------------------

def _cells(line):
    parts = re.split(r"(?<!\\)\|", line.strip())
    cells = []
    for c in parts[1:-1]:
        c = c.strip().replace("\\|", "|")
        if len(c) >= 2 and c.startswith("`") and c.endswith("`"):
            c = c[1:-1]
        cells.append(c)
    return cells


def parse_table(path):
    """Return {"revision": int, "predates": [unit], "rows": [dict], "path": path}.
    Raises ContractError."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        raise ContractError(message("ERROR", "cannot read the finish-condition table",
                                    "a readable finish-conditions.md", str(exc), path, "tooling",
                                    "create it with scripts/finish-table.py init", f"{CONTRACT} §3"))
    return parse_table_text(text, path)


def parse_table_text(text, path):
    docs = f"{CONTRACT} §3"
    lines = text.splitlines()
    schema = rev = approved = None
    predates = []
    for line in lines:
        m = re.match(r"^\*\*Schema version:\*\*\s*(\S+)", line)
        if m:
            schema = m.group(1)
        m = re.match(r"^\*\*Revision:\*\*\s*(\S+)", line)
        if m:
            rev = m.group(1)
        m = re.match(r"^\*\*Predates gate:\*\*\s*(.*)$", line)
        if m:
            predates = [u.strip() for u in m.group(1).split(",") if u.strip()]
        m = re.match(r"^\*\*Approved:\*\*\s*(.*)$", line)
        if m:
            approved = m.group(1).strip()
    errors = []
    # §3.5 human checkpoint: `pending`, or `rev N — <who>, <date>`. No line = a table that
    # predates the checkpoint (exempt).
    approved_rev = None
    if approved is not None and approved != "pending":
        m = re.match(r"^rev (\d+) — \S.*$", approved)
        if m:
            approved_rev = int(m.group(1))
        else:
            errors.append(("header", "**Approved:** pending | rev <N> — <who>, <date>", approved))
    if schema != SCHEMA:
        errors.append(("header", f"**Schema version:** {SCHEMA}", schema or "missing"))
    if not (rev or "").isdigit():
        errors.append(("header", "**Revision:** <integer>", rev or "missing"))
    for u in predates:
        if not re.match(r"^\d+\.\d+$", u):
            errors.append(("header", "**Predates gate:** plan numbers `N.P`, comma-separated", u))

    rows, header_at = [], None
    for i, line in enumerate(lines):
        if header_at is None:
            if line.strip().startswith("|") and _cells(line)[:1] == ["check_id"]:
                header_at = i
                if tuple(_cells(line)) != COLUMNS:
                    errors.append((f"line {i + 1}", " | ".join(COLUMNS), " | ".join(_cells(line))))
            continue
        if i == header_at + 1:
            continue  # separator
        if not line.strip().startswith("|"):
            break
        cells = _cells(line)
        where = f"line {i + 1}"
        if len(cells) != len(COLUMNS):
            errors.append((where, f"{len(COLUMNS)} cells", f"{len(cells)} (an unescaped `|`? write `\\|`)"))
            continue
        row = dict(zip(COLUMNS, cells))
        row["_line"] = i + 1
        errors.extend(_validate_row(row, where))
        rows.append(row)
    if header_at is None:
        errors.append(("table", "a table whose first column is `check_id`", "none"))
    ids = [r["check_id"] for r in rows]
    for dup in sorted({x for x in ids if ids.count(x) > 1}):
        errors.append(("table", "unique check_id values", f"`{dup}` appears {ids.count(dup)} times"))
    if errors:
        where, expected, found = errors[0]
        more = f" (+{len(errors) - 1} more)" if len(errors) > 1 else ""
        raise ContractError(message("ERROR", f"finish-condition table is malformed{more}", expected,
                                    found, f"{path} {where}", "code",
                                    f"fix the row, bump **Revision:**, add a Changelog line", docs))
    for r in rows:
        r["timeout"] = DEFAULT_TIMEOUT if r["timeout"] == "-" else int(r["timeout"])
        r["rung"] = int(r["rung"])
        r["env"] = {} if r["env"] == "-" else dict(kv.split("=", 1) for kv in shlex.split(r["env"]))
        r["unreachable_ok"] = r["unreachable_ok"].startswith("yes")
        r["is_judge"] = r["check"] == "judge"
    owned = [u for u in predates if select(rows, u)]
    if owned:
        raise ContractError(message("ERROR", "a phase that predates the gate owns rows",
                                    "no rows owned by a **Predates gate:** phase", ", ".join(owned),
                                    path, "code", "drop the rows or the phase from **Predates gate:**", docs))
    return {"revision": int(rev), "predates": predates, "rows": rows, "path": path,
            "approval": None if approved is None else ("pending" if approved_rev is None else approved_rev)}


def _validate_row(r, where):
    errs = []

    def bad(col, expected):
        errs.append((f"{where} `{col}`", expected, r[col] or "empty"))

    for col in COLUMNS:
        if r[col] == "":
            bad(col, "a value (use `-` where the column allows it)")
    if errs:
        return errs
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", r["check_id"]):
        bad("check_id", "kebab-case")
    if not re.match(r"^\d+\.\d+(/[\w.-]+)?$", r["owner"]):
        bad("owner", "a plan number `5.1` or unit `5.1/1.3`")
    if r["class"] not in ("A", "B"):
        bad("class", "`A` or `B`")
    if r["timeout"] != "-" and not r["timeout"].isdigit():
        bad("timeout", "seconds, or `-`")
    if r["rung"] not in ("1", "2", "3", "4", "5"):
        bad("rung", "1–5")
    if not (r["unreachable_ok"] == "no" or re.match(r"^yes:\s*\S", r["unreachable_ok"])):
        bad("unreachable_ok", "`no` or `yes: <reason>`")
    if r["env"] != "-":
        try:
            if not all(re.match(r"^[A-Za-z_]\w*=", kv) for kv in shlex.split(r["env"])):
                bad("env", "`KEY=value` pairs or `-`")
        except ValueError:
            bad("env", "`KEY=value` pairs or `-`")
    return errs


def bases(ledger, unit):
    """{repo: sha} from closeout-prep.md — the FIRST `- base: <unit> <repo> <sha>` per repo,
    written by ledger-init.sh --repo (§5.2). First, because a resumed phase must not shrink
    the range."""
    out = {}
    if not os.path.exists(ledger):
        return out
    with open(ledger, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^\s*-\s*base:\s*(\S+)\s+(\S+)\s+([0-9a-f]{7,40})\s*$", line)
            if m and m.group(1) == unit:
                out.setdefault(m.group(2), m.group(3))
    return out


def select(rows, owner):
    """§3.4: `5.1` selects `5.1` and every `5.1/…` row; `None` selects all (closeout)."""
    if owner is None:
        return list(rows)
    return [r for r in rows if r["owner"] == owner or r["owner"].startswith(owner + "/")]


# ---------- §4 verdict log ---------------------------------------------------------

def read_jsonl(path):
    """Records in file order. Raises ContractError on a malformed line."""
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except ValueError as exc:
                raise ContractError(message(
                    "ERROR", "verdict log has a malformed line", "one JSON object per line",
                    f"{exc}", f"{path}:{i}", "tooling",
                    "inspect the line — a partial write means the run never landed; re-run it",
                    f"{CONTRACT} §4"))
    return out


def authority(p, j):
    """§5.1 — final {result, rung_reached, reason} for one check, from its pending record `p`
    and its judged record `j` (or None). One implementation: verify-run.py finalizes with it
    and verdict-gate.py re-checks every final result against it. A judged record from a
    `none …` judge is not evidence — the judge did not run — so it counts as absent
    (review 5.2-r1-03)."""
    if j is not None and str(j.get("judge", "")).startswith("none "):
        j = None
    if p["command"] == "judge":
        if j is None:
            return {"result": "inconclusive", "rung_reached": 0, "reason": "judge row: no judge verdict"}
        return {"result": j["verdict"], "rung_reached": j["rung_reached"], "reason": f"judge: {j['reason']}"}
    if j is None:
        return {"result": p["result"], "rung_reached": p["rung_reached"], "reason": f"runner: {p['reason']}"}
    if p["result"] == "verified-unreachable" and p.get("unreachable_ok"):
        # §5.1: a row whose table declares `unreachable_ok: yes: <reason>` carries a human
        # exemption — the judge's verdict is recorded, never applied (kalpa-iris scope 1:
        # a declared exemption was downgraded to inconclusive and blocked anyway)
        return {"result": p["result"], "rung_reached": p["rung_reached"],
                "reason": f"runner: {p['reason']}; declared unreachable_ok — judge said {j['verdict']} "
                          f"(flagged, not applied): {j['reason']}"}
    if ORDER[j["verdict"]] < ORDER[p["result"]]:
        return {"result": j["verdict"], "rung_reached": min(p["rung_reached"], j["rung_reached"]),
                "reason": f"judge downgraded runner {p['result']}: {j['reason']}"}
    return {"result": p["result"], "rung_reached": min(p["rung_reached"], j["rung_reached"]),
            "reason": f"runner: {p['reason']}; judge concurs"}


KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# review/SKILL.md §5.1: rounds of one review lineage before a loop without SHIP stops and asks
# the user. review.py's deferral rule and verdict-gate.py's re-review waiver read the same number.
ROUND_CAP = 3


def _ranges_share(path, a, b):
    """Do the ranges a=(base, head) and b share a commit, as git reads them? Reachable from both
    heads (their merge bases), from neither base. None when git cannot tell."""
    bases = _git_lines(path, "merge-base", "--all", a[1], b[1])
    if not bases:
        return None
    out = _git_lines(path, "rev-list", "--count", *bases, f"^{a[0]}", f"^{b[0]}")
    return int(out[0]) > 0 if out and out[0].isdigit() else None


def _range_holds(path, base, head, shas, cache):
    """Does base..head contain one of `shas` (full or abbreviated)? None when git cannot tell."""
    import subprocess
    if (path, base, head) not in cache:
        out = subprocess.run(["git", "-C", path, "rev-list", f"{base}..{head}"], capture_output=True, text=True)
        cache[(path, base, head)] = out.stdout.split() if out.returncode == 0 else None
    commits = cache[(path, base, head)]
    if commits is None:
        return None
    return any(c.startswith(s) for c in commits for s in shas if s)


def lineage_links(recs):
    """({review_id: {fix shas}}, {review_id: continued review_id}, {stamped review_id}) from
    review-log records: the commits named by a `fixed` disposition of each review's findings,
    each review record's explicit `continues` (review.py --continues), and the reviews recorded
    under rules 2+ (an int `rules_version` >= 2). review_lineage's inputs."""
    of = {r.get("finding_id"): r.get("review_id") for r in recs if r.get("record") == "finding"}
    fixes, continues = {}, {}
    stamped = {r.get("review_id") for r in recs if r.get("record") == "review"
               and isinstance(r.get("rules_version"), int) and r["rules_version"] >= 2}
    for r in recs:
        if r.get("record") == "disposition" and r.get("disposition") == "fixed" and r.get("sha") \
                and of.get(r.get("finding_id")):
            fixes.setdefault(of[r["finding_id"]], set()).add(r["sha"])
        elif r.get("record") == "review" and r.get("continues"):
            continues[r.get("review_id")] = r["continues"]
    return fixes, continues, stamped


def review_lineage(reviews, path_of, fixes=None, continues=None, stamped=None):
    """{review_id: (root review_id, round)} for `reviews`, [(review_id, repo, base, head)] in
    review order (repo a canonical key; `path_of(repo)` is where git reads it). Rounds follow
    the code, not the repo (WellMed 171.2: two lanes in one repo hit the round cap on a first
    review of new code). A review continues an earlier review of the same repo when its range
    shares a commit with it (the same code, read again), or when it starts at that review's head
    AND contains a commit a `fixed` disposition named for a finding of that review's lineage
    (`fixes`, {review_id: {sha}} — a fix re-review) — the highest-round one when several do.
    Starting at a head alone is not enough: a lane's next unit starts there too, and was counted
    round 4–5 (WellMed 171.2-r15, 171.3-r5). `continues` ({review_id: earlier review_id}, from
    `--continues`) names the parent outright. Anything else starts a lineage at round 1. When git
    cannot tell, it fails closed: the review continues the repo's highest round in the unit,
    with a warning on stderr — a silent round 1 would disable the round-3 STOP.
    The fix-commit test is versioned like the loop rules (decision 65, review 10.2-r1-02): only a
    lineage whose ROOT is in `stamped` (recorded under rules 2+) needs it, root-scoped like
    lineage_rules. A lineage rooted unstamped keeps the rule it was recorded under — starting at a head continues, decided without git — so a closed unit's
    round-cap stop stands (kalpa-docs 194.1: r6 continued r5, r7 was round 3 and its `accept`
    stood in for the re-review; under the new rule r7 was round 2 and the gate blocked)."""
    fixes, continues, stamped = fixes or {}, continues or {}, stamped or set()
    out, seen, cache = {}, [], {}
    for rid, repo, base, head in reviews:
        parent, unsure = None, False
        if continues.get(rid) in out:
            parent = continues[rid]
        for prid, prepo, pbase, phead in reversed(seen if parent is None else []):
            if prepo != repo or not (base and head and pbase and phead):
                continue
            if base == phead and out[prid][0] not in stamped:
                share = True   # rules 1 (the parent lineage's root predates the stamp): old continuation, never re-decided by git
            elif base == phead:
                shas = set().union(*(fixes.get(x, ()) for x, (rt, _) in out.items() if rt == out[prid][0]))
                held = _range_holds(path_of(repo), base, head, shas, cache) if shas else False
                # git cannot tell (pruned history, a gone checkout): continue prid, the old rule's
                # answer. `base == phead` is read without git, so prid is the one review this can
                # continue, at its round + 1. A restart at round 1 could disable the round-3 STOP;
                # the `unsure` fallback below (the repo's highest round) could merge an unrelated
                # lineage into this one and inflate the round (149.2-r36 went 2 -> 8).
                if held is None:
                    print(f"[WARN] lineage of {rid}: git cannot tell whether it holds a fix of {prid}'s lineage; "
                          f"continuing {prid} (round {out[prid][1] + 1}) rather than restarting at round 1",
                          file=sys.stderr)
                share = True if held is None else held
            else:
                share = (base, head) == (pbase, phead) or \
                    _ranges_share(path_of(repo), (base, head), (pbase, phead))
            unsure = unsure or share is None
            if share:
                parent = prid if parent is None or out[prid][1] > out[parent][1] else parent
        if parent is None and unsure:
            parent = max((p for p, prepo, *_ in seen if prepo == repo), key=lambda p: out[p][1])
            print(f"[WARN] lineage of {rid}: git cannot tell whether its range overlaps an earlier {repo} review; "
                  f"continuing {parent} (round {out[parent][1]}) rather than restarting at round 1",
                  file=sys.stderr)
        out[rid] = (out[parent][0], out[parent][1] + 1) if parent else (rid, 1)
        seen.append((rid, repo, base, head))
    return out


# review/SKILL.md §5.1 rules a review lineage runs under, stamped on every `review` record (scope 10,
# decision 65). Skills symlink into the live checkout, so sessions mid-review see new scripts at
# cutover: a lineage finishes under the version its root was recorded with. 1 = before scope 10
# (no stamp); 2 = scope 10's findings budget (notes from round 2 log, at most one batch fix, never
# re-reviewed), `reopens` chain stop, and effort trial.
RULES_VERSION = 2


def lineage_rules(recs, lineage):
    """{review_id: rules version of its lineage's root} — `lineage` from review_lineage, `recs`
    the review log. A root without a stamp is version 1; a stamp that is not an int is version
    1 too (the older, stricter rules), never the newer ones by default."""
    stamp = {r.get("review_id"): r.get("rules_version") for r in recs if r.get("record") == "review"}
    v = lambda rid: stamp.get(rid) if isinstance(stamp.get(rid), int) else 1
    return {rid: v(root) for rid, (root, _) in lineage.items()}


def accepted_nits(recs):
    """[(finding, disposition)] for every finding in review-log records `recs` whose latest
    disposition is `accepted` — a process nit (review/SKILL.md §5.1). The gate lists them apart
    from rejections; the /verify judge spot-checks each, inside its run (verify-contracts.md §4.4)."""
    latest, found = {}, {}
    for r in recs:
        if r.get("record") == "disposition":
            latest[r.get("finding_id")] = r
        elif r.get("record") == "finding":
            found[r.get("finding_id")] = r
    return [(found.get(fid, {"finding_id": fid}), d) for fid, d in sorted(latest.items())
            if d.get("disposition") == "accepted"]


# who took a reframe (review/SKILL.md §5.1): `judge` (the fresh judge's accepted verdict, §5.2)
# or `user` (the user's call at a stop) — the first word of a `reframed` disposition's `by`
REFRAMED_BY = re.compile(r"^(judge|user)\b")


def judge_may_take(v):
    """True when an accepted reframe-verdict is the judge's to take: no `overturns`, and a
    `user_call` (review.py's door/overturn decision, review 10.2-r3-01) that is present and empty.
    Fails closed: a verdict with no `user_call` key was never classified, so it is the user's."""
    return not v.get("overturns") and "user_call" in v and not v["user_call"]


def user_call_of(v):
    if v.get("overturns"):
        return f"overturns a recorded decision: {v['overturns']}"
    return v.get("user_call") or "no door classification on the verdict: treated as the user's call"


def judge_took(recs, finding_id, lineage):
    """None when a `reframed --by judge` of `finding_id` is backed by the log, else why not.
    Backed = a review in the finding's lineage (`lineage` from review_lineage) proposed a reframe
    whose `removes` names the finding, and that review's latest `reframe-verdict` is `accepted`
    and the judge's to take (judge_may_take) — an accept that overturns a recorded decision or
    touches a one-way door is the user's call (`--by user`), never the judge's. Review 10.2-r1-01: `--by judge` was the driver's word, so a
    driver could clear any finding, blocking included, without a judge ever running. Fails
    closed: a finding whose review has no lineage (unknown, or a log without review records)
    has nothing to back it."""
    f = next((r for r in recs if r.get("record") == "finding" and r.get("finding_id") == finding_id), None)
    froot = (lineage.get((f or {}).get("review_id")) or (None,))[0]
    if froot is None:
        return f"{finding_id}'s review has no lineage to find the judge's verdict in"
    reframe, verdict = {}, {}
    for r in recs:   # the latest of each, per review
        if r.get("record") == "reframe":
            reframe[r.get("review_id")] = r
        elif r.get("record") == "reframe-verdict":
            verdict[r.get("review_id")] = r
    mine = [rid for rid, r in reframe.items() if finding_id in (r.get("removes") or [])
            and (lineage.get(rid) or (None,))[0] == froot]
    if not mine:
        return f"no reframe in {finding_id}'s review lineage removes it"
    took = [rid for rid in mine if (verdict.get(rid) or {}).get("verdict") == "accepted"]
    if any(judge_may_take(verdict[rid]) for rid in took):
        return None
    if took:
        return (f"the judge's accept of {', '.join(took)} is the user's call "
                f"({'; '.join(user_call_of(verdict[rid]) for rid in took)})")
    return (f"the judge did not accept the reframe of {', '.join(mine)} (latest verdict: "
            f"{', '.join((verdict.get(rid) or {}).get('verdict') or 'none' for rid in mine)})")


# a judge row the runner decided itself (verify-run.py: zero rejections to audit); the judge never sees it
AUTO_PREFIX = "auto: "
# verify/SKILL.md §3.9: finalized /verify runs of one unit before the fix loop stops and asks.
VERIFY_RUN_CAP = 2

# codex reasoning effort scales with the size of what it reads (Alex, 2026-09-29): a one-commit
# re-review at `high` is what drained a 5-hour window in scope 5.3 (12 review rounds, all high).
EFFORT_TIERS = ((80, 4, "low"), (500, 15, "medium"))   # (max changed lines, max files, effort)


def effort_for(stats):
    """`(effort, why)` for a list of (files, lines) diffs — one per repo range. Past every
    tier, `high`. An empty list (a commit-less unit) is `medium`: it reads evidence, not a diff."""
    if not stats:
        return "medium", "no diff (commit-less unit)"
    files, lines = sum(f for f, _ in stats), sum(n for _, n in stats)
    why = f"{files} file(s), {lines} changed line(s)"
    for max_lines, max_files, level in EFFORT_TIERS:
        if lines <= max_lines and files <= max_files:
            return level, why
    return "high", why


EFFORT_LEVELS = ("low", "medium", "high", "xhigh")   # codex-exec.py's --effort choices, lowest first
# The review effort trial (scope 10 §4.2, eng review 2026-10-26): every round of a lineage rooted
# under rules 2+ runs one tier above effort_for, and the review record keeps tier + round so the
# scorecard can compare round 1 with fix rounds. False ends the trial; nothing else changes.
EFFORT_TRIAL = True


def review_effort(stats, rules):
    """(effort, base, why) for a codex review: `base` is effort_for's tier, `effort` the one to
    run — a tier higher under the trial when the lineage's rules (`rules`, from lineage_rules)
    are 2+, capped at the top tier. An older lineage keeps its own effort (decision 65)."""
    base, why = effort_for(stats)
    if not (EFFORT_TRIAL and rules >= 2):
        return base, base, why
    up = EFFORT_LEVELS[min(EFFORT_LEVELS.index(base) + 1, len(EFFORT_LEVELS) - 1)]
    return up, base, f"{why}; effort trial: {base} → {up}"


LEAN_CAP = 1500  # changed lines a lean bundle inlines, across every repo (plan 7, Alex 2026-10-02)


def capped_diff(path, rng, budget=LEAN_CAP):
    """(diff text, inlined, [not-covered lines], total files, lines used) for `rng` in the repo
    at `path`. Files go in whole, in diff order, while they fit in `budget` changed lines; one
    that doesn't is listed by name and size, never cut. Shared by /review's and /verify's lean
    bundles so the two cap the same way. Raises ContractError when git cannot read the range."""
    import subprocess

    def g(*args):
        p = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True)
        if p.returncode != 0:
            raise ContractError(p.stderr.strip() or f"git {args[0]} exit {p.returncode}")
        return p.stdout

    # -z: names unquoted and NUL-terminated, so a name git would quote (spaces, non-ASCII) is
    # read as-is; `:(literal)` keeps it from acting as a glob (review 7.1-r1-06)
    rows = [r.split("\t", 2) for r in g("diff", "--numstat", "-z", "--no-renames", rng).split("\0") if r]
    parts, used, uncovered = [], 0, []
    for added, deleted, name in rows:
        n = (int(added) if added.isdigit() else 0) + (int(deleted) if deleted.isdigit() else 0)
        if used + n > budget:
            uncovered.append(f"`{name}` — {n:,} changed lines; the bundle had {budget - used:,} of its "
                             f"{LEAN_CAP:,}-line lean cap left, so this file was not reviewed")
            continue
        body = g("diff", "--no-color", "--no-ext-diff", "--no-renames", rng, "--", f":(literal){name}")
        if n and not body.strip():
            raise ContractError(f"git produced no patch for `{name}` ({n} changed lines)")
        parts.append(body)
        used += n
    return "\n".join(parts), len(parts), uncovered, len(rows), used


def diff_stat(path, rng):
    """(files, changed lines) for `rng` in the repo at `path`, from `git diff --shortstat`."""
    import subprocess
    p = subprocess.run(["git", "-C", path, "diff", "--shortstat", rng], capture_output=True, text=True)
    nums = [int(x) for x in re.findall(r"(\d+) (?:files? changed|insertions?|deletions?)", p.stdout)]
    files = nums[0] if nums else 0
    return files, sum(nums[1:])


def levers(final, raw):
    """§4.9 lever candidates for one final run: the judge's (from its raw output `raw`),
    plus one automatic candidate per inconclusive / unreachable check the judge left
    unnamed — keyed `<check_id minus its p<P>- phase prefix>-<result>`, so the same
    standard row failing the same way in another scope matches. One implementation:
    judge.py report renders it, lever-candidates.py records it."""
    def key(cid):
        res = final["results"].get(cid, {}).get("result", "judged")
        return f"{re.sub(r'^p[0-9]+-', '', cid)}-{res}"

    # A judge answer recorded before `lever_id` was required (scope 5.3) gets the automatic key.
    out = {c["check_id"]: {"lever_id": key(c["check_id"]), **c} for c in raw.get("lever_candidates", [])}
    for cid, res in final["results"].items():
        if res["result"] in ("inconclusive", "verified-unreachable") and cid not in out:
            out[cid] = {"lever_id": key(cid), "check_id": cid, "gap": res["reason"],
                        "lever": "(judge named none — decide at /closeout)"}
    return list(out.values())


def _tail(path, n):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(x) for x in fh.read().splitlines() if x.strip()][-n:]


def append_verified(path, records, tail=None):
    """Append records as JSONL in one write, then read the last len(records) lines back
    and compare (the dispatch-log.py pattern). Raises ContractError if they differ."""
    tail = tail or _tail
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    lines = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(lines)
    try:
        back = tail(path, len(records))
    except (OSError, ValueError) as exc:
        back = f"unreadable: {exc}"
    if back != [json.loads(json.dumps(r, ensure_ascii=False)) for r in records]:
        raise ContractError(message(
            "ERROR", "verdict-log write did not land", f"the last {len(records)} line(s) of the log "
            "equal what was written", f"read back {back if isinstance(back, str) else len(back)} "
            "differing record(s)", path, "tooling",
            "check disk space and that nothing else writes this file, then re-run", f"{CONTRACT} §4"))
