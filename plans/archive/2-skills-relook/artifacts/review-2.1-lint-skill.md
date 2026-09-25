# /review — ai-skills @ feature/skills-relook-opus5 (plan 2.1)

**Date:** 2026-09-23
**Target:** `scripts/lint-skill.py` (the accretion linter; 483 → 545 lines after fixes) + doc wiring
**Passes:** gstack engine — substantive checklist pass ✓ (telemetry/Greptile/Aside machinery n/a: no PR, generic repo) · Kalpa domain pass — **SKIPPED** (generic repo, not `wellmed/*` or `pmg/*`; inventing domain checks would be dishonest)
**Adversarial:** Claude fresh-context subagent ✓ · **codex cross-model DEGRADED — timed out at 300s, no output**
**Fix policy:** findings fixed in-band (Alex's standing pref), split fixed/not-fixed below

Scope check: CLEAN. Intent = build the accretion linter + dogfood on `/concurrency` (plan 2.1). Delivered exactly that; doc wiring (CLAUDE.md/README) is in-scope per "fix the doc as part of the work."

---

## BLOCKING (2) — both FIXED

1. **`scripts/lint-skill.py` `split_frontmatter`** — unclosed frontmatter (`---`
   opened, never closed) swallowed the entire file as frontmatter → 0 body lines →
   linter reported **clean, exit 0**. A 303-line skill with a dropped closing `---`
   escaped every check including oversize. Fail-open, the worst class for a linter.
   → **Fixed:** `split_frontmatter` returns a status (`none`/`closed`/`unclosed`);
   `unclosed` emits an ISSUE and returns the content as body so oversize still fires.
   Verified: now 2 ISSUEs (unclosed + oversize), exit 1.

2. **`lint_file`** — a SKILL.md with invalid UTF-8 raised an uncaught
   `UnicodeDecodeError`, crashing the whole run and aborting sibling files (the
   good file listed first never got reported; `--json` produced nothing).
   → **Fixed:** read wrapped in try/except → per-file parse error, exit 2, loop
   continues. Verified: good file reported, bad file → stderr parse error, exit 2,
   no crash.

## SHOULD FIX (6) — all FIXED

3. **BOM before `---`** defeated frontmatter detection (`str.strip()` doesn't remove
   U+FEFF) → false "no frontmatter" ISSUE and the real body went unmeasured.
   → **Fixed:** strip a leading BOM before the `---` test.
4. **Quoted `name: "x"`** or **trailing `# comment`** → false name-mismatch ISSUE.
   → **Fixed:** `_scalar()` strips a matching quote pair and an unquoted trailing comment.
5. **Zero-indent `allowed-tools` block list** (`- Bash` at column 0, legal YAML) →
   false "empty or malformed" ISSUE. → **Fixed:** accept list items at any indent.
6. **Headings inside fenced code blocks counted** → false duplicate-section-number.
   This was the `prd` finding: its `3.1/3.2/3.3` live inside a fenced ```` ```markdown ````
   template example (L164–280), not the real document. → **Fixed:** fence-aware
   heading scan (`iter_headings`). `prd` now correctly shows only oversize.
7. **Mixed resolvable + missing paths** exited 0 (a typo'd skill path silently
   "passed"). → **Fixed:** any unresolved/parse-error path forces exit 2.
8. **Year-prefixed headings** (`## 2024 Roadmap` / `## 2024 Review`) collided on
   `2024`. → **Fixed:** section integer capped at 3 digits with a no-more-digits guard.

## NOTE (not fixed — accepted)

- N2 (subagent): NOTE-tier fence handling misses `~~~` and indented fences. Advisory
  tier only, no exit-code effect. Accepted — the NOTE tier is best-effort by design.
- N3 (subagent): bare-filename invocation from an oddly-named cwd can false-positive
  the name check. Edge case; normal usage passes a dir. Accepted.

---

## Verification

- Full regression matrix (8 fixed cases + originals) all green; negative-control
  fixture still fires all 4 ISSUE checks; `python3 -m py_compile` clean.
- Fleet re-run: 16→13 ISSUEs, only `prd` changed (4→1), which is the corrected
  false positive. No other skill's verdict moved.

## What this review did NOT cover

- **codex cross-model pass DEGRADED** — timed out at 300s with no output. The
  cross-model angle (which the `/review` skill's own history says catches parser
  bugs the same-model pass misses) is therefore absent. The Claude adversarial
  subagent + my critical pass stand in, and they converged on the same 2 BLOCKING
  findings independently, but a second model did not confirm.
- **gstack engine bookkeeping** (telemetry, Greptile triage, Aside web-research,
  learnings-log) not run — n/a for a generic repo with no PR; best-effort anyway.
- **Kalpa domain pass** skipped — generic repo.
- No load/performance testing (a lint of 26 small files; not a concern).

Verdict: **SHIP** — all BLOCKING + SHOULD-FIX findings fixed in-band and
regression-tested. The one gap is the missing codex confirmation, recorded above.
