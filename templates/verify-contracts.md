# Verification contracts — `/verify`, `/review` and their scripts

**Schema version:** verify/1
**Status:** Draft for approval (scope 5, Plan 5.1 Task 1.1)
**Owner:** ai-skills (public). Product specifics live in each product's private test-suite.

These are the formats every verification artifact follows, and the rules the scripts
enforce. A gate is a script, not a paragraph a skill can skip — every rule below with one
correct answer is enforced by `scripts/verify-run.py`, `scripts/verdict-gate.py` or
`scripts/plans-index.py`, and the section says which. Filled examples live in
`templates/examples/`, never inside a template.

---

## 1. Map

```
 /scope ----writes----> finish-conditions.md  (scope folder; revisioned; §3)
                               |
                               v
 verify-run.py --run ------> artifacts/verify-<unit>.jsonl   pending   (§4)
 /verify judge (codex) -> verify-run.py --judged ------->    judged
 verify-run.py --finalize -------------------------->        final
                               |
                               v
 verdict-gate.py  <---- plans-index.py status / validate     (§5)
                               |
 /review (codex) ------> artifacts/review-<unit>.jsonl       (§6, audited by /verify)
 /closeout ------------> artifacts/feature-map-handoff-<unit>.md  -> test-suite features/ (§8)
```

| # | Artifact | Writer | Readers |
|---|---|---|---|
| §3 | `finish-conditions.md` | `/scope`; `/plan` self-heal drafts it, Alex confirms | `verify-run.py`, `verdict-gate.py`, `/verify`, `/closeout` |
| §4 | `artifacts/verify-<unit>.jsonl` | `verify-run.py` only (all three run states) | `verdict-gate.py`, `/verify`, `/closeout` |
| §5 | gate result (stdout + exit) | `verdict-gate.py` | `plans-index.py status`/`validate`, `/plan`, `/closeout` |
| §6 | `artifacts/review-<unit>.jsonl` | `review/scripts/review.py` (`record`, `dispose`) | `verdict-gate.py` (coverage), `/verify` (rejection audit) |
| §8 | `features/README.md` + feature files | agents in the product test-suite | `/verify`, the author's inner loop |
| §8 | `artifacts/feature-map-handoff-<unit>.md` | `/closeout` | whoever applies it in the test-suite repo, `/closeout-extended` |
| §9 | adapter CLI | the product test-suite | `verify-run.py` (through finish-table commands), `/verify` |
| §10 | every message | all of the above scripts | a teammate, or a model reading stderr |

`<unit>` is the plan number (`5.1`) — one verdict log and one review log per plan.

---

## 2. Evidence ladder — report the rung, never a score

| Rung | Means | Typical evidence |
|---|---|---|
| 1 | said so | an agent's claim, a progress note |
| 2 | pointed at the line | file:line citation |
| 3 | showed the bad case can't happen | type, constraint, or proof by construction, cited |
| 4 | ran a script that fails loud | runner record: command, exit code, output hash |
| 5 | reproduced in the running app | runner record against a live env via the adapter |

Every row declares the rung it requires; every verdict records the rung it reached. There
is no threshold score — a rung-2 proof isn't blocked by a number, it is visibly weak.

---

## 3. Finish-condition table — `finish-conditions.md`

**Writer:** `/scope` (template `templates/finish-conditions.md.template`, through
`scripts/finish-table.py`); on an older scope with none, `/plan` drafts it from the scope's
deliverables and Alex confirms once.
**Readers:** `verify-run.py` (executes rows), `verdict-gate.py` (evaluates rows), `/verify`
(judges `judge` rows), `/closeout` (runs all rows).

Lives in the scope folder, never inside `scope.md` (a write-once design record).

3.1 **Header fields:** `**Schema version:** verify/1` and `**Revision:** <integer>`. Every
change to a row bumps the revision and adds a Changelog line (rev · date · change · by).
Optional `**Predates gate:** <N.P>, …` names phases already started (Done or in
progress) when the table was created (self-heal on a running scope); they own no rows, `verdict-gate.py` reports them
`predates-gate` and `plans-index.py validate` accepts their Done — a scope already in
flight is never asked to reconcile verification after the fact (Alex, 2026-09-29).
**Writer in practice:** `scripts/finish-table.py` (`init` with the standard rows per
phase, `add` with the revision bump) — never typed by hand.

