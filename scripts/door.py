#!/usr/bin/env python3
"""door.py — classify a change as a one-way door (scope 10 §4.1, plan 10.1 task 1.2).

Approach: the floor is a list of gitignore-style globs, the union of
scripts/one-way-doors.defaults and the repo's `.one-way-doors` read AT THE BASE
REVISION (`git show BASE:.one-way-doors`), so a change can never authorize its own
removal from the floor. Every path the range touches counts — added, modified,
deleted, mode-changed, and BOTH sides of a rename (git diff --no-renames reports a
rename as delete + add). Any hit, or any edit to `.one-way-doors` itself, = one-way.

Promote-only: the result is max(agent claim, computed); a `--claim two-way` can never
lower a floor hit. Fails closed: an unparseable range, a ref that does not resolve, a
git error, an unreadable defaults file, an unreadable base `.one-way-doors`, or an
invalid claim all return one-way with the reason — a wrong "two-way" is the only
costly error, a wrong "one-way" costs one human glance. Matching is case-insensitive
(macOS volumes are), `!` negation lines are ignored for the same reason.

    door.py classify --repo PATH --range BASE..HEAD [--claim one-way|two-way|info]
                     [--defaults FILE]
      stdout: {"door", "paths": [{"path","pattern","change"}], "reason"}
      exit: 0 classified (including a fail-closed one-way) · 2 usage
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

DEFAULTS = Path(__file__).resolve().parent / "one-way-doors.defaults"
REPO_FILE = ".one-way-doors"
RANK = {"info": 0, "two-way": 1, "one-way": 2}


def glob_to_regex(pat):
    """gitignore-style glob -> compiled regex (None for a blank/comment/negation line)."""
    pat = pat.strip()
    if not pat or pat.startswith("#") or pat.startswith("!"):
        return None
    anchored = pat.startswith("/") or "/" in pat.rstrip("/")
    dir_only = pat.endswith("/")
    pat = pat.strip("/")
    out, i = [], 0
    while i < len(pat):
        c = pat[i]
        if pat.startswith("**/", i):
            out.append("(?:.*/)?"); i += 3
        elif pat.startswith("/**", i) and i + 3 == len(pat):
            out.append("/.*"); i += 3
        elif pat.startswith("**", i):
            out.append(".*"); i += 2
        elif c == "*":
            out.append("[^/]*"); i += 1
        elif c == "?":
            out.append("[^/]"); i += 1
        elif c == "[" and "]" in pat[i + 2:]:
            j = pat.index("]", i + 2)
            out.append("[" + pat[i + 1:j].replace("\\", "\\\\") + "]"); i = j + 1
        else:
            out.append(re.escape(c)); i += 1
    body = "".join(out)
    head = "^" if anchored else "^(?:.*/)?"
    tail = "/.*$" if dir_only else "(?:/.*)?$"
    return re.compile(head + body + tail, re.IGNORECASE)


def compile_rules(text):
    rules = []
    for line in text.splitlines():
        rx = glob_to_regex(line)
        if rx:
            rules.append((line.strip(), rx))
    return rules


class Failed(Exception):
    """A fail-closed condition: message becomes the one-way reason."""


def git(repo, *args):
    try:
        p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                           timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        raise Failed(f"git could not run: {e}")
    return p


def parse_range(rng):
    if not isinstance(rng, str) or rng.count("..") != 1 or "..." in rng or re.search(r"\s", rng):
        raise Failed(f"unparseable range {rng!r} (want BASE..HEAD)")
    base, head = rng.split("..")
    for ref in (base, head):
        if not ref or ref.startswith("-"):
            raise Failed(f"unparseable range {rng!r} (empty or option-like side)")
    return base, head


def resolve(repo, ref):
    p = git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    sha = p.stdout.strip()
    if p.returncode != 0 or not sha:
        raise Failed(f"ref {ref!r} does not resolve to a commit")
    return sha


def touched(repo, base, head):
    """[(change, path)] for every path the range touches; renames yield both sides."""
    p = git(repo, "diff", "--name-status", "--no-renames", "--no-ext-diff", "-z", base, head, "--")
    if p.returncode != 0:
        raise Failed(f"git diff failed: {p.stderr.strip()[:200]}")
    parts = p.stdout.split("\0")
    if parts and parts[-1] == "":
        parts.pop()
    if len(parts) % 2:
        raise Failed("git diff output not parseable")
    return [(parts[i][:1], parts[i + 1]) for i in range(0, len(parts), 2)]


def base_repo_rules(repo, base_sha):
    p = git(repo, "cat-file", "-e", f"{base_sha}:{REPO_FILE}")
    if p.returncode != 0:
        # absent at base is legitimate (no repo floor); verify it is absence, not an error
        t = git(repo, "ls-tree", "--name-only", base_sha, "--", REPO_FILE)
        if t.returncode != 0:
            raise Failed(f"cannot read tree at base: {t.stderr.strip()[:200]}")
        if not t.stdout.strip():
            return []
        raise Failed(f"{REPO_FILE} exists at base but is unreadable")
    s = git(repo, "show", f"{base_sha}:{REPO_FILE}")
    if s.returncode != 0:
        raise Failed(f"cannot read {REPO_FILE} at base: {s.stderr.strip()[:200]}")
    return compile_rules(s.stdout)


def classify(repo, rng, claim=None, defaults=DEFAULTS):
    try:
        if claim is not None and claim not in RANK:
            raise Failed(f"invalid claim {claim!r}")
        base, head = parse_range(rng)
        if not Path(repo).is_dir():
            raise Failed(f"repo path {repo!r} is not a directory")
        base_sha, head_sha = resolve(repo, base), resolve(repo, head)
        try:
            rules = compile_rules(Path(defaults).read_text())
        except OSError as e:
            raise Failed(f"defaults file unreadable: {e}")
        rules += base_repo_rules(repo, base_sha)
        hits = []
        for change, path in touched(repo, base_sha, head_sha):
            if path == REPO_FILE or path.endswith("/" + REPO_FILE):
                hits.append({"path": path, "pattern": f"{REPO_FILE} (edit judged at base)", "change": change})
                continue
            for text, rx in rules:
                if rx.match(path):
                    hits.append({"path": path, "pattern": text, "change": change})
                    break
    except Failed as e:
        return {"door": "one-way", "paths": [], "reason": f"fail-closed: {e}"}
    door = "one-way" if hits else "two-way"
    reason = (f"{len(hits)} floor path(s) touched" if hits else "no floor path touched")
    if claim and RANK[claim] > RANK[door]:
        door, reason = claim, f"{reason}; promoted by agent claim"
    elif claim and RANK[claim] < RANK[door]:
        reason += f"; agent claim {claim!r} ignored (promote-only)"
    return {"door": door, "paths": hits, "reason": reason}


def main(argv):
    ap = argparse.ArgumentParser(prog="door.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("classify")
    c.add_argument("--repo", required=True)
    c.add_argument("--range", required=True, dest="rng")
    c.add_argument("--claim")
    c.add_argument("--defaults", default=str(DEFAULTS))
    a = ap.parse_args(argv)
    print(json.dumps(classify(a.repo, a.rng, a.claim, a.defaults)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
