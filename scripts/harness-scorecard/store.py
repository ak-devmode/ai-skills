"""Run store, delta and rendering for the harness scorecard.

Approach: each run's tables are saved as one JSON file under the store dir
(`~/.cache/harness-scorecard/<UTC stamp>.json`, written to a temp file and renamed, then read
back). A table is {"cols": [...], "rows": {label: [numbers]}} — numbers only, so the store
never holds transcript text. The delta is cell-wise current − previous for the same table /
row / column; rendering adds a Δ column after every numeric column when a previous run exists.
The previous run is the latest with the same profile (flags + window length): a Δ against a
run computed another way measures the configuration, not the harness.

A previous run that cannot be read does not stop the scorecard: the delta is advisory (nothing
gates on it), so the run prints with no Δ and a WARN naming the file — failing the whole report
over a corrupt history file would hide today's numbers, which are the point.
"""

import glob
import json
import os
import tempfile
from datetime import datetime, timezone


def stamp(now=None):
    # microseconds: two runs in one second must not share a name (names sort chronologically)
    return (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%S%fZ")


def save(store_dir, result, now=None):
    """Write `result` as <stamp>.json, read it back, return the path. Never overwrites an earlier
    run: the temp file is hard-linked into place, which fails when the name exists. Raises on a
    failed write."""
    os.makedirs(store_dir, exist_ok=True)
    path = os.path.join(store_dir, stamp(now) + ".json")
    fd, tmp = tempfile.mkstemp(dir=store_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(result, fh, indent=1, sort_keys=True)
        os.link(tmp, path)
    finally:
        os.unlink(tmp)
    with open(path) as fh:  # a green write is not a completed action: read it back
        if json.load(fh).get("tables") != json.loads(json.dumps(result)).get("tables"):
            raise OSError(f"{path}: read-back does not match what was written")
    return path


def profile(result):
    """What makes two runs comparable: their flags and their window length. A run stored before
    profiles existed has neither, and matches no profiled run."""
    return {"flags": result.get("flags"), "window_class": (result.get("window") or {}).get("class")}


def previous(store_dir, before=None, match=None):
    """(path, result) of the latest stored run (excluding `before`'s path) whose profile equals
    `match` (any run when None), (path, None) when a newer run is unreadable, (None, None) when
    there is none. An unreadable run newer than the match stops the search: it may have been
    the reference, and a Δ against an older one would be read as today's movement."""
    runs = sorted(p for p in glob.glob(os.path.join(store_dir, "*.json")) if p != before)  # stamps sort by time
    for path in reversed(runs):
        try:
            with open(path) as fh:
                res = json.load(fh)
            if not isinstance(res.get("tables"), dict):
                return path, None
        except (OSError, ValueError, AttributeError):
            return path, None
        if match is None or profile(res) == match:
            return path, res
    return None, None


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def delta(cur, prev):
    """{table: {row: [Δ or None]}} — None where either side is not a number; a row new in this run
    gets "new"."""
    out = {}
    for name, t in cur.items():
        pt = (prev or {}).get(name) or {}
        pcols, prows = pt.get("cols") or [], pt.get("rows") or {}
        rows = {}
        for label, vals in t["rows"].items():
            if label not in prows:
                rows[label] = "new"
                continue
            pv = dict(zip(pcols, prows[label]))
            rows[label] = [round(v - pv[c], 2) if _num(v) and _num(pv.get(c)) else None
                           for c, v in zip(t["cols"], vals)]
        out[name] = rows
    return out


def _fmt(v):
    if v is None:
        return "–"
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".") if abs(v) < 10 else f"{v:.1f}"
    return str(v)


def _fmt_d(d):
    if d is None:
        return ""
    if d == 0:
        return "0"
    return ("+" if d > 0 else "") + _fmt(d)


def render(name, table, d=None):
    """One markdown table; `d` is this table's delta rows (None = no previous run)."""
    cols = ["", *[x for c in table["cols"] for x in ((c, "Δ") if d is not None else (c,))]]
    lines = [f"### {name}", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for label, vals in table["rows"].items():
        cells = [label]
        for i, v in enumerate(vals):
            cells.append(_fmt(v))
            if d is not None:
                dr = d.get(label)
                cells.append("new" if dr == "new" else _fmt_d(dr[i] if dr and i < len(dr) else None))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
