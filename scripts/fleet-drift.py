#!/usr/bin/env python3
"""fleet-drift.py — fail when a deployed service is missing from the fleet list.

Approach: a project that keeps a fleet list (WellMed: wellmed-infrastructure
`operations/fleet.txt`, the loop every fleet-wide CI sync runs over) drifts from its
architecture inventory silently — WellMed scope 149 found bpjs and finance in neither
`fleet.txt` nor the Prometheus scrape map, so a fleet-wide sync had been skipping two
live services. This compares the two and exits 1 on any gap.

  inventory   every repo in the ARCHITECTURE.md port-allocation table — rows shaped
              "| `:NNNN` | <repo> | …". A port is what makes a repo a deployed
              service; the §3 narrative table also lists planned repos ("repo TBD")
              and external surfaces that are deliberately not in the fleet.
  fleet       the first column of every non-comment line of the fleet list.
  exclusions  comment lines "#   <repo> — excluded …" under a comment header
              "EXCLUDED, dated (… YYYY-MM-DD)". An exclusion with no dated header is
              not honoured: an absence nobody dated is drift with an excuse.

Exit 0 every inventory repo is in the fleet or excluded · 1 drift (each gap printed
as `missing: <repo>`) · 3 cannot evaluate (unreadable input, or an input that parsed
to nothing — an empty inventory must never read as "no drift").

Usage:
  fleet-drift.py --arch ARCHITECTURE.md --fleet operations/fleet.txt
  fleet-drift.py --arch ARCHITECTURE.md --fleet-git ~/Projects/wellmed/wellmed-infrastructure \\
      origin/develop:operations/fleet.txt
"""

import argparse
import re
import subprocess
import sys

PORT_ROW = re.compile(r"^\|\s*`:\d+`\s*\|\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*\|")
EXCL_HEADER = re.compile(r"^#.*EXCLUDED, dated \(.*?(\d{4}-\d{2}-\d{2})")
EXCL_ROW = re.compile(r"^#\s+([A-Za-z0-9][A-Za-z0-9._-]*)\s+(?:—|--?)\s+excluded\b")


def inventory(arch_text):
    """Repos in the port-allocation table, in order, de-duplicated."""
    seen = []
    for line in arch_text.splitlines():
        m = PORT_ROW.match(line.strip())
        if m and m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def fleet(fleet_text):
    """(members, {excluded repo: date}, [undated exclusion repos])."""
    members, excluded, undated = [], {}, []
    date = None
    for raw in fleet_text.splitlines():
        line = raw.rstrip()
        if not line.startswith("#"):
            date = None  # a dated block ends at the first non-comment line
            if line.strip():
                members.append(line.split()[0])
            continue
        h = EXCL_HEADER.match(line)
        if h:
            date = h.group(1)
            continue
        r = EXCL_ROW.match(line)
        if r:
            if date:
                excluded[r.group(1)] = date
            else:
                undated.append(r.group(1))
    return members, excluded, undated


def read_git(repo, spec):
    out = subprocess.run(["git", "-C", repo, "show", spec], capture_output=True, text=True)
    if out.returncode != 0:
        raise OSError(f"git -C {repo} show {spec}: {out.stderr.strip()}")
    return out.stdout


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arch", required=True, help="ARCHITECTURE.md holding the port table")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--fleet", help="fleet list file")
    src.add_argument("--fleet-git", nargs=2, metavar=("REPO", "REV:PATH"),
                     help="read the fleet list from git (e.g. origin/develop:operations/fleet.txt)")
    a = ap.parse_args(argv)
    try:
        with open(a.arch, encoding="utf-8") as fh:
            arch_text = fh.read()
        if a.fleet:
            with open(a.fleet, encoding="utf-8") as fh:
                fleet_text = fh.read()
        else:
            fleet_text = read_git(*a.fleet_git)
    except OSError as e:
        print(f"cannot evaluate: {e}")
        return 3

    inv = inventory(arch_text)
    members, excluded, undated = fleet(fleet_text)
    if not inv:
        print(f"cannot evaluate: no port-table rows in {a.arch}")
        return 3
    if not members:
        print("cannot evaluate: the fleet list has no member rows")
        return 3

    missing = [r for r in inv if r not in members and r not in excluded]
    for r in inv:
        if r in excluded and r not in members:
            print(f"excluded: {r} (dated {excluded[r]})")
    for r in undated:
        print(f"undated exclusion ignored: {r}")
    for r in missing:
        print(f"missing: {r} — in the ARCHITECTURE.md port table, not in the fleet list or a dated exclusion")
    if missing:
        print(f"drift: {len(missing)} of {len(inv)} inventory repos missing")
        return 1
    print(f"ok: {len(inv)} inventory repos covered ({len(members)} fleet rows, {len(excluded)} dated exclusions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
