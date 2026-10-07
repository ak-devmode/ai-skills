"""resolve-identifiers.py — counterexamples first: every way a name can look declared
without being declared must fail, and a real declaration in the same change must pass.

Approach: table-driven. Each case builds a throwaway repo with a base commit and a head
commit, runs the script over base..head exactly as /verify will, and asserts the exit
code, the summary line, and — on failure — that every message carries the six fields of
the message contract (templates/verify-contracts.md §10).
"""

import json
import os
import re
import subprocess
import tempfile
import unittest

from _helpers import run

CONTRACT_FIELDS = ("expected ·", "found    ·", "where    ·", "cause    ·", "next     ·", "docs     ·")

PROTO = """syntax = "proto3";
package clinic.v1;
// patient_id in a comment must not count for Appointment
message Invoice { string patient_id = 1; int64 total = 2; }
message Appointment {
  string slot = 1;
  oneof who { string doctor_id = 2; }
  message Inner { string patient_id = 1; }
}
"""


def git(path, *args):
    return subprocess.run(["git", "-C", path, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          check=True, capture_output=True, text=True).stdout.strip()


def write(root, files):
    for rel, text in files.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)


class Repo:
    def __init__(self, base, head):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = self.tmp.name
        git(self.path, "init", "-q", "-b", "main")
        write(self.path, dict({"README.md": "x\n"}, **base))
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", "base")
        self.base = git(self.path, "rev-parse", "HEAD")
        write(self.path, head)
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "--allow-empty", "-m", "head")

    def check(self, *extra):
        return run("resolve-identifiers.py", "--repo", self.path, "--range", f"{self.base}..HEAD", *extra)

    def close(self):
        self.tmp.cleanup()


