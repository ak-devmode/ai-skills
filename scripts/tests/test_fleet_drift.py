"""fleet-drift.py — a deployed service missing from the fleet list fails /closeout.

Approach: fixtures shaped like WellMed's real inputs (ARCHITECTURE.md §3.1 port table,
wellmed-infrastructure operations/fleet.txt with its dated hq exclusion), run as a
subprocess the way /closeout calls it. The acceptance case is plan 149.3 Task 3.4's:
remove bpjs from the fleet list and the check must fail naming it.
"""

import os
import subprocess
import tempfile
import unittest

from _helpers import run

ARCH = """\
## 3. Microservice Inventory
| 13 | BPJS | wellmed-bpjs *(repo TBD)* | `integration-ms` (planned) | — |
### 3.1 Port Allocation
| Port | Service | Protocol | Class | Notes |
|---|---|---|---|---|
| `:8080` | wellmed-gateway-go | HTTP | `frontend` | Sole external HTTP entry |
| `:50050` | wellmed-gateway-go | gRPC | `frontend` | egress broker |
| `:50051` | wellmed-backbone | gRPC | `core-ms` | |
| `:50059` | wellmed-hq | gRPC | `integration-ms` | Reserved |
| `:50060` | wellmed-bpjs | gRPC | `integration-ms` | |
## 4. Next
"""

FLEET = """\
# WellMed fleet
#
# EXCLUDED, dated (scope 149, Alex 2026-09-26):
#   wellmed-hq — excluded until after Padma go-live. It is a real fleet member;
#                the check treats this line as the one sanctioned absence.

wellmed-backbone        go    full
wellmed-gateway-go      go    full
wellmed-bpjs            go    full
wellmed-fe              nuxt  simple
"""


class FleetDriftTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, text):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def check(self, arch=ARCH, fleet=FLEET):
        return run("fleet-drift.py", "--arch", self.write("ARCHITECTURE.md", arch),
                   "--fleet", self.write("fleet.txt", fleet))

    def test_cases(self):
        no_bpjs = FLEET.replace("wellmed-bpjs            go    full\n", "")
        undated = FLEET.replace("# EXCLUDED, dated (scope 149, Alex 2026-09-26):\n", "")
        # A member row between the header and the hq line closes the dated block.
        split = FLEET.replace("#   wellmed-hq", "wellmed-extra go full\n#   wellmed-hq")
        cases = [
            # name, arch, fleet, exit, must-contain, must-not-contain
            ("in sync, hq excluded by date", ARCH, FLEET, 0, ["excluded: wellmed-hq (dated 2026-09-26)", "ok: 4"], ["missing"]),
            ("bpjs removed from the fleet list fails", ARCH, no_bpjs, 1, ["missing: wellmed-bpjs", "drift: 1 of 4"], []),
            ("undated exclusion is not honoured", ARCH, undated, 1, ["undated exclusion ignored: wellmed-hq", "missing: wellmed-hq"], []),
            ("dated block ends at a member row", ARCH, split, 1, ["missing: wellmed-hq"], []),
            ("planned 'repo TBD' row outside the port table is not inventory", ARCH.replace("| `:50060` | wellmed-bpjs | gRPC | `integration-ms` | |\n", ""), no_bpjs, 0, ["ok: 3"], []),
            ("empty inventory cannot evaluate", "## 3.\nno table\n", FLEET, 3, ["cannot evaluate: no port-table rows"], []),
            ("empty fleet list cannot evaluate", ARCH, "# only comments\n", 3, ["cannot evaluate: the fleet list has no member rows"], []),
        ]
        for name, arch, fleet, code, want, not_want in cases:
            with self.subTest(name):
                p = self.check(arch, fleet)
                self.assertEqual(p.returncode, code, p.stdout + p.stderr)
                for w in want:
                    self.assertIn(w, p.stdout)
                for w in not_want:
                    self.assertNotIn(w, p.stdout)

    def test_fleet_git_reads_the_ref_and_fails_closed(self):
        repo = os.path.join(self.tmp.name, "infra")
        os.makedirs(os.path.join(repo, "operations"))
        git = ["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(["git", "init", "-q", repo], check=True)
        with open(os.path.join(repo, "operations", "fleet.txt"), "w", encoding="utf-8") as fh:
            fh.write(FLEET.replace("wellmed-bpjs            go    full\n", ""))
        subprocess.run(git + ["add", "."], check=True)
        subprocess.run(git + ["commit", "-qm", "fleet"], check=True)
        arch = self.write("ARCHITECTURE.md", ARCH)

        p = run("fleet-drift.py", "--arch", arch, "--fleet-git", repo, "HEAD:operations/fleet.txt")
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("missing: wellmed-bpjs", p.stdout)

        p = run("fleet-drift.py", "--arch", arch, "--fleet-git", repo, "HEAD:operations/nope.txt")
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertIn("cannot evaluate", p.stdout)


if __name__ == "__main__":
    unittest.main()
