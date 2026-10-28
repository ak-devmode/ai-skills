"""Packet schema vs fixtures (10.1 task 1.1).

Approach: every file under fixtures/packets/valid validates, every file under
invalid is refused (subTest per file so a regression names the fixture). Events
validate against $defs/event. Run through scripts/schema_check.py's library.
"""
import importlib.util
import json
import os
import unittest

from _helpers import script

spec = importlib.util.spec_from_file_location("schema_check", script("schema_check.py"))
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)
FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "packets")


def fixtures(kind):
    d = os.path.join(FIX, kind)
    for name in sorted(os.listdir(d)):
        with open(os.path.join(d, name)) as f:
            yield name, json.load(f)


class TestPacketSchema(unittest.TestCase):
    def test_valid_fixtures_pass(self):
        for name, doc in fixtures("valid"):
            with self.subTest(name):
                self.assertEqual(sc.validate(doc, "event" if name.startswith("event-") else None), [])

    # each invalid fixture must fail for ITS reason, not a typo elsewhere (10.1-r1-10)
    WHY = {
        "bad-door.json": "/door: must be one of",
        "bad-lane-tag.json": "/reply: does not match",
        "data-model-bad-payload.json": "missing required 'tables'",
        "event-closed-no-packet.json": "missing required 'packet_id'",
        "event-stale-no-packet.json": "missing required 'packet_id'",
        "generic-bad-payload.json": "missing required 'body'",
        "id-trailing-newline.json": "/id: does not match",
        "missing-agent.json": "missing required 'agent'",
        "missing-door.json": "missing required 'door'",
        "missing-machine.json": "missing required 'machine'",
        "missing-workspace.json": "missing required 'workspace'",
        "no-recommended.json": "0 items match 'contains'",
        "slash-in-agent.json": "/agent: does not match",
        "ui-bad-payload.json": "missing required 'callouts'",
        "ui-non-png-image.json": "/payload/new/image: does not match",
        "ui-path-image.json": "/payload/old/image: does not match",
        "two-recommended.json": "2 items match 'contains'",
        # v2 caps (10.4 cards lane): each over-cap field is refused on its own
        "v1-with-context.json": "/context: must be one of []",
        "v2-body-in-payload.json": "/payload: unexpected property 'body'",
        "v2-context-missing.json": "missing required 'context'",
        "v2-context-too-long.json": "/context: does not match",
        "v2-evidence-too-long.json": "/evidence: does not match",
        "v2-label-says-recommended.json": "/options/0/label: does not match",
        "v2-label-too-long.json": "/options/0/label: does not match",
        "v2-option-detail.json": "/options/1: unexpected property 'detail'",
        "v2-title-too-long.json": "/title: does not match",
        "v2-why-missing.json": "/options/1: missing required 'why'",
        "v2-why-too-long.json": "/options/1/why: does not match",
    }

    def test_invalid_fixtures_refused_for_the_right_reason(self):
        names = {n for n, _ in fixtures("invalid")}
        self.assertEqual(names, set(self.WHY), "every invalid fixture needs an expected error")
        for name, doc in fixtures("invalid"):
            with self.subTest(name):
                errs = sc.validate(doc, "event" if name.startswith("event-") else None)
                self.assertTrue(any(self.WHY[name] in e for e in errs), errs)

    def test_valid_fixtures_cover_each_packet_type_and_event_kind(self):
        have = {n for n, _ in fixtures("valid")}
        for want in ("ui-two-way.json", "event-merged.json", "event-stale.json",
                     "event-done.json", "event-touch.json", "generic-two-way.json",
                     "data-model-one-way.json", "v2-generic-one-way.json", "v2-generic-info.json"):
            self.assertIn(want, have)

    def test_v2_caps_are_exact(self):
        # each v2 cap passes at N chars and fails at N+1 (an off-by-one would let a long card through)
        base = next(d for n, d in fixtures("valid") if n == "v2-generic-one-way.json")
        cases = [("title", 100, lambda d, s: d.update(title=s)),
                 ("context", 400, lambda d, s: d.update(context=s)),
                 ("evidence", 4000, lambda d, s: d.update(evidence=s)),
                 ("label", 60, lambda d, s: d["options"][0].update(label=s)),
                 ("why", 140, lambda d, s: d["options"][0].update(why=s))]
        for field, cap, put in cases:
            for n, ok in ((cap, True), (cap + 1, False)):
                with self.subTest(field=field, n=n):
                    doc = json.loads(json.dumps(base))
                    put(doc, "x" * n)
                    self.assertEqual(sc.validate(doc) == [], ok, sc.validate(doc)[:1])

    def test_v2_info_packet_needs_no_options(self):
        doc = next(d for n, d in fixtures("valid") if n == "v2-generic-info.json")
        self.assertEqual(doc["options"], [])
        self.assertEqual(sc.validate(doc), [])

    def test_ui_image_cap_is_exact(self):
        # 2,000,000 base64 chars (1.5 MB of PNG) passes; one more fails. Built in-test: no 2 MB fixture.
        doc = dict(next(d for n, d in fixtures("valid") if n == "ui-two-way.json"))
        doc["payload"] = dict(doc["payload"])
        pre = "data:image/png;base64,"
        for n, ok in ((2000000, True), (2000004, False)):
            doc["payload"]["old"] = {"label": "x", "image": pre + "A" * n}
            errs = sc.validate(doc)
            self.assertEqual(errs == [], ok, errs[:1])
            if not ok:
                self.assertTrue(any("/payload/old/image: does not match" in e for e in errs), errs)

    def test_trailing_newline_does_not_satisfy_end_anchor(self):
        # ECMA-262 `$` rejects 'x\n'; Python's would accept it (10.1-r1-14)
        schema = {"type": "string", "pattern": "^[a-z]+$"}
        self.assertEqual(sc.validate("abc", schema=schema), [])
        self.assertTrue(sc.validate("abc\n", schema=schema))

    def test_schema_version_must_be_an_integer_discriminator(self):
        # 10.4-r14-03: true matched enum [1, 2] by Python membership but neither branch's const,
        # so a packet skipped option, payload and cap checks. Every non-integer version is refused.
        base = next(d for n, d in fixtures("valid") if n == "v2-generic-one-way.json")
        for bad in (True, False, "2", 2.0, 1.0):
            with self.subTest(version=bad):
                doc = json.loads(json.dumps(base))
                doc.update(schema_version=bad, options=[{"recommended": True}],
                           payload={"anything": 1}, context="x" * 401)
                errs = sc.validate(doc)
                self.assertTrue(any(e.startswith("/schema_version:") for e in errs), errs)

    def test_enum_and_const_distinguish_booleans_from_numbers(self):
        for value, schema in ((True, {"enum": [1, 2]}), (1, {"enum": [True]}),
                              (True, {"const": 1}), (0, {"const": False})):
            with self.subTest(value=value, schema=schema):
                self.assertTrue(sc.validate(value, schema=schema))
        self.assertEqual(sc.validate(2, schema={"enum": [1, 2]}), [])

    def test_recommended_marker_refused_in_any_case_on_any_option(self):
        # 10.4-r14-05 / r15-03: the schema matched only (recommended)/(Recommended)
        base = next(d for n, d in fixtures("valid") if n == "v2-generic-one-way.json")
        for marker in ("(RECOMMENDED)", "(ReCoMmEnDeD)", "(recommended)", "(Recommended)"):
            for i in range(len(base["options"])):
                with self.subTest(marker=marker, recommended=base["options"][i]["recommended"]):
                    doc = json.loads(json.dumps(base))
                    doc["options"][i]["label"] = f"Alt {marker}"
                    errs = sc.validate(doc)
                    self.assertTrue(any(f"/options/{i}/label: does not match" in e for e in errs), errs)

    def test_no_schema_pattern_ends_in_a_bare_dollar(self):
        # 10.4-r15-02: schema_check maps a final `$` to \\Z, but the queue's jsonschema runs Python re,
        # where `$` matches before a final newline — a cap+1 newline passed there. (?![\\s\\S]) is
        # end-of-input in Python re and ECMA-262 alike.
        def patterns(node):
            if isinstance(node, dict):
                if isinstance(node.get("pattern"), str):
                    yield node["pattern"]
                for v in node.values():
                    yield from patterns(v)
            elif isinstance(node, list):
                for v in node:
                    yield from patterns(v)
        pats = list(patterns(sc.load_schema()))
        self.assertGreater(len(pats), 5)
        for pat in pats:
            with self.subTest(pat):
                body = pat[:-1]
                self.assertFalse(pat.endswith("$") and (len(body) - len(body.rstrip("\\"))) % 2 == 0)

    def test_cap_plus_newline_and_embedded_newline_refused(self):
        base = next(d for n, d in fixtures("valid") if n == "v2-generic-one-way.json")
        cases = [("title", lambda d, s: d.update(title=s), 100, True),
                 ("context", lambda d, s: d.update(context=s), 400, False),
                 ("evidence", lambda d, s: d.update(evidence=s), 4000, False),
                 ("label", lambda d, s: d["options"][0].update(label=s), 60, True),
                 ("why", lambda d, s: d["options"][0].update(why=s), 140, False),
                 ("head_sha", lambda d, s: d.update(head_sha=s), 7, True),
                 ("machine", lambda d, s: d.update(machine=s), 5, True)]
        for field, put, cap, one_line in cases:
            values = [("x" if field != "head_sha" else "a") * cap + "\n"]
            if one_line:
                values.append("ab\ncd" if field != "head_sha" else "abcdef1\nabcdef1")
            for v in values:
                with self.subTest(field=field, value=v[-6:]):
                    doc = json.loads(json.dumps(base))
                    put(doc, v)
                    self.assertTrue(sc.validate(doc), field)

    def test_additional_properties_other_than_false_fails_closed(self):
        for val in (True, {"type": "string"}):
            with self.subTest(val=val), self.assertRaises(sc.SchemaError):
                sc.validate({}, schema={"type": "object", "additionalProperties": val})

    def test_missing_identity_or_door_names_the_field(self):
        for field in ("machine", "workspace", "agent", "door"):
            with self.subTest(field):
                errs = sc.validate(json.load(open(os.path.join(FIX, "invalid", f"missing-{field}.json"))))
                self.assertTrue(any(f"'{field}'" in e for e in errs), errs)

    def test_unknown_schema_keyword_fails_closed(self):
        with self.assertRaises(sc.SchemaError):
            sc.validate({}, schema={"patternProperties": {}})


if __name__ == "__main__":
    unittest.main()
