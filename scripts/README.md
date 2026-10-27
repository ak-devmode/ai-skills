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
| `plans-index.py` | "append a row" with no header written — **leaked 40 untabled rows** | /scope §5.8, /plan §11.4, /closeout §13, /repo-cleanup §6; `status` runs the verdict gate before Done, `validate` catches a hand-edited Done, `gate-count` counts clean gated scopes toward the blocking flip |
| `repo-graph-snapshot.sh` | /scope §0.5.2's serial per-repo walk | /scope §0.5.2 |
| `edit-guard.py` | `python3 - <<PY` string-replaces that **no-op silently** | any scripted multi-file edit |
| `plans-folder.sh` | hand-run `mkdir`/`mv` sweep copied into two skills | /plan §2.5, /scope §5.6–5.7 |
| `context-gather.sh` | Step-0 bash blocks copied into two skills — /prd's cat'ed both indexes whole | /scope Step 0, /prd Step 0 |
| `stamp-executed-by.sh` | "derive the name, write the header" prose | /plan §3.1 |
| `repo-graph-check.py` | a four-way SHA/branch classification written as steps | /plan §5.6.1 |
| `ledger-init.sh` | "copy the template, append a phase header" prose; `--repo` records the unit's base SHA for the gate | /plan §5.13 |
| `dispatch-log.py` | hand-written JSONL lines | /concurrency §6, §7.1 |
| `herdr-pane.sh` | the two-call pane naming rule (the second call was the recurring miss) + helper split | /concurrency §6, herdr §2/§5 |
| `repo-survey.sh` | default-branch + survey cascade + MERGED/LIVE shell — **its `\|\| echo main` never fell back** | /cross-repo-init §2.1–2.2 |
| `lint-skill.py` | eyeballing SKILL.md quality — CLAUDE.md §6 said "no linter currently" while the skills accreted past obey-able size | any skill edit; `/scope`, `/plan`, `/closeout` bodies |
| `resolve-identifiers.py` | grepping for a name and calling it declared — comment, fixture and sibling-service hits read as real; shell `$NAME` reads fail closed | `/verify` + `/review` local-maxima lens (scope 5 Phase 2) |
| `verify-run.py` | "it passed" as a claim — runs each finish-table row in its declared context and is the only writer of the verdict log | `/verify`, `/plan` checkpoints, `/closeout` (scope 5) |
| `verdict-gate.py` | "verify ran, so it's done" — applies §5 to the latest final verdict per owned check (range, rung, revision, disposition coverage); `--all` is /closeout's whole-scope view; `**Predates gate:**` phases exempt; advisory until 5 clean scopes | `plans-index.py status`/`validate`, `/plan`, `/closeout` |
| `finish-table.py` | a finish table typed by hand — standard rows per phase, Revision + Changelog on every change, read back through the runner's parser | /scope Step 5.10, /plan §5.6.2a self-heal |
| `review-mode.py` | each skill deciding lean vs full on its own — flag > `AI_SKILLS_REVIEW_MODE` > default `lean`; a bad env value is an error, never a silent lean | `/review`, `/verify` (plan 7) |
| `plans-publish.sh` | commit per task, push per phase — on a trunk every machine writes; **kalpa-docs sat 11 ahead / 21 behind** | /plan §8.5b |
| `ff-local-trunk.sh` | nothing — worktree teardown left the primary checkout's trunk behind what just merged | /closeout §13.6, herdr §3 |
| `verify_lib.py` | (library, not a CLI) one table parser, message formatter and verified JSONL appender for the verify scripts, and `capped_diff` — the one 1,500-line cap both lean bundles use | `verify-run.py`, `verdict-gate.py`, `resolve-identifiers.py`, `review.py`, `judge.py` |

**Tests:** `python3 -m unittest discover scripts/tests` from the repo root (stdlib only,
Python >= 3.9). One `test_<name>.py` per script; `_helpers.py` runs a script as a
subprocess or loads it by path. The older scripts predate the suite and are covered only
by `test_entrypoint.py`'s compile check.

