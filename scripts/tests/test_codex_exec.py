"""codex-exec.py — every codex failure mode ends as a `none …` judge line, never `codex …`.

Approach: a fake codex (bash) stands in via VERIFY_CODEX_BIN; FAKE_MODE picks its
behaviour — a healthy answer, or one of the failure modes the CEO review named (F2):
not installed, not authed, model unusable, timeout, empty, refusal, malformed. The real
codex is never called from the suite: it costs money and its availability is exactly
what these tests must not depend on.
"""

import json
import os
import stat
import tempfile
import unittest
from unittest import mock

from _helpers import load, run


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()

FAKE = r"""#!/usr/bin/env bash
if [ "$1" = "--version" ]; then echo "codex-cli 9.9.9"; exit 0; fi
out=""; prev=""
for a in "$@"; do [ "$prev" = "-o" ] && out="$a"; prev="$a"; done
[ -n "$FAKE_ARGS" ] && printf '%s\n' "$@" > "$FAKE_ARGS"
banner() { printf 'OpenAI Codex v9\n--------\nmodel: %s\nprovider: openai\n--------\n' "${FAKE_BANNER:-gpt-fake-1}" >&2; }
case "$FAKE_MODE" in
  ok)        banner; [ -n "$out" ] && printf '{"verdicts": []}' > "$out"; echo pong ;;
  nomodel)   [ -n "$out" ] && printf '{"verdicts": []}' > "$out"; echo pong ;;
  auth)      echo "Error: Not logged in. Run codex login." >&2; exit 1 ;;
  model)     banner; echo "Error: model gpt-6-astra is not supported by this version" >&2; exit 1 ;;
  crash)     echo "segfault somewhere" >&2; exit 7 ;;
  hang)      exec sleep 30 ;;
  empty)     banner; [ -n "$out" ] && : > "$out"; echo "" ;;
  refusal)   banner; [ -n "$out" ] && echo "I can't help with that request." > "$out"; echo "nope" ;;
  malformed) banner; [ -n "$out" ] && echo "verdict: looks fine to me" > "$out"; echo "hm" ;;
  credits)   banner; echo "ERROR: Your workspace is out of credits. Add credits to continue."; exit 1 ;;
  array)     banner; [ -n "$out" ] && echo "[1, 2]" > "$out"; echo "hm" ;;
esac
"""


