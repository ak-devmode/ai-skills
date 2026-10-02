"""landed_lib.py — did a commit reach what ships? Shared by verdict-gate.py. Not a CLI.

Approach (templates/verify-contracts.md §5.2.2), pure git, no forge API, never fetches. What
ships is the repo's HEAD — the branch the unit is on — or, when that does not hold it, the
repo's trunk (`trunk`): after a squash merge the lane's worktree is gone and the main checkout
can sit on any branch. A commit F has landed on a target when, in this order:
  1. F is an ancestor of the target (a true merge, or a fast-forward);
  2. F's `git patch-id --stable` matches a commit in merge-base(F, target)..target — a rebase
     merge or a cherry-pick, which copy the patch but not the ancestry;
  3. F's own change (F^..F) is contained in a commit S on the target's first-parent line after
     the fork point — a squash merge (`arrival`); or
  4. F^..L is contained in such an S, for a *known* commit L (one the review log names) that F
     is an ancestor of — F and what its lane did after it, up to L, so a fix whose lines a
     later lane commit reworked before the squash still lands. Never the lane before F: a
     commit pushed onto a lane after its squash finds its own change, 0% of it, and blocks.
     F is then in what was squashed by the same ancestry rule as 1; a fix reverted before L
     nets out of F^..L and does not land this way (ancestry would have passed it).

"Contained" is line-exact. A change's significant edits are its added lines, in the after
side's own line numbers, and its pure deletions, at their gap; significant = the line holds a
3-character word run, so `}`, blank lines and lone punctuation never decide. An edit is
*informative* when the fork point lacks it — diff(after, fork point) undoes it — so a change
the trunk already holds proves nothing. An edit is *undone* in a tree X when diff(after, X)
deletes that added line or re-adds that deleted line at its gap. A change is contained in S
when more than half of its informative edits are not undone in S; the first such S on the
first-parent line is the commit that brought it. Majority, not all: in scope 149.2 a squashed
lane kept 96–99% of its edits (later lane commits and trunk work reworked the rest) and a fix
42–99%, while an unmerged commit keeps ~0% in every trunk commit. With no informative edit
nothing is proved, and a git failure is never a landing.
"""

import os
import re
import subprocess


SIG = re.compile(r"[A-Za-z0-9_]{3}")
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_CACHE = {}


def reset():
    """Forget every memoized answer. Callers run it once per evaluation: refs move between
    evaluations (a test merging a branch, a long-lived importer), never during one."""
    _CACHE.clear()


def _git(path, *args, inp=None):
    """(returncode, stdout), memoized until reset(): every call here is a read."""
    key = ("git", path, args, inp)
    if key not in _CACHE:
        p = subprocess.run(["git", "-C", path, "-c", "core.quotePath=false", *args], input=inp,
                           capture_output=True, text=True, errors="replace")
        _CACHE[key] = (p.returncode, p.stdout)
    return _CACHE[key]


def _ok(path, *args):
    return _git(path, *args)[0] == 0


def _name(s):
    """A diff header path without its a/ b/ prefix (C-quoted names unquoted)."""
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1].encode("latin-1", "backslashreplace").decode("unicode_escape").encode("latin-1").decode(
            "utf-8", "replace")
    return s[2:] if s[:2] in ("a/", "b/") else s


def hunks(path, a, b, files=()):
    """({file: [(old_start, old_len, new_start, new_len, removed, added)]}, {binary files}) for
    `git diff -U0 a b`, or None when git fails."""
    rc, out = _git(path, "diff", "-U0", "--no-renames", "--no-color", "--no-ext-diff", a, b,
                   *(["--", *files] if files else []))
    if rc:
        return None
    res, binary, old, cur, h = {}, set(), None, None, None
    for line in out.split("\n"):
        if line.startswith("diff --git "):
            old = cur = h = None
        elif line.startswith("--- ") and h is None:
            old = None if line == "--- /dev/null" else _name(line[4:])
        elif line.startswith("+++ ") and h is None:
            cur = old if line == "+++ /dev/null" else _name(line[4:])
        elif line.startswith("Binary files "):
            m = re.match(r"Binary files (.*) and (.*) differ$", line)
            if m:
                binary.add(_name(m.group(2)) if m.group(2) != "/dev/null" else _name(m.group(1)))
        elif HUNK.match(line):
            m = HUNK.match(line)
            h = (int(m[1]), int(m[2] if m[2] is not None else 1), int(m[3]),
                 int(m[4] if m[4] is not None else 1), [], [])
            res.setdefault(cur, []).append(h)
        elif h is not None and line[:1] == "-":
            h[4].append(line[1:])
        elif h is not None and line[:1] == "+":
            h[5].append(line[1:])
    return res, binary


