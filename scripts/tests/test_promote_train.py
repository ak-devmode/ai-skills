"""promote-train.py — a failed check gets one re-run before the train stops (WellMed 231, 2026-11-20).
Approach: load the script as a module and fake `sh` and `gh_json`, so wait_checks runs with no network.
"""
import unittest
from unittest import mock

from _helpers import load

LINT = "https://github.com/o/r/actions/runs/111/job/9"


class TestFailedRuns(unittest.TestCase):
    def test_ids_from_failed_rows_only(self):
        pt = load("promote-train.py")
        rows = [{"name": "Lint", "state": "FAILURE", "link": LINT},
                {"name": "Lint2", "state": "FAILURE", "link": "https://github.com/o/r/actions/runs/111/job/10"},
                {"name": "Test", "state": "SUCCESS", "link": "https://github.com/o/r/actions/runs/222/job/1"},
                {"name": "ext", "state": "FAILURE", "link": "https://example.com/status"}]
        self.assertEqual(pt.failed_runs(rows), ["111"])


class TestWaitChecks(unittest.TestCase):
    def run_with(self, results):
        pt = load("promote-train.py")
        calls = []
        with mock.patch.object(pt, "sh", side_effect=lambda c, **k: calls.append(c) or (0, "", "")), \
                mock.patch.object(pt, "gh_json", side_effect=results), mock.patch.object(pt.time, "sleep"):
            bad = pt.wait_checks("o", "r", 5)
        return bad, [c for c in calls if c[:3] == ["gh", "run", "rerun"]]

    def test_flaky_check_rerun_then_green(self):
        bad, reruns = self.run_with([[{"name": "Lint", "state": "FAILURE", "link": LINT}],
                                     [{"name": "Lint", "state": "SUCCESS", "link": LINT}]])
        self.assertEqual(bad, [])
        self.assertEqual(len(reruns), 1)
        self.assertEqual(reruns[0][3], "111")

    def test_stops_after_one_rerun(self):
        red = [{"name": "Lint", "state": "FAILURE", "link": LINT}]
        bad, reruns = self.run_with([red, red])
        self.assertEqual(bad, ["Lint"])
        self.assertEqual(len(reruns), 1)


class TestWaitCD(unittest.TestCase):
    """A dropped `gh run watch` is not a failed deploy: the run's own conclusion decides (WellMed 231.5)."""

    def run_with(self, watch_rc, conclusion):
        pt = load("promote-train.py")
        runs = [{"databaseId": 7, "workflowName": "CD", "headSha": "abc"}]
        view = {"status": "completed", "conclusion": conclusion}
        with mock.patch.object(pt, "sh", return_value=(watch_rc, "", "")), \
                mock.patch.object(pt, "gh_json", side_effect=lambda a: runs if a[1] == "list" else view), \
                mock.patch.object(pt.time, "sleep"):
            return pt.wait_cd("o", "r", "abc")

    def test_watch_dropped_but_run_succeeded(self):
        self.assertEqual(self.run_with(1, "success"), (7, True))

    def test_watch_failed_and_run_failed(self):
        self.assertEqual(self.run_with(1, "failure"), (7, False))

    def test_watch_ok(self):
        self.assertEqual(self.run_with(0, "success"), (7, True))


if __name__ == "__main__":
    unittest.main()
