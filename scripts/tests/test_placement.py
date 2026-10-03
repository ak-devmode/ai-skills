"""Tests for scripts/placement.py — recommend, check-base, fetch-back.

Approach: recommend runs as a subprocess against a fixture merged.json and accounts map,
with stub `hostname`, `herdr`, `ssh` and per-account `claude-*` / `codex-*` launchers on
PATH. The ssh stub runs the remote command locally with STUB_ON=<host>, so a login can be
dead on one machine only. check-base and fetch-back run against real throwaway git repos:
a bare origin, a "local" clone and a "box" clone, with the box reached by path instead of
ssh (--remote-url) — the fetch and its read-back are the real code paths.
"""

import json
import os
import subprocess
import tempfile
import textwrap
import time
import unittest

from _helpers import run

NOW = int(time.time())

STUBS = {
    "hostname": 'echo "${STUB_HOST:-mba}"',
    "herdr": 'exit "${STUB_HERDR_RC:-0}"',
    "ssh": textwrap.dedent('''\
        [ -n "${STUB_SSH_FAIL:-}" ] && exit 255
        for a in "$@"; do host=$last; last=$a; done      # ssh [opts] HOST CMD
        STUB_ON=$host exec sh -c "$last"'''),
}
for key in ("alex", "int"):
    STUBS[f"claude-{key}"] = (
        f'case " ${{STUB_DEAD:-}} " in *" ${{STUB_ON:-mba}}:{key}:opus "*) '
        f'echo \'{{"loggedIn": false}}\';; *) echo \'{{"loggedIn": true}}\';; esac')
    STUBS[f"codex-{key}"] = (                  # :codex0 = dead login that still exits 0
        f'case " ${{STUB_DEAD:-}} " in *" ${{STUB_ON:-mba}}:{key}:codex "*) '
        f'echo "Not logged in" >&2; exit 1;; *" ${{STUB_ON:-mba}}:{key}:codex0 "*) '
        f'echo "Not logged in" >&2;; *) echo "Logged in using ChatGPT" >&2;; esac')

MAP = ("host\tkey\tdisplay\tclaude_dir\tcodex_home\tkeychain\tdefault\n"
       "mba\talex\talex@work\t~/.claude\t~/.codex\tsvc\tyes\n"
       "mba\tint\tintegrations\t~/.claude-int\t~/.codex-int\tsvc2\tno\n"
       "box\tint\tintegrations\t~/.claude\t~/.codex\t-\tyes\n"
       "box\talex\talex@work\t~/.claude-alex\t~/.codex-alex\t-\tno\n")


def win(used, age=60, inferred=False):
    return {"used_pct": used, "resets_at": NOW + 3600, "observed_at": NOW - age,
            "inferred": inferred, "source": "local"}


def merged(int5=17, int7=5, alex5=30, alex7=61, oai_int=(29, 5), oai_alex=(0, 100), **over):
    acc = {
        "int": {"display": "integrations",
                "claude": {"windows": {"5h": win(int5), "7d": win(int7)}},
                "oai": {"windows": {"5h": win(oai_int[0]), "7d": win(oai_int[1])}}},
        "alex": {"display": "alex@work",
                 "claude": {"windows": {"5h": win(alex5), "7d": win(alex7)}},
                 "oai": {"windows": {"5h": win(oai_alex[0]), "7d": win(oai_alex[1])}}},
    }
    for path, value in over.items():           # e.g. int_claude_5h=win(...)
        k, prov, w = path.split("_")
        acc[k][prov]["windows"][w] = value
    return {"schema": 1, "generated_at": NOW, "host": "mba", "accounts": acc}


