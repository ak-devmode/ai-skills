"""landed_lib.py — did a commit reach what ships through a true, squash or rebase merge?

Approach: one throwaway repo per case. `main` (the trunk) holds a small Go-ish file; a lane
branch adds code and fixes it; the case then lands the lane on main the way GitHub would
(merge, squash, rebase) — or doesn't — and the table says what `landed` must answer for each
lane commit, given the SHAs a review log would name. Everything that must not read as merged
(an unmerged branch, the tail of a partial squash, a fix reverted before the squash, a
follow-up pushed onto a lane after its squash, a SHA the repo lacks) is a row here.
"""

import os
import subprocess
import tempfile
import unittest

from _helpers import load

ll = load("landed_lib.py")

BASE = "".join(f"func f{i}() int {{\n\treturn value{i}\n}}\n\n" for i in range(12))


def git(path, *args):
    return subprocess.run(["git", "-C", path, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          check=True, capture_output=True, text=True).stdout.strip()


class Repo:
    def __init__(self, root):
        self.p = root
        git(root, "init", "-q", "-b", "main")
        self.write("app.go", BASE)
        self.commit("base")

    def write(self, name, text):
        with open(os.path.join(self.p, name), "w") as fh:
            fh.write(text)

    def read(self, name):
        with open(os.path.join(self.p, name)) as fh:
            return fh.read()

    def edit(self, old, new, name="app.go"):
        text = self.read(name)
        assert text.count(old) == 1, old
        self.write(name, text.replace(old, new))

    def commit(self, msg):
        git(self.p, "add", "-A")
        git(self.p, "commit", "-q", "-m", msg)
        return git(self.p, "rev-parse", "HEAD")

    def lane(self):
        """lane: L1 adds a handler, F1 fixes it, F2 adds a guard. Returns their SHAs."""
        git(self.p, "checkout", "-q", "-b", "lane")
        self.edit("func f3() int {\n", "func handler(x int) error {\n\tlog.Print(\"handling request\", x)\n"
                  "\treturn nil\n}\n\nfunc f3() int {\n")
        l1 = self.commit("L1 handler")
        self.edit('\tlog.Print("handling request", x)\n\treturn nil\n',
                  '\tif err := validate(x); err != nil {\n\t\treturn fmt.Errorf("handler: %w", err)\n\t}\n'
                  '\treturn nil\n')
        f1 = self.commit("F1 fail loud")
        self.edit("\treturn value9\n", "\tif value9 < 0 {\n\t\tpanic(\"negative value9\")\n\t}\n\treturn value9\n")
        f2 = self.commit("F2 guard f9")
        return l1, f1, f2

    def main_moves(self):
        git(self.p, "checkout", "-q", "main")
        self.edit("\treturn value0\n", "\treturn value0 + offsetZero\n")
        self.commit("unrelated trunk work")


def case_true_merge(r):
    shas = r.lane()
    r.main_moves()
    git(r.p, "merge", "-q", "--no-ff", "-m", "merge lane", "lane")
    return shas, {}


def case_squash(r):
    shas = r.lane()
    r.main_moves()
    git(r.p, "merge", "-q", "--squash", "lane")
    r.commit("lane (#1)")
    return shas, {}


def case_rebase(r):
    shas = r.lane()
    r.main_moves()
    for s in shas:
        git(r.p, "cherry-pick", s)
    return shas, {}


def case_unmerged(r):
    shas = r.lane()
    r.main_moves()
    return shas, {}


def case_partial_squash(r):
    """Only the lane up to F1 is squash-merged; F2 stays on the branch."""
    shas = r.lane()
    r.main_moves()
    git(r.p, "merge", "-q", "--squash", shas[1])
    r.commit("lane part 1 (#1)")
    return shas, {}


def case_reverted_before_squash(r):
    """F2 is reverted on the lane, then the lane is squashed: F2 is not in what shipped."""
    shas = r.lane()
    git(r.p, "revert", "--no-edit", shas[2])
    rev = git(r.p, "rev-parse", "HEAD")
    r.main_moves()
    git(r.p, "merge", "-q", "--squash", "lane")
    r.commit("lane (#1)")
    return shas, {"revert": rev}


def case_adjacent_later_work(r):
    """A later lane commit inserts lines right next to F1's and rewrites one of its two
    significant lines — half of F1's own change, so F1 lands only with its lane (known L)."""
    shas = r.lane()
    r.edit("\tif err := validate(x); err != nil {\n",
           "\tmetrics.Inc(\"handler_calls\")\n\tif err := validate(x); err != nil {\n")
    r.edit('\t\treturn fmt.Errorf("handler: %w", err)\n', '\t\treturn fmt.Errorf("handler %d: %w", x, err)\n')
    later = r.commit("later: count calls")
    r.main_moves()
    git(r.p, "merge", "-q", "--squash", "lane")
    r.commit("lane (#1)")
    return shas, {"later": later}


def case_follow_up_after_squash(r):
    """The lane is squash-merged, then a follow-up F3 is pushed onto it and never merged. Its
    lane is ~all in trunk; F3 itself is not — it must block, however much is known."""
    shas = r.lane()
    r.main_moves()
    git(r.p, "merge", "-q", "--squash", "lane")
    r.commit("lane (#1)")
    git(r.p, "checkout", "-q", "lane")
    r.edit("\treturn value7\n", "\tif value7 > limitSeven {\n\t\treturn clampSeven(value7)\n\t}\n\treturn value7\n")
    f3 = r.commit("F3 follow-up, never merged")
    git(r.p, "checkout", "-q", "main")
    return (*shas, f3), {"f3": f3}


def case_head_elsewhere(r):
    """Squash-merged on main, but the checkout sits on an unrelated branch: what ships is the
    trunk, so the lane still lands — and an unmerged commit on that branch does not."""
    shas = r.lane()
    r.main_moves()
    git(r.p, "merge", "-q", "--squash", "lane")
    r.commit("lane (#1)")
    git(r.p, "checkout", "-q", "-b", "other", "main~1")
    r.edit("\treturn value11\n", "\treturn value11 * otherScale\n")
    o = r.commit("other: unrelated, unmerged")
    git(r.p, "checkout", "-q", "-b", "elsewhere", "main~2")
    return (*shas, o), {}


def case_reworked_then_squashed(r):
    """F1's lines are rewritten wholesale by a later lane commit W: F1's own change is gone,
    but F1 is an ancestor of W, whose change landed — so F1 is in what was squashed."""
    shas = r.lane()
    r.edit('\tif err := validate(x); err != nil {\n\t\treturn fmt.Errorf("handler: %w", err)\n\t}\n',
           '\tswitch check := validateStrict(x); {\n\tcase check != nil:\n\t\treturn wrapHandlerError(check)\n\t}\n')
    w = r.commit("W rework")
    r.main_moves()
    git(r.p, "merge", "-q", "--squash", "lane")
    r.commit("lane (#1)")
    return shas, {"rework": w}


def _deletion_lane(r):
    """main gains a debug line; the lane's F deletes it; main then moves on."""
    r.edit("\treturn value5\n", "\tdebugDump(value5)\n\treturn value5\n")
    r.commit("main has a debug dump")
    git(r.p, "checkout", "-q", "-b", "lane")
    r.edit("\tdebugDump(value5)\n", "")
    f = r.commit("F drop the debug dump")
    r.main_moves()
    return f


def case_pure_deletion(r):
    f = _deletion_lane(r)
    git(r.p, "merge", "-q", "--squash", "lane")
    r.commit("lane (#1)")
    return (f,), {}


def case_pure_deletion_unmerged(r):
    return (_deletion_lane(r),), {}


A, P, S, N = "ancestor", "patch-id", "squash", None
# (name, build, known extras, expected kind per lane commit [L1, F1, F2, …])
CASES = [
    ("true merge", case_true_merge, (), [A, A, A]),
    ("squash merge", case_squash, (), [S, S, S]),
    ("rebase merge", case_rebase, (), [P, P, P]),
    ("unmerged branch", case_unmerged, (), [N, N, N]),
    ("partial squash: tail stays unmerged", case_partial_squash, (), [S, S, N]),
    ("fix reverted on the lane before the squash, revert known", case_reverted_before_squash, ("revert",),
     [S, S, N]),
    ("later lane work beside the fix, nothing after it known", case_adjacent_later_work, (), [S, N, S]),
    ("later lane work beside the fix, the later commit known", case_adjacent_later_work, ("later",), [S, S, S]),
    ("follow-up pushed after the squash stays unmerged", case_follow_up_after_squash, ("f3",), [S, S, S, N]),
    ("HEAD on another branch: the trunk decides", case_head_elsewhere, (), [S, S, S, N]),
    ("fix reworked later: lands via the known reworking commit", case_reworked_then_squashed, ("rework",),
     [S, S, S]),
    ("fix reworked later, reworking commit unknown", case_reworked_then_squashed, (), [S, N, S]),
    ("pure-deletion fix squash-merged (alone, so the same patch-id)", case_pure_deletion, (), [P]),
    ("pure-deletion fix unmerged", case_pure_deletion_unmerged, (), [N]),
]


class TestLanded(unittest.TestCase):
    def test_cases(self):
        for name, build, extras, want in CASES:
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                ll.reset()
                r = Repo(tmp)
                shas, named = build(r)
                known = [named[k] for k in extras]
                got = [(ll.landed(r.p, s, known) or (None,))[0] for s in shas]
                self.assertEqual(got, want, f"{name}: {[ll.describe(ll.landed(r.p, s, known)) for s in shas]}")

    def test_rework_lands_via_the_reworking_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            ll.reset()
            r = Repo(tmp)
            (_, f1, _), named = case_reworked_then_squashed(r)
            how = ll.landed(r.p, f1, [named["rework"]])
            self.assertEqual((how[0], how[2]), ("squash", named["rework"]))
            self.assertEqual(how[1], git(r.p, "rev-parse", "HEAD"))

    def test_unknown_sha_and_missing_repo_are_not_landed(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            self.assertIsNone(ll.landed(r.p, "0123456789abcdef0123456789abcdef01234567"))
            self.assertIsNone(ll.landed(os.path.join(tmp, "gone"), git(r.p, "rev-parse", "HEAD")))

    def test_empty_commit_proves_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Repo(tmp)
            git(r.p, "checkout", "-q", "-b", "lane")
            git(r.p, "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "empty")
            e = git(r.p, "rev-parse", "HEAD")
            git(r.p, "checkout", "-q", "main")
            r.main_moves()
            self.assertIsNone(ll.landed(r.p, e))


if __name__ == "__main__":
    unittest.main()