# (name, base files, head files, expected exit, summary regex, extra stdout needle)
CASES = [
    # a docs-only range is a clean, explicit pass — never a bare `found 0` (kalpa-iris scope 1)
    ("docs-only range is not applicable",
     {}, {"docs/plan.md": "uses process.env.NOT_CODE\n"},
     0, r"found 0 · resolved 0", "not applicable: "),
    ("source with no references has nothing to resolve",
     {}, {"src/app.ts": "export const x = 1;\n"},
     0, r"found 0 · resolved 0", "nothing to resolve: 1 changed source file(s)"),
    ("fake env var fails",
     {".env.example": "REAL_VAR=1\n"},
     {"src/app.ts": "const x = process.env.FAKE_VAR;\n"},
     1, r"found 1 · resolved 0 · unresolved 1", "env `FAKE_VAR` does not resolve"),
    ("declared env var passes",
     {".env.example": "REAL_VAR=1\n"},
     {"src/app.ts": "const x = process.env.REAL_VAR;\n"},
     0, r"found 1 · resolved 1 · unresolved 0", ".env.example:1"),
    ("comment-only declaration fails",
     {".env.example": "# COMMENTED=1\n"},
     {"src/app.ts": "const x = process.env.COMMENTED;\n"},
     1, r"unresolved 1", "1 hit(s) in comments or fixtures ignored"),
    ("fixture-only declaration fails",
     {"test/fixtures/.env.example": "FIX_ONLY=1\n"},
     {"test/app.py": "import os\nv = os.environ.get('FIX_ONLY')\n"},
     1, r"unresolved 1", "env `FIX_ONLY` does not resolve"),
    ("same-diff declaration passes",
     {".env.example": "OLD=1\n"},
     {".env.example": "OLD=1\nNEW_VAR=2\n", "cmd/main.go": "package main\nvar v = os.Getenv(\"NEW_VAR\")\n"},
     0, r"found 1 · resolved 1", "NEW_VAR"),
    ("sibling service's declaration does not count",
     {"services/a/.env.example": "A_ONLY=1\n"},
     {"services/b/main.go": "package b\nvar v = os.Getenv(\"A_ONLY\")\n"},
     1, r"unresolved 1", "env `A_ONLY` does not resolve"),
    # plain `env.example`, no leading dot — the WellMed fleet's filename (149.2: catalog,
    # pharmacy, bpjs reported their declared names unresolved)
    ("plain env.example declares",
     {"env.example": "APP_ENV=dev\nDB_URL=postgres://x\n"},
     {"cmd/main.go": "package main\nvar v = os.Getenv(\"DB_URL\")\n"},
     0, r"found 1 · resolved 1", "env.example:2"),
    ("a sibling service's plain env.example does not count",
     {"services/a/env.example": "A_ONLY=1\n"},
     {"services/b/main.go": "package b\nvar v = os.Getenv(\"A_ONLY\")\n"},
     1, r"unresolved 1", "env `A_ONLY` does not resolve"),
    ("env.example.bak is not a declaration file",
     {"env.example.bak": "BAK_ONLY=1\n"},
     {"cmd/main.go": "package main\nvar v = os.Getenv(\"BAK_ONLY\")\n"},
     1, r"unresolved 1", "env `BAK_ONLY` does not resolve"),
    ("ancestor declaration counts",
     {".env.example": "ROOT_VAR=1\n"},
     {"services/b/main.go": "package b\nvar v = os.Getenv(\"ROOT_VAR\")\n"},
     0, r"resolved 1", "ROOT_VAR"),
    # shell (5.3 lever shell-env-identifier-scan)
    ("shell env read undeclared fails",
     {".env.example": "REAL_VAR=1\n"},
     {"bin/run.sh": "#!/bin/sh\necho \"${SH_FAKE:-x}\" $REAL_VAR\n"},
     1, r"found 2 · resolved 1 · unresolved 1", "env `SH_FAKE` does not resolve"),
    ("shell: names the script assigns, single-quoted text and shell variables are not env reads",
     {"bin/run.sh": "#!/bin/sh\nOUT=/tmp/x\nlocal N=1\n"},
     {"bin/run.sh": "#!/bin/sh\nOUT=/tmp/x\nlocal N=1\nfor F in a b; do echo $F; done\n"
                    "read -r LINE\necho \"$OUT $N $HOME $PATH $LINE\" 'awk $NOT_ENV'\n"},
     0, r"found 0 · resolved 0", ""),
    ("shell: a self-defaulting assignment still reads the env (5.3-r5-01)",
     {},
     {"bin/run.sh": "#!/bin/sh\nFOO=${FOO:-fallback}\necho \"$FOO\"\n"},
     1, r"unresolved 1", "env `FOO` does not resolve"),
    ("shell: read before a later assignment is an env read (5.3-r5-01)",
     {},
     {"bin/run.sh": "#!/bin/sh\necho $LATE\nLATE=1\n"},
     1, r"unresolved 1", "env `LATE` does not resolve"),
    ("shell: case-conversion expansion is a read (5.3-r5-02)",
     {},
     {"bin/run.sh": "#!/bin/bash\necho ${UPPER_ME^^} ${ARR_X[0]}\n"},
     1, r"unresolved 2", "env `UPPER_ME` does not resolve"),
    ("shell: a loop or read over its own name reads the env first (5.3-r6-01)",
     {},
     {"bin/run.sh": "#!/bin/bash\nfor LOOPV in \"$LOOPV\"; do :; done\nread RV <<< \"$RV\"\n"},
     1, r"unresolved 2", "env `LOOPV` does not resolve"),
    ("shell: NAME= in a comment or quoted text is not an assignment (5.3-r6-02)",
     {},
     {"bin/run.sh": "#!/bin/sh\necho ok # TOKEN=sample\necho \"sample TOKEN2=abc\"\necho $TOKEN $TOKEN2\n"},
     1, r"unresolved 2", "env `TOKEN` does not resolve"),
    ("shell: assign then read on one line binds first (5.3-r6-03)",
     {},
     {"bin/run.sh": "#!/bin/sh\nFOO=1; echo \"$FOO\"\nif true; then BAR=2; fi; echo $BAR\n"},
     0, r"found 0 · resolved 0", ""),
    ("shell: quoted whitespace or substitution in an assignment still reads (5.3-r7-01)",
     {},
     {"bin/run.sh": "#!/bin/sh\nQW=\"a b $QW\"\nQS=$(printf %s \"$QS\")\n"},
     1, r"unresolved 2", "env `QW` does not resolve"),
    ("shell: a quoted `do` or `;` is not the loop's end (5.3-r7-02)",
     {},
     {"bin/run.sh": "#!/bin/bash\nfor LV in \"do $LV\"; do :; done\nread RD <<< \"x; $RD\"\n"},
     1, r"unresolved 2", "env `LV` does not resolve"),
    ("shell: then/do/else as plain arguments start no command (5.3-r7-03)",
     {},
     {"bin/run.sh": "#!/bin/sh\necho then TOK=sample; echo $TOK\n"},
     1, r"unresolved 1", "env `TOK` does not resolve"),
    ("shell: several assignments, and export over names, all bind (5.3-r7-04)",
     {},
     {"bin/run.sh": "#!/bin/sh\nA1=1 B1=2; echo $B1\nexport C1 D1=3\necho $C1 $D1 $A1\n"},
     0, r"found 0 · resolved 0", ""),
    ("shell: a read option's operand is not a destination (5.3-r8-01)",
     {},
     {"bin/run.sh": "#!/bin/bash\nread -p \"Enter token\" TOKEN_IN\necho $TOKEN_IN $X\nread -rp 'p' -t 5 OTHER\necho $OTHER\n"},
     1, r"found 1 · resolved 0 · unresolved 1", "env `X` does not resolve"),
    ("shell: 2>&1 is a redirection, not a background separator (5.3-r8-02)",
     {},
     {"bin/run.sh": "#!/bin/sh\nRED=1 2>&1; echo $RED\n"},
     0, r"found 0 · resolved 0", ""),
    ("shell: after r11-01 a backgrounding line binds nothing, even `sleep 1 & AMP=1` (fails closed)",
     {},
     {"bin/run.sh": "#!/bin/sh\nsleep 1 & AMP=1; echo \"$AMP\"\n"},
     1, r"unresolved 1", "env `AMP` does not resolve"),
    ("shell: a backgrounded or piped assignment never reaches the script (5.3-r9-01)",
     {},
     {"bin/run.sh": "#!/bin/bash\nBG=1 & wait; echo $BG\nPP=1 | cat; echo $PP\n"},
     1, r"unresolved 2", "env `BG` does not resolve"),
    ("shell: grouped read options with an attached operand (5.3-r9-02)",
     {},
     {"bin/run.sh": "#!/bin/bash\nread -rpd GRP <<< hi\necho $GRP\n"},
     0, r"found 0 · resolved 0", ""),
    ("shell: a backgrounded AND list and a |& pipeline bind nothing (5.3-r10-01, r10-02)",
     {},
     {"bin/run.sh": "#!/bin/bash\nAL=1 && BL=2 & wait; echo $AL\nprintf x |& read PT; echo $PT\n"},
     1, r"unresolved 2", "env `AL` does not resolve"),
    ("shell: a line that backgrounds or continues binds nothing (5.3-r11-01)",
     {},
     {"bin/run.sh": "#!/bin/bash\nAP=1 && printf x | cat & wait; echo $AP\nAC=1 &&\n  true & wait\necho $AC\n"},
     1, r"unresolved 2", "env `AP` does not resolve"),
    ("shell: `X=$(…) \\` continued only into an `||` / `&&` tail still binds X",
     {},
     {"bin/run.sh": "#!/bin/bash\nSHA=$(curl -sf x | jq -r .v) \\\n  || { echo \"down\"; exit 1; }\n"
                    "OK=1 \\\n  && true\necho $SHA $OK\n"},
     0, r"found 0 · resolved 0", ""),
    ("shell: a `\\` continued into a pipe, a background, a command or a further continuation binds nothing",
     {},
     {"bin/run.sh": "#!/bin/bash\nCP=1 \\\n  | cat\nCB=1 \\\n  || true & wait\nCW=1 \\\n  echo hi\n"
                    "CC=1 \\\n  || true \\\n  || false\nCE=1 \\\n\necho $CP $CB $CW $CC $CE\n"},
     1, r"found 5 · resolved 0 · unresolved 5", "env `CB` does not resolve"),
    ("shell: a `NAME=… node -e '…'` prefix provides process.env.NAME inside that body only",
     {},
     {"bin/run.sh": "#!/bin/bash\nr=$(UNDER=\"${SRC_URL:-}\" node -e '\n  const v = process.env.UNDER || \"\"\n"
                    "  const w = process.env.NODE_OTHER\n') || r=x\n"
                    "node -e 'console.log(process.env.UNDER)'\n"
                    "NOT_CMD=1\nnode -e 'process.env.NOT_CMD'\n"
                    "echo X=1 node -e 'process.env.X'\n"},
     1, r"found 5 · resolved 0 · unresolved 5", "env `NODE_OTHER` does not resolve"),
    ("shell: an assignment after a case-arm pattern binds, `a|b)` and `(a)` included",
     {},
     {"bin/run.sh": "#!/bin/sh\ncase \"$1\" in\n  develop) BLUE=3004; GREEN=3006 ;;\n"
                    "  staging|production) BLUE=3000; GREEN=3001 ;;\n  (*) BLUE=1 ;;\nesac\n"
                    "case \"$1\" in a) NX=x ;; *) NX=y ;; esac\necho $BLUE $GREEN $NX\n"},
     0, r"found 0 · resolved 0", ""),
    ("shell: case arms bind only inside a case; reads in a header, pattern or arm still count",
     {},
     {"bin/run.sh": "#!/bin/sh\ncase \"$MODE\" in\n  \"$WANT\") HIT=1 ;;\n  *) X=$ARM_RD ;;\nesac\n"
                    "echo $HIT\nfoo) OUTSIDE=1\necho $OUTSIDE\n"
                    "case x in\n  a) PIPED=1 | cat ;;\nesac\necho $PIPED\n"},
     1, r"found 5 · resolved 0 · unresolved 5", "env `OUTSIDE` does not resolve"),
    ("use inside a comment is not a reference",
     {},
     {"src/app.ts": "// process.env.GHOST is mentioned here only\nconst y = 1;\n"},
     0, r"found 0 · resolved 0", ""),
    ("unrelated-proto field fails",
     {"proto/clinic.proto": PROTO},
     {"svc/h.go": "package svc\nvar a = &clinicv1.Appointment{PatientId: id}\n"},
     1, r"unresolved 1", "field `PatientId` in `message Appointment`"),
    ("field on its own message passes (multi-line literal, oneof)",
     {"proto/clinic.proto": PROTO},
     {"svc/h.go": "package svc\nvar a = &clinicv1.Invoice{\n\tPatientId: id,\n\tTotal: 3,\n}\n"
                  "var b = &clinicv1.Appointment{Slot: s, Who: w}\n"},
     0, r"found 4 · resolved 4", "message Invoice"),
    ("a nested literal's fields belong to the nested message, on one line or the next",
     {"proto/clinic.proto": PROTO + "message Visit { Appointment appt = 1; string note = 2; }\n"},
     {"svc/h.go": "package svc\nvar a = send(&clinicv1.Visit{Appt: &clinicv1.Appointment{\n"
                  "\tSlot: s, Who: w,\n}})\n"
                  "var b = &clinicv1.Visit{Appt: &clinicv1.Appointment{Slot: s}, Note: n}\n"},
     0, r"found 4 · resolved 4", "message Appointment"),
    ("a field set on the outer message after a nested literal closes is the outer's",
     {"proto/clinic.proto": PROTO + "message Visit { Appointment appt = 1; string note = 2; }\n"},
     {"svc/h.go": "package svc\nvar a = &clinicv1.Visit{\n\tAppt: &clinicv1.Appointment{\n\t\tSlot: s,\n\t},\n"
                  "\tSlot: s,\n}\n"},
     1, r"found 3 · resolved 2 · unresolved 1", "field `Slot` in `message Visit`"),
    ("keys of a non-pb literal or a string inside a pb literal are not its fields",
     {"proto/clinic.proto": PROTO},
     {"svc/h.go": "package svc\nvar a = &clinicv1.Invoice{\n\tPatientId: fmt.Sprintf(\"{Bogus: %d}\", 1),\n"
                  "\tTotal: opts{Limit: 3}.Limit,\n}\nvar after = cfg{Name: n}\n"},
     0, r"found 2 · resolved 2", ""),
    ("python _pb2 kwarg on the wrong message fails",
     {"proto/clinic.proto": PROTO},
     {"svc/h.py": "a = clinic_pb2.Appointment(slot='x', patient_id='p')\n"},
     1, r"found 2 · resolved 1 · unresolved 1", "Appointment.patient_id"),
    ("ssm path matches a placeholder declaration",
     {"infra/ssm.tf": 'resource "aws_ssm_parameter" "db" {\n  name = "/app/{env}/db/password"\n}\n'},
     {"svc/cfg.go": "package svc\nvar p = ssmClient.GetParameter(\"/app/dev/db/password\")\n"},
     0, r"resolved 1", "infra/ssm.tf:2"),
    ("invented ssm path fails",
     {"infra/ssm.tf": 'resource "aws_ssm_parameter" "db" {\n  name = "/app/{env}/db/password"\n}\n'},
     {"svc/cfg.go": "package svc\nvar p = ssmClient.GetParameter(\"/app/dev/db/pasword\")\n"},
     1, r"unresolved 1", "ssm `/app/dev/db/pasword` does not resolve"),
    ("route resolves with params; invented route fails",
     {"server/routes.js": "router.get('/patients/:id', show);\n"},
     {"web/api.ts": "fetch(`/patients/${id}`);\nfetch('/patient-list');\n"},
     1, r"found 2 · resolved 1 · unresolved 1", "route `/patient-list` does not resolve"),
    ("a fetch to an interpolated base or absolute origin is external; a relative one is checked",
     {"server/routes.js": "router.get('/patients/:id', show);\n"},
     {"web/alert.mjs": "fetch(`${SENTRY_URL}/api/0${path}`);\nfetch('https://api.ocr.space/parse');\n"
                       "fetch('/api/invented');\naxios.get(`${base}/api/also-invented`);\n"},
     1, r"found 2 · resolved 0 · unresolved 2", "route `/api/invented` does not resolve"),
    ("a suffix-only match is not resolved (prefix unseen)",
     {"server/routes.go": "package server\nfunc reg(g *gin.RouterGroup) { g.GET(\"/invoices\", h) }\n"},
     {"web/api.ts": "axios.get('/api/v1/invoices');\n"},
     1, r"unresolved 1", "matches only as a suffix"),
    ("a gin group prefix in the same file resolves the full route",
     {"server/routes.go": "package server\nfunc reg(r *gin.Engine) {\n\tapi := r.Group(\"/api\")\n"
                          "\tv1 := api.Group(\"/v1\")\n\tv1.GET(\"/invoices\", h)\n}\n"},
     {"web/api.ts": "axios.get('/api/v1/invoices');\n"},
     0, r"resolved 1", "server/routes.go:5"),
    ("a group var reused across functions does not leak its prefix (5.2-r1-02)",
     {"server/routes.go": "package server\nfunc users(r *gin.Engine) {\n\tg := r.Group(\"/users\")\n"
                          "\tg.GET(\"/list\", h)\n}\nfunc admin(r *gin.Engine) {\n"
                          "\tg := r.Group(\"/admin\")\n\tg.GET(\"/stats\", h)\n}\n"},
     {"web/api.ts": "axios.get('/users/list');\naxios.get('/admin/stats');\naxios.get('/admin/list');\n"},
     1, r"found 3 · resolved 2 · unresolved 1", "route `/admin/list` does not resolve"),
    ("generated .pb.go struct declares a Go caller's fields",
     {"proto/approvalpb/approval.pb.go": "package approvalpb\n\ntype UpsertPolicyRequest struct {\n"
                                          "\tstate protoimpl.MessageState\n\tActionKey string `protobuf:\"x\"`\n}\n"},
     {"h.go": "package h\nvar r = &approvalpb.UpsertPolicyRequest{ActionKey: k}\n"
              "var s = &approvalpb.UpsertPolicyRequest{Enabled: true}\n"},
     1, r"found 2 · resolved 1 · unresolved 1", "UpsertPolicyRequest.Enabled"),
    ("env read in a test file is skipped",
     {},
     {"x/db_integration_test.go": "package x\nvar d = os.Getenv(\"ONLY_IN_TESTS\")\n"},
     0, r"found 0", ""),
    ("an ESM/CJS test file (.test.mjs, .spec.cjs) is skipped; a plain .mjs is still scanned",
     {},
     {".github/scripts/deploy.test.mjs": "const p = process.env.MJS_TEST_ONLY;\n",
      "lib/x.spec.cjs": "const p = process.env.CJS_TEST_ONLY;\n",
      "core/scripts/alert.mjs": "const t = process.env.MJS_REAL;\n"},
     1, r"found 1 · resolved 0 · unresolved 1", "env `MJS_REAL` does not resolve"),
    ("source embedded as strings in a test file is not a reference",
     {},
     {"tests/test_thing.py": "SRC = 'var a = &clinicv1.Invoice{Total: 3}'\nJS = \"fetch('/nope')\"\n"},
     0, r"found 0", ""),
    ("route method mismatch fails",
     {"server/routes.js": "router.post('/invoices', create);\n"},
     {"web/api.ts": "axios.get('/invoices');\n"},
     1, r"unresolved 1", "GET /invoices"),
]


