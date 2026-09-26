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
| `plans-folder.sh` | hand-run `mkdir`/`mv` sweep copied into two skills | /plan §2.5, /scope §5.6–5.7 |
| `context-gather.sh` | Step-0 bash blocks copied into two skills — /prd's cat'ed both indexes whole | /scope Step 0, /prd Step 0 |
| `stamp-executed-by.sh` | "derive the name, write the header" prose | /plan §3.1 |
| `repo-graph-check.py` | a four-way SHA/branch classification written as steps | /plan §5.6.1 |
| `ledger-init.sh` | "copy the template, append a phase header" prose | /plan §5.13 |
| `dispatch-log.py` | hand-written JSONL lines | /concurrency §6, §7.1 |
| `herdr-pane.sh` | the two-call pane naming rule (the second call was the recurring miss) + helper split | /concurrency §6, herdr §2/§5 |
| `repo-survey.sh` | default-branch + survey cascade + MERGED/LIVE shell — **its `\|\| echo main` never fell back** | /cross-repo-init §2.1–2.2 |
| `lint-skill.py` | eyeballing SKILL.md quality — CLAUDE.md §6 said "no linter currently" while the skills accreted past obey-able size | any skill edit; `/scope`, `/plan`, `/closeout` bodies |
| `resolve-identifiers.py` | grepping for a name and calling it declared — comment, fixture and sibling-service hits read as real | `/verify` + `/review` local-maxima lens (scope 5 Phase 2) |
| `verify-run.py` | "it passed" as a claim — runs each finish-table row in its declared context and is the only writer of the verdict log | `/verify`, `/plan` checkpoints, `/closeout` (scope 5) |
| `verify_lib.py` | (library, not a CLI) one table parser, message formatter and verified JSONL appender for the verify scripts | `verify-run.py`, `verdict-gate.py`, `resolve-identifiers.py` |

**Tests:** `python3 -m unittest discover scripts/tests` from the repo root (stdlib only,
Python >= 3.9). One `test_<name>.py` per script; `_helpers.py` runs a script as a
subprocess or loads it by path. The older scripts predate the suite and are covered only
by `test_entrypoint.py`'s compile check.

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

    plans-folder.sh <plans-dir> <folder-name> [--slug S] [--move FILE]... [--dry-run]
      exit: 0 ok · 1 a move refused (destination exists) or failed to land · 2 usage
    context-gather.sh [repo-dir]          always exit 0; `== section ==` blocks on stdout
    stamp-executed-by.sh <plan-file> [--repo DIR]
      exit: 0 stamped/unchanged · 1 write did not land · 2 usage · 3 no git user.name
    repo-graph-check.py <scope.md> [--projects DIR]
      exit: 0 unchanged · 1 advanced only (confirm) · 3 diverged/missing (stop) · 4 no Repo Graph · 2 usage
    ledger-init.sh <folder> --plan <plan> --phase "<P>: <name>" [--slug S] [--resumed]
      exit: 0 ok · 1 write did not land · 2 usage · 4 template missing
    dispatch-log.py --scope --task --status {dispatched,done,blocked,failed} [--seat --branch --worktree --pane --tail --log]
      exit: 0 written + read back · 1 did not land · 2 usage
    herdr-pane.sh name <pane> <task> <seat> [--source SKILL]  |  herdr-pane.sh helper [--cwd DIR]
      exit: 0 ok · 1 herdr call failed / label not visible · 2 usage · 3 not in herdr / no server
    repo-survey.sh [repo-dir] [--no-fetch]
      exit: 0 ok · 1 not a git repo. Read-only; never checks out.

    Every writer above reads its result back from the destination before reporting
    success — a green exit is a landed write, not a printed intention (CLAUDE.md §3.6.2).

    lint-skill.py <skill-dir|SKILL.md>... [--max-body-lines N] [--no-history] [--json] [--no-notes] [--quiet]
      exit: 0 no ISSUES (NOTES allowed) · 1 ISSUES found · 2 usage/parse error
      Reads only. Each finding is `expected · found · where · next`.
      ISSUES (fail the run, deterministic): duplicate section numbers, malformed frontmatter (missing name/description,
      empty allowed-tools, name≠dir), dead renamed-skill references, agent-memory
      file citations (memory is per-cwd; CLAUDE.md §9.3).
      NOTES (advisory, never fail): growth (deletions < 20% of additions over the
      last 10 modifying commits, from git), cross-skill-duplicate (word 5-gram
      overlap between skills in one run), size (>N lines, default 250 — a hint,
      not a cap), determinism-as-prose (filesystem-mutation verbs in a fenced shell
      block), supersession sites (where a live contradiction may hide). The ISSUE/NOTE split IS the design — fuzzy checks are NOTES so the
      linter never cries wolf. Semantic contradiction detection is deferred to an
      eval pass (scope 2 §2.1). Bump the threshold only with a recorded reason.

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
