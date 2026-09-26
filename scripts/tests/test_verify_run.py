"""verify-run.py — the runner records evidence, never a claim; the judge may only downgrade.

Approach: each test builds a fake ~/Projects (a target repo plus a private and a public
destination repo), writes a finish-condition table, and runs the script as /verify will.
Read-back failure is simulated in-process by swapping verify_lib's tail reader, the one
place a test reaches inside the script.
"""

import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from _helpers import load, run

HEADER = ("| check_id | deliverable | owner | class | check | repo | dir | env | timeout | rung "
          "| unreachable_ok | evidence |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n")
FIELDS = ("expected ·", "found    ·", "where    ·", "cause    ·", "next     ·", "docs     ·")


def git(path, *args):
    return subprocess.run(["git", "-C", path, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          check=True, capture_output=True, text=True).stdout.strip()


def mkrepo(path, origin=None):
    os.makedirs(os.path.join(path, "sub"), exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    with open(os.path.join(path, "sub", "f.txt"), "w") as fh:
        fh.write("x\n")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "init")
    if origin:
        git(path, "remote", "add", "origin", origin)
    return git(path, "rev-parse", "HEAD")


def row(cid, check, cls="B", owner="5.1", repo="svc", d="sub", env="-", timeout="-", rung="4", ok="no"):
    check = check.replace("|", "\\|")
    return f"| {cid} | deliverable {cid} | {owner} | {cls} | `{check}` | {repo} | {d} | {env} | {timeout} | {rung} | {ok} | ev |\n"


class Env:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.projects = os.path.join(self.tmp.name, "projects")
        self.svc_sha = mkrepo(os.path.join(self.projects, "svc"))
        mkrepo(os.path.join(self.projects, "priv"), "git@github.com:acme/priv.git")
        mkrepo(os.path.join(self.projects, "pub"), "git@github.com:ak-devmode/ai-skills.git")
        self.priv_log = os.path.join(self.projects, "priv", "artifacts", "verify-5.1.jsonl")
        self.pub_log = os.path.join(self.projects, "pub", "artifacts", "verify-5.1.jsonl")

    def table(self, rows, rev=1):
        path = os.path.join(self.tmp.name, "finish-conditions.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"# t\n\n**Schema version:** verify/1\n**Revision:** {rev}\n\n{HEADER}{''.join(rows)}\n")
        return path

    def run(self, rows, log=None, owner="5.1"):
        args = ["run", "--table", self.table(rows), "--log", log or self.priv_log, "--projects", self.projects]
        if owner:
            args += ["--owner", owner]
        return run("verify-run.py", *args)

    def records(self, log=None):
        with open(log or self.priv_log, encoding="utf-8") as fh:
            return [json.loads(x) for x in fh if x.strip()]

    def close(self):
        self.tmp.cleanup()


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.env = Env()

    def tearDown(self):
        self.env.close()

    def pending(self, cid):
        return [r for r in self.env.records() if r["check_id"] == cid and r["run_state"] == "pending"][-1]


class TestRun(RunnerTest):
    def test_exit_code_mapping(self):
        cases = [("ok", "true", "pass", 4), ("bad", "exit 1", "fail", 4), ("usage", "exit 2", "inconclusive", 4),
                 ("away", "exit 3", "verified-unreachable", 4), ("odd", "exit 9", "fail", 4),
                 ("nope", "./does-not-exist.sh", "inconclusive", 4)]
        p = self.env.run([row(c, cmd) for c, cmd, _, _ in cases])
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        for cid, _, result, rung in cases:
            with self.subTest(check=cid):
                rec = self.pending(cid)
                self.assertEqual(rec["result"], result)
                self.assertEqual(rec["rung_reached"], rung)
        self.assertIn("not executable", self.pending("nope")["reason"])

    def test_all_pass_exits_zero(self):
        p = self.env.run([row("ok", "true"), row("jr", "judge", rung="2")])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(self.pending("jr")["result"], "inconclusive")
        self.assertEqual(self.pending("jr")["rung_reached"], 0)

    def test_timeout_is_inconclusive(self):
        p = self.env.run([row("slow", "sleep 5", timeout="1")])
        self.assertEqual(p.returncode, 1)
        rec = self.pending("slow")
        self.assertEqual((rec["result"], rec["reason"]), ("inconclusive", "timed out after 1s"))
        self.assertIn("cause    · environment", p.stdout)

    def test_resolved_context_recorded(self):
        # Run from a different cwd: the row's repo/dir/env must be what executes and what is recorded.
        p = self.env.run([row("ctx", "pwd; echo FOO=$FOO; git rev-parse HEAD", env="FOO=bar")])
        self.assertEqual(p.returncode, 0, p.stderr)
        rec = self.pending("ctx")
        want_cwd = os.path.realpath(os.path.join(self.env.projects, "svc", "sub"))
        self.assertEqual(os.path.realpath(rec["cwd"]), want_cwd)
        self.assertEqual(os.path.realpath(rec["output_tail"].splitlines()[0]), want_cwd)
        self.assertIn("FOO=bar", rec["output_tail"])
        self.assertIn(self.env.svc_sha, rec["output_tail"])
        self.assertEqual(rec["sha"], self.env.svc_sha)
        self.assertEqual(rec["env"], {"FOO": "bar"})
        self.assertEqual(len(rec["output_sha256"]), 64)

    def test_missing_repo_is_inconclusive(self):
        p = self.env.run([row("ghost", "true", repo="no-such-repo")])
        self.assertEqual(p.returncode, 1)
        self.assertIn("not executable", self.pending("ghost")["reason"])

    def test_escaped_pipe_runs_as_pipe(self):
        p = self.env.run([row("pipe", "echo hi | grep -q hi")])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_failure_message_carries_contract_fields(self):
        p = self.env.run([row("bad", "exit 1")])
        for f in FIELDS:
            self.assertIn(f, p.stdout)
        self.assertIn("cause    · code", p.stdout)

    def test_owner_selection(self):
        rows = [row("a", "true", owner="5.1"), row("b", "true", owner="5.1/1.3"), row("c", "true", owner="5.2")]
        self.env.run(rows, owner="5.1")
        self.assertEqual({r["check_id"] for r in self.env.records()}, {"a", "b"})

    def test_class_a_deployed_version(self):
        p = self.env.run([row("live", "echo '{\"deployed_version\": \"v1.2.3\"}'", cls="A", rung="5")])
        self.assertEqual(p.returncode, 0, p.stderr)
        rec = self.pending("live")
        self.assertEqual((rec["deployed_version"], rec["rung_reached"]), ("v1.2.3", 5))


class TestPlacement(RunnerTest):
    def test_class_a_refused_in_public_repo(self):
        p = self.env.run([row("live", "true", cls="A")], log=self.env.pub_log)
        self.assertEqual(p.returncode, 1)
        self.assertIn("class-A evidence for `live` refused", p.stderr)
        for f in FIELDS:
            self.assertIn(f, p.stderr)
        self.assertFalse(os.path.exists(self.env.pub_log), "nothing may be written on refusal")

    def test_class_a_refused_outside_git(self):
        log = os.path.join(self.env.tmp.name, "loose", "verify.jsonl")
        os.makedirs(os.path.dirname(log))
        p = self.env.run([row("live", "true", cls="A")], log=log)
        self.assertEqual(p.returncode, 1)
        self.assertIn("outside any git repo", p.stderr)

    def test_public_repo_holds_class_b_on_itself_only(self):
        other = self.env.run([row("b1", "true", repo="svc")], log=self.env.pub_log)
        self.assertEqual(other.returncode, 1)
        self.assertIn("another repo refused", other.stderr)
        own = self.env.run([row("b2", "true", repo="pub")], log=self.env.pub_log)
        self.assertEqual(own.returncode, 0, own.stderr)


class TestReadBack(RunnerTest):
    def test_write_that_did_not_land_exits_3(self):
        mod = load("verify-run.py")
        lib = mod.vl
        saved = lib._tail
        lib._tail = lambda path, n: []
        out, err = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(out), redirect_stderr(err):
                code = mod.main(["run", "--table", self.env.table([row("ok", "true")]), "--log",
                                 self.env.priv_log, "--projects", self.env.projects, "--owner", "5.1"])
        finally:
            lib._tail = saved
        self.assertEqual(code, 3)
        self.assertIn("write did not land", err.getvalue())


class TestJudgeAndFinalize(RunnerTest):
    def start(self, rows):
        p = self.env.run(rows)
        return p.stdout.split("run_id: ")[1].split()[0]

    def judge(self, run_id, items, line="codex gpt-test"):
        path = os.path.join(self.env.tmp.name, "judge.json")
        with open(path, "w") as fh:
            json.dump(items, fh)
        return run("verify-run.py", "judged", "--log", self.env.priv_log, "--run-id", run_id,
                   "--judge", line, "--input", path)

    def finalize(self, run_id, *extra):
        return run("verify-run.py", "finalize", "--log", self.env.priv_log, "--run-id", run_id, *extra)

    def final(self):
        return [r for r in self.env.records() if r["run_state"] == "final"][-1]

    def v(self, cid, verdict, rung=4):
        return {"check_id": cid, "verdict": verdict, "rung_reached": rung, "reason": f"judge says {verdict}"}

    def test_authority_rule(self):
        rid = self.start([row("up", "true"), row("down", "exit 1"), row("jr", "judge", rung="2"),
                          row("keep", "true")])
        j = self.judge(rid, [self.v("up", "fail"), self.v("down", "pass"), self.v("jr", "pass", 2),
                             self.v("keep", "pass", 3)])
        self.assertEqual(j.returncode, 0, j.stderr)
        f = self.finalize(rid)
        self.assertEqual(f.returncode, 1)
        res = self.final()["results"]
        self.assertEqual(res["up"]["result"], "fail")          # judge downgrades a runner pass
        self.assertEqual(res["down"]["result"], "fail")        # judge cannot upgrade a runner fail
        self.assertEqual(res["jr"]["result"], "pass")          # judge row takes the judge verdict
        self.assertEqual((res["keep"]["result"], res["keep"]["rung_reached"]), ("pass", 3))  # lower rung
        self.assertEqual(self.final()["judge"], "codex gpt-test")
        self.assertEqual(len([r for r in self.env.records() if r["run_state"] == "final"]), 1)

    def test_no_judge(self):
        rid = self.start([row("ok", "true"), row("jr", "judge", rung="2")])
        refused = self.finalize(rid)
        self.assertEqual(refused.returncode, 3)
        self.assertIn("no judge verdicts", refused.stderr)
        f = self.finalize(rid, "--judge", "none codex not installed")
        res = self.final()["results"]
        self.assertEqual(res["ok"]["result"], "pass")          # runner result stands
        self.assertEqual(res["jr"]["result"], "inconclusive")  # judge row cannot pass without a judge
        self.assertEqual(f.returncode, 1)

    def test_malformed_judge_output_writes_nothing(self):
        rid = self.start([row("ok", "true")])
        before = len(self.env.records())
        for items in ([{"check_id": "ok", "verdict": "great", "rung_reached": 4, "reason": "x"}],
                      [{"check_id": "zzz", "verdict": "pass", "rung_reached": 4, "reason": "x"}],
                      [{"check_id": "ok", "verdict": "pass", "rung_reached": 4, "reason": ""}], []):
            with self.subTest(items=items):
                j = self.judge(rid, items)
                self.assertEqual(j.returncode, 3, j.stdout)
                self.assertIn("none malformed judge output", j.stderr)
        self.assertEqual(len(self.env.records()), before)

    def test_double_finalize_refused(self):
        rid = self.start([row("ok", "true")])
        self.assertEqual(self.finalize(rid, "--judge", "none skipped").returncode, 0)
        again = self.finalize(rid, "--judge", "none skipped")
        self.assertEqual(again.returncode, 3)
        self.assertIn("already final", again.stderr)

    def test_malformed_judge_line_is_usage(self):
        rid = self.start([row("ok", "true")])
        self.assertEqual(self.finalize(rid, "--judge", "codex").returncode, 2)


class TestTable(RunnerTest):
    def test_malformed_tables(self):
        cases = [
            ("unescaped pipe", row("ok", "true").replace("`true`", "echo a | cat"), "unescaped"),
            ("empty cell", row("ok", "true").replace("| ev |", "|  |"), "`evidence`"),
            ("bad class", row("ok", "true", cls="C"), "`class`"),
            ("bad unreachable_ok", row("ok", "true", ok="yes"), "`unreachable_ok`"),
            ("duplicate id", row("ok", "true") + row("ok", "false"), "unique check_id"),
        ]
        for name, rows, needle in cases:
            with self.subTest(case=name):
                p = self.env.run([rows])
                self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
                self.assertIn(needle, p.stderr)
                self.assertIn("cause    · code", p.stderr)


if __name__ == "__main__":
    unittest.main()