def _undone(path, after, x, change, files):
    """Keys of the change's significant edits that diff(after, x) undoes; None when git fails."""
    h1, b1 = change
    d2 = hunks(path, after, x, files)
    if d2 is None:
        return None
    h2, _ = d2
    out = set()
    for f in b1:
        if _git(path, "rev-parse", "-q", "--verify", f"{after}:{f}")[1] != \
                _git(path, "rev-parse", "-q", "--verify", f"{x}:{f}")[1]:
            out.add((f, "bin"))
    for f, hs in h1.items():
        if f in b1:
            continue
        added, gaps = {}, {}
        for _, _, ns, nl, rem, add in hs:
            added.update((ns + i, t) for i, t in enumerate(add) if SIG.search(t))
            if not nl:
                gaps[ns] = {t for t in rem if SIG.search(t)}
        for os_, ol, _, _, _, add in h2.get(f, []):
            if ol:
                out.update((f, "+", i) for i in set(added) & set(range(os_, os_ + ol)))
            back = set(add)
            for gp, dl in gaps.items():
                if dl & back and (os_ - 1 <= gp <= os_ + ol - 1 if ol else os_ == gp):
                    out.update((f, "-", gp, t) for t in dl & back)
    return out


def _mb(path, sha, target):
    rc, out = _git(path, "merge-base", sha, target)
    return out.strip() if rc == 0 and out.strip() else None


def arrival(path, a, b, target="HEAD"):
    """The first commit on target's first-parent line after merge-base(b, target) that contains
    the change a..b (module docstring), or None. a = b^ asks about one commit, a = F^ with a
    later b about F and what followed it, a = a review's base about what that review read."""
    key = ("arrival", path, a, b, target)
    if key in _CACHE:
        return _CACHE[key]
    _CACHE[key] = None
    mb = _mb(path, b, target)
    change = hunks(path, a, b) if mb else None
    if change is None:
        return None
    files = sorted(set(change[0]) | change[1])
    informative = _undone(path, b, mb, change, files) if files else None
    if not informative:
        return None
    rc, revs = _git(path, "rev-list", "--first-parent", "--reverse", f"{mb}..{target}", "--", *files)
    # the first commit to contain the change turns at least one of its edits from undone to
    # kept, so it adds one of its added lines or deletes one of its deleted ones (a speed-up:
    # skipping the real S could only block, never pass)
    plus = {t for hs in change[0].values() for h in hs for t in h[5] if SIG.search(t)}
    minus = {t for hs in change[0].values() for h in hs if not h[3] for t in h[4] if SIG.search(t)}
    log = _trunk_lines(path, mb, target)
    for s in revs.split() if rc == 0 else []:
        if s in log and not change[1] and not (log[s][0] & plus or log[s][1] & minus):
            continue
        gone = _undone(path, b, s, change, files)
        if gone is not None and 2 * len(informative - gone) > len(informative):
            _CACHE[key] = s
            return s
    return None




def _trunk_lines(path, mb, target):
    """{commit: (added texts, removed texts)} for target's first-parent line after mb, each
    commit against its first parent (a merge's own diff included)."""
    key = ("lines", path, mb, target)
    if key not in _CACHE:
        rc, out = _git(path, "log", "--first-parent", "--diff-merges=first-parent", "-p", "-U0", "--no-color",
                       "--no-ext-diff", "--format=commit %H", f"{mb}..{target}")
        res, cur = {}, None
        for line in out.split("\n") if rc == 0 else []:
            if line.startswith("commit ") and len(line) == 47:
                cur = res.setdefault(line[7:], (set(), set()))
            elif cur is not None and line[:1] in "+-" and line[:4] not in ("+++ ", "--- ") and SIG.search(line):
                cur[0 if line[0] == "+" else 1].add(line[1:])
        _CACHE[key] = res
    return _CACHE[key]


def _patch_id(path, rev_or_text, stdin=False):
    """{patch_id: commit} for `git patch-id --stable` over a `git log -p` text, or one commit's."""
    if not stdin:
        rc, rev_or_text = _git(path, "show", "--no-color", "--no-ext-diff", "--format=commit %H", rev_or_text)
        if rc:
            return {}
    rc, out = _git(path, "patch-id", "--stable", inp=rev_or_text)
    return {ln.split()[0]: ln.split()[1] for ln in out.splitlines() if len(ln.split()) == 2} if rc == 0 else {}


