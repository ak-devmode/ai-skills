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
    ("ancestor declaration counts",
     {".env.example": "ROOT_VAR=1\n"},
     {"services/b/main.go": "package b\nvar v = os.Getenv(\"ROOT_VAR\")\n"},
     0, r"resolved 1", "ROOT_VAR"),
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
    ("route under an unseen group prefix resolves as suffix",
     {"server/routes.go": "package server\nfunc reg(g *gin.RouterGroup) { g.GET(\"/invoices\", h) }\n"},
     {"web/api.ts": "axios.get('/api/v1/invoices');\n"},
     0, r"resolved 1", "suffix — group prefix assumed"),
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

    def test_ssm_declared_env(self):
        infra = Repo({"ssm/parameters/gateway-go.json":
                      '[\n  "_comment: /wellmed/{env}/shared/COMMENT_ONLY is not a declaration",\n'
                      '  {"path": "/wellmed/{env}/gateway-go/ROUTER_URL"},\n'
                      '  {"path": "/wellmed/{env}/shared/DB_HOST"},\n'
                      '  {"path": "/wellmed/{env}/cashier/CASHIER_ONLY"}\n]\n'}, {})
        cases = [("ROUTER_URL", 0), ("DB_HOST", 0), ("CASHIER_ONLY", 1), ("COMMENT_ONLY", 1)]
        try:
            for name, code in cases:
                with self.subTest(env=name):
                    tmp = tempfile.TemporaryDirectory()
                    svc = os.path.join(tmp.name, "wellmed-gateway-go")
                    os.makedirs(svc)
                    git(svc, "init", "-q", "-b", "main")
                    write(svc, {"README.md": "x\n"})
                    git(svc, "add", "-A")
                    git(svc, "commit", "-q", "-m", "base")
                    base = git(svc, "rev-parse", "HEAD")
                    write(svc, {"cfg.go": f"package c\nvar v = os.Getenv(\"{name}\")\n"})
                    git(svc, "add", "-A")
                    git(svc, "commit", "-q", "-m", "head")
                    p = run("resolve-identifiers.py", "--repo", svc, "--range", f"{base}..HEAD",
                            "--decl-repo", infra.path)
                    tmp.cleanup()
                    self.assertEqual(p.returncode, code, p.stdout + p.stderr)
        finally:
            infra.close()


if __name__ == "__main__":
    unittest.main()
