#!/usr/bin/env python3
"""codex-exec.py — run codex headless as the opposing voice, and say honestly when it
could not run. Shared by /verify (judge) and /review (gate).

Approach: `probe` answers "can codex judge right now?" fresh on every call — never a
cached result — with `codex --version` and a one-line `codex exec` ping. `exec` runs a
prompt in a read-only sandbox with an output schema and a timeout, and checks the answer
is JSON. Both print exactly one judge line on their last stdout line (verify-contracts.md
§4.6): `codex <model codex reported>` on success, `none <reason>` on every failure mode —
not installed, not authed, model unusable, timeout, empty, refusal, malformed. None of
those can come out as a codex line, so none can pass. No model is pinned; the model is
read from the banner codex prints on stderr (its JSON event stream carries none).
stdin is always closed: codex otherwise waits for more input and a headless run hangs.

Usage:
  codex-exec.py probe [--timeout S]
  codex-exec.py exec --prompt FILE --out FILE [--schema FILE] [--cd DIR] [--timeout S]
                     [--effort LEVEL]
  env VERIFY_CODEX_BIN overrides the codex binary (tests use fakes).
Output: diagnostics on stderr (§10 messages); the judge line as the last stdout line.
Exit:   0 codex ran and answered · 1 a failure mode (judge line is `none …`) · 2 usage
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_lib as vl  # noqa: E402

DOCS = f"{vl.CONTRACT} §4.6"
AUTH = re.compile(r"(?i)not logged in|login|unauthori[sz]ed|401|api key|authenticat")
MODEL_ERR = re.compile(r"(?i)model .*(not (found|supported|available)|does not exist|unsupported)|"
                       r"unknown model|invalid model|upgrade")


def codex_bin():
    return os.environ.get("VERIFY_CODEX_BIN") or shutil.which("codex")


def model_from(stderr):
    m = re.search(r"^model:\s*(\S+)", stderr, re.M)
    return m.group(1) if m else None


def fail(reason, found, nxt, cause="environment"):
    print(vl.message("WARN", f"codex cannot judge: {reason}", "codex installed, logged in, and answering",
                     found, "codex-exec.py", cause, nxt, DOCS), file=sys.stderr)
    print(f"none {reason}")
    return vl.EXIT_FAIL


def classify(rc, stderr):
    """Reason for a non-zero codex exit."""
    tail = " ".join(stderr.strip().splitlines()[-3:])[:300] or f"exit {rc}"
    if AUTH.search(stderr):
        return "codex not authed", tail, "codex login"
    if MODEL_ERR.search(stderr):
        return "codex model unusable", tail, "npm i -g @openai/codex@latest, then codex-exec.py probe"
    return f"codex exited {rc}", tail, "run the same codex exec by hand and read ~/.codex/logs/"


def run_codex(args, timeout):
    """(rc or None on timeout, stdout, stderr)."""
    try:
        p = subprocess.run([codex_bin(), *args], stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        err = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return None, "", err


def check_installed():
    b = codex_bin()
    if not b or not os.path.exists(b):
        return "codex not installed", "no `codex` on PATH", "npm i -g @openai/codex && codex login"
    try:
        v = subprocess.run([b, "--version"], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "codex not runnable", str(exc), "reinstall: npm i -g @openai/codex"
    if v.returncode != 0:
        return "codex not runnable", (v.stderr or v.stdout).strip()[:200], "reinstall: npm i -g @openai/codex"
    return None


def cmd_probe(a):
    bad = check_installed()
    if bad:
        return fail(*bad)
    rc, out, err = run_codex(["exec", "-s", "read-only", "--ephemeral", "--skip-git-repo-check",
                              "--color", "never", "Reply with exactly: pong"], a.timeout)
    if rc is None:
        return fail("codex probe timed out", f"no answer in {a.timeout}s", "retry; check network and ~/.codex/logs/")
    if rc != 0:
        return fail(*classify(rc, err))
    if "pong" not in out.lower():
        return fail("codex probe answered unexpectedly", repr(out.strip()[:120]), "run `codex exec 'say pong'` by hand")
    model = model_from(err)
    if not model:
        return fail("codex did not report its model", "no `model:` line on stderr", "check codex version output",
                    cause="tooling")
    print(f"codex {model}")
    return vl.EXIT_PASS


def cmd_exec(a):
    bad = check_installed()
    if bad:
        return fail(*bad)
    try:
        with open(a.prompt, encoding="utf-8") as fh:
            prompt = fh.read()
    except OSError as exc:
        print(vl.message("ERROR", "cannot read the prompt", "a readable prompt file", str(exc), a.prompt,
                         "tooling", "re-render the prompt", DOCS), file=sys.stderr)
        return vl.EXIT_USAGE
    if os.path.exists(a.out):
        os.remove(a.out)  # a stale answer must never be read as this run's
    args = ["exec", "-s", "read-only", "--ephemeral", "--skip-git-repo-check", "--color", "never",
            "-c", f'model_reasoning_effort="{a.effort}"', "-o", a.out]
    if a.schema:
        args += ["--output-schema", a.schema]
    if a.cd:
        args += ["-C", a.cd]
    rc, out, err = run_codex(args + [prompt], a.timeout)
    if rc is None:
        return fail("codex timed out", f"no answer in {a.timeout}s", "split the prompt or raise --timeout")
    if rc != 0:
        return fail(*classify(rc, err))
    text = open(a.out, encoding="utf-8").read().strip() if os.path.exists(a.out) else ""
    if not text:
        return fail("codex returned an empty answer", "empty last message", "re-run; check the prompt size",
                    cause="tooling")
    try:
        doc = json.loads(text)
    except ValueError:
        if re.search(r"(?i)\b(i can(no|')t|i'm unable|i won't|cannot help)\b", text[:400]):
            return fail("codex refused", text[:160].replace("\n", " "), "reword the prompt", cause="tooling")
        return fail("codex answer is malformed", f"not JSON: {text[:120]!r}", "check --schema is passed",
                    cause="tooling")
    if not isinstance(doc, dict):
        return fail("codex answer is malformed", f"JSON {type(doc).__name__}, not an object", "check --schema",
                    cause="tooling")
    model = model_from(err)
    if not model:
        return fail("codex did not report its model", "no `model:` line on stderr", "check codex version output",
                    cause="tooling")
    print(f"codex {model}")
    return vl.EXIT_PASS


def main(argv):
    ap = argparse.ArgumentParser(description="Run codex headless (probe | exec).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe")
    p.add_argument("--timeout", type=int, default=90)
    e = sub.add_parser("exec")
    e.add_argument("--prompt", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--schema")
    e.add_argument("--cd")
    e.add_argument("--timeout", type=int, default=600)
    e.add_argument("--effort", default="high", choices=("low", "medium", "high", "xhigh"))
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return vl.EXIT_USAGE if exc.code else vl.EXIT_PASS
    return cmd_probe(a) if a.cmd == "probe" else cmd_exec(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
