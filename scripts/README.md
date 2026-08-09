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
| `plans-index.py` | "append a row" with no header written — **leaked 40 untabled rows** | /scope §5.8, /plan §12.4, /closeout §13, /repo-cleanup §6 |

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
silently appending a mismatched row. Cells over 300 chars are truncated with a
`… → detail in progress.md` pointer (§11.7.4) — the index says where to look, not
what happened. Neither command ever rewrites a row it was not asked to touch.

Canonical row shape (decided 2026-08-09):

    | # | Status | Folder | Description | Created by |

`validate` treats un-numbered rows whose `#` is a slug (`catalog-program`,
`roadmap`) as valid programs/standing docs, not malformed rows — a validator that
cries wolf is a validator that gets ignored.
