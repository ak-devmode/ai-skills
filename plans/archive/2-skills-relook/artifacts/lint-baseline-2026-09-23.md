# Accretion linter — baseline run (2026-09-23)

**Tool:** `scripts/lint-skill.py` (built in plan 2.1)
**Command:** `./scripts/lint-skill.py */SKILL.md` (from ai-skills root)
**Raw output:** `lint-baseline-2026-09-23.txt` (text) · `lint-baseline-2026-09-23.json` (CI)
**Fleet totals:** 13 ISSUEs, 14 NOTEs across 26 skills (threshold 250 body lines)
**Linter version:** hardened after `/review` (2026-09-23) — 8 fixes, see §5 below.

## 1. Dogfood target — `/concurrency` (plan 2.1's gate)

347 body lines. Linter verdict: **1 ISSUE, 1 NOTE.**

| Finding | Tier | Disposition |
|---|---|---|
| oversize — 347 > 250 (97 over) | ISSUE | **True positive.** Fix = move §10 traps + §7 supervision lore to `references/` (AUDIT §6.4 progressive disclosure). **Routed to plan 2.3** ("apply the loop to core skills … + `/concurrency`") — not fixed here; slimming is out of 2.1's scope (build linter + dogfood). |
| supersession-site — L301 | NOTE | **Cleared on review.** L301 is `/freeze is REMOVED from concurrent dispatch (2026-09-02)` — cleanly superseded, no surviving "use /freeze" directive beside it. No live contradiction. |

Gate C is met: the linter **flags** `/concurrency` with a correct, actionable verdict.

## 2. Linter defects caught by dogfooding (fixed in 2.1)

The control run against `/ready-to-clear` (the AUDIT's reference model) exposed two
cry-wolf bugs, both fixed before the baseline:

- **Lettered subsections collapsed to the parent number.** `5.A`–`5.E` were read as
  five duplicates of `5`. Fixed: section token now captures the full dotted/lettered
  label (`\d+(?:\.[0-9A-Za-z]+)*`), so `5` ≠ `5.A` ≠ `5.1`.
- **Benign "removed" flagged as supersession.** "worktree removed" matched. Fixed:
  supersession scan is case-sensitive on the repo's emphatic form `REMOVED`, plus the
  phrase forms (superseded/deprecated/no longer/replaced by/obsolete).

## 3. Fleet worklist (feeds plan 2.3)

**Oversize (13 skills)** — the accretion the AUDIT diagnosed. This is the sole
ISSUE class the fleet trips. Body lines:

    plan 852 · closeout 842 · scope 826 · cross-repo-init 705 · closeout-extended 644
    markdown-style 619 · repo-cleanup 418 · concurrency 347 · scope-review 338
    prd 306 · review 296 · kalpa-coding-standards 280 · ready-to-clear 258

**Duplicate section numbers: none.** An early linter build flagged `prd`'s
`3.1/3.2/3.3`, but `/review` proved that a false positive — those headings live
inside `prd`'s fenced ```` ```markdown ```` template example (L164–280), not in the
real document. The fence-aware fix (S4 below) suppressed it. No real dup-number
defect exists in the fleet today.

**Clean of ISSUES (13 skills)** — the linter clears well-sized skills, confirming it
does not fire on structure alone: pha-console, research, todo-sweep, herdr,
member-record-amend, kalpa-satu-sehat-fhir, md2docx, kalpa-generate-api, kalpa-migrate,
nano-banana, grafana-remediate, kalpa-context, repo-cleanup-all.

**NOTEs (14 total)** — advisory only, mostly supersession sites and a few
determinism-as-prose shell blocks in `plan`/`scope`/`closeout-extended`. Review during
each skill's 2.3 pass; none block.

## 4. Threshold note

`ready-to-clear` is 258 body lines — 8 over the 250 gate, though the AUDIT (2026-08-09)
called it "the model" at 176. It has itself accreted +82 since. This is a true (marginal)
signal, not a linter bug; do not raise the threshold to hide it — trim `ready-to-clear`
in a later pass instead. The threshold stays 250, changed only with a recorded reason.

## 5. Linter hardened via `/review` (2026-09-23)

`/review` (Claude adversarial subagent + my critical pass; codex pass DEGRADED —
timed out) found 8 fail-open/false-positive bugs in the first linter build. All
fixed + regression-tested. Full report: `review-2.1-lint-skill.md`.

- **BLOCKING** — unclosed frontmatter swallowed the whole file (0 body lines →
  reported clean); invalid UTF-8 crashed the run and aborted sibling files.
- **SHOULD FIX** — BOM defeated frontmatter detection; quoted/commented `name:`,
  zero-indent `allowed-tools` list, and fenced-example headings all cried wolf;
  a missing path exited 0 instead of 2.

The `prd` correction above came out of this pass. Net effect on the fleet: 16→13
ISSUEs (the 3 removed were `prd`'s false dups).
