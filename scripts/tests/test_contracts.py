"""Contracts (templates/verify-contracts.md) and the templates generated from them.

Approach: generate each file the way a skill would — copy the template, substitute its
{{PLACEHOLDERS}} — then assert the result carries no example rows: every markdown table
has a header and separator and nothing else, and no data row from the matching filled
example appears anywhere in it (HTML comments included, since an example parked in a
comment survives copying). Separately, every contract section names its writer and
readers, and every template points back at its contract section.
"""

import json
import os
import re
import unittest

from _helpers import REPO

TEMPLATES = os.path.join(REPO, "templates")
EXAMPLES = os.path.join(TEMPLATES, "examples")
SPEC = os.path.join(TEMPLATES, "verify-contracts.md")

# template -> its filled example
PAIRS = {
    "finish-conditions.md.template": "finish-conditions.md",
    "features-README.md.template": os.path.join("features", "README.md"),
    "feature.md.template": os.path.join("features", "sign-in.md"),
    "feature-map-handoff.md.template": "feature-map-handoff.md",
}

PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")
SEPARATOR = re.compile(r"^\|(\s*:?-+:?\s*\|)+\s*$")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def generate(template_text):
    """What a skill writes: the template with every placeholder filled."""
    return PLACEHOLDER.sub(lambda m: f"generated-{m.group(1).lower()}", template_text)


def data_rows(text):
    """Example-shaped content: list items, and table rows that are neither a header
    (followed by a separator) nor a separator."""
    lines = text.splitlines()
    rows = []
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("- "):
            rows.append(s)
            continue
        if not s.startswith("|") or SEPARATOR.match(s):
            continue
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if SEPARATOR.match(nxt):
            continue  # header row
        rows.append(s)
    return rows


class TestTemplatesGenerateClean(unittest.TestCase):
    def test_pairs_exist(self):
        for tpl, ex in PAIRS.items():
            with self.subTest(template=tpl):
                self.assertTrue(os.path.isfile(os.path.join(TEMPLATES, tpl)), tpl)
                self.assertTrue(os.path.isfile(os.path.join(EXAMPLES, ex)), ex)

    def test_generated_file_has_no_data_rows(self):
        for tpl in PAIRS:
            with self.subTest(template=tpl):
                out = generate(read(os.path.join(TEMPLATES, tpl)))
                self.assertEqual(PLACEHOLDER.findall(out), [])
                self.assertEqual(data_rows(out), [],
                                 f"{tpl} generates rows — examples belong in templates/examples/")

    def test_no_example_row_leaks_into_template(self):
        for tpl, ex in PAIRS.items():
            with self.subTest(template=tpl):
                out = generate(read(os.path.join(TEMPLATES, tpl)))
                example_rows = data_rows(read(os.path.join(EXAMPLES, ex)))
                self.assertTrue(example_rows, f"example {ex} has no rows to compare against")
                for row in example_rows:
                    self.assertNotIn(row, out)

    def test_example_is_marked_as_example(self):
        for ex in PAIRS.values():
            with self.subTest(example=ex):
                self.assertIn("EXAMPLE", read(os.path.join(EXAMPLES, ex)).splitlines()[0])

    def test_template_names_its_contract_writer_and_readers(self):
        for tpl in PAIRS:
            with self.subTest(template=tpl):
                head = read(os.path.join(TEMPLATES, tpl))[:600]
                self.assertRegex(head, r"verify-contracts\.md §\d")
                self.assertIn("Writer:", head)
                self.assertRegex(head, r"Readers?:")


class TestSpec(unittest.TestCase):
    def setUp(self):
        self.spec = read(SPEC)

    def test_every_contract_section_names_writer_and_readers(self):
        # §3–§10 are contracts; §1 is the map, §2 the ladder.
        sections = re.split(r"^## (?=\d+\. )", self.spec, flags=re.M)[1:]
        numbered = {int(s.split(".", 1)[0]): s for s in sections}
        for n in range(3, 11):
            with self.subTest(section=n):
                self.assertIn(n, numbered, f"§{n} missing")
                body = numbered[n]
                self.assertRegex(body, r"\*\*Writers?:\*\*")
                self.assertRegex(body, r"\*\*Readers?:\*\*")

    def test_template_references_resolve(self):
        for ref in re.findall(r"`templates/([\w.-]+\.template)`", self.spec):
            with self.subTest(template=ref):
                self.assertTrue(os.path.isfile(os.path.join(TEMPLATES, ref)), ref)


class TestJsonlExamples(unittest.TestCase):
    def _records(self, name):
        with open(os.path.join(EXAMPLES, name), encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def test_verify_log_example(self):
        recs = self._records("verify-log.jsonl")
        self.assertEqual({r["schema"] for r in recs}, {"verify/1"})
        self.assertEqual([r["run_state"] for r in recs][-1], "final")
        final = recs[-1]
        pending = {r["check_id"] for r in recs if r["run_state"] == "pending"}
        self.assertEqual(set(final["results"]), pending)

    def test_review_log_example_every_finding_dispositioned(self):
        recs = self._records("review-log.jsonl")
        findings = {r["finding_id"] for r in recs if r["record"] == "finding"}
        covered = {r["finding_id"] for r in recs if r["record"] == "disposition"}
        self.assertTrue(findings)
        self.assertEqual(findings, covered)
        for r in recs:
            if r["record"] == "disposition":
                self.assertTrue(r["sha"] if r["disposition"] == "fixed" else r["reason"])


if __name__ == "__main__":
    unittest.main()
