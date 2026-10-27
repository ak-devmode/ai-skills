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
                     "data-model-one-way.json"):
            self.assertIn(want, have)

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