3.1.1 **`**Approved:**`** — the human checkpoint on the table (Alex, 2026-09-29). `init`
writes `pending`; `finish-table.py approve --by <name>` writes `rev <N> — <who>, <date>`,
run only on the user's explicit yes after they have read the rows in plain English; `add`
resets it to `pending`, because a changed table is a new promise. The gate blocks
(`table-approval`) while the line names anything but the current revision. A table with no
`**Approved:**` line predates the checkpoint and is exempt — from both this and §6.4.

3.2 **One row per check**, columns in this order:

| Column | Value |
|---|---|
| `check_id` | stable, unique, kebab-case; never reused for a different check |
| `deliverable` | the scope deliverable this proves, in words |
| `owner` | the plan that must pass it (`5.1`), or a unit within it (`5.1/1.3`) |
| `class` | `A` behavior (runs against a product env) · `B` conformance (repo content) |
| `check` | a shell command, or the literal `judge` |
| `repo` | repo path under `~/Projects/` (`ai-skills`, `wellmed/wellmed-testsuite`) |
| `dir` | working dir relative to the repo root; `.` for the root |
| `env` | space-separated `KEY=value` pairs, or `-`; names and pointers only, never a secret |
| `timeout` | seconds, or `-` for the default 120 |
| `rung` | the minimum rung (§2) a pass must reach |
| `unreachable_ok` | `no`, or `yes: <Alex's reason>` |
| `evidence` | the artifact a pass leaves behind |

3.3 **Cell rules.** A literal `|` inside a cell is written `\|`. Commands may be wrapped in
backticks; the parser strips one pair. An empty cell is an error, not a default — use `-`
where a column allows it (`env`, `timeout`).

3.4 **Ownership.** A checkpoint runs exactly the rows its unit owns: `--owner 5.1` selects
`5.1` and every `5.1/…` row. `/closeout` runs every row.

---

## 4. Verdict log — `artifacts/verify-<unit>.jsonl`

**Writer:** `verify-run.py` only — `--run` writes `pending`, `--judged` records the judge's
verdict from its output file, `--finalize` writes `final`. Every write is followed by a
read-back of the last line (the `dispatch-log.py` pattern); a write that didn't land exits
non-zero. No hand-written JSON.
**Readers:** `verdict-gate.py`, `/verify`, `/closeout`.

Append-only: a failed run is never deleted, it is superseded.

4.1 **Run states.** A run is one invocation over a set of owned rows, identified by
`run_id` (`<unit>-<UTC yyyymmddThhmmss>-<4 hex>`). Its records move `pending → judged →
final`. The `final` record is **one line per run** holding every check's result, so
finalization is a single append — a run is final entirely or not at all.

4.2 **Fields common to every record:** `schema` (`verify/1`) · `ts` (UTC ISO-8601) ·
`run_id` · `run_state` · `unit`.

