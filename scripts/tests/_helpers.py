"""Shared helpers for scripts/tests.

Approach: the scripts under test are hyphenated executables (`verify-run.py`), which
`import` cannot name, so tests either run them as subprocesses — the way skills call
them, exit code and stdout included — or load one by path when a unit test needs a
function directly. Stdlib only: the tests must run on a fresh clone with Python >= 3.9
and nothing installed.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(SCRIPTS)


def script(name):
    """Absolute path of scripts/<name>, or of a repo-relative path like verify/scripts/x.py."""
    return os.path.join(REPO if "/" in name else SCRIPTS, name)


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


def fake_herdr(tmp, mode, path):
    """A `herdr` on PATH answering `agent list` for pane w9:p2: named `driver`, named a lane,
    unnamed, absent from the list, or failing. Returns the env that puts the pane in herdr."""
    d = tempfile.mkdtemp(dir=tmp)
    me = {"agent": "claude", "pane_id": "w9:p2", "workspace_id": "w9"}
    if mode in ("driver", "lane"):
        me["name"] = "driver" if mode == "driver" else "lane-x"
    agents = [{"agent": "claude", "pane_id": "w9:p1", "name": "driver"}] + ([] if mode == "absent" else [me])
    body = ("echo 'herdr: socket unreachable' >&2; exit 1" if mode == "error" else
            "cat <<'EOF'\n" + json.dumps({"result": {"agents": agents}}) + "\nEOF")
    with open(os.path.join(d, "herdr"), "w") as f:
        f.write("#!/bin/sh\n" + body + "\n")
    os.chmod(os.path.join(d, "herdr"), 0o755)
    return {"HERDR_PANE_ID": "w9:p2", "HERDR_WORKSPACE_ID": "w9", "PATH": d + os.pathsep + path}
