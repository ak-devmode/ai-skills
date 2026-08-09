# scripts/ — shared deterministic helpers

Top-level because more than one skill calls each of these (same rule as
`templates/` — see `CLAUDE.md` §3.6). Skill-private scripts stay in
`<skill>/scripts/`, e.g. `closeout/scripts/verify-archive.sh`.

**Why these are scripts and not prose.** Each replaces an instruction that told an
LLM to do something deterministic, and two of them replace instructions that had
already caused real data loss. Prose cannot enforce itself — the same reasoning
`/closeout` §14.0 already applies to its archive gate.

| Script | Replaces | Callers |
|---|---|---|
| `resolve-plans-dir.sh` | A `case` block copy-pasted into 5 skills | /scope, /plan, /prd, /closeout, /repo-cleanup |
| `claim-scope-number.sh` | "read the index, find the highest, increment" — **raced; scope 110 collided** | /scope §5.2 |
| `plans-index.py` | "append a row" with no header written — **leaked 40 untabled rows** | /scope §5.8, /plan §11.4, /closeout §13, /repo-cleanup §6 |
| `repo-graph-snapshot.sh` | /scope §0.5.2's serial per-repo walk | /scope §0.5.2 |
| `edit-guard.py` | `python3 - <<PY` string-replaces that **no-op silently** | any scripted multi-file edit |

## Contracts

    resolve-plans-dir.sh [path]
      stdout: absolute plans dir     exit: 0 ok · 3 unknown project · 4 dir missing

    claim-scope-number.sh <plans-dir>
      stdout: claimed integer        stderr: provenance across all four sources
      Maxes over origin/main index, local index, scope folders, and branch names.
      Not atomic — nothing short of a server write is — but closes every gap that
      has bitten. Read the stderr note when local and origin disagree.

    plans-index.py validate <index>       exit: 0 conformant · 1 issues found
    plans-index.py next-number <index>    stdout: highest whole scope number + 1
    plans-index.py add  <index> --num --status --folder --desc [--creator] [--dry-run]
    plans-index.py move <index> --num --to {active,archived} [--folder] [--status] [--dry-run]

`add` and `move` refuse to write against a non-canonical header rather than
silently appending a mismatched row. **Nothing is ever truncated** — the
Description column is Alex's console status tracker, and 3-4 sentences there is
the intended use (`markdown-style` §11.7.4). Cells past ~900 chars get a note, not
a cut. Per-plan `{N}.{P}` rows are valid (§11.7.5). Neither command ever rewrites
a row it was not asked to touch.

Canonical row shape (decided 2026-08-09):

    | # | Status | Folder | Description | Created by |

## edit-guard.py

    edit-guard.py <spec.json|-> [--write] [--root DIR]
      exit: 0 all validated (applied with --write) · 1 an edit failed, NOTHING written · 2 bad spec

Ops: `replace` (exact substring, must match `count` times, default 1) · `sub` (regex,
`expect` or `expect_min`) · `cut` (from one anchor to another, optional `with`).

**All-or-nothing.** Every edit is validated against current file contents before any
write, so a partially-applied refactor never becomes the new baseline. A missed anchor,
an ambiguous one, a regex matching 0 times, or an `old == new` no-op each fail the run.

Use it instead of a `python3 - <<PY` replace whenever an edit spans multiple files or
you are about to commit the result. On 2026-08-09 three such edits reported success
while changing nothing: an anchor that ignored leading whitespace, a regex anchored to
`^### 12\\.` that skipped seven body items, and a `--folder` override writing an
invented path over a correct one. All three printed a MISS to stdout and all three were
followed by a commit. Printing is not checking.

`validate` reports as ISSUES only things that are actually broken: a
non-canonical header, mixed row widths, an unparseable `#`, or a row whose table
disagrees with where its folder sits on disk. Everything else — un-numbered
program rows (`catalog-program`, `roadmap`), per-plan rows, long descriptions — is
a NOTE. A validator that cries wolf is a validator that gets ignored, which is the
same failure as a rule nobody obeys.
