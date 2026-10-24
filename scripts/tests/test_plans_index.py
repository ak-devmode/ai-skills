"""plans-index.py records mode (scope 9) — add / status / move / render / migrate / check.

Approach: each test builds a throwaway plans dir — a README.md declaring the render mode
and a few scope folders — and drives the script as a subprocess, the way skills call it.
Assertions read the files back from disk; an exit code alone is never proof a write landed
(CLAUDE.md §3.6.2). Git is only set up where the behaviour depends on it (migrate --branch,
the kalpa-docs archive guard), with an isolated config so the host's never leaks in.
"""

import os
import subprocess
import tempfile
import unittest

from _helpers import load, run

BEGIN, END = "<!-- plans-index:begin -->", "<!-- plans-index:end -->"
HEADER = "| # | Status | Folder | Description | Created by |\n|---|---|---|---|---|\n"


class Base(unittest.TestCase):
    MODE = "bot"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.realpath(self.tmp.name)
        self.env = {**os.environ, "HOME": self.root, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull, "VERIFY_PROJECTS": self.root,
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        self.plans = os.path.join(self.root, "repo", "plans")
        os.makedirs(self.plans)
        if self.MODE:
            self.write("README.md", f"# Plans\n\n**Index render:** {self.MODE}\n")
        for f in ("3-alpha", "4-beta", "10-gamma"):
            os.makedirs(os.path.join(self.plans, f))

    def tearDown(self):
        self.tmp.cleanup()

    def pi(self, *args):
        return run("plans-index.py", args[0], self.plans, *args[1:], env=self.env)

    def ok(self, *args):
        p = self.pi(*args)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p

    def write(self, rel, text):
        path = os.path.join(self.plans, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def read(self, rel):
        with open(os.path.join(self.plans, rel), encoding="utf-8") as fh:
            return fh.read()

    def exists(self, rel):
        return os.path.exists(os.path.join(self.plans, rel))

    def snapshot(self):
        out = {}
        for d, _, files in os.walk(self.plans):
            for f in files:
                path = os.path.join(d, f)
                with open(path, encoding="utf-8") as fh:
                    out[os.path.relpath(path, self.plans)] = fh.read()
        return out

    def add(self, num, folder, status="📝 Scoped", desc="d"):
        return self.ok("add", "--num", str(num), "--status", status, "--folder", folder,
                       "--desc", desc, "--creator", "t")

    def git(self, cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()


class Writers(Base):
    def test_add_writes_the_scope_record_and_never_the_index(self):
        self.add(3, "3-alpha/")
        text = self.read("3-alpha/progress.md")
        self.assertIn(BEGIN, text)
        self.assertIn("| 3 | 📝 Scoped | 3-alpha/ | d | t |", text)
        self.assertFalse(self.exists("PLANS-INDEX.md"))

    def test_two_scopes_touch_disjoint_files(self):
        self.add(3, "3-alpha/")
        before = self.snapshot()
        self.add(4, "4-beta/")
        after = self.snapshot()
        changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
        self.assertEqual(changed, {"4-beta/progress.md"})

    def test_existing_progress_keeps_its_prose(self):
        self.write("3-alpha/progress.md", "# Progress\n\nlog line\n\n## 1. Plans\n\nbody\n")
        self.add(3, "3-alpha/")
        text = self.read("3-alpha/progress.md")
        self.assertTrue(text.startswith("# Progress\n\nlog line\n"))
        self.assertLess(text.index(BEGIN), text.index("## 1. Plans"))
        self.assertIn("body", text)

    def test_folder_not_on_disk_goes_loose(self):
        self.add(7, "_(not created)_")
        self.assertIn("| 7 |", self.read("index-loose.md"))
        self.assertIn("<!-- plans-index:begin active -->", self.read("index-loose.md"))

    def test_duplicate_number_refused(self):
        self.add(3, "3-alpha/")
        p = self.pi("add", "--num", "3", "--status", "x", "--folder", "4-beta/", "--desc", "d")
        self.assertEqual(p.returncode, 2)
        self.assertFalse(self.exists("4-beta/progress.md"))

    def test_status_rewrites_the_record(self):
        self.add(3, "3-alpha/")
        self.add("3.1", "3-alpha/3.1-x-PLAN.md", status="🔲 Draft")
        self.ok("status", "--num", "3.1", "--status", "🔄 In progress")
        text = self.read("3-alpha/progress.md")
        self.assertIn("| 3.1 | 🔄 In progress |", text)
        self.assertIn("| 3 | 📝 Scoped |", text)
        self.assertFalse(self.exists("PLANS-INDEX.md"))

    def test_move_moves_the_folder_and_repoints_rows(self):
        self.add(3, "3-alpha/")
        self.add("3.1", "3-alpha/3.1-x-PLAN.md")
        self.write("3-alpha/3.1-x-PLAN.md", "plan\n")
        self.ok("move", "--num", "3", "--to", "archived", "--status", "✅ Done")
        self.assertFalse(self.exists("3-alpha"))
        text = self.read("archive/3-alpha/progress.md")
        self.assertIn("| 3 | ✅ Done | archive/3-alpha/ |", text)
        self.assertIn("| 3.1 | 📝 Scoped | archive/3-alpha/3.1-x-PLAN.md |", text)
        self.ok("render")
        self.assertIn("| 3 | ✅ Done |", self.read("archive/INDEX.md"))
        self.assertNotIn("| 3 |", self.read("PLANS-INDEX.md"))

    def test_move_after_a_hand_mv_repoints_the_rows(self):
        self.add(3, "3-alpha/")
        self.add("3.1", "3-alpha/3.1-x-PLAN.md")
        os.makedirs(os.path.join(self.plans, "archive"))
        os.rename(os.path.join(self.plans, "3-alpha"), os.path.join(self.plans, "archive", "3-alpha"))
        self.ok("move", "--num", "3", "--to", "archived", "--folder", "archive/3-alpha/", "--status", "✅ Done")
        text = self.read("archive/3-alpha/progress.md")
        self.assertIn("| 3 | ✅ Done | archive/3-alpha/ |", text)
        self.assertIn("| 3.1 | 📝 Scoped | archive/3-alpha/3.1-x-PLAN.md |", text)

    def test_loose_row_moves_into_its_new_folder(self):
        self.add(12, "12-plan-PLAN.md")  # a raw plan file at the plans root: loose
        self.assertIn("| 12 |", self.read("index-loose.md"))
        os.makedirs(os.path.join(self.plans, "12-plan"))
        self.ok("move", "--num", "12", "--to", "active", "--folder", "12-plan/")
        self.assertIn("| 12 | 📝 Scoped | 12-plan/ |", self.read("12-plan/progress.md"))
        self.assertNotIn("| 12 |", self.read("index-loose.md"))

    def test_move_refuses_an_occupied_destination(self):
        self.add(3, "3-alpha/")
        os.makedirs(os.path.join(self.plans, "archive", "3-alpha"))
        self.assertEqual(self.pi("move", "--num", "3", "--to", "archived").returncode, 2)
        self.assertTrue(self.exists("3-alpha/progress.md"))

    def test_uppercase_progress_file_is_the_record(self):
        # kalpa-docs 45: a second progress.md beside PROGRESS.md would split the record from
        # the log on a case-sensitive runner; on macOS it would be the same file anyway
        self.write("4-beta/PROGRESS.md", "# Progress\n\nlog\n")
        self.add(4, "4-beta/")
        self.assertEqual(sorted(os.listdir(os.path.join(self.plans, "4-beta"))), ["PROGRESS.md"])
        self.assertIn(BEGIN, self.read("4-beta/PROGRESS.md"))
        self.ok("render")
        self.assertIn("| 4 |", self.read("PLANS-INDEX.md"))

    def test_a_failed_write_leaves_the_progress_file_whole(self):
        # 9.1-r1-02: an in-place 'w' write truncates progress.md before it writes
        self.add(3, "3-alpha/")
        path = os.path.join(self.plans, "3-alpha", "progress.md")
        os.chmod(path, 0o640)
        before = self.read("3-alpha/progress.md")
        pi = load("plans-index.py")
        real = pi.os.replace

        def boom(src, dst):
            raise OSError("disk full")
        pi.os.replace = boom
        try:
            with self.assertRaises(OSError):
                pi.write_block(path, [["3", "🔄 Active", "3-alpha/", "d", "t"]])
        finally:
            pi.os.replace = real
        self.assertEqual(before, self.read("3-alpha/progress.md"))
        self.assertEqual(os.listdir(os.path.dirname(path)), ["progress.md"])  # no temp left
        pi.write_block(path, [["3", "🔄 Active", "3-alpha/", "d", "t"]])
        self.assertIn("| 3 | 🔄 Active |", self.read("3-alpha/progress.md"))
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o640)

    def test_unknown_render_mode_refused(self):
        self.write("README.md", "**Index render:** botty\n")
        p = self.pi("add", "--num", "3", "--status", "x", "--folder", "3-alpha/", "--desc", "d")
        self.assertEqual(p.returncode, 2)
        self.assertIn("expected bot | local", p.stderr)


class Readers(Base):
    """Freshness-sensitive readers see the records before the bot renders (eng D23)."""

    def test_verify_archive_reads_a_fresh_render(self):
        self.add(3, "3-alpha/")
        self.add("3.1", "3-alpha/3.1-x-PLAN.md")
        self.ok("move", "--num", "3", "--to", "archived", "--status", "✅ Done")
        self.assertFalse(self.exists("PLANS-INDEX.md"))  # bot mode: nothing rendered yet
        p = run("closeout/scripts/verify-archive.sh", self.plans, "3", env=self.env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        p = run("closeout/scripts/verify-archive.sh", self.plans, "4", env=self.env)
        self.assertEqual(p.returncode, 1)
        self.assertIn("NO INDEX ROW", p.stdout)

    def test_verify_archive_names_a_clobbered_record(self):
        # 9.1-r1-13: a record block overwritten after the render read as a plain NO INDEX ROW
        self.add(3, "3-alpha/")
        self.ok("move", "--num", "3", "--to", "archived", "--status", "\u2705 Done")
        self.ok("render")
        self.write("archive/3-alpha/progress.md", "# Progress\n")  # an agent's Write
        p = run("closeout/scripts/verify-archive.sh", self.plans, "3", env=self.env)
        self.assertEqual(p.returncode, 1)
        self.assertIn("NO INDEX ROW", p.stdout)
        self.assertIn("LOST row 3", p.stderr)

    def test_scan_archive_drift_counts_record_rows_once(self):
        self.write("3-alpha/progress.md",
                   "# Progress\n\n## 1. Plans\n\n| # | Plan | Status |\n|---|---|---|\n"
                   "| 3.1 | a | Done |\n| 3.2 | b | Done |\n")
        self.add(3, "3-alpha/")
        self.add("3.1", "3-alpha/a.md", status="✅ Done")
        self.add("3.2", "3-alpha/b.md", status="✅ Done", desc="was pending review")
        p = run("closeout/scripts/scan-archive-drift.py", self.plans, env=self.env)
        self.assertIn("2/2 plans Done", p.stdout)
        self.ok("status", "--num", "3.2", "--status", "🔄 In progress")
        p = run("closeout/scripts/scan-archive-drift.py", self.plans, env=self.env)
        self.assertNotIn("scope 3", p.stdout)  # the record is current; the hand table is stale


class LocalMode(Base):
    MODE = "local"

    def test_every_write_re_renders(self):
        self.add(3, "3-alpha/")
        self.assertIn("| 3 | 📝 Scoped |", self.read("PLANS-INDEX.md"))
        self.ok("status", "--num", "3", "--status", "🔄 Active")
        self.assertIn("| 3 | 🔄 Active |", self.read("PLANS-INDEX.md"))
        self.ok("check")


class Render(Base):
    def test_render_is_deterministic_and_numeric(self):
        self.add(10, "10-gamma/")
        self.add(4, "4-beta/")
        self.add(3, "3-alpha/")
        self.ok("render")
        first = self.snapshot()
        p = self.ok("render")
        self.assertIn("unchanged", p.stdout)
        self.assertEqual(first, self.snapshot())
        text = self.read("PLANS-INDEX.md")
        self.assertLess(text.index("| 3 |"), text.index("| 4 |"))
        self.assertLess(text.index("| 4 |"), text.index("| 10 |"))
        self.assertIn("GENERATED", text)

    def test_stdout_writes_nothing(self):
        self.add(3, "3-alpha/")
        p = self.ok("render", "--stdout")
        self.assertIn("| 3 |", p.stdout)
        self.assertFalse(self.exists("PLANS-INDEX.md"))

    def test_check_passes_on_a_fresh_render(self):
        self.add(3, "3-alpha/")
        self.ok("render")
        self.ok("check")

    def test_check_fails_on_a_hand_edit(self):
        self.add(3, "3-alpha/")
        self.ok("render")
        self.write("PLANS-INDEX.md", self.read("PLANS-INDEX.md") + "| 99 | x | y | z | t |\n")
        p = self.pi("check")
        self.assertEqual(p.returncode, 1)
        self.assertIn("differs from a fresh render", p.stdout)

    def test_clobbered_block_fails_check_and_refuses_render(self):
        self.add(3, "3-alpha/")
        self.add(4, "4-beta/")
        self.ok("render")
        self.write("4-beta/progress.md", "# Progress\n\nan agent's Write replaced it\n")
        p = self.pi("check")
        self.assertEqual(p.returncode, 1)
        self.assertIn("row 4 rendered before but has no record", p.stdout)
        before = self.read("PLANS-INDEX.md")
        self.assertEqual(self.pi("render").returncode, 1)
        self.assertEqual(before, self.read("PLANS-INDEX.md"))
        self.ok("render", "--allow-loss")
        self.assertNotIn("| 4 |", self.read("PLANS-INDEX.md"))

    def test_a_number_held_twice_fails_check_render_and_status(self):
        # 9.1-r1-06: check passed (committed == fresh) and status edited only the first row
        self.add(3, "3-alpha/")
        self.ok("render")
        self.write("index-loose.md", "<!-- plans-index:begin active -->\n" + HEADER
                   + "| 3 | 📝 PRD | _(not created)_ | dup | t |\n<!-- plans-index:end active -->\n")
        before = self.snapshot()
        p = self.pi("render", "--allow-loss")
        self.assertEqual(p.returncode, 1)
        self.assertIn("DUPLICATE # 3 has 2 rows", p.stderr)
        self.assertEqual(before, self.snapshot())
        p = self.pi("check")
        self.assertEqual(p.returncode, 1)
        self.assertIn("# 3 has 2 rows", p.stdout)
        p = self.pi("status", "--num", "3", "--status", "🔄 Active")
        self.assertEqual(p.returncode, 2)
        self.assertEqual(before, self.snapshot())

    def test_half_a_block_is_refused(self):
        self.add(3, "3-alpha/")
        self.write("3-alpha/progress.md", self.read("3-alpha/progress.md").replace(END, ""))
        self.assertEqual(self.pi("check").returncode, 1)
        self.assertEqual(self.pi("render").returncode, 2)


LEGACY = f"""# Plans Index

## Active Plans

{HEADER}| 3 | 🔄 Active | `3-alpha/` | a | t |
| 3.1 | 🔲 Draft | `3-alpha/3.1-x-PLAN.md` | a1 | t |
| 4 | ✅ Done | `4-beta/` | b — folder already archived on disk | t |
| 5 | 📝 PRD | _(not created)_ | loose | t |

## Completed / Archived

{HEADER}| 2 | ✅ Done | `archive/2-old/` | old | t |
"""


class Migrate(Base):
    def setUp(self):
        super().setUp()
        os.makedirs(os.path.join(self.plans, "archive", "2-old"))
        os.rename(os.path.join(self.plans, "4-beta"), os.path.join(self.plans, "archive", "4-beta"))
        self.write("PLANS-INDEX.md", LEGACY.replace("`4-beta/`", "`archive/4-beta/`"))

    def test_migrate_then_render_reproduces_every_row(self):
        p = self.ok("migrate")
        self.assertIn("LOOSE  5", p.stdout)
        self.assertIn("TABLE  4: active -> archived", p.stdout)
        self.ok("render")
        rendered = self.read("PLANS-INDEX.md") + self.read("archive/INDEX.md")
        for num in ("3", "3.1", "4", "5", "2"):
            self.assertIn(f"| {num} |", rendered)
        self.assertIn("| 4 |", self.read("archive/INDEX.md"))
        self.ok("check")

    def test_gate_mode_line_moves_to_readme_and_stays_blocking(self):
        # 9.1-r1-01: a blocking graph (IRIS) must still block after the render drops the line
        self.write("PLANS-INDEX.md", self.read("PLANS-INDEX.md")
                   .replace("## Active Plans", "**Gate mode:** blocking\n\n## Active Plans"))
        readme = self.read("README.md")
        self.ok("migrate", "--dry-run")
        self.assertEqual(readme, self.read("README.md"))
        p = self.ok("migrate")
        self.assertIn("MOVED  **Gate mode:** blocking -> README.md", p.stdout)
        moved = self.read("README.md")
        self.assertIn("**Gate mode:** blocking", moved)
        self.write("README.md", readme)  # as if the line had never moved
        p = self.pi("render", "--allow-loss")
        self.assertEqual(p.returncode, 1)  # --allow-loss never covers the gate line
        self.assertIn("Gate mode", p.stderr)
        self.assertIn("Gate mode", self.pi("check").stdout)
        self.write("README.md", moved)
        self.ok("render")
        self.assertNotIn("Gate mode", self.read("PLANS-INDEX.md"))
        self.assertEqual(load("verify_lib.py").gate_mode(os.path.join(self.plans, "3-alpha")), "blocking")
        self.write("README.md", moved.replace("blocking", "advisory"))
        self.write("PLANS-INDEX.md", "**Gate mode:** blocking\n" + self.read("PLANS-INDEX.md"))
        self.assertEqual(self.pi("migrate").returncode, 2)  # two answers: a human picks

    def test_other_tables_and_prose_refuse_render(self):
        self.write("PLANS-INDEX.md", self.read("PLANS-INDEX.md")
                   + "\n## Pending PRDs\n\n| PRD | Owner |\n|---|---|\n| x | t |\n\nA note.\n")
        p = self.ok("migrate")
        self.assertIn("DROP   PLANS-INDEX.md § Pending PRDs: 4 line(s)", p.stdout)
        before = self.read("PLANS-INDEX.md")
        p = self.pi("render")
        self.assertEqual(p.returncode, 1)
        self.assertIn("STRAY PLANS-INDEX.md § Pending PRDs", p.stderr)
        self.assertEqual(before, self.read("PLANS-INDEX.md"))
        self.assertEqual(self.pi("check").returncode, 1)
        self.ok("render", "--allow-loss")
        self.ok("check")

    def test_migrate_twice_changes_nothing(self):
        self.ok("migrate")
        once = self.snapshot()
        p = self.ok("migrate")
        self.assertIn("0 record file(s) written", p.stdout)
        self.assertEqual(once, self.snapshot())

    def test_render_before_migrate_refuses(self):
        p = self.pi("render")
        self.assertEqual(p.returncode, 2)
        self.assertIn("not migrated", p.stderr)

    def test_migrate_branch_imports_the_branch_edits(self):
        repo = os.path.dirname(self.plans)
        self.git(repo, "init", "-q", "-b", "main")
        self.git(repo, "add", ".")
        self.git(repo, "commit", "-q", "-m", "base")
        base = self.git(repo, "rev-parse", "HEAD")
        self.git(repo, "checkout", "-q", "-b", "feature/x")
        self.write("PLANS-INDEX.md", self.read("PLANS-INDEX.md")
                   .replace("| 3.1 | 🔲 Draft |", "| 3.1 | ✅ Done |")
                   .replace("| 5 | 📝 PRD |", "| 3.2 | 🔲 Draft | `3-alpha/` | a2 | t |\n| 5 | 📝 PRD |"))
        self.git(repo, "commit", "-q", "-am", "branch edits")
        self.git(repo, "checkout", "-q", "main")
        self.ok("migrate")
        p = self.ok("migrate", "--branch", "feature/x", "--base", base)
        self.assertIn("2 row(s) changed", p.stdout)
        text = self.read("3-alpha/progress.md")
        self.assertIn("| 3.1 | ✅ Done |", text)
        self.assertIn("| 3.2 | 🔲 Draft |", text)

    def test_migrate_branch_reports_deletes_and_refuses_a_wrong_path(self):
        # 9.1-r1-10: a deleted row vanished silently; a wrong plans path read as 0 changed
        repo = os.path.dirname(self.plans)
        self.git(repo, "init", "-q", "-b", "main")
        self.git(repo, "add", ".")
        self.git(repo, "commit", "-q", "-m", "base")
        base = self.git(repo, "rev-parse", "HEAD")
        self.git(repo, "checkout", "-q", "-b", "feature/x")
        self.write("PLANS-INDEX.md", "\n".join(l for l in self.read("PLANS-INDEX.md").split("\n")
                                             if not l.startswith("| 5 |")))
        self.git(repo, "commit", "-q", "-am", "drop 5")
        self.git(repo, "checkout", "-q", "main")
        self.ok("migrate")
        p = self.ok("migrate", "--branch", "feature/x", "--base", base)
        self.assertIn("DELETED row 5 on feature/x", p.stdout)
        other = os.path.join(repo, "elsewhere")
        os.makedirs(other)
        p = run("plans-index.py", "migrate", other, "--branch", "feature/x", "--base", base, env=self.env)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("has no elsewhere/PLANS-INDEX.md", p.stdout + p.stderr)


class Legacy(Base):
    MODE = None

    def test_without_the_readme_line_the_index_is_edited_in_place(self):
        self.write("PLANS-INDEX.md", LEGACY)
        self.add(10, "`10-gamma/`")
        self.assertIn("| 10 | 📝 Scoped |", self.read("PLANS-INDEX.md"))
        self.assertFalse(self.exists("10-gamma/progress.md"))
        self.ok("status", "--num", "3", "--status", "🔄 Still active")
        self.assertIn("| 3 | 🔄 Still active |", self.read("PLANS-INDEX.md"))

    def test_legacy_repoint_in_place(self):
        self.write("PLANS-INDEX.md", LEGACY)
        self.ok("move", "--num", "3", "--to", "active", "--folder", "`10-gamma/`")
        lines = self.read("PLANS-INDEX.md").split("\n")
        self.assertEqual(lines[6], "| 3 | 🔄 Active | `10-gamma/` | a | t |")  # same line, new folder


class ArchiveGuard(Base):
    """kalpa-docs only: an open kalpa-orchestra backlog row at scoped(N) blocks the archive."""

    def setUp(self):
        super().setUp()
        self.plans = os.path.join(self.root, "wellmed", "kalpa-docs", "plans")
        os.makedirs(os.path.join(self.plans, "3-alpha"))
        self.write("README.md", "**Index render:** bot\n")
        self.git(os.path.dirname(self.plans), "init", "-q", "-b", "main")
        backlog = os.path.join(self.root, "wellmed", "kalpa-orchestra", "projects", "p1", "BACKLOG.md")
        os.makedirs(os.path.dirname(backlog))
        with open(backlog, "w", encoding="utf-8") as fh:
            fh.write("| Item | State |\n|---|---|\n| widget | scoped(3) |\n")
        self.add(3, "3-alpha/")

    def test_open_backlog_row_blocks_archive(self):
        p = self.pi("move", "--num", "3", "--to", "archived")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("open backlog row", p.stdout + p.stderr)
        self.assertTrue(self.exists("3-alpha/progress.md"))

    def test_force_overrides_out_loud(self):
        p = self.ok("move", "--num", "3", "--to", "archived", "--force", "row is stale")
        self.assertIn("overridden", p.stderr)
        self.assertTrue(self.exists("archive/3-alpha/progress.md"))


if __name__ == "__main__":
    unittest.main()
