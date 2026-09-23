#!/usr/bin/env python3
"""lint-skill.py — the accretion linter. The SKILL.md quality bar is enforced
here, not eyeballed.

Approach: parse a SKILL.md into (frontmatter, body, headings), then run a fixed
set of checks. Each check emits findings in one shape — `expected · found ·
where · next` — so a finding is actionable without re-reading the skill. ISSUES
fail the run (exit 1); NOTES never do.

This exists because CLAUDE.md §6 said "No linter currently" while the skills
accreted past the size a model can obey — the diagnosis in
`plans/skills-relook/AUDIT.md`. Eyeballing does not hold a line across eight
skills and years of incident lore; a script does. Same reasoning `/closeout`
§14.0 applies to its archive gate and §3.6.1 applies to the other scripts here:
prose (and eyeballing) cannot enforce itself.

Two tiers, and the split is the whole design:

  ISSUE  — deterministic, zero false positives. A real, mechanical defect.
           Fails the run. (oversize, duplicate section numbers, malformed
           frontmatter, dead renamed-skill references.)
  NOTE   — heuristic. Surfaces a site worth a human's eye without claiming a
           defect. Never fails the run.

The tier split is not timidity; it is the load-bearing decision. `plans-index.py`
and `scripts/README.md` both state it: "A validator that cries wolf is a
validator that gets ignored, which is the same failure as a rule nobody obeys."
So the fuzzy checks (determinism-as-prose, live-contradiction sites) are NOTES,
never ISSUES. High-confidence *semantic* contradiction detection — the AUDIT §5.3
class where "never halt" survives beside "halt at Step 1" — needs an LLM/eval
pass and is deferred (scope §2.1, second-sighting rule). What ships here is the
deterministic spine plus conservative NOTE-tier signals that point at where such
defects hide, not a guesser that invents them.

Maps AUDIT.md §1 defect classes:
  §1.1 dilution/oversize            -> oversize            (ISSUE)
  §1.2 determinism-written-as-prose -> determinism-as-prose (NOTE)
  §1.3 live contradictions          -> supersession-site   (NOTE)
plus AUDIT §5.5 (duplicate section numbers) and §5.6 (dead skill-name refs).

Commands / contract:

    lint-skill.py <path>...            one or more SKILL.md files, or dirs
                                       containing SKILL.md (a bare dir is fine).
      --max-body-lines N               oversize threshold (default 250; AUDIT
                                       §6.4 target, ready-to-clear=176 is the model).
      --json                           machine-readable report to stdout.
      --notes                          include NOTES in text output (default:
                                       shown; --no-notes to suppress).
      --no-notes                       ISSUES only in text output.
      --quiet                          print nothing; rely on exit code (CI).

      exit: 0 no ISSUES (NOTES allowed) · 1 ISSUES found · 2 usage/parse error

Stdlib only. Reads files; never writes. A green run is a run with no ISSUES —
NOTES are advisory and do not change the exit code.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Tunables. Named, not buried, so a justified change is visible in a diff.
# ---------------------------------------------------------------------------

DEFAULT_MAX_BODY_LINES = 250  # AUDIT §6.4: "SKILL.md judgment, gates, run order. <250 lines."

# Skills renamed in the repo's history whose old names still leak into prose
# (AUDIT §5.6). A dead reference points a teammate's grep at a skill that does
# not exist. Extend as renames happen — this is the one factual list the linter
# carries. Value is the current name to point `next` at.
RENAMED_SKILLS = {
    "task-runner": "/plan",
}

# NOTE-tier signals. Filesystem-MUTATION verbs in a fenced shell block are the
# determinism-as-prose smell (AUDIT §1.2): a deterministic edit an LLM is being
# asked to perform by hand instead of a script calling it. Read-only/orchestration
# commands (grep, ls, herdr, git status) are deliberately NOT here — flagging them
# is exactly the cry-wolf failure this linter is built to avoid.
MUTATION_VERB_RE = re.compile(
    r"(?<![\w/-])(mv|rm|mkdir|cp|sed\s+-i|touch|rmdir)(?![\w-])"
)

# Supersession markers (AUDIT §1.3): where a "this is no longer true" note was
# added but the superseded text may still be living beside it. A site to review,
# not a defect on its own. Case-sensitive on REMOVED — the repo's emphatic
# supersession form ("/freeze is REMOVED") — so a benign lowercase "worktree
# removed" does not dilute the signal (found via dogfood 2026-09-23).
SUPERSESSION_RE = re.compile(
    r"\bREMOVED\b|\b[Ss]uperseded\b|\b[Dd]eprecated\b|\bno longer\b"
    r"|\breplaced by\b|\b[Oo]bsolete\b"
)

HEADING_RE = re.compile(r"^(#{2,6})\s+(.*)$")
# Leading section token on a heading. Captures the FULL dotted/lettered label so
# sub-sections stay distinct: "5" vs "5.A" vs "5.1", and "3.1a"/"8.7a" (glued
# letter) and "14.3" all keep their identity. A too-greedy `\d+(?:\.\d+)*` would
# collapse "5.A"→"5" and cry wolf on lettered subsections (found via dogfood
# against ready-to-clear, 2026-09-23). A trailing "." (as in "5. The Checks") is
# not alnum, so the token stops at "5" — parent and children never collide.
SECTION_NUM_RE = re.compile(r"^\s*(\d+(?:\.[0-9A-Za-z]+)*)")


# ---------------------------------------------------------------------------
# Finding model
# ---------------------------------------------------------------------------


class Finding:
    """One lint result in the `expected · found · where · next` shape."""

    def __init__(self, tier, check, expected, found, where, nxt):
        self.tier = tier  # "ISSUE" | "NOTE"
        self.check = check
        self.expected = expected
        self.found = found
        self.where = where
        self.next = nxt

    def as_dict(self):
        return {
            "tier": self.tier,
            "check": self.check,
            "expected": self.expected,
            "found": self.found,
            "where": self.where,
            "next": self.next,
        }

    def as_text(self):
        return (
            f"  [{self.tier}] {self.check}\n"
            f"      expected · {self.expected}\n"
            f"      found    · {self.found}\n"
            f"      where    · {self.where}\n"
            f"      next     · {self.next}"
        )


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def split_frontmatter(text):
    """Return (frontmatter_lines, body_lines, body_start_lineno).

    Frontmatter is a leading `---` … `---` block. body_start_lineno is 1-indexed
    (the line number in the file where the body's first line sits), so `where`
    references point at real file lines. No frontmatter -> ([], all-lines, 1).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], lines, 1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], lines[i + 1 :], i + 2
    # Opened but never closed — malformed; treat the whole thing as body so the
    # frontmatter check can report the missing close.
    return lines[1:], [], 2


