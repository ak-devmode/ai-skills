import unittest

from notes import store


class TestStore(unittest.TestCase):
    def test_add_returns_count(self):
        n = store.add("x")
        self.assertEqual(store.all_notes()[-1], "x")
        self.assertEqual(n, len(store.all_notes()))
