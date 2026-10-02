"""The verifier's own fixtures: /verify must catch every planted defect and pass the control.

Approach: two tiers. The deterministic tier always runs — build `bad`, `clean` and each
`repaired-<defect>` variant of the notes fixture (verify/scripts/fixture.py), run the real
runner and gate, and check each script-caught defect blocks by name and clears when
repaired. It also proves the two ways a judge could fake a green suite don't work: an
always-failing judge fails the control, and a missing judge fails `demo.py --check`. The
judge tier (a live codex /verify on bad + clean, and the judge-caught repaired copies)
costs real model calls, so it runs only with VERIFY_EVAL=1.
"""

import json
import os
import sys
import tempfile
import unittest

from _helpers import REPO, run

sys.path.insert(0, os.path.join(REPO, "verify", "scripts"))
import fixture  # noqa: E402

DETERMINISTIC = {"invented-env": "names-resolve", "under-rung": "export-runs",
                 "rejection-no-reason": "9.9-r1-02", "dropped-finding": "9.9-r1-03"}
JUDGE_CAUGHT = {"over-build": "no-overbuild", "missing-evidence": "changelog-entry"}


# A fake codex whose answers are well formed but are not catches. FAKE_JUDGE=inconclusive
# (default): inconclusive on the bad fixture's judge rows, plus an over-build finding on no
# check. FAKE_JUDGE=split: fails both rows, but the over-build lens and the no-overbuild
# finding are two unrelated findings. The control passes either way.
INCONCLUSIVE_CODEX = r'''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
if a == ["--version"]:
    print("codex-cli 9.9.9"); sys.exit(0)
sys.stderr.write("--------\nmodel: gpt-fake-1\n--------\n")
out = a[a.index("-o") + 1] if "-o" in a else None
cd = a[a.index("-C") + 1] if "-C" in a else ""
ids = ["names-resolve", "tests-pass", "export-runs", "no-overbuild", "changelog-entry"]
bad = "/bad/" in cd + "/"
split = os.environ.get("FAKE_JUDGE") == "split"
miss = "fail" if split else "inconclusive"
stray = [{"check_id": "unowned", "lens": "over-build", "severity": "low", "where": "x:1", "text": "maybe"}]
if split:
    stray += [{"check_id": c, "lens": "evidence", "severity": "low", "where": "y:1", "text": "generic"}
              for c in ("no-overbuild", "changelog-entry")]
doc = {"verdicts": [{"check_id": c, "rung_reached": 2 if c in ("no-overbuild", "changelog-entry") else 4,
                     "verdict": miss if bad and c in ("no-overbuild", "changelog-entry") else "pass",
                     "reason": "fake"} for c in ids],
       "findings": stray if bad else [],
       "lever_candidates": [], "feature_map": "n/a"}
if out:
    with open(out, "w") as fh:
        json.dump(doc if cd else {"verdicts": []}, fh)
print("pong")
'''


def gate_run(info, judge_items=None, judge_line="none not configured"):
    """Runner → (judged) → finalize → gate on a built fixture; returns (blocked ids, gate json, exit)."""
    env = dict(os.environ, VERIFY_PROJECTS=info["projects"])
    sc, unit = info["scope"], info["unit"]
    table, log = os.path.join(sc, "finish-conditions.md"), os.path.join(sc, "artifacts", f"verify-{unit}.jsonl")
    p = run("verify-run.py", "run", "--table", table, "--log", log, "--owner", unit, env=env)
    rid = p.stdout.split("run_id: ")[1].split()[0]
    if judge_items is not None:
        path = os.path.join(sc, "judge.json")
        with open(path, "w") as fh:
            json.dump(judge_items, fh)
        run("verify-run.py", "judged", "--log", log, "--run-id", rid, "--judge", judge_line, "--input", path, env=env)
        run("verify-run.py", "finalize", "--log", log, "--run-id", rid, env=env)
    else:
        run("verify-run.py", "finalize", "--log", log, "--run-id", rid, "--judge", judge_line, env=env)
    g = run("verdict-gate.py", "--scope", sc, "--unit", unit, "--blocking", "--json", env=env)
    doc = json.loads(g.stdout)
    # a judge row nobody judged is NOT-JUDGED, not a block — but it still never passes (plan 7.1-12)
    return {b["id"] for b in doc["blocks"]} | set(doc.get("not_judged", [])), doc, g.returncode


def gate_blocks(*args, **kw):
    return gate_run(*args, **kw)[0]


def verdicts(verdict):
    return [{"check_id": c, "verdict": verdict, "rung_reached": 4 if c in ("names-resolve", "tests-pass", "export-runs")
             else 2, "reason": f"fake judge: {verdict}"}
            for c in ("names-resolve", "tests-pass", "export-runs", "no-overbuild", "changelog-entry")]


