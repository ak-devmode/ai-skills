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
# line in its PLANS-INDEX.md (kalpa-iris, 2026-09-29 — code nobody reads needs a gate that stops).
GATE_MODE_LINE = re.compile(r"^\*\*Gate mode:\*\*[ \t]*(.*?)[ \t]*$", re.M)
# Finish-table `repo` cells are paths under this root (§3.2). Tests point it elsewhere.
PROJECTS = os.environ.get("VERIFY_PROJECTS", os.path.expanduser("~/Projects"))


def _git_lines(path, *args):
    import subprocess
    p = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True)
    return p.stdout.splitlines() if p.returncode == 0 else []


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
    """The mode the gate runs in for this scope: the nearest PLANS-INDEX.md's
    `**Gate mode:**` line, else GATE_MODE. Walks up at most three levels, which covers
    plans/{N}/, plans/archive/{N}/ and plans/{program}/archive/{N}/."""
    d = os.path.realpath(scope_dir)
    for _ in range(3):
        d = os.path.dirname(d)
        index = os.path.join(d, "PLANS-INDEX.md")
        if os.path.isfile(index):
            with open(index, encoding="utf-8") as fh:
                m = GATE_MODE_LINE.search(fh.read())
            if m is None:
                return GATE_MODE
            if m.group(1) not in ("blocking", "advisory"):
                # a typo must never quietly downgrade a blocking graph (review adhoc-02)
                raise ContractError(message(
                    "ERROR", "the index declares an unknown gate mode", "**Gate mode:** blocking | advisory",
                    repr(m.group(1)), index, "code", "fix the **Gate mode:** line", f"{CONTRACT} §5.4.2"))
            return m.group(1)
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

_TYPES = {"object": dict, "array": list, "string": str}


def schema_problems(doc, schema, path="answer"):
    """Problems with `doc` against the JSON Schema subset our answer schemas use — type,
    required, additionalProperties: false, enum, items. Both answer writers (review.py,
    judge.py) run this before any semantic check, so a wrong container or a missing field
    is exit 3 and never a crash or a partial write (review 5.2-r1-06)."""
    t = schema.get("type")
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
# review/SKILL.md §5.1: rounds of one repo in a unit before the loop stops and asks the user.
# review.py's deferral rule and verdict-gate.py's re-review waiver read the same number.
ROUND_CAP = 3
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
