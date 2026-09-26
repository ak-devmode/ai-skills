"""codex-exec.py — every codex failure mode ends as a `none …` judge line, never `codex …`.

Approach: a fake codex (bash) stands in via VERIFY_CODEX_BIN; FAKE_MODE picks its
behaviour — a healthy answer, or one of the failure modes the CEO review named (F2):
not installed, not authed, model unusable, timeout, empty, refusal, malformed. The real
codex is never called from the suite: it costs money and its availability is exactly
what these tests must not depend on.
"""

import os
import stat
import tempfile
import unittest

from _helpers import run

FAKE = r"""#!/usr/bin/env bash
if [ "$1" = "--version" ]; then echo "codex-cli 9.9.9"; exit 0; fi
out=""; prev=""
for a in "$@"; do [ "$prev" = "-o" ] && out="$a"; prev="$a"; done
banner() { printf 'OpenAI Codex v9\n--------\nmodel: gpt-fake-1\nprovider: openai\n--------\n' >&2; }
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
        return dict(os.environ, VERIFY_CODEX_BIN=binary or self.fake, FAKE_MODE=mode)

    def judge_line(self, p):
        return p.stdout.strip().splitlines()[-1]

    def test_probe(self):
        cases = [
            ("ok", 0, "codex gpt-fake-1"),
            ("auth", 1, "none codex not authed"),
            ("model", 1, "none codex model unusable"),
            ("crash", 1, "none codex exited 7"),
            ("nomodel", 1, "none codex did not report its model"),
            ("malformed", 1, "none codex probe answered unexpectedly"),
        ]
        for mode, code, line in cases:
            with self.subTest(mode=mode):
                p = run("codex-exec.py", "probe", env=self.env(mode))
                self.assertEqual(p.returncode, code, p.stderr)
                self.assertEqual(self.judge_line(p), line)

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


if __name__ == "__main__":
    unittest.main()