## Contracts

    resolve-plans-dir.sh [path]
      stdout: absolute plans dir     exit: 0 ok · 3 unknown project · 4 dir missing

    claim-scope-number.sh <plans-dir>
      stdout: claimed integer        stderr: provenance across all four sources
      exit: 0 claimed · 2 usage · 3 records mode and the local records do not render
      Maxes over origin/main (index, archive index, folders), local index (a fresh
      `render --stdout` in records mode), scope folders, and branch names — a branch's
      number counts only if its tip has that scope folder, or a row for it in this plans
      dir's index / archive index / index-loose.md. Folder sources count directories only.
      Not atomic — nothing short of a server write is — but closes every gap that
      has bitten. Read the stderr note when local and origin disagree.

    packet.py new --door {one-way|two-way|info} [--type data-model|generic] --title --unit --option LABEL...
              [--recommended N] [--body|--body-file|--payload-file] [--blocks] [--continues-on]
              [--range BASE..HEAD] [--id ID] [--driver]
    packet.py close|touch ID · stale ID [--force] · event --kind K [--body] [--packet-id ID]
    packet.py check-reply (--reply TEXT|--file F|-) [--lane M/W/A] · flush [--driver]   (all: --outbox DIR…)
      stdout: `PACKET <id>` + the card · exit: 0 ok (a blocked POST is ok) · 1 refused / error · 2 usage
      Every packet lands in `<worktree>/.decision-queue/outbox/` (self-ignoring); only a driver
      (`--driver` or $HERDR_AGENT_NAME=driver) POSTs, and only with $DECISION_QUEUE_URL set (hard 3 s
      deadline, redirects refused, /packets and /events, idempotent on id; "sent" is a `<id>.sent` marker). A dead queue prints a `Blocked` note and exits 0;
      `flush` re-sends. Only 400/409/413/415/422 are permanent (`<id>.rejected` / `.conflict`); every other 4xx is Blocked and retried. Events of a refused packet are marked `evt-<id>.rejected`, never POSTed. To clear a marker, delete the `<id>.rejected` / `.conflict` file (and its events' `evt-*.rejected`) from the outbox. `flush --outbox DIR` on a missing DIR prints `Skipped: outbox DIR does not exist` (exit 0). check-reply refuses a missing/other-lane tag, an unknown, closed, stale or
      other lane's packet, two different tags, unreadable state, and a one-way packet whose HEAD moved. `--range` runs door.py and a
      floor hit promotes the door. Lane identity: machine/workspace/agent from herdr env, else
      machine/repo-hash/session id ($CLAUDE_CODE_SESSION_ID); with none, check-reply needs --lane. Schema: schemas/packet.schema.json, checked by schema_check.py.

    packet_emit.py (importable)   emit(repo, unit, title, options, body, door, range_, blocks, pid) -> id | None
      Review + verify's packet writer (scope 10 §4.2): runs `packet.py new` with cwd = the repo under review,
      prints `PACKET <id>`, and on ANY failure warns on stderr and returns None — a harness error never
      stops the caller, which keeps its inline question. `stable_id(*parts)` makes re-emitting idempotent.

    door.py classify --repo PATH --range BASE..HEAD [--claim one-way|two-way|info] [--defaults FILE]
      stdout: JSON {door, paths[{path,pattern,change}], reason} · exit: 0 classified · 2 usage
      Floor = scripts/one-way-doors.defaults + the repo's `.one-way-doors` read at the BASE
      revision. Every touched path counts (renames and deletes both sides); an edit to
      `.one-way-doors` is one-way. Promote-only: a `two-way` claim never lowers a hit (an `info` claim with no hit is kept). Fails
      closed: bad range, unresolved ref, git error, unreadable defaults/base file = one-way.
      Callers treat a non-zero exit as one-way.

    driver-merge.py check|merge --repo PATH --pr N --scope DIR --unit N.P [--driver] [--method squash|merge|rebase]
      stdout: one `[ok]`/`[FAIL]` line per condition, `verdict: ELIGIBLE|REFUSED …`; merge adds
      `MERGED <owner/repo>#N <sha>` + `EVENT … merged`, or `PACKET <id>` + `NOT MERGED — <why>`
      exit: 0 eligible / merged + event written · 1 refused / not merged · 2 usage · 4 merged, event not written
      /plan §6.8 step 4 (scope 10 §4.3). Merges only when ALL hold: caller is a driver
      ($HERDR_AGENT_NAME=driver, or --driver outside herdr; any other $HERDR_AGENT_NAME is a lane and
      `merge` refuses it before any gh call, whatever --driver says), PR open + not draft, base = `main` for kalpa-docs /
      pmg-docs / ai-skills else `develop` (anything else — a code repo's prod `main` — is refused, never
      touched), every check finished green or skipped/neutral with at least one real green run (an empty or
      skipped-only list is vacuous, refused), the unit's latest review of the repo is SHIP or accepted and
      saw the PR head (later commits plans/-only), every non-plans/ commit in merge-base..head sits in some
      review's base..head for the repo in the unit (else "unreviewed commits", named), verdict-gate.py
      --blocking reads `pass` (advisory, not-judged, predates or unknown = no merge), door.py finds no floor path on
      merge-base..head, mergeStateStatus CLEAN/HAS_HOOKS (BLOCKED → `--admin` only when every required
      check of the base — classic protection and rulesets, both read — is SUCCESS on the head; unreadable
      protection is no merge; anything else refused).
      `gh pr merge --match-head-commit`, never `--auto`; the merge is read back as MERGED before the
      `merged` event (repo, PR, base, sha; degraded review / admin / gate marker flagged). A failed
      condition writes a packet instead: one-way with the matched paths for a floor hit, else two-way.
      Fails closed on every gh/git error, unreadable verdict, or unknown check/merge state.

    plans-index.py validate <index>       exit: 0 conformant · 1 issues found
    plans-index.py next-number <index>    stdout: highest whole scope number + 1
    plans-index.py add  <index> --num --status --folder --desc [--creator] [--dry-run]
    plans-index.py move <index> --num --to {active,archived} [--folder] [--status] [--dry-run]
    plans-index.py status <index> --num --status [--skip-verify R] [--blocking|--advisory] [--dry-run]
    plans-index.py gate-count [<index>...] [--discover]  stdout: `clean gated scopes: N/5`, + REMINDER line at 5 · exit 0
      exit: 0 written · 1 gate BLOCKED (row untouched) or write did not land · 2 usage · 3 gate could not evaluate
    plans-index.py render  <plans-dir> [--stdout] [--allow-loss]   exit: 0 · 1 a rendered row lost its record, or non-scope
      content (other tables, prose) would be dropped, or the index's `**Gate mode:**` line is not in
      README.md, or a number is held by two rows (--allow-loss covers neither) · 2 not migrated.
      `--stdout` is a read: exit 0, with each lost row named on stderr
    plans-index.py migrate <plans-dir> [--branch REF [--base REV]] [--dry-run]   exit: 0 (every loose row
      and non-scope section reported; moves `**Gate mode:**` to README.md) · 2 index and README disagree on it
    plans-index.py check   <plans-dir>   exit: 0 render matches records · 1 issues (lost row, stale render, size,
      non-scope content, unmoved gate line, a number held twice)
      Records mode: plans/README.md declares `**Index render:** bot | local`. add/status/move
      then write the scope's block in its own progress.md (loose rows: index-loose.md);
      `local` re-renders after each write, `bot` leaves the index to the bot. No line =
      the index is edited in place. A number held by two rows refuses add/status/move (exit 2). `move --to archived` on kalpa-docs refuses while a
      kalpa-orchestra BACKLOG row reads scoped(N) (`--force REASON`).

    plans-publish.sh <plans-dir> -m <msg> -- <path>...
      Commits ONLY the named paths; on the repo's trunk also rebases onto origin (only if
      origin moved), pushes, retries a rejected push once, reads back with merge-base.
      Off trunk: commit only. A shared code trunk (ai-skills `main`) publishes too.
      Bot render mode: PLANS-INDEX.md and archive/INDEX.md are dropped from the paths.
      exit: 0 published / committed off trunk · 2 usage · 3 HALT — conflict or stash not
            re-applied (commit kept, nothing pushed), or repo busy / add / commit failed
            (nothing committed) · 4 not pushed (offline, auth, rejected, origin/HEAD unset)
            — commit kept, git's reason in the message

    ff-local-trunk.sh <repo> [<trunk>]      trunk default: origin/HEAD's target
      Fast-forward only, wherever trunk is checked out (primary or linked worktree), else
      the ref itself. Read back against origin/<trunk>.
      exit: 0 current or advanced · 2 usage · 3 ahead/diverged or blocked, nothing
            changed · 4 fetch failed

    plans-folder.sh <plans-dir> <folder-name> [--slug S] [--move FILE]... [--dry-run]
      exit: 0 ok · 1 a move refused (destination exists) or failed to land · 2 usage
    context-gather.sh [repo-dir]          always exit 0; `== section ==` blocks on stdout
    stamp-executed-by.sh <plan-file> [--repo DIR]
      exit: 0 stamped/unchanged · 1 write did not land · 2 usage · 3 no git user.name
    repo-graph-check.py <scope.md> [--projects DIR]
      exit: 0 unchanged · 1 advanced only (confirm) · 3 diverged/missing (stop) · 4 no Repo Graph table / every row skipped · 2 usage
    ledger-init.sh <folder> --plan <plan> --phase "<P>: <name>" [--slug S] [--resumed] [--repo PATH [--base REV]]...
      a worktree --repo is recorded under its main checkout's name; --base REV replaces HEAD as that repo's base
      exit: 0 ok · 1 write did not land / --repo not a git repo · 2 usage · 4 template missing
    resolve-identifiers.py --repo P (--range BASE..HEAD | --ids FILE) [--decl-repo P]... [--json]
      exit: 0 all resolved · 1 unresolved or unsupported · 2 usage · 3 git error / empty range
    review-mode.py [--full | --lean]
      stdout: `mode: <lean|full> (<flag|env|default>)`   exit: 0 resolved · 2 both flags / bad env value / unknown arg
    verify-run.py run|judged|finalize ...  (templates/verify-contracts.md §4)
      exit: 0 runner rows passed / recorded · 1 a row failed or refused · 2 usage · 3 malformed input / write did not land
    verdict-gate.py --scope DIR (--unit N.P | --all) [--advisory|--blocking] [--skip-verify R] [--json]
      exit: 0 pass / advisory / skipped / predates-gate · 1 blocked (--all: any block) · 2 usage · 3 could not evaluate
    finish-table.py init --scope DIR --phase N.P[=repo,...]... [--rows F] [--test-plan-owner N.P] [--predates N.P,...]
    finish-table.py add  --scope DIR --rows F --change TEXT [--replace]
      exit: 0 written · 2 usage · 3 refused (exists / missing / would not parse — nothing written)
    dispatch-log.py --scope --task --status {dispatched,done,blocked,failed} [--seat --branch --worktree --pane --tail --log]
      exit: 0 written + read back · 1 did not land · 2 usage
    herdr-pane.sh name <pane> <name> [--source SKILL]  |  herdr-pane.sh helper [--cwd DIR]
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
