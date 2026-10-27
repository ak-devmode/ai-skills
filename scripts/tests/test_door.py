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
            # WellMed keeps migrations in a singular folder (backbone, catalog, consultation, finance,
            # hq, pharmacy, infrastructure): backbone #658, a tenant migration, passed the floor without it.
            ("internal/db/migration/000042_tenant.up.sql", "migration/"),
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

    def test_ci_definitions_are_not_floor(self):
        # CI edits are reversible: driver-merge.py refuses to auto-merge them (two-way packet), but
        # the floor would park every lane that touches a workflow (10.3-r2-04)
        write(self.repo, ".github/workflows/ci.yml")
        self.commit("add ci")
        self.assertEqual(self.classify()["door"], "two-way")

    def test_case_insensitive_match(self):
        # ADRS/ has no lowercase twin in the repo, so core.ignorecase cannot fold the path
        # before door.py sees it: the match has to come from IGNORECASE (10.1-r1-16)
        write(self.repo, "ADRS/0007-x.md")
        self.commit("case")
        r = self.classify()
        self.assertEqual(r["door"], "one-way")
        self.assertEqual(r["paths"][0]["path"], "ADRS/0007-x.md")


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

    def test_info_claim_without_floor_hit_is_kept(self):
        write(self.repo, "src/app.py", "print(5)\n")
        self.commit("e")
        self.assertEqual(self.classify("HEAD~1..HEAD", "--claim", "info")["door"], "info")

    def test_info_claim_on_floor_path_still_one_way(self):
        write(self.repo, "db/migrations/009.sql")
        self.commit("m")
        self.assertEqual(self.classify("HEAD~1..HEAD", "--claim", "info")["door"], "one-way")

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
        # src/billing/ is floored ONLY by the repo file, so a regression that honoured the
        # `!` line would turn this two-way (10.1-r1-08)
        write(self.repo, ".one-way-doors", "src/billing/\n!src/billing/\n")
        self.commit("floor")
        write(self.repo, "src/billing/charge.py")
        self.commit("billing")
        r = self.classify()
        self.assertEqual((r["door"], r["paths"][0]["pattern"]), ("one-way", "src/billing/"))


class TestGlobClass(DoorBase):
    """glob compiler siblings: newline names (04), negated class (13), bad class (fail closed)."""

    def floor(self, line):
        write(self.repo, ".one-way-doors", line + "\n")
        self.commit("floor")

    def test_newline_in_path_still_matches(self):
        self.floor("")  # defaults floor covers migrations/
        write(self.repo, "db/migrations/a\nb.sql")
        self.commit("nl")
        r = self.classify("HEAD~1..HEAD")
        self.assertEqual(r["door"], "one-way", r)

    def test_newline_in_name_under_repo_dir_rule(self):
        self.floor("src/billing/")
        write(self.repo, "src/billing/a\nb.py")
        self.commit("nl")
        self.assertEqual(self.classify()["door"], "one-way")

    def test_negated_bracket_class(self):
        self.floor("src/[!x]ule.py")
        write(self.repo, "src/mule.py")
        self.commit("m")
        self.assertEqual(self.classify()["door"], "one-way")  # 'm' is not 'x'
        write(self.repo, "src/xule.py")
        self.commit("x")
        self.assertEqual(self.classify()["door"], "two-way")  # 'x' is excluded

    def test_uncompilable_floor_line_fails_closed(self):
        self.floor("src/[z-a]x")
        write(self.repo, "docs/notes.md", "changed\n")
        self.commit("e")
        r = self.classify()
        self.assertEqual(r["door"], "one-way")
        self.assertIn("fail-closed", r["reason"])


class TestSubmodule(DoorBase):
    def test_gitlink_bump_counts_even_when_ignored(self):
        git(self.repo, "config", "diff.ignoreSubmodules", "all")
        for sha, msg in (("1" * 40, "gl1"), ("2" * 40, "gl2")):
            git(self.repo, "update-index", "--add", "--cacheinfo", f"160000,{sha},db/migrations/sub")
            git(self.repo, "commit", "-q", "-m", msg)
        r = self.classify()
        self.assertEqual(r["door"], "one-way", r)
        self.assertEqual(r["paths"][0]["path"], "db/migrations/sub")


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