def parse_frontmatter_keys(fm_lines):
    """Light, deliberately-not-YAML parse. Returns (keys_set, allowed_tools_ok,
    name_value). Only enough structure to check well-formedness — no dependency
    on a YAML lib (there is none in stdlib)."""
    keys = set()
    name_value = None
    allowed_tools_ok = None  # None = key absent; True/False = present + (mal)formed
    i = 0
    n = len(fm_lines)
    while i < n:
        line = fm_lines[i]
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        keys.add(key)
        if key == "name" and val:
            name_value = val
        if key == "allowed-tools":
            # Valid either inline (`allowed-tools: [Bash, Read]`) or as a block
            # list on following `  - ` lines.
            if val.startswith("[") and val.endswith("]"):
                allowed_tools_ok = bool(val.strip("[]").strip())
            elif val == "":
                j = i + 1
                items = 0
                while j < n and (fm_lines[j].startswith(" ") or fm_lines[j].startswith("\t")):
                    if re.match(r"^\s*-\s+\S", fm_lines[j]):
                        items += 1
                    elif fm_lines[j].strip() == "":
                        pass
                    else:
                        break
                    j += 1
                allowed_tools_ok = items > 0
            else:
                # A scalar value for a list key — malformed.
                allowed_tools_ok = False
        i += 1
    return keys, allowed_tools_ok, name_value


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_frontmatter(fm_lines, had_frontmatter, skill_dirname, findings):
    if not had_frontmatter:
        findings.append(Finding(
            "ISSUE", "frontmatter",
            "a `---` frontmatter block with name + description",
            "no frontmatter block (or it never closes)",
            "top of file",
            "add `---`-delimited frontmatter with `name:` and `description:`",
        ))
        return

    keys, allowed_tools_ok, name_value = parse_frontmatter_keys(fm_lines)

    for required in ("name", "description"):
        if required not in keys:
            findings.append(Finding(
                "ISSUE", "frontmatter",
                f"frontmatter key `{required}:`",
                f"`{required}:` missing",
                "frontmatter",
                f"add `{required}:` — Claude Code needs it to register/route the skill",
            ))

    if allowed_tools_ok is False:
        findings.append(Finding(
            "ISSUE", "frontmatter",
            "`allowed-tools:` as a non-empty list (block `- ` items or inline [..])",
            "`allowed-tools:` present but empty or malformed",
            "frontmatter",
            "make it a list of tool names, or remove the key if the skill needs none",
        ))

    if name_value and skill_dirname and name_value != skill_dirname:
        findings.append(Finding(
            "ISSUE", "frontmatter",
            f"`name:` matches the skill directory (`{skill_dirname}`)",
            f"`name: {name_value}`",
            "frontmatter",
            f"rename so `name:` == dir; Claude Code registers by directory, a mismatch mis-routes",
        ))