class TestResolveIdentifiers(unittest.TestCase):
    def test_cases(self):
        for name, base, head, code, summary, needle in CASES:
            with self.subTest(case=name):
                repo = Repo(base, head)
                try:
                    p = repo.check()
                finally:
                    repo.close()
                out = p.stdout + p.stderr
                self.assertEqual(p.returncode, code, out)
                self.assertRegex(out, summary)
                self.assertIn(needle, out)
                if code == 1:
                    for field in CONTRACT_FIELDS:
                        self.assertIn(field, p.stdout, f"message missing `{field}`")
                    self.assertRegex(p.stdout, r"cause    · (code|environment|tooling)")

    def test_unsupported_kind_is_never_green(self):
        repo = Repo({".env.example": "REAL_VAR=1\n"}, {})
        try:
            ids = os.path.join(repo.path, "ids.jsonl")
            with open(ids, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"kind": "env", "name": "REAL_VAR"}) + "\n")
                fh.write(json.dumps({"kind": "kafka-topic", "name": "clinic.events"}) + "\n")
            p = run("resolve-identifiers.py", "--repo", repo.path, "--ids", ids)
        finally:
            repo.close()
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("found 2 · resolved 1 · unresolved 0 · unsupported kinds 1 (kafka-topic)", p.stdout)
        self.assertIn("cause    · tooling", p.stdout)

    def test_empty_range_is_a_failure(self):
        repo = Repo({}, {})
        try:
            p = repo.check()
        finally:
            repo.close()
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertIn("the range has no changes", p.stderr)
        for field in CONTRACT_FIELDS:
            self.assertIn(field, p.stderr)

    def test_bad_range_is_usage(self):
        p = run("resolve-identifiers.py", "--repo", ".", "--range", "HEAD")
        self.assertEqual(p.returncode, 2)

    def test_cross_repo_declaration(self):
        decl = Repo({"proto/clinic.proto": PROTO}, {})
        use = Repo({}, {"svc/h.go": "package svc\nvar a = &clinicv1.Invoice{Total: 3}\n"})
        try:
            alone = use.check()
            joined = use.check("--decl-repo", decl.path)
        finally:
            decl.close()
            use.close()
        self.assertEqual(alone.returncode, 1, alone.stdout)
        self.assertEqual(joined.returncode, 0, joined.stdout)

    def test_decl_rev_checks_a_closed_unit_against_later_declarations(self):
        repo = Repo({".env.example": "A=1\n"}, {"x.ts": "process.env.LATER;\n"})
        try:
            unit_head = git(repo.path, "rev-parse", "HEAD")
            write(repo.path, {".env.example": "A=1\nLATER=1\n"})
            git(repo.path, "add", "-A")
            git(repo.path, "commit", "-q", "-m", "declare later")
            rng = f"{repo.base}..{unit_head}"
            at_unit = run("resolve-identifiers.py", "--repo", repo.path, "--range", rng)
            today = run("resolve-identifiers.py", "--repo", repo.path, "--range", rng, "--decl-rev", "HEAD")
        finally:
            repo.close()
        self.assertEqual(at_unit.returncode, 1, at_unit.stdout)
        self.assertEqual(today.returncode, 0, today.stdout)

    def test_json_output(self):
        repo = Repo({".env.example": "A=1\n"}, {"x.ts": "process.env.A; process.env.B;\n"})
        try:
            p = repo.check("--json")
        finally:
            repo.close()
        doc = json.loads(p.stdout)
        self.assertEqual((doc["found"], doc["resolved"]), (2, 1))
        self.assertEqual([u["name"] for u in doc["unresolved"]], ["B"])