4.3 **`pending`** — one record per check the runner touched:
`check_id` · `deliverable` · `class` · `rung_required` · `rung_reached` (4 for a class-B
command, 5 for a class-A command, 0 when not executed) · `table_rev` · `repo` · `dir` ·
`env` (the row's overlay only — never the caller's environment — plus `VERIFY_UNIT` and, when
the ledger records one for the row's repo, `VERIFY_BASE`, which the runner exports so a
static command can name the unit's range, e.g. `--range $VERIFY_BASE..HEAD`) · `cwd` (resolved) · `sha`
(repo HEAD when run) · `dirty` (bool) · `deployed_version` (class A: what the env reported;
else `null`) · `command` · `exit_code` (`null` if not run) · `duration_s` · `output_sha256` ·
`output_tail` (last 40 lines, at most 4000 chars — the evidence the judge reads) · `result` ·
`reason`.

4.4 **`judged`** — one record per check the judge assessed: `check_id` · `judge` (§4.6) ·
`verdict` (`pass | fail | inconclusive`) · `rung_reached` · `reason`.

4.5 **`final`** — one record per run: `judge` · `table_rev` · `results`, a map of
`check_id → {result, rung_reached, reason}` computed by the §5.1 authority rule.

4.6 **Judge line** — exactly one of `codex <model codex reported>` ·
`claude-fallback <reason>` · `none <reason>`. The model is a family (`VERIFY_CODEX_MODEL`,
default `sol`) resolved on every call from codex's own model list to its current slug,
following retirement upgrades — never codex's floating default. Every codex failure mode
(not installed, not authed, out of credits, model unusable or unresolved, a different model
than requested, timeout, empty, refusal, malformed output) ends as a non-codex line.

4.7 **Results:** `pass | fail | inconclusive | verified-unreachable`. The runner maps exit
codes: `0` pass · `1` fail · `2` inconclusive (usage/config) · `3` verified-unreachable ·
timeout → inconclusive `timed out after <N>s` · `126`/`127` or command missing →
inconclusive `not executable: <why>` · any other non-zero → fail.

4.8 **Latest final run decides.** For each `check_id`, the most recent `final` record
that contains it is the check's verdict. A fixed failure clears by re-running; nothing is
edited.

4.9 **Lever candidates.** Each final run yields candidates: the judge's
(`lever_candidates`, each with a kebab-case `lever_id` naming the *kind* of gap), plus one
automatic candidate per `inconclusive` / `verified-unreachable` check the judge left
unnamed, keyed `<check_id minus its p<P>- prefix>-<result>` (`verify_lib.levers`, the one
implementation). `/closeout` records them through `scripts/lever-candidates.py` in a
`## Lever candidates` section of the project's `plans/TO-DO.md`: one item per `lever_id`
with `Touches:` and a `Sighting: <docs repo>/<scope> · run <run_id> · <date>` line each.
The same scope and run twice is a no-op. Another run of the same scope adds a line but
never counts. The same `lever_id` from a **different scope** is the second sighting: the
item flips to `BUILD NOW`, once.

---

## 5. Gate semantics — `verdict-gate.py`

**Writer:** `verdict-gate.py` (stdout table + exit code).
**Readers:** `plans-index.py status` (refuses Done on a block), `plans-index.py validate`
(fails on a Done phase row without a passing gate), `/plan`, `/closeout`.

5.1 **Authority rule** (applied at finalize, re-checked by the gate). Order results
`pass > verified-unreachable > inconclusive > fail`.
- **Runner row** (`check` is a command): final = the runner result, lowered to the judge's
  verdict if that is worse. **The judge may only downgrade.** Final rung = the lower of the
  two. With judge `none`, the runner result stands.
- **Judge row** (`check` is `judge`): final = the judge's verdict, pass or fail. With judge
  `none`, final = `inconclusive`.

5.2 **Per owned check, the gate blocks when:**
- there is no `final` verdict for it;
- a `pending` record for it is newer than its latest `final` (an unfinished run);
- the result is `fail` or `inconclusive`;
- the result is `verified-unreachable` and the row's `unreachable_ok` is `no`;
- `rung_reached` < the row's `rung`;
- the verdict's `table_rev` differs from the table's current `Revision` (re-run after a
  table change);
- the verdict's `sha` for that repo is outside the unit's range `base..HEAD` — `base` is the
  repo's SHA recorded by `ledger-init.sh` in the phase block at phase start.

**Uncommitted work is accepted, deliberately** (Alex, 2026-09-26). Verification runs
pre-PR, on the working tree the author is about to commit — so evidence with `dirty: true`
passes. The flag stays on the record so a reader can see it; it is not a block.

5.2.1 **Per unit, the gate also blocks when** a repo with a recorded base has commits in
`base..HEAD` but no `review` record (§6.0) names that repo and covers the unit's first
commit on the current branch — a unit that commits must be reviewed (review 5.3-r1-03);
when a **blocking** finding's `fixed <sha>` sits in no later review's range — the fixes
are reviewed again (`/plan` §6.8, 5.3-r2-03); when git cannot count the range (a block,
never a zero); or when `artifacts/review-<unit>.jsonl` breaks §6.3: a `finding_id` with no disposition, a `fixed` without `sha`, or a `rejected`
without `reason`. Deterministic, so the gate owns it — `/verify` judges whether a rejection
was *right*, never whether one was recorded.

5.3 **Judge marker.** When the deciding `final` record's judge line is not `codex …`, the
gate reports `⚠ judge: <line>` and `plans-index.py status` appends it to the phase's index
status. A later final run with a codex judge clears it. The same holds for review: when the
unit has a `review` record (§6.0) with a non-codex reviewer, the gate reports
`⚠ judge: review <line>` until a later codex review *covers* it: same repo, the codex
base an ancestor of the fallback's base, the fallback's head an ancestor of the codex head.
A record without resolved `shas` cannot prove coverage and keeps the marker.

5.4 **Advisory mode** (the default until five real scopes pass cleanly — Alex, 2026-09-29;
`plans-index.py gate-count`, printed by `/closeout`, counts them and says when to flip
`GATE_MODE`): the gate prints
the same result and the same marker, and exits `0` with `ADVISORY` on the verdict line
instead of blocking. `--skip-verify "<reason>"` bypasses the gate and is written into the
verdict header and the index status.

5.4.1 **Closeout view** — `verdict-gate.py --all` evaluates every gated unit in the table.
Any block is a failure whatever the mode: the scope cannot report HEALED, it still
archives, and its index row carries the printed `⚠ verify failed <check_ids>` marker.

5.4.2 **Per-graph override** — a `**Gate mode:** blocking` (or `advisory`) line in a graph's
`PLANS-INDEX.md` sets the default for every scope under it; an explicit `--blocking` /
`--advisory` flag still wins. kalpa-iris runs blocking from its first scope (Alex,
2026-09-29): its code is not read by a human, so an advisory gate there is a report
nobody reads.

5.5 **Exit codes** for every script in this contract: `0` pass · `1` blocked / failed ·
`2` usage · `3` could not evaluate (missing or malformed input, git error) — never read as
pass.

---

## 6. Review disposition log — `artifacts/review-<unit>.jsonl`

**Writer:** `review/scripts/review.py` only — `record` (findings, from the reviewer's JSON)
and `dispose` (dispositions). No hand-written JSON.
**Readers:** `verdict-gate.py` enforces coverage (§5.2.1); `/verify` audits every
rejection's reasoning.

Every record carries `record`: `review`, `finding` or `disposition`.

6.0 **`review`** records — one per `record` call, written even when there are no findings:
`schema` · `ts` · `review_id` · `reviewer` (judge line, §4.6) · `range` · `shas`
(`{base, head}`, the range resolved to commits at record time) · `passes` · `findings`
(count) · `verdict`. `review.py` allocates the `review_id` and appends under an
exclusive lock on the log, so concurrent or clean reviews never share an ID.

6.1 **`finding`** records keep the reviewer's raw output: `schema` · `ts` · `review_id`
(`<unit>-r<n>`) · `finding_id` (`<review_id>-<nn>`, stable for that review) · `reviewer`
(judge line, §4.6) · `range` (`{repo: "base..head"}`) · `file` · `line` · `category`
(`engine | domain | local-maxima | silent-failure | dirty-comment | doc-claim | fail-open`) ·
`group` (the domain rule section, else empty) · `severity` (`blocking | should-fix | note`) ·
`text` · `fix`. IDs are assigned in severity order.

6.2 **`disposition`** records: `schema` · `ts` · `finding_id` · `disposition`
(`fixed | rejected | deferred`) · `sha` (required for `fixed`, the full SHA) · `via` (`fixed` only:
`anchor` — the commit changes the finding's file · `test` — it changes a test file in the
anchor's directory · `off-anchor` — neither, and `reason` says how it fixes the finding) ·
`reason` (required for `rejected` and for a `fixed` via `off-anchor`; for `deferred`, a note; the link is the finding ID, which must lead an open `- [ ]` item line in the project's `TO-DO.md` as `[review <id>]` followed by the work left, and the gate rechecks that item still exists, open or closed into `archive/TO-DO-archive.md` — never on a `blocking` finding or before round 4 *of the finding's repo* (rounds count the unit's reviews of that repo, not the unit-wide `r<n>`), `review/SKILL.md` §5.1) ·
`by`.

6.3 **Coverage rule.** Every `finding_id` has at least one disposition; the latest one
decides. A `finding_id` carried by two findings blocks — one disposition must never clear two. A `fixed <sha>` commit must touch the finding's `file` or a test file beside it,
or carry an `off-anchor` reason — `dispose` refuses it otherwise, at write time, and the
gate blocks an `off-anchor` fix without a reason. Nothing silently
dismissed, nothing silently dropped. A re-review mints a new `review_id`; the old findings
stay.

6.4 **`acceptance`** records — the human checkpoint on review outcomes: `schema` · `ts` ·
`by` · `findings` · `fixed` · `rejected` · `deferred`. Written by `review.py accept --by
<name>` on the user's yes, refused while any finding lacks a disposition. Under a table
with an `**Approved:**` line (§3.1.1), the gate blocks (`review-acceptance`) when a
`finding` or `disposition` record follows the last acceptance — a new round reopens it.

---

## 7. Evidence placement

**Writer:** `verify-run.py` enforces it on every write. **Readers:** anyone publishing a
verdict.

7.1 **Class-A evidence** (URLs, screenshots, command output from a product env) is written
only to the product's private location — its kalpa-docs scope folder or the test-suite
repo. `verify-run.py` refuses to write a class-A record into a repo whose `origin` remote is
on its public denylist, or into a directory that is not in a git repo (fail closed).

7.2 **Public repos hold class-B verdicts on their own content only.** A public summary of a
class-A run may carry these fields and no others: `run_id` · `unit` · `check_id` · `class` ·
`rung_required` · `rung_reached` · `result` · `judge` · `ts` · `sha`.

7.3 Never in any verdict, public or private: credentials, tokens, full request bodies, PHI,
tenant names other than `clinic_3`.

---

## 8. Feature map

**Writers:** agents in the product's private test-suite generate and maintain it (nobody
hand-writes it); `/closeout` writes only the handoff. **Readers:** `/verify`, and the
author's own inner loop.

8.1 **Index** — `features/README.md` (template `templates/features-README.md.template`):
one row per feature — feature · status (`roadmap · scoped · in progress · in testing ·
shipped`, as scope 5 §4.1 fixes it; `shipped` with no evidence renders `shipped (unproven)`) · last
verdict (date + rung) · file.

8.2 **Feature file** — `features/<feature>.md` (template `templates/feature.md.template`):
a header with status and last evidence, then exactly four H2s: `Sub-features` ·
`How to get to it` (user's point of view) · `Driving it with <cli>` · `Gotchas`.

8.3 **Maintenance handoff** — `artifacts/feature-map-handoff-<unit>.md` in the scope folder
(template `templates/feature-map-handoff.md.template`): result exactly
`clean | changed | blocked` plus the change list (feature · add/update/retire · what ·
evidence). `/closeout` never edits the test-suite; the handoff is applied in that repo or
by `/closeout-extended`.

---

## 9. Adapter — what `/verify` consumes from a product test-suite

**Writer:** the product test-suite (e.g. `wellmed-testsuite`). **Readers:** `verify-run.py`
(finish-table class-A commands call it), `/verify`.

9.1 **Commands:**
- `doctor` — checks the env is reachable and credentials resolve; message per failure.
- `env --json` — the env handle: `{name, url, tenant, credential_ref}`. `credential_ref`
  is a pointer (an SSM path, a keychain item), never the value.
- verbs — the product's journeys and probes, one subcommand each. A verb's `--json` output
  may carry `deployed_version`; the runner records it on the class-A row.

9.2 **CLI rules:** subcommands for progressive disclosure · rich `--help` · `--json` output
on every verb · `--dry-run` on anything destructive · errors per §10.

9.3 **Exit codes:** `0` pass · `1` fail · `2` usage · `3` unreachable (→
`verified-unreachable`, which passes only where the row declared `unreachable_ok`).

---

## 10. Message contract

**Writer:** every script above, plus the judge line and `plans-index.py status`.
**Reader:** a teammate who didn't ask for the gate, or a model reading stderr.

Every error, block and warning carries six fields, with actual values, never placeholders:

```
  [BLOCK] <what happened, one line>
      expected · <what should have been true>
      found    · <what was actually true — values, not adjectives>
      where    · <check_id / file:line / command / repo@sha>
      cause    · code | environment | tooling
      next     · <the exact command to run next>
      docs     · templates/verify-contracts.md §<n>
```

- Levels: `[BLOCK]` stops the gate · `[FAIL]` a check failed · `[WARN]` does not block
  (advisory mode, judge fallback) · `[ERROR]` the script could not evaluate (exit 3).
- `cause` answers the reader's first question — is this my code, or the setup? `code` = the
  change under test; `environment` = the env, network, credentials, or a missing tool the
  row needs; `tooling` = these scripts, the judge, or a malformed contract file.
- `--json` emits the same message as one object with keys `level, what, expected, found,
  where, cause, next, docs`.
- The first four fields match `lint-skill.py`'s `expected · found · where · next`; `cause`
  and `docs` are the additions. Script tests assert every emitted message carries all six.