class Recommend(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        self.bin = os.path.join(d, "bin")
        os.mkdir(self.bin)
        for name, body in STUBS.items():
            path = os.path.join(self.bin, name)
            with open(path, "w") as fh:
                fh.write("#!/bin/sh\n" + body + "\n")
            os.chmod(path, 0o755)
        self.map = os.path.join(d, "accounts.tsv")
        with open(self.map, "w") as fh:
            fh.write(MAP)
        self.merged = os.path.join(d, "merged.json")

    def tearDown(self):
        self.tmp.cleanup()

    def rec(self, data, *args, **env):
        if data is not None:
            with open(self.merged, "w") as fh:
                fh.write(data if isinstance(data, str) else json.dumps(data))
        e = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"], **env)
        p = run("placement.py", "recommend", "--json", "--merged", self.merged,
                "--accounts", self.map, *args, env=e)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return json.loads(p.stdout)

    def pick(self, out, seat="opus"):
        c = out["recommended"].get(seat)
        return (c["machine"], c["account"]) if c else None

    def cand(self, out, machine, account, seat="opus"):
        return next(c for c in out["candidates"]
                    if (c["machine"], c["account"], c["seat"]) == (machine, account, seat))

    def test_cases(self):
        # (name, merged data, env, seat, expected pick, extra check)
        cases = [
            ("most headroom wins; tie goes to the account's home machine", merged(), {}, "opus",
             ("box", "int"), None),
            ("box offline: box never recommended", merged(), {"STUB_HERDR_RC": "1"}, "opus",
             ("mba", "int"), lambda o: self.assertFalse(self.cand(o, "box", "int")["reachable"])),
            ("box int login dead: falls to the MBA's int", merged(), {"STUB_DEAD": "box:int:opus"},
             "opus", ("mba", "int"), lambda o: self.assertFalse(self.cand(o, "box", "int")["login"])),
            ("codex seat reads the OpenAI windows", merged(), {}, "codex", ("box", "int"),
             lambda o: self.assertEqual(self.cand(o, "box", "int", "codex")["headroom"], 71)),
            ("exhausted seat is never recommended", merged(oai_int=(100, 5)), {}, "codex", None,
             lambda o: self.assertEqual(self.cand(o, "mba", "alex", "codex")["headroom"], 0)),
            ("inferred window is unknown headroom and ranks below a known one",
             merged(int_claude_5h=win(0, inferred=True)), {}, "opus", ("mba", "alex"),
             lambda o: self.assertIn("inferred", " ".join(self.cand(o, "box", "int")["notes"]))),
            ("stale window is unknown headroom", merged(int_claude_7d=win(5, age=3600)), {}, "opus",
             ("mba", "alex"),
             lambda o: self.assertIsNone(self.cand(o, "box", "int")["headroom"])),
            ("over quota is exhausted, not negative headroom", merged(oai_int=(120, 5)), {},
             "codex", None,
             lambda o: self.assertEqual(self.cand(o, "box", "int", "codex")["headroom"], 0)),
            ("a dead codex login that exits 0 is still dead", merged(oai_alex=(50, 60)),
             {"STUB_DEAD": "box:int:codex0 mba:int:codex0"}, "codex", ("mba", "alex"), None),
            ("ssh failing while herdr answers: box login unverified, not recommended", merged(),
             {"STUB_SSH_FAIL": "1"}, "opus", ("mba", "int"),
             lambda o: self.assertFalse(self.cand(o, "box", "int")["login"])),
            ("only unknown headroom left: still recommended, flagged",
             merged(int_claude_5h=win(0, inferred=True), alex_claude_7d=win(1, age=99999)),
             {"STUB_DEAD": ""}, "opus", ("box", "int"), None),
        ]
        for name, data, env, seat, want, check in cases:
            with self.subTest(case=name):
                out = self.rec(data, "--seat", seat, **env)
                self.assertEqual(self.pick(out, seat), want)
                if check:
                    check(out)

    def test_missing_merged_still_lists_machines(self):
        out = self.rec(None)
        self.assertTrue(out["candidates"])
        self.assertTrue(all(c["headroom"] is None for c in out["candidates"]))
        self.assertIn("no usable merged.json", out["candidates"][0]["notes"][0])

    def test_bad_map_is_could_not_check(self):
        e = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"])
        p = run("placement.py", "recommend", "--accounts", self.map + ".missing", env=e)
        self.assertEqual(p.returncode, 3, p.stderr)
        with open(self.map, "a") as fh:
            fh.write("-oProxyCommand=x\tint\tintegrations\t~/.claude\t~/.codex\t-\tno\n")
        p = run("placement.py", "recommend", "--accounts", self.map, env=e)
        self.assertEqual(p.returncode, 3, p.stdout)
        self.assertIn("unsafe host", p.stderr)

    def test_mixed_case_host_is_local(self):
        with open(self.map, "w") as fh:
            fh.write(MAP.replace("mba\t", "MBA\t"))
        out = self.rec(merged(), "--seat", "opus", STUB_HERDR_RC="1", STUB_SSH_FAIL="1")
        self.assertTrue(self.cand(out, "mba", "int")["eligible"])

    def test_unknown_schema_is_not_trusted(self):
        out = self.rec({"schema": 2, "accounts": merged()["accounts"]})
        self.assertTrue(all(c["headroom"] is None for c in out["candidates"]))
        self.assertIn("schema", out["candidates"][0]["notes"][0])

    def test_text_output_names_the_pick(self):
        with open(self.merged, "w") as fh:
            json.dump(merged(), fh)
        e = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"])
        p = run("placement.py", "recommend", "--seat", "opus", "--merged", self.merged,
                "--accounts", self.map, env=e)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("recommended opus: box as integrations", p.stdout)


def git(cwd, *args):
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if p.returncode:
        raise AssertionError(f"git {' '.join(args)}: {p.stderr}")
    return p.stdout.strip()


class Git(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        self.origin = os.path.join(d, "origin.git")
        git(d, "init", "-q", "--bare", "-b", "main", self.origin)
        for name in ("local", "box"):
            git(d, "clone", "-q", self.origin, name)
            git(os.path.join(d, name), "config", "user.email", "t@t")
            git(os.path.join(d, name), "config", "user.name", "t")
        self.local, self.box = os.path.join(d, "local"), os.path.join(d, "box")
        git(self.local, "commit", "-q", "--allow-empty", "-m", "first")
        git(self.local, "push", "-q", "origin", "main")
        git(self.box, "pull", "-q", "origin", "main")

    def tearDown(self):
        self.tmp.cleanup()

    def test_check_base(self):
        p = run("placement.py", "check-base", "--repo", self.local, "--base", "HEAD")
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("is on origin", p.stdout)
        git(self.local, "commit", "-q", "--allow-empty", "-m", "unpushed")
        p = run("placement.py", "check-base", "--repo", self.local)
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("refuse", p.stdout)
        self.assertIn("not on origin", p.stdout)
        p = run("placement.py", "check-base", "--repo", self.local, "--base", "nope")
        self.assertEqual(p.returncode, 3, p.stdout)

    def test_check_base_deleted_origin_branch_does_not_vouch(self):
        git(self.local, "checkout", "-q", "-b", "tmp")
        git(self.local, "commit", "-q", "--allow-empty", "-m", "on tmp only")
        git(self.local, "push", "-q", "origin", "tmp")
        git(self.box, "push", "-q", "origin", "--delete", "tmp")    # gone from origin
        p = run("placement.py", "check-base", "--repo", self.local)
        self.assertEqual(p.returncode, 1, p.stdout)

    def test_fetch_back(self):
        git(self.box, "checkout", "-q", "-b", "concurrency/3-lane")
        git(self.box, "commit", "-q", "--allow-empty", "-m", "lane work")
        tip = git(self.box, "rev-parse", "HEAD")
        p = run("placement.py", "fetch-back", "--repo", self.local, "--machine", "box",
                "--branch", "concurrency/3-lane", "--remote-url", self.box)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertEqual(git(self.local, "rev-parse", "concurrency/3-lane"), tip)
        p = run("placement.py", "fetch-back", "--repo", self.local, "--machine", "box",
                "--branch", "concurrency/missing", "--remote-url", self.box)
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("failed", p.stdout)

    def test_fetch_back_never_overwrites_local_work(self):
        git(self.box, "checkout", "-q", "-b", "lane")
        git(self.box, "commit", "-q", "--allow-empty", "-m", "box side")
        git(self.local, "checkout", "-q", "-b", "lane")
        git(self.local, "commit", "-q", "--allow-empty", "-m", "local side")
        mine = git(self.local, "rev-parse", "lane")
        for case in ("checked out", "diverged"):
            with self.subTest(case=case):
                if case == "diverged":
                    git(self.local, "checkout", "-q", "main")
                p = run("placement.py", "fetch-back", "--repo", self.local, "--machine", "box",
                        "--branch", "lane", "--remote-url", self.box)
                self.assertEqual(p.returncode, 1, p.stdout)
                self.assertEqual(git(self.local, "rev-parse", "lane"), mine)


if __name__ == "__main__":
    unittest.main()
