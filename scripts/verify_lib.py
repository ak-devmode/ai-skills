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
JUDGE_LINE = re.compile(r"^(codex|claude-fallback|none) \S.*$")               # §4.6
# §5.4: advisory until three real scopes pass cleanly — then Alex flips this to "blocking".
GATE_MODE = "advisory"
# Finish-table `repo` cells are paths under this root (§3.2). Tests point it elsewhere.
PROJECTS = os.environ.get("VERIFY_PROJECTS", os.path.expanduser("~/Projects"))


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
    """Return {"revision": int, "rows": [dict], "path": path}. Raises ContractError."""
    docs = f"{CONTRACT} §3"
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        raise ContractError(message("ERROR", "cannot read the finish-condition table",
                                    "a readable finish-conditions.md", str(exc), path, "tooling",
                                    "create it from templates/finish-conditions.md.template", docs))
    schema = rev = None
    for line in lines:
        m = re.match(r"^\*\*Schema version:\*\*\s*(\S+)", line)
        if m:
            schema = m.group(1)
        m = re.match(r"^\*\*Revision:\*\*\s*(\S+)", line)
        if m:
            rev = m.group(1)
    errors = []
    if schema != SCHEMA:
        errors.append(("header", f"**Schema version:** {SCHEMA}", schema or "missing"))
    if not (rev or "").isdigit():
        errors.append(("header", "**Revision:** <integer>", rev or "missing"))

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
    return {"revision": int(rev), "rows": rows, "path": path}


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