def patch_match(path, sha, target="HEAD"):
    """A commit in merge-base(sha, target)..target with sha's patch-id, or None."""
    mine = _patch_id(path, sha)
    mb = _mb(path, sha, target)
    if not mine or not mb:
        return None
    key = ("pids", path, mb, target)
    if key not in _CACHE:
        rc, log = _git(path, "log", "-p", "--no-merges", "--no-color", "--no-ext-diff", "--format=commit %H",
                       f"{mb}..{target}")
        _CACHE[key] = _patch_id(path, log, stdin=True) if rc == 0 else {}
    pid = next(iter(mine))
    hit = _CACHE[key].get(pid)
    return hit if hit and hit != sha else None


def trunk(path):
    """The repo's trunk ref, the cascade of scripts/repo-survey.sh: CROSS-REPO.md
    `trunk-branch:`, else origin/develop, else origin/HEAD's branch, else local develop/main.
    None when none resolves. Read-only: never fetches."""
    if ("trunk", path) in _CACHE:
        return _CACHE[("trunk", path)]
    names = []
    try:
        with open(os.path.join(path, "CROSS-REPO.md")) as fh:
            m = re.search(r"trunk-branch: *([A-Za-z0-9._/-]+)", fh.read())
        if m:
            names += [f"origin/{m[1]}", m[1]]
    except OSError:
        pass
    rc, head = _git(path, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD")
    names += ["origin/develop", *([head.strip()] if rc == 0 and head.strip() else []), "origin/main",
              "develop", "main"]
    _CACHE[("trunk", path)] = next((n for n in names if _ok(path, "rev-parse", "-q", "--verify",
                                                            f"refs/remotes/{n}" if n.startswith("origin/")
                                                            else f"refs/heads/{n}")), None)
    return _CACHE[("trunk", path)]


def targets(path):
    """What ships: [HEAD, trunk] — the branch the unit is on, or the trunk it merged into. Just
    [trunk] when HEAD is an ancestor of it (a stale or clean main checkout: whatever HEAD holds,
    trunk holds), just [HEAD] when there is no trunk."""
    t = trunk(path)
    if not t:
        return ["HEAD"]
    return [t] if _ok(path, "merge-base", "--is-ancestor", "HEAD", t) else ["HEAD", t]


def landed(path, sha, known=(), target=None):
    """How `sha` reached target (default: HEAD, else the trunk) in repo `path`: ("ancestor",
    None), ("patch-id", S), ("squash", S), or ("squash", S, L) when it rode in with its lane
    up to L — or None (not landed, or git cannot tell). `known` is every SHA the caller's
    records name; ones not in this repo are skipped."""
    if not sha or not os.path.isdir(path):
        return None
    if target is None:
        key = ("landed", path, sha, tuple(sorted(set(known))))
        if key not in _CACHE:
            _CACHE[key] = next((h for t in targets(path) for h in [landed(path, sha, known, t)] if h), None)
        return _CACHE[key]
    if _ok(path, "merge-base", "--is-ancestor", sha, target):
        return ("ancestor", None)
    if not _ok(path, "cat-file", "-e", f"{sha}^{{commit}}"):
        return None
    s = patch_match(path, sha, target)
    if s:
        return ("patch-id", s)
    s = arrival(path, f"{sha}^", sha, target)
    if s:
        return ("squash", s)
    for L in _descendants(path, sha, tuple(sorted(set(known))), target):
        s = arrival(path, f"{sha}^", L, target)
        if s:
            return ("squash", s, L)
    return None


def _descendants(path, sha, known, target):
    """The known commits of this repo that sha is an ancestor of, off target, nearest first."""
    rc, out = _git(path, "cat-file", "--batch-check", inp="".join(f"{k}\n" for k in known))
    here = {ln.split()[0] for ln in out.splitlines() if ln.split()[1:2] == ["commit"]} if rc == 0 else set()
    near = []
    for L in here:
        if not L.startswith(sha) and _ok(path, "merge-base", "--is-ancestor", sha, L) \
                and not _ok(path, "merge-base", "--is-ancestor", L, target):
            rc, n = _git(path, "rev-list", "--count", f"{sha}..{L}")
            near.append((int(n) if rc == 0 else 1 << 30, L))
    return [L for _, L in sorted(near)]


def describe(how):
    """One phrase for a landing, for gate output."""
    if how is None:
        return "not landed"
    if how[0] == "ancestor":
        return "an ancestor"
    if how[0] == "patch-id":
        return f"rebase-merged as {how[1][:10]} (same patch-id)"
    return f"squash-merged in {how[1][:10]}" + (f" (with its lane up to {how[2][:10]})" if len(how) > 2 else "")
