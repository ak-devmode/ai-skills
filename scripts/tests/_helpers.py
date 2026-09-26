"""Shared helpers for scripts/tests.

Approach: the scripts under test are hyphenated executables (`verify-run.py`), which
`import` cannot name, so tests either run them as subprocesses — the way skills call
them, exit code and stdout included — or load one by path when a unit test needs a
function directly. Stdlib only: the tests must run on a fresh clone with Python >= 3.9
and nothing installed.
"""

import importlib.util
import os
import subprocess
import sys

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(SCRIPTS)


def script(name):
    """Absolute path of scripts/<name>."""
    return os.path.join(SCRIPTS, name)


def run(name, *args, cwd=None, env=None, timeout=60):
    """Run scripts/<name> with the current interpreter; return CompletedProcess (text)."""
    path = script(name)
    cmd = [sys.executable, path] if name.endswith(".py") else [path]
    return subprocess.run(cmd + list(args), cwd=cwd, env=env, timeout=timeout,
                          capture_output=True, text=True)


def load(name):
    """Import scripts/<name> as a module by path, for direct unit tests."""
    mod_name = os.path.splitext(name)[0].replace("-", "_")
    spec = importlib.util.spec_from_file_location(mod_name, script(name))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