class TestSsmAsEnv(unittest.TestCase):
    """An SSM loader injects `/…/<shared|service>/<NAME>` as env NAME — namespace = service."""

    def setUp(self):
        self.infra = Repo({"ssm/parameters/gateway-go.json":
                           '[\n  "_comment: /wellmed/{env}/shared/COMMENT_ONLY is not a declaration",\n'
                           '  {"path": "/wellmed/{env}/gateway-go/ROUTER_URL"},\n'
                           '  {"path": "/wellmed/{env}/shared/DB_HOST"},\n'
                           '  {"path": "/wellmed/{env}/cashier/CASHIER_ONLY"}\n]\n'}, {})
        self.addCleanup(self.infra.close)

    def service(self, root, folder, name, layout):
        """A repo whose change reads env `name`, checked out as `layout`: `main` (the folder is
        the repo's name), `worktree` (a linked worktree `<folder>.worktrees/fix-149-final`), or
        `clone` (a folder named `fix-149-final` whose origin is the repo)."""
        svc = os.path.join(root, folder)
        os.makedirs(svc)
        git(svc, "init", "-q", "-b", "main")
        write(svc, {"README.md": "x\n"})
        git(svc, "add", "-A")
        git(svc, "commit", "-q", "-m", "base")
        base = git(svc, "rev-parse", "HEAD")
        if layout == "clone":
            git(svc, "remote", "add", "origin", f"git@github.com:Kalpa-Health/{folder}.git")
            os.rename(svc, os.path.join(root, "fix-149-final"))
            svc = os.path.join(root, "fix-149-final")
        elif layout == "worktree":
            wt = os.path.join(root, f"{folder}.worktrees", "fix-149-final")
            git(svc, "worktree", "add", "-q", "-b", "fix/149", wt)
            svc = wt
        write(svc, {"cfg.go": f"package c\nvar v = os.Getenv(\"{name}\")\n"})
        git(svc, "add", "-A")
        git(svc, "commit", "-q", "-m", "head")
        return svc, base

    def test_ssm_declared_env(self):
        # (env name, repo folder, layout, expected exit)
        cases = [("ROUTER_URL", "wellmed-gateway-go", "main", 0),
                 ("DB_HOST", "wellmed-gateway-go", "main", 0),
                 ("CASHIER_ONLY", "wellmed-gateway-go", "main", 1),
                 ("COMMENT_ONLY", "wellmed-gateway-go", "main", 1),
                 # 149.2: inside a worktree the folder is `fix-149-final` — the repo is named
                 # by its git common dir, or its origin remote
                 ("ROUTER_URL", "wellmed-gateway-go", "worktree", 0),
                 ("ROUTER_URL", "wellmed-gateway-go", "clone", 0),
                 ("CASHIER_ONLY", "wellmed-gateway-go", "worktree", 1),
                 ("ROUTER_URL", "wellmed-cashier", "worktree", 1),
                 ("CASHIER_ONLY", "wellmed-cashier", "clone", 0)]
        for name, folder, layout, code in cases:
            with self.subTest(env=name, repo=folder, layout=layout), tempfile.TemporaryDirectory() as tmp:
                svc, base = self.service(tmp, folder, name, layout)
                p = run("resolve-identifiers.py", "--repo", svc, "--range", f"{base}..HEAD",
                        "--decl-repo", self.infra.path)
                self.assertEqual(p.returncode, code, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
