"""door.py classify (10.1 task 1.2).

Approach: build throwaway git repos in a temp dir, commit a base, apply a change,
commit a head, and run `door.py classify` as a subprocess (the way skills call it).
Table-driven where the shape repeats. Every fail-closed branch has its own case.
"""
import json
import os
import subprocess
import tempfile
import unittest

from _helpers import run


def git(repo, *args):
    subprocess.run(["git", "-C", repo, "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   check=True, capture_output=True)


def write(repo, path, text="x\n"):
    full = os.path.join(repo, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(text)


class DoorBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = self._tmp.name
        git(self.repo, "init", "-q", "-b", "main")
        write(self.repo, "README.md", "hi\n")
        write(self.repo, "src/app.py", "print(1)\n")
        write(self.repo, "db/migrations/001_init.sql", "select 1;\n")
        write(self.repo, "docs/notes.md", "n\n")
        self.commit("base")

    def commit(self, msg):
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", msg)

    def classify(self, rng="HEAD~1..HEAD", *extra):
        p = run("door.py", "classify", "--repo", self.repo, f"--range={rng}", *extra)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)


class TestFloor(DoorBase):
    def test_plain_change_is_two_way(self):
        write(self.repo, "src/app.py", "print(2)\n")
        self.commit("edit")
        r = self.classify()
        self.assertEqual((r["door"], r["paths"]), ("two-way", []))

    def test_floor_paths_force_one_way(self):
        cases = [
            ("db/migrations/002_add.sql", "migrations/"),
            ("api/service.proto", "*.proto"),
            ("api/openapi.yaml", "openapi*.yaml"),
            ("docs/adrs/0007-x.md", "adrs/"),
            ("infra/main.tf", "*.tf"),
            ("deploy/.env.production", ".env.*"),
            ("config/prod/app.yml", "prod/"),
        ]
        for path, pattern in cases:
            with self.subTest(path):
                write(self.repo, path)
                self.commit(f"add {path}")
                r = self.classify()
                self.assertEqual(r["door"], "one-way", r)
                self.assertEqual(r["paths"][0]["path"], path)
                self.assertEqual(r["paths"][0]["pattern"], pattern)

    def test_case_insensitive_match(self):
        write(self.repo, "DB/Migrations/002.sql")
        self.commit("case")
        self.assertEqual(self.classify()["door"], "one-way")


class TestPromoteOnly(DoorBase):
    def test_two_way_claim_on_floor_path_stays_one_way(self):
        write(self.repo, "db/migrations/002.sql")
        self.commit("m")
        r = self.classify("HEAD~1..HEAD", "--claim", "two-way")
        self.assertEqual(r["door"], "one-way")
        self.assertIn("promote-only", r["reason"])

    def test_one_way_claim_promotes_a_plain_change(self):
        write(self.repo, "src/app.py", "print(3)\n")
        self.commit("e")
        self.assertEqual(self.classify("HEAD~1..HEAD", "--claim", "one-way")["door"], "one-way")

    def test_invalid_claim_fails_closed(self):
        write(self.repo, "src/app.py", "print(4)\n")
        self.commit("e")
        self.assertEqual(self.classify("HEAD~1..HEAD", "--claim", "whatever")["door"], "one-way")


class TestRenameDelete(DoorBase):
    def test_delete_of_floor_path(self):
        git(self.repo, "rm", "-q", "db/migrations/001_init.sql")
        self.commit("rm")
        r = self.classify()
        self.assertEqual((r["door"], r["paths"][0]["change"]), ("one-way", "D"))

    def test_rename_out_of_floor_path(self):
        os.makedirs(os.path.join(self.repo, "archive"))
        git(self.repo, "mv", "db/migrations/001_init.sql", "archive/001_init.sql")
        self.commit("mv out")
        r = self.classify()
        self.assertEqual(r["door"], "one-way")
        self.assertEqual(r["paths"][0]["path"], "db/migrations/001_init.sql")

    def test_rename_into_floor_path(self):
        git(self.repo, "mv", "docs/notes.md", "db/migrations/notes.md")
        self.commit("mv in")
        self.assertEqual(self.classify()["door"], "one-way")


class TestRepoFile(DoorBase):
    def test_repo_file_at_base_adds_floor(self):
        write(self.repo, ".one-way-doors", "# repo floor\nsrc/billing/\n")
        self.commit("floor")
        write(self.repo, "src/billing/charge.py")
        self.commit("billing")
        r = self.classify()
        self.assertEqual((r["door"], r["paths"][0]["pattern"]), ("one-way", "src/billing/"))

    def test_edit_of_repo_file_is_one_way(self):
        write(self.repo, ".one-way-doors", "src/billing/\n")
        self.commit("floor")
        write(self.repo, ".one-way-doors", "src/billing/\n# tweak\n")
        self.commit("edit floor")
        self.assertEqual(self.classify()["door"], "one-way")

    def test_creating_repo_file_is_one_way(self):
        write(self.repo, ".one-way-doors", "src/x/\n")
        self.commit("create floor")
        self.assertEqual(self.classify()["door"], "one-way")

    def test_change_cannot_authorize_its_own_removal(self):
        write(self.repo, ".one-way-doors", "src/billing/\n")
        self.commit("floor")
        # one commit removes the floor line AND touches the path it protected
        write(self.repo, ".one-way-doors", "# nothing\n")
        write(self.repo, "src/billing/charge.py")
        self.commit("remove floor and edit")
        r = self.classify()
        self.assertEqual(r["door"], "one-way")
        pats = {h["pattern"] for h in r["paths"]}
        self.assertIn("src/billing/", pats)  # judged against the BASE file

    def test_negation_line_is_ignored(self):
        write(self.repo, ".one-way-doors", "!db/migrations/\n")
        self.commit("neg")
        write(self.repo, "db/migrations/003.sql")
        self.commit("m")
        self.assertEqual(self.classify()["door"], "one-way")


class TestFailClosed(DoorBase):
    def test_range_and_git_failures_are_one_way(self):
        cases = ["HEAD", "a...b", "..HEAD", "HEAD..", "-x..HEAD", "nope..HEAD", "HEAD~1 ..HEAD",
                 "HEAD~1..HEAD..HEAD"]
        for rng in cases:
            with self.subTest(rng):
                r = self.classify(rng)
                self.assertEqual(r["door"], "one-way", r)
                self.assertIn("fail-closed", r["reason"])

    def test_not_a_repo_is_one_way(self):
        with tempfile.TemporaryDirectory() as d:
            p = run("door.py", "classify", "--repo", d, "--range", "HEAD~1..HEAD")
            self.assertEqual(json.loads(p.stdout)["door"], "one-way")

    def test_missing_defaults_file_is_one_way(self):
        write(self.repo, "src/app.py", "print(5)\n")
        self.commit("e")
        r = self.classify("HEAD~1..HEAD", "--defaults", os.path.join(self.repo, "nope"))
        self.assertEqual(r["door"], "one-way")
        self.assertIn("defaults file", r["reason"])


if __name__ == "__main__":
    unittest.main()
