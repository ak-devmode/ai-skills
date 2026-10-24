"""Skill prose that drives plans-index.py says what the records model needs.

Approach: these are prose rules, so the regression test is a grep over the skill
bodies — each assertion names the review finding it pins (9.1-r1-NN). A rewrite that
drops the rule fails here instead of in a live graph.
"""

import os
import re
import unittest

from _helpers import REPO


def body(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def section(text, start, stop):
    """Text from the first line matching `start` up to the next line matching `stop`."""
    m = re.search(start, text, re.M)
    if not m:
        raise AssertionError(f"no section {start!r}")
    end = re.search(stop, text[m.end():], re.M)
    return text[m.start():m.end() + end.start()] if end else text[m.start():]


class IndexProse(unittest.TestCase):
    def test_local_mode_publishes_name_the_archive_index(self):
        # 9.1-r1-07: local-mode publishes named PLANS-INDEX.md but not archive/INDEX.md
        scope = body("scope/SKILL.md")
        for start in (r"^In `local` mode add `archive/INDEX\.md`",
                      r"^\*\*5\.10\.2 Publish the stubs",
                      r"\"archive/\{N\}-\{slug\}\" PLANS-INDEX\.md`"):
            self.assertIn("archive/INDEX.md", section(scope, start, r"^\s*$"), start)
        self.assertIn("archive/INDEX.md", section(body("plan/SKILL.md"), r"^8\.5b ", r"^\s*$"))

    def test_child_rows_get_a_status_before_archive(self):
        # 9.1-r1-08: move never touches child Status, so archived scopes kept Draft children
        plan = section(body("plan/SKILL.md"), r"^#+ 11\.4", r"^#+ 11\.5")
        self.assertRegex(plan, r"plans-index\.py status --num \{N\}\.\{P\}")
        cleanup = section(body("repo-cleanup/SKILL.md"), r"^3\. \*\*The index", r"^\d\. ")
        self.assertRegex(cleanup, r"plans-index\.py status --num <N>\.<P>")

    def test_no_prose_hand_edits_the_index(self):
        # 9.1-r1-15 / -16: registry "gets edited"; AGENTS.md assigned the next number itself
        self.assertNotIn("these get edited", body("repo-cleanup/SKILL.md"))
        self.assertNotIn("Assign the next whole number", body("scope/AGENTS.md"))

    def test_prd_names_the_folder_form(self):
        # 9.1-r1-14: a folder-form PRD registered as a loose root file
        self.assertIn("prd-{slug}/prd-{slug}.md\\`\"", body("prd/SKILL.md"))


if __name__ == "__main__":
    unittest.main()