class TestCodexExec(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fake = os.path.join(self.tmp.name, "codex")
        with open(self.fake, "w") as fh:
            fh.write(FAKE)
        os.chmod(self.fake, os.stat(self.fake).st_mode | stat.S_IEXEC)
        self.prompt = os.path.join(self.tmp.name, "p.md")
        with open(self.prompt, "w") as fh:
            fh.write("judge this")
        self.out = os.path.join(self.tmp.name, "out.json")

    def tearDown(self):
        self.tmp.cleanup()

    def env(self, mode, binary=None):
        return dict(os.environ, VERIFY_CODEX_BIN=binary or self.fake, FAKE_MODE=mode,
                    VERIFY_CODEX_MODEL="gpt-fake-1", CODEX_HOME=self.tmp.name)

    def judge_line(self, p):
        return p.stdout.strip().splitlines()[-1]

    def test_probe(self):
        cases = [
            ("ok", 0, "codex gpt-fake-1"),
            ("auth", 1, "none codex not authed"),
            ("model", 1, "none codex model unusable"),
            ("crash", 1, "none codex exited 7"),
            ("credits", 1, "none codex out of credits"),
            ("nomodel", 1, "none codex did not report its model"),
            ("malformed", 1, "none codex probe answered unexpectedly"),
        ]
        for mode, code, line in cases:
            with self.subTest(mode=mode):
                p = run("codex-exec.py", "probe", env=self.env(mode))
                self.assertEqual(p.returncode, code, p.stderr)
                self.assertEqual(self.judge_line(p), line)

    def test_model_family_resolves_from_codex_cache(self):
        # Like Claude's `opus`: a family tracks the current slug; never codex's own default.
        models = [{"slug": "gpt-9-astra", "priority": 2, "visibility": "list"},
                  {"slug": "gpt-9-sol", "priority": 3, "visibility": "list"},
                  {"slug": "gpt-8-sol", "priority": 5, "visibility": "list"},
                  {"slug": "gpt-x-sol", "priority": 1, "visibility": "hide"},
                  {"slug": "gpt-8-luna", "priority": 4, "visibility": "list", "upgrade": {"model": "gpt-9-luna"}}]
        with open(os.path.join(self.tmp.name, "models_cache.json"), "w") as fh:
            json.dump({"models": models}, fh)
        cx = load("codex-exec.py")
        cases = [(None, "gpt-9-sol"), ("sol", "gpt-9-sol"), ("luna", "gpt-9-luna"),
                 ("gpt-9-astra", "gpt-9-astra"), ("gpt-7-sol", "gpt-7-sol"), ("terra", None),
                 ("gpt-8-luna", "gpt-8-luna")]  # an exact slug is never upgraded (5.2-r2-03)
        for want, slug in cases:
            with self.subTest(want=want):
                env = {"CODEX_HOME": self.tmp.name, **({"VERIFY_CODEX_MODEL": want} if want else {})}
                with mock.patch.dict(os.environ, env, clear=False):
                    if not want:
                        os.environ.pop("VERIFY_CODEX_MODEL", None)
                    got, why = cx.resolve_model()
                self.assertEqual(got, slug, why)
                if slug is None:
                    self.assertEqual(why[0], "codex model family terra unresolved")

    def test_probe_requests_and_checks_the_model(self):
        args = os.path.join(self.tmp.name, "args")
        p = run("codex-exec.py", "probe", env=dict(self.env("ok"), FAKE_ARGS=args))
        self.assertEqual(self.judge_line(p), "codex gpt-fake-1")
        self.assertIn("-m\ngpt-fake-1\n", read(args))
        drift = run("codex-exec.py", "probe", env=dict(self.env("ok"), FAKE_BANNER="gpt-6-astra"))
        self.assertEqual((drift.returncode, self.judge_line(drift)), (1, "none codex ran a different model"))
        nocache = run("codex-exec.py", "probe", env=dict(self.env("ok"), VERIFY_CODEX_MODEL="sol"))
        self.assertEqual(self.judge_line(nocache), "none codex model family sol unresolved")

    def test_probe_not_installed(self):
        p = run("codex-exec.py", "probe", env=self.env("ok", binary=os.path.join(self.tmp.name, "nope")))
        self.assertEqual((p.returncode, self.judge_line(p)), (1, "none codex not installed"))
        self.assertIn("npm i -g @openai/codex", p.stderr)
        self.assertIn("cause    · environment", p.stderr)

    def test_probe_timeout(self):
        p = run("codex-exec.py", "probe", "--timeout", "1", env=self.env("hang"))
        self.assertEqual((p.returncode, self.judge_line(p)), (1, "none codex probe timed out"))

    def test_exec(self):
        cases = [
            ("ok", 0, "codex gpt-fake-1"),
            ("auth", 1, "none codex not authed"),
            ("model", 1, "none codex model unusable"),
            ("empty", 1, "none codex returned an empty answer"),
            ("refusal", 1, "none codex refused"),
            ("malformed", 1, "none codex answer is malformed"),
            ("array", 1, "none codex answer is malformed"),
        ]
        for mode, code, line in cases:
            with self.subTest(mode=mode):
                p = run("codex-exec.py", "exec", "--prompt", self.prompt, "--out", self.out, env=self.env(mode))
                self.assertEqual(p.returncode, code, p.stderr)
                self.assertEqual(self.judge_line(p), line)
                if code:
                    self.assertFalse(self.judge_line(p).startswith("codex "))

    def test_exec_timeout(self):
        p = run("codex-exec.py", "exec", "--prompt", self.prompt, "--out", self.out, "--timeout", "1",
                env=self.env("hang"))
        self.assertEqual((p.returncode, self.judge_line(p)), (1, "none codex timed out"))

    def test_stale_answer_is_never_reused(self):
        with open(self.out, "w") as fh:
            fh.write('{"verdicts": ["from an earlier run"]}')
        p = run("codex-exec.py", "exec", "--prompt", self.prompt, "--out", self.out, env=self.env("crash"))
        self.assertEqual(p.returncode, 1)
        self.assertFalse(os.path.exists(self.out))


class TestEffortScaling(unittest.TestCase):
    """Effort scales with what codex reads (Alex, 2026-09-29)."""

    def test_tiers(self):
        vl = load("verify_lib.py")
        cases = [([], "medium"), ([(1, 12)], "low"), ([(4, 80)], "low"), ([(5, 20)], "medium"),
                 ([(10, 310)], "medium"), ([(3, 300), (3, 300)], "high"), ([(56, 3344)], "high")]
        for stats, want in cases:
            with self.subTest(stats=stats):
                self.assertEqual(vl.effort_for(stats)[0], want)


if __name__ == "__main__":
    unittest.main()
