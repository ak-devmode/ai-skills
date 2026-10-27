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
import socket
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


def dispatch_env(tmp, mode, pane="w9:p2"):
    """Env that puts this process in herdr pane `pane` with a fresh $HOME whose dispatch log
    (~/.config/herdr/concurrency-log.jsonl, what /concurrency writes) holds: "lane" — an open
    dispatched record for the pane; "closed" — dispatched then done; "other" — open records
    for another pane and for this pane on another machine; "none" — no log; "unreadable" — a
    log line that is not JSON."""
    home = tempfile.mkdtemp(dir=tmp)
    me = socket.gethostname().split(".")[0].lower()
    rec = lambda pane_id, status, machine=me: json.dumps(
        {"scope": "10", "task": "t", "pane_id": pane_id, "status": status, "machine": machine})
    lines = {"lane": [rec(pane, "dispatched")],
             "closed": [rec(pane, "dispatched"), rec(pane, "done")],
             "other": [rec("w9:p1", "dispatched"), rec(pane, "dispatched", "elsewhere-box")],
             "unreadable": [rec("w9:p1", "done"), "{not json"]}.get(mode)
    if lines is not None:
        os.makedirs(os.path.join(home, ".config", "herdr"))
        with open(os.path.join(home, ".config", "herdr", "concurrency-log.jsonl"), "w") as f:
            f.write("\n".join(lines) + "\n")
    return {"HOME": home, "HERDR_PANE_ID": pane, "HERDR_WORKSPACE_ID": "w9"}
