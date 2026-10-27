"""Tests for scripts/harness-scorecard/ — lineage counting, reply tagging, delta, the CLI.

Approach: small synthetic logs in a temp dir, laid out as the real cache is
(`<logs>/mba-plans/.../artifacts/review-<unit>.jsonl`, `<logs>/mba/claude-projects/<p>/<s>.jsonl`),
and a throwaway git repo as the projects root so review.py's lineage rules read real ancestry.
No real transcript or review text is used. Stdlib only.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from _helpers import REPO, SCRIPTS

HS = os.path.join(SCRIPTS, "harness-scorecard")
sys.path.insert(0, HS)
import review_loop  # noqa: E402
import sessions  # noqa: E402
import store  # noqa: E402

SECRET = "pasien Budi Santoso RM-000123"  # must never reach the store


def git(d, *a):
    return subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, check=True).stdout.strip()


def make_repo(root):
    """demo repo: a → b → c on main, y on a side branch from a. Returns {name: sha}."""
    d = os.path.join(root, "demo")
    os.makedirs(d)
    git(d, "init", "-q", "-b", "main")
    git(d, "config", "user.email", "t@example.com"); git(d, "config", "user.name", "t")
    shas = {}
    for n in ("a", "b", "c"):
        with open(os.path.join(d, "f.txt"), "a") as fh:
            fh.write(n + "\n")
        git(d, "add", "f.txt"); git(d, "commit", "-qm", n)
        shas[n] = git(d, "rev-parse", "HEAD")
    git(d, "checkout", "-q", "-b", "side", shas["a"])
    with open(os.path.join(d, "g.txt"), "w") as fh:
        fh.write("y\n")
    git(d, "add", "g.txt"); git(d, "commit", "-qm", "y")
    shas["y"] = git(d, "rev-parse", "HEAD")
    git(d, "checkout", "-q", "main")
    return shas


def review(unit, n, base, head, ts, reviewer="codex gpt-6.1-sol", **extra):
    return {"record": "review", "review_id": f"{unit}-r{n}", "reviewer": reviewer, "ts": ts,
            "range": {"demo": f"{base}..{head}"}, "shas": {"base": base, "head": head}, "verdict": "SHIP AFTER BLOCKING", **extra}


def finding(unit, n, i, ts, severity="should-fix", reviewer="codex gpt-6.1-sol", file="f.txt"):
    return {"record": "finding", "review_id": f"{unit}-r{n}", "finding_id": f"{unit}-r{n}-{i:02d}", "reviewer": reviewer,
            "severity": severity, "file": file, "line": 1, "category": "engine", "text": SECRET, "ts": ts,
            "range": {}}


def write_log(logs, scope, unit, recs, host="mba"):
    d = os.path.join(logs, f"{host}-plans", "Projects", "demo", "plans", scope, "artifacts")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"review-{unit}.jsonl"), "w") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")


def unit_11(s):
    """r1 a..b, r2 b..c (a fix re-review: round 2), r3 a..y (new code: round 1 again)."""
    return [review("1.1", 1, s["a"], s["b"], "2026-10-10T00:00:00Z"),
            finding("1.1", 1, 1, "2026-10-10T00:00:00Z", "blocking"), finding("1.1", 1, 2, "2026-10-10T00:00:00Z"),
            review("1.1", 2, s["b"], s["c"], "2026-10-11T00:00:00Z", reviewer="claude-fallback codex out of credits"),
            finding("1.1", 2, 1, "2026-10-11T00:00:00Z", reviewer="claude-fallback codex out of credits"),
            review("1.1", 3, s["a"], s["y"], "2026-10-12T00:00:00Z")]


def unit_12(s):
    """Effort trial: stamped rules 2, r1 then an explicit continuation → trial round 1 + fix round."""
    st = {"rules_version": 2}
    return [review("1.2", 1, s["a"], s["b"], "2026-10-20T00:00:00Z", effort="high", effort_base="medium", round=1, **st),
            finding("1.2", 1, 1, "2026-10-20T00:00:00Z", "blocking"),
            review("1.2", 2, s["b"], s["c"], "2026-10-21T00:00:00Z", effort="high", round=2, continues="1.2-r1", **st)]


def ts(s):
    return review_loop.parse_ts(s)


class LineageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.projects = os.path.join(cls.tmp.name, "projects")
        cls.shas = make_repo(cls.projects)
        cls.rv = review_loop.load_review_module()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def analyze(self, units, since=None):
        with mock.patch.object(self.rv.vl, "PROJECTS", self.projects):
            return review_loop.analyze(units, self.rv, since=since, git=review_loop.Git(self.projects))

    def test_rounds_follow_lineage_not_unit_rn(self):
        out = self.analyze({("s", "1.1"): unit_11(self.shas)})
        rows = out["tables"]["3.1 Lineage rounds"]["rows"]
        # r3 is the unit's third review but new code: lineage round 1, so r1 has 2 reviews
        self.assertEqual(rows["r1"][0], 2)
        self.assertEqual(rows["r2"][0], 1)
        self.assertNotIn("r3", rows)
        self.assertEqual(rows["r1"][2], 1.0)  # 2 findings over 2 r1 reviews
        summary = out["tables"]["3.1 Lineage summary"]["rows"]
        self.assertEqual(summary["lineages (r1 reviews)"], [2])
        self.assertEqual(summary["fallback out of credits"], [1])

    def test_rounds_called_once_per_unit(self):
        calls = []
        real = self.rv.rounds
        with mock.patch.object(self.rv, "rounds", side_effect=lambda recs, unit: calls.append(unit) or real(recs, unit)):
            out = self.analyze({("s", "1.1"): unit_11(self.shas), ("s", "1.2"): unit_12(self.shas)})
        self.assertEqual(sorted(calls), ["1.1", "1.2"])
        self.assertEqual(out["notes"]["rounds_calls"], 2)

    def test_since_keeps_history_for_lineage(self):
        # r1 falls before the window: not counted, but r2 is still round 2 of its lineage
        out = self.analyze({("s", "1.1"): unit_11(self.shas)}, since=ts("2026-10-11T00:00:00Z"))
        rows = out["tables"]["3.1 Lineage rounds"]["rows"]
        self.assertEqual(rows["r2"][0], 1)
        self.assertEqual(rows["r1"][0], 1)  # only r3

    def test_until_drops_later_records(self):
        logs = os.path.join(self.tmp.name, "logs-until")
        write_log(logs, "s", "1.1", unit_11(self.shas))
        units, stats = review_loop.load_logs(logs, until=ts("2026-10-11T12:00:00Z"))
        self.assertEqual(stats["dropped_after_until"], 1)  # r3
        self.assertEqual(len(units[("s", "1.1")]), 5)

    def test_largest_copy_wins(self):
        logs = os.path.join(self.tmp.name, "logs-dedupe")
        write_log(logs, "s", "1.1", unit_11(self.shas)[:2], host="homelab")
        write_log(logs, "s", "1.1", unit_11(self.shas), host="mba")
        units, _ = review_loop.load_logs(logs)
        self.assertEqual(len(units), 1)
        self.assertEqual(len(units[("s", "1.1")]), 6)

    def test_worktree_copies_under_hidden_dirs_are_read(self):
        # worktree copies live under .herdr/worktrees; glob's ** skips dot-directories
        logs = os.path.join(self.tmp.name, "logs-hidden")
        d = os.path.join(logs, "homelab-plans", ".herdr", "worktrees", "demo", "lane", "plans", "s", "artifacts")
        os.makedirs(d)
        with open(os.path.join(d, "review-1.1.jsonl"), "w") as fh:
            fh.writelines(json.dumps(r) + "\n" for r in unit_11(self.shas))
        units, stats = review_loop.load_logs(logs)
        self.assertEqual(stats["files"], 1)
        self.assertEqual(len(units[("s", "1.1")]), 6)

    def test_effort_trial_splits_round1_and_fix_rounds(self):
        out = self.analyze({("s", "1.1"): unit_11(self.shas), ("s", "1.2"): unit_12(self.shas)})
        rows = out["tables"]["Effort trial (codex)"]["rows"]
        self.assertEqual(rows["trial · base medium · round 1"], [1, 1.0, 1.0])
        # r2 carries no effort_base: counted as unstamped, never dropped or recomputed
        self.assertEqual(rows["trial · base unstamped · fix rounds"][0], 1)
        # pre-trial reviews carry no stamp: effort_for on their range (1 file, 1 line → low)
        self.assertEqual(rows["pre-trial · base low · round 1"][0], 2)   # the fallback r2 is not a codex review
        self.assertFalse([k for k in rows if k.startswith("pre-trial") and k.endswith("fix rounds")])
        self.assertEqual(list(rows)[0], "pre-trial · base low · round 1")
        lin = out["tables"]["Effort trial lineages"]["rows"]
        # a lineage takes its root's base; none of these closed (no SHIP, no acceptance)
        self.assertEqual(lin["trial · base medium"], [0, None, None, 1, 0])
        self.assertEqual(lin["pre-trial · base low"], [0, None, None, 2, 0])
        self.assertEqual(out["notes"]["trial_effort_tiers"], {"high": 2})
        self.assertEqual(out["notes"]["stamped_round_mismatches"], 0)

    def test_trial_lineages_count_closed_and_in_window_only(self):
        u12 = unit_12(self.shas)
        u12[-1] = {**u12[-1], "verdict": "SHIP"}             # trial lineage closes on SHIP
        u11 = unit_11(self.shas) + [{"record": "acceptance", "by": "t", "ts": "2026-10-12T00:00:00Z"}]
        out = self.analyze({("s", "1.1"): u11, ("s", "1.2"): u12}, since=ts("2026-10-11T00:00:00Z"))
        lin = out["tables"]["Effort trial lineages"]["rows"]
        self.assertEqual(lin["trial · base medium"], [1, 1.0, 0.0, 0, 0])
        # 1.1: r1's lineage is rooted before `since` (excluded, counted); r3's closed by the acceptance
        self.assertEqual(lin["pre-trial · base low"], [1, 0.0, 0.0, 0, 1])
        # an acceptance before the lineage's last review does not close it
        u11b = unit_11(self.shas) + [{"record": "acceptance", "by": "t", "ts": "2026-10-11T12:00:00Z"}]
        lin = self.analyze({("s", "1.1"): u11b})["tables"]["Effort trial lineages"]["rows"]
        self.assertEqual(lin["pre-trial · base low"], [1, 1.0, 50.0, 1, 0])   # r1–r2 closed (r2 fell back), r3 open

    def test_git_reads_a_non_utf8_diff(self):
        d = os.path.join(self.projects, "demo")
        base = git(d, "rev-parse", "HEAD")
        with open(os.path.join(d, "latin.txt"), "wb") as fh:
            fh.write(b"caf\xe9 \xe2\x28\n")
        git(d, "add", "latin.txt"); git(d, "commit", "-qm", "latin")
        head = git(d, "rev-parse", "HEAD")
        try:
            g = review_loop.Git(self.projects)
            self.assertEqual(g.hunks("demo", f"{base}..{head}")["latin.txt"], [(1, 1)])
            self.assertEqual(g.stat("demo", f"{base}..{head}"), (1, 1))
        finally:
            git(d, "reset", "-q", "--hard", base)

    def test_trial_root_on_a_fallback_review_takes_its_range_tier(self):
        # review.py stamps effort_base on codex reviews only: a trial lineage rooted on a codex
        # credit-out is recomputed from its range, exactly as a pre-trial one is
        st, s = {"rules_version": 2}, self.shas
        fb = "claude-fallback codex out of credits"
        u = [review("1.3", 1, s["a"], s["b"], "2026-10-20T00:00:00Z", reviewer=fb, round=1, **st),
             review("1.3", 2, s["b"], s["c"], "2026-10-21T00:00:00Z", effort="medium", effort_base="low",
                    round=2, continues="1.3-r1", verdict="SHIP", **st)]
        out = self.analyze({("s", "1.3"): u})
        lin = out["tables"]["Effort trial lineages"]["rows"]
        self.assertEqual(list(lin), ["trial · base low"])
        self.assertEqual(lin["trial · base low"][2], 50.0)   # the credit-out stays in its tier
        # a codex trial review that should have carried a stamp is still `unstamped`
        u[1] = {k: v for k, v in u[1].items() if k != "effort_base"}
        rows = self.analyze({("s", "1.3"): u})["tables"]["Effort trial (codex)"]["rows"]
        self.assertEqual(list(rows), ["trial · base unstamped · fix rounds"])

    def test_effort_base_unreadable_range_is_unresolved(self):
        with mock.patch.object(self.rv.vl, "PROJECTS", self.projects):
            out = review_loop.analyze({("s", "1.1"): unit_11(self.shas)}, self.rv, git=review_loop.Git("", enabled=False))
        self.assertEqual(list(out["tables"]["Effort trial (codex)"]["rows"]), ["pre-trial · base unresolved · round 1"])

    def test_lineage_warns_are_counted_not_dropped(self):
        real = self.rv.rounds

        def noisy(recs, unit):
            print("[WARN] lineage of 1.1-r2: git cannot tell ...", file=sys.stderr)
            print("[WARN] lineage of 1.1-r3: git cannot tell ...", file=sys.stderr)
            print("something else", file=sys.stderr)
            return real(recs, unit)
        with mock.patch.object(self.rv, "rounds", side_effect=noisy):
            out = self.analyze({("s", "1.1"): unit_11(self.shas), ("s", "1.2"): unit_12(self.shas)})
        n = out["notes"]
        self.assertEqual(n["lineage_warns"], {"total": 4, "units": {"s/1.1": 2, "s/1.2": 2}})
        self.assertEqual(n["other_stderr_lines"]["total"], 2)

    def test_unit_that_fails_is_reported(self):
        with mock.patch.object(self.rv, "rounds", side_effect=RuntimeError("boom")):
            out = self.analyze({("s", "1.1"): unit_11(self.shas)})
        self.assertEqual(out["notes"]["failed_units"], ["s/1.1: RuntimeError"])
        self.assertEqual(out["tables"]["3.1 Lineage summary"]["rows"]["units"], [0])


def session_lines(cwd="/Users/x/Projects/wellmed/kalpa-docs"):
    base = {"cwd": cwd, "sessionId": "s1"}
    return [
        {**base, "type": "permission-mode", "permissionMode": "bypassPermissions", "timestamp": "2026-10-20T00:00:00Z"},
        {**base, "type": "assistant", "timestamp": "2026-10-20T00:00:00Z",
         "message": {"model": "claude-opus-5-5", "usage": {"input_tokens": 100, "output_tokens": 10},
                     "content": [{"type": "tool_use", "name": "Bash", "input": {"command": "python3 review/scripts/review.py prepare"}},
                                 {"type": "text", "text": "Packet posted."}]}},
        {**base, "type": "user", "turnOrigin": "human", "timestamp": "2026-10-20T00:05:00Z",
         "message": {"content": "[lane mba/ws/agent p-7] option B"}},
        {**base, "type": "assistant", "timestamp": "2026-10-20T00:06:00Z",
         "message": {"model": "claude-opus-5-5", "usage": {"input_tokens": 50}, "content": [{"type": "text", "text": "ok"}]}},
        {**base, "type": "user", "turnOrigin": "human", "timestamp": "2026-10-20T00:16:00Z",
         "message": {"content": f"check the record for {SECRET} before you go on"}},
        {**base, "type": "user", "turnOrigin": "human", "timestamp": "2026-10-20T00:17:00Z",
         "message": {"content": "<command-name>/plan</command-name>"}},
    ]


def write_session(logs, lines, name="s1"):
    d = os.path.join(logs, "mba", "claude-projects", "-proj")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name + ".jsonl"), "w") as fh:
        for r in lines:
            fh.write(json.dumps(r) + "\n")


class ReplyTaggingTest(unittest.TestCase):
    def test_category(self):
        cases = [("[lane homelab2026/w/a p-1] go with A", "queue answer"),
                 ("  [lane mba/x/y p-2] B", "queue answer"),
                 ("lane answer [lane mba/x/y p-2]", "substantive"),
                 ("merge it", "merge/push stamp"),
                 ("yes", "other stamp"),
                 ("status?", "status ping"),
                 ("no, use the other table", "redirect"),
                 ("merged, carry on", "merge/push stamp"),
                 ("1 yes 2 no", "other stamp"),
                 ("done", "other stamp"),
                 ("Read and follow /tmp/briefs/common.md, then execute lane-a.md", "lane brief"),
                 ("yes but first move the tenant check into the gateway, then rerun the suite on homelab", "substantive"),
                 ("why does the SG allow 5432 from the VPC", "substantive")]
        for text, want in cases:
            with self.subTest(text=text):
                self.assertEqual(sessions.category(text), want)

    def test_queue_answer_latency(self):
        with tempfile.TemporaryDirectory() as logs:
            write_session(logs, session_lines())
            out = sessions.scan(logs, ts("2026-10-19T00:00:00Z"), ts("2026-10-21T00:00:00Z"))
            t = sessions.tables(out)
        att = t["4 Attention"]["rows"]
        self.assertEqual(att["typed prompts"], [2])          # the <command-name> turn is not typed
        self.assertEqual(att["queue answers"], [1])
        self.assertEqual(att["queue answer latency median min"], [5.0])
        self.assertEqual(att["wait median min"], [10.0])     # waits 5 and 10 min; median of two = upper
        self.assertEqual(t["4 Prompt categories"]["rows"]["queue answer"], [1, 50.0])
        self.assertIn("review", t["2 Activity cost (driver)"]["rows"])
        self.assertNotIn(SECRET, json.dumps(t))

    def test_non_kalpa_and_out_of_window_skipped(self):
        with tempfile.TemporaryDirectory() as logs:
            write_session(logs, session_lines(cwd="/Users/x/Projects/pmg/pmg-docs"))
            self.assertEqual(sessions.scan(logs, None, None)["sessions"], [])
            write_session(logs, session_lines(), name="s2")
            out = sessions.scan(logs, None, ts("2026-10-19T00:00:00Z"))
        self.assertEqual(out["sessions"], [])


class DeltaTest(unittest.TestCase):
    CUR = {"t": {"cols": ["Reviews", "Share %"], "rows": {"r1": [10, 50.0], "r2": [4, None], "r9": [1, 1.0]}}}
    PREV = {"t": {"cols": ["Reviews", "Share %"], "rows": {"r1": [8, 55.5], "r2": [4, 20.0]}}}

    def test_delta(self):
        d = store.delta(self.CUR, self.PREV)["t"]
        self.assertEqual(d["r1"], [2, -5.5])
        self.assertEqual(d["r2"], [0, None])
        self.assertEqual(d["r9"], "new")

    def test_render_adds_delta_column_only_with_previous(self):
        with_d = store.render("t", self.CUR["t"], store.delta(self.CUR, self.PREV)["t"])
        self.assertIn("|  | Reviews | Δ | Share % | Δ |", with_d)
        self.assertIn("| r1 | 10 | +2 | 50.0 | -5.5 |", with_d)
        self.assertIn("| r9 | 1 | new | 1 | new |", with_d)
        self.assertNotIn("Δ", store.render("t", self.CUR["t"]))

    def test_save_previous_and_corrupt(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(store.previous(d), (None, None))
            p = store.save(d, {"window": {}, "tables": self.PREV})
            self.assertEqual(store.previous(d)[1]["tables"], self.PREV)
            with open(os.path.join(d, "99999999T999999Z.json"), "w") as fh:
                fh.write("{not json")
            path, res = store.previous(d)
            self.assertTrue(path.endswith("99999999T999999Z.json"))
            self.assertIsNone(res)
            self.assertEqual(store.previous(d, before=path)[0], p)

    def test_previous_matches_profile(self):
        a = {"window": {"class": "21d"}, "flags": {"git": True}, "tables": self.PREV}
        b = {"window": {"class": "21d"}, "flags": {"git": False}, "tables": self.CUR}
        with tempfile.TemporaryDirectory() as d:
            pa = store.save(d, a)
            store.save(d, {"window": {}, "tables": self.CUR})          # pre-profile run: matches nothing
            store.save(d, b)
            self.assertEqual(store.previous(d, match=store.profile(a)), (pa, json.loads(json.dumps(a))))
            self.assertEqual(store.previous(d, match=store.profile(b))[1]["flags"], {"git": False})
            self.assertEqual(store.previous(d, match={"flags": None, "window_class": "7d"}), (None, None))

    def test_save_never_overwrites_an_earlier_run(self):
        # two runs stamped the same instant: the second must fail, not clobber the first
        now = store.datetime(2026, 10, 27, 1, 2, 3, 456789, tzinfo=store.timezone.utc)
        with tempfile.TemporaryDirectory() as d:
            p = store.save(d, {"window": {}, "tables": self.PREV}, now=now)
            with self.assertRaises(FileExistsError):
                store.save(d, {"window": {}, "tables": self.CUR}, now=now)
            with open(p) as fh:
                self.assertEqual(json.load(fh)["tables"], self.PREV)
            self.assertEqual([f for f in os.listdir(d) if f.endswith(".tmp")], [])


class CliTest(unittest.TestCase):
    def run_cli(self, *args, env):
        return subprocess.run([sys.executable, os.path.join(HS, "scorecard.py"), *args],
                              capture_output=True, text=True, env=env, timeout=120)

    def test_run_twice_prints_delta_and_stores_aggregates_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects, logs, st = (os.path.join(tmp, n) for n in ("projects", "logs", "store"))
            shas = make_repo(projects)
            env = {**os.environ, "VERIFY_PROJECTS": projects}
            write_log(logs, "s", "1.1", unit_11(shas))
            write_session(logs, session_lines())
            args = ["run", "--since", "2026-10-05", "--until", "2026-10-25", "--logs", logs, "--store", st]
            first = self.run_cli(*args, env=env)
            self.assertEqual(first.returncode, 0, first.stderr[-800:])
            self.assertIn("No previous run", first.stdout)
            self.assertIn("### 3.1 Lineage rounds", first.stdout)
            write_log(logs, "s", "1.2", unit_12(shas))
            second = self.run_cli(*args, env=env)
            self.assertEqual(second.returncode, 0, second.stderr[-800:])
            self.assertIn("Δ against", second.stdout)
            self.assertRegex(second.stdout, r"\| r1 \| 3 \| \+1 \|")
            stored = [os.path.join(st, f) for f in os.listdir(st)]
            self.assertEqual(len(stored), 2)
            for p in stored:
                with open(p) as fh:
                    self.assertNotIn(SECRET, fh.read())
            self.assertNotIn(SECRET, second.stdout)

    def test_delta_reference_has_the_same_flags_and_window_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects, logs, st = (os.path.join(tmp, n) for n in ("projects", "logs", "store"))
            shas = make_repo(projects)
            env = {**os.environ, "VERIFY_PROJECTS": projects}
            write_log(logs, "s", "1.1", unit_11(shas))
            win = ["run", "--since", "2026-10-05", "--until", "2026-10-25", "--logs", logs, "--store", st, "--no-sessions"]
            first = self.run_cli(*win, env=env)
            self.assertEqual(first.returncode, 0, first.stderr[-800:])
            ref = sorted(os.listdir(st))[0]
            # a --no-git run and a long-window run are stored, but are never a default run's reference
            self.assertEqual(self.run_cli(*win, "--no-git", env=env).returncode, 0)
            self.assertIn("No previous run with 298d, git off sessions off",
                          self.run_cli(*win, "--no-git", "--no-save", "--since", "2026-01-01", env=env).stdout)
            again = self.run_cli(*win, "--no-save", env=env)
            self.assertIn(f"Δ against {ref} (window 2026-10-05 00:00 → 2026-10-25 23:59, 21d, git on sessions off)", again.stdout)
            with open(os.path.join(st, ref)) as fh:
                self.assertEqual(json.load(fh)["flags"], {"git": True, "sessions": False})

    def test_bad_date_is_usage_but_an_inner_value_error_is_not(self):
        import scorecard
        with tempfile.TemporaryDirectory() as tmp, mock.patch("sys.stderr", __import__("io").StringIO()) as err:
            self.assertEqual(scorecard.main(["run", "--since", "2026-13-45", "--logs", tmp]), 2)
            self.assertIn("[USAGE]", err.getvalue())
            # a decode error inside a run is a failure, never reported as a bad flag
            with mock.patch.object(scorecard.review_loop, "load_logs",
                                   side_effect=UnicodeDecodeError("utf-8", b"\xe2", 0, 1, "x")):
                with self.assertRaises(UnicodeDecodeError):
                    scorecard.main(["run", "--logs", tmp])

    def test_empty_logs_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.run_cli("run", "--logs", tmp, "--store", os.path.join(tmp, "st"), env=dict(os.environ))
            self.assertEqual(r.returncode, 1)
            self.assertIn("no review logs", r.stderr)
            self.assertFalse(os.path.exists(os.path.join(tmp, "st")))


class PullTest(unittest.TestCase):
    """cmd_pull's safety claims, with platform, subprocess and HOME patched: MBA only, never
    overwrites a cache link it did not make, fails when homelab lacks a source, reads the
    destination back, and only ever reads from homelab (the host is on rsync's source side)."""

    HOST = "hl"

    def setUp(self):
        import scorecard
        self.sc = scorecard
        self.tmp = tempfile.TemporaryDirectory()
        self.home, self.logs = os.path.join(self.tmp.name, "home"), os.path.join(self.tmp.name, "logs")
        os.makedirs(os.path.join(self.home, ".claude", "projects", "-p"))
        with open(os.path.join(self.home, ".claude", "projects", "-p", "s.jsonl"), "w") as fh:
            fh.write("{}\n")
        os.makedirs(os.path.join(self.home, ".codex", "sessions"))
        os.makedirs(os.path.join(self.home, "Projects"))
        self.calls, self.probe_out, self.copy = [], ".claude/projects\n.codex/sessions\nProjects\n", True

    def tearDown(self):
        self.tmp.cleanup()

    def fake_run(self, cmd, **kw):
        self.calls.append(cmd)
        if cmd[0] == "ssh":
            return subprocess.CompletedProcess(cmd, 0, self.probe_out, "")
        src, dst = cmd[-2], cmd[-1]
        if self.copy and src.startswith(self.HOST + ":"):   # what a real pull would land
            sub = "projects/-p" if src.endswith(".claude/projects/") else "demo/plans/s/artifacts" if "Projects" in src else None
            if sub:
                os.makedirs(os.path.join(dst, sub), exist_ok=True)
                name = "s.jsonl" if "projects" in sub else "review-1.1.jsonl"
                with open(os.path.join(dst, sub, name), "w") as fh:
                    fh.write("{}\n")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def pull(self, system="Darwin"):
        a = mock.Mock(logs=self.logs, host=self.HOST)
        err = __import__("io").StringIO()
        with mock.patch.object(self.sc, "HOME", self.home), \
                mock.patch.object(self.sc.platform, "system", return_value=system), \
                mock.patch.object(self.sc.subprocess, "run", side_effect=self.fake_run), \
                mock.patch("sys.stderr", err), mock.patch("sys.stdout", __import__("io").StringIO()):
            code = self.sc.cmd_pull(a)
        return code, err.getvalue()

    def pulled(self):
        return os.path.exists(os.path.join(self.logs, self.sc.PULLED))

    def test_refuses_off_the_mba(self):
        code, err = self.pull(system="Linux")
        self.assertEqual((code, self.calls), (1, []))
        self.assertIn("MBA only", err)

    def test_refuses_a_link_pointing_elsewhere(self):
        link = os.path.join(self.logs, "mba", "claude-projects")
        os.makedirs(os.path.dirname(link))
        os.symlink(self.tmp.name, link)
        code, err = self.pull()
        self.assertEqual((code, self.calls), (1, []))
        self.assertIn("not overwritten", err)
        self.assertEqual(os.readlink(link), self.tmp.name)

    def test_refuses_a_non_symlink(self):
        os.makedirs(os.path.join(self.logs, "mba", "codex-sessions"))
        code, err = self.pull()
        self.assertEqual((code, self.calls), (1, []))
        self.assertIn("is not a symlink", err)

    def test_missing_homelab_source_fails(self):
        self.probe_out = ".codex/sessions\nProjects\n"
        code, err = self.pull()
        self.assertEqual(code, 1)
        self.assertIn("hl:~/.claude/projects missing", err)
        self.assertFalse(self.pulled())

    def test_empty_read_back_fails_without_stamp(self):
        self.copy = False
        code, err = self.pull()
        self.assertEqual(code, 1)
        self.assertIn("read back empty", err)
        self.assertFalse(self.pulled())

    def test_pull_reads_homelab_only_and_stamps(self):
        code, err = self.pull()
        self.assertEqual(code, 0, err)
        self.assertTrue(self.pulled())
        self.assertEqual(os.path.realpath(os.path.join(self.logs, "mba", "claude-projects")),
                         os.path.realpath(os.path.join(self.home, ".claude", "projects")))
        rsyncs = [c for c in self.calls if c[0] == "rsync"]
        self.assertTrue(any(c[-2].startswith("hl:") for c in rsyncs))
        for c in rsyncs:
            self.assertNotIn("--delete", c)
            self.assertNotIn(":", c[-1])                         # destination is always local
            self.assertTrue(c[-1].startswith(self.logs))
            self.assertTrue(c[-2].startswith(("hl:", self.home)), c)
        self.assertEqual([c[0] for c in self.calls if c[0] != "rsync"], ["ssh"])   # one read-only probe


if __name__ == "__main__":
    unittest.main()
