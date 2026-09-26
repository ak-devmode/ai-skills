import unittest

from notes import store
from notes.export import export_text


class TestExport(unittest.TestCase):
    def test_export_joins_notes(self):
        store.add("first")
        self.assertIn("first", export_text().splitlines())
