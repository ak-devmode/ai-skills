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

    def test_invalid_fixtures_refused(self):
        for name, doc in fixtures("invalid"):
            with self.subTest(name):
                self.assertTrue(sc.validate(doc, "event" if name.startswith("event-") else None))

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