def check_oversize(body_lines, max_body_lines, findings):
    n = len(body_lines)
    if n > max_body_lines:
        findings.append(Finding(
            "ISSUE", "oversize",
            f"body <= {max_body_lines} lines (AUDIT §6.4; ready-to-clear=176 is the model)",
            f"{n} body lines ({n - max_body_lines} over)",
            "whole SKILL.md body",
            "move institutional facts/postmortems to references/, templates to templates/, "
            "deterministic steps to scripts/ (AUDIT §6.4 progressive disclosure)",
        ))


def check_duplicate_section_numbers(body_lines, body_start, findings):
    seen = {}  # number -> list of (lineno, heading_text)
    for idx, line in enumerate(body_lines):
        m = HEADING_RE.match(line)
        if not m:
            continue
        num_m = SECTION_NUM_RE.match(m.group(2))
        if not num_m:
            continue
        num = num_m.group(1)
        seen.setdefault(num, []).append((body_start + idx, m.group(2).strip()))
    for num, occurrences in sorted(seen.items()):
        if len(occurrences) > 1:
            locs = ", ".join(f"L{ln} “{txt}”" for ln, txt in occurrences)
            findings.append(Finding(
                "ISSUE", "duplicate-section-number",
                f"section number {num} used once (markdown-style §3.3.2)",
                f"{len(occurrences)} headings share {num}",
                locs,
                "renumber the duplicates; run the numbering audit across the body",
            ))


def check_stale_skill_names(body_lines, body_start, findings):
    for old, new in RENAMED_SKILLS.items():
        hits = []
        pat = re.compile(r"(?<![\w/-])" + re.escape(old) + r"(?![\w-])")
        for idx, line in enumerate(body_lines):
            if pat.search(line):
                hits.append(body_start + idx)
        if hits:
            where = ", ".join(f"L{ln}" for ln in hits[:8]) + (" …" if len(hits) > 8 else "")
            findings.append(Finding(
                "ISSUE", "stale-skill-name",
                f"no reference to renamed skill `{old}`",
                f"{len(hits)} reference(s) to `{old}`",
                where,
                f"rename `{old}` -> `{new}` (a dead name sends a teammate's grep nowhere)",
            ))


def check_determinism_as_prose(body_lines, body_start, findings):
    """NOTE: fenced shell blocks that perform filesystem mutation are candidates
    for a script (AUDIT §1.2). Conservative by design — read-only/orchestration
    commands are ignored so this does not cry wolf on skills that legitimately
    show CLI recipes."""
    in_fence = False
    fence_lang = ""
    fence_start = 0
    mutation_lines = []
    for idx, line in enumerate(body_lines):
        fence_m = re.match(r"^```(\w*)", line)
        if fence_m:
            if not in_fence:
                in_fence = True
                fence_lang = fence_m.group(1).lower()
                fence_start = body_start + idx
                mutation_lines = []
            else:
                if fence_lang in ("bash", "sh", "shell", "") and mutation_lines:
                    verbs = sorted({v for v in mutation_lines})
                    findings.append(Finding(
                        "NOTE", "determinism-as-prose",
                        "deterministic file mutation lives in scripts/, not prose (§3.6.1)",
                        f"shell block mutates the filesystem ({', '.join(verbs)})",
                        f"fenced block at L{fence_start}",
                        "if this is a fixed procedure, move it to scripts/ and call it; "
                        "if it is illustrative, leave it — this is advisory",
                    ))
                in_fence = False
            continue
        if in_fence and fence_lang in ("bash", "sh", "shell", ""):
            for vm in MUTATION_VERB_RE.finditer(line):
                mutation_lines.append(vm.group(1).split()[0])