class TestDeterministicTier(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, variant):
        return fixture.build(os.path.join(self.tmp.name, variant), variant)

    def test_bad_blocks_every_script_caught_defect_by_name(self):
        blocked = gate_blocks(self.build("bad"))
        for defect, cid in DETERMINISTIC.items():
            with self.subTest(defect=defect):
                self.assertIn(cid, blocked)

    def test_clean_control_has_no_script_caught_block(self):
        blocked = gate_blocks(self.build("clean"))
        self.assertEqual(blocked & set(DETERMINISTIC.values()), set())

    def test_each_repaired_copy_clears_exactly_its_defect(self):
        for defect, cid in DETERMINISTIC.items():
            with self.subTest(repaired=defect):
                blocked = gate_blocks(self.build(f"repaired-{defect}"))
                self.assertNotIn(cid, blocked)
                for other, ocid in DETERMINISTIC.items():
                    if other != defect:
                        self.assertIn(ocid, blocked, f"repairing {defect} also cleared {other}")

    def test_judge_none_cannot_pass_the_control(self):
        blocked, doc, code = gate_run(self.build("clean"))
        self.assertEqual(blocked, set(JUDGE_CAUGHT.values()))  # judge rows stay inconclusive
        # reported as not judged rather than blocked, and still refused in blocking mode
        self.assertEqual((doc["verdict"], set(doc["not_judged"]), doc["blocks"], code),
                         ("not-judged", set(JUDGE_CAUGHT.values()), [], 1))

    def test_always_failing_judge_fails_the_control(self):
        blocked = gate_blocks(self.build("clean"), verdicts("fail"), "codex fake-always-fail")
        self.assertTrue(blocked, "a judge that fails everything must not produce a passing control")

    def test_agreeing_judge_passes_the_control(self):
        self.assertEqual(gate_blocks(self.build("clean"), verdicts("pass"), "codex fake"), set())

    def test_demo_check_fails_without_a_judge(self):
        env = dict(os.environ, VERIFY_CODEX_BIN=os.path.join(self.tmp.name, "no-codex"))
        p = run("verify/scripts/demo.py", "--check", "--keep", os.path.join(self.tmp.name, "demo"), env=env,
                timeout=300)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("No judge ran (none codex not installed)", p.stdout)
        self.assertIn("EXPECTATIONS NOT MET", p.stdout)

    def test_demo_check_fails_on_an_inconclusive_judge(self):
        # 5.2-r1-09: a codex judge that answers inconclusive on the bad fixture's judge rows
        # (and passes the control) blocks them — but that is not a catch, so --check fails.
        fake = os.path.join(self.tmp.name, "codex")
        with open(fake, "w") as fh:
            fh.write(INCONCLUSIVE_CODEX)
        os.chmod(fake, 0o755)
        env = dict(os.environ, VERIFY_CODEX_BIN=fake, VERIFY_CODEX_MODEL="gpt-fake-1")
        p = run("verify/scripts/demo.py", "--check", "--keep", os.path.join(self.tmp.name, "demo"), env=env,
                timeout=300)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("judge did not fail it with a finding", p.stdout)
        self.assertIn("EXPECTATIONS NOT MET", p.stdout)
        # 5.2-r2-02: failing verdicts whose over-build lens and no-overbuild finding are
        # two unrelated findings do not explain the planted registry.
        split = run("verify/scripts/demo.py", "--check", "--keep", os.path.join(self.tmp.name, "demo2"),
                    env=dict(env, FAKE_JUDGE="split"), timeout=300)
        self.assertEqual(split.returncode, 1, split.stdout + split.stderr)
        self.assertIn("names the planted registry", split.stdout)


@unittest.skipUnless(os.environ.get("VERIFY_EVAL") == "1", "judge tier: set VERIFY_EVAL=1 (live codex calls)")
class TestJudgeTier(unittest.TestCase):
    def test_live_demo_catches_every_planted_defect(self):
        p = run("verify/scripts/demo.py", "--check", timeout=1500)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_judge_caught_repaired_copies_pass_their_row(self):
        sys.path.insert(0, os.path.join(REPO, "verify", "scripts"))
        import demo  # noqa: E402
        probe = run("codex-exec.py", "probe").stdout.strip().splitlines()[-1]
        self.assertTrue(probe.startswith("codex "), probe)
        with tempfile.TemporaryDirectory() as tmp:
            for defect, cid in JUDGE_CAUGHT.items():
                with self.subTest(repaired=defect):
                    info = fixture.build(os.path.join(tmp, defect), f"repaired-{defect}")
                    g, used, _ = demo.verify(info, probe, 600)
                    self.assertTrue(used.startswith("codex "), used)
                    self.assertNotIn(cid, {b["id"] for b in g["blocks"]})


if __name__ == "__main__":
    unittest.main()