def check_supersession_sites(body_lines, body_start, findings):
    """NOTE: lines marking something superseded/removed are where a live
    contradiction hides (AUDIT §1.3) — the "no longer true" note landed but the
    old directive may still live beside it. Surface the sites for a human to
    confirm the old text was actually deleted. This is not a claim of a defect."""
    hits = []
    for idx, line in enumerate(body_lines):
        if SUPERSESSION_RE.search(line):
            hits.append(body_start + idx)
    if hits:
        where = ", ".join(f"L{ln}" for ln in hits[:12]) + (" …" if len(hits) > 12 else "")
        findings.append(Finding(
            "NOTE", "supersession-site",
            "a supersession fully replaces the old text, leaving no live contradiction",
            f"{len(hits)} supersession marker(s)",
            where,
            "confirm the superseded directive was deleted, not left living beside its "
            "replacement (AUDIT §5.3 class); deep semantic check is the eval pass (deferred)",
        ))


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def resolve_skill_path(path):
    """Accept a SKILL.md file or a directory containing one. Returns the file
    path or None."""
    if os.path.isdir(path):
        candidate = os.path.join(path, "SKILL.md")
        return candidate if os.path.isfile(candidate) else None
    if os.path.isfile(path):
        return path
    return None


def lint_file(skill_path, max_body_lines):
    with open(skill_path, "r", encoding="utf-8") as fh:
        text = fh.read()

    fm_lines, body_lines, body_start = split_frontmatter(text)
    had_frontmatter = bool(fm_lines) or text.splitlines()[:1] == ["---"]
    skill_dirname = os.path.basename(os.path.dirname(os.path.abspath(skill_path)))

    findings = []
    check_frontmatter(fm_lines, had_frontmatter, skill_dirname, findings)
    check_oversize(body_lines, max_body_lines, findings)
    check_duplicate_section_numbers(body_lines, body_start, findings)
    check_stale_skill_names(body_lines, body_start, findings)
    check_determinism_as_prose(body_lines, body_start, findings)
    check_supersession_sites(body_lines, body_start, findings)
    return findings, len(body_lines)


def main(argv):
    ap = argparse.ArgumentParser(
        description="Accretion linter for SKILL.md files. Emits "
        "`expected · found · where · next` findings; ISSUES fail the run.",
    )
    ap.add_argument("paths", nargs="+", help="SKILL.md files or dirs containing one")
    ap.add_argument("--max-body-lines", type=int, default=DEFAULT_MAX_BODY_LINES)
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--no-notes", action="store_true", help="ISSUES only in text output")
    ap.add_argument("--notes", action="store_true", help="(default) include NOTES in text output")
    ap.add_argument("--quiet", action="store_true", help="print nothing; rely on exit code")
    args = ap.parse_args(argv)

    reports = []
    total_issues = 0
    total_notes = 0
    unresolved = []

    for path in args.paths:
        skill_path = resolve_skill_path(path)
        if skill_path is None:
            unresolved.append(path)
            continue
        findings, body_len = lint_file(skill_path, args.max_body_lines)
        issues = [f for f in findings if f.tier == "ISSUE"]
        notes = [f for f in findings if f.tier == "NOTE"]
        total_issues += len(issues)
        total_notes += len(notes)
        reports.append({
            "skill": skill_path,
            "body_lines": body_len,
            "issues": issues,
            "notes": notes,
        })

    if unresolved:
        if not args.quiet and not args.as_json:
            for p in unresolved:
                sys.stderr.write(f"error: no SKILL.md found at {p}\n")
        if not reports:
            if args.as_json:
                print(json.dumps({"error": "no SKILL.md found", "paths": unresolved}))
            return 2

    if args.as_json:
        out = {
            "summary": {"issues": total_issues, "notes": total_notes,
                        "skills": len(reports), "max_body_lines": args.max_body_lines},
            "reports": [
                {
                    "skill": r["skill"],
                    "body_lines": r["body_lines"],
                    "findings": [f.as_dict() for f in (r["issues"] + r["notes"])],
                }
                for r in reports
            ],
            "unresolved": unresolved,
        }
        print(json.dumps(out, indent=2))
        return 1 if total_issues else 0

    if not args.quiet:
        show_notes = not args.no_notes
        for r in reports:
            status = "ISSUES" if r["issues"] else ("clean (notes)" if r["notes"] else "clean")
            print(f"\n{r['skill']}  —  {r['body_lines']} body lines  —  {status}")
            shown = r["issues"] + (r["notes"] if show_notes else [])
            if not shown:
                print("  ok")
            for f in shown:
                print(f.as_text())
        print(
            f"\nsummary: {total_issues} ISSUE(s), {total_notes} NOTE(s) "
            f"across {len(reports)} skill(s) (threshold {args.max_body_lines} body lines)"
        )

    return 1 if total_issues else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
