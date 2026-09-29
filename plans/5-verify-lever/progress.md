# Progress: `/verify` + the verification lever

## Operating Contract (pinned — survives compaction; re-read on every resume)
1. Scope↔code mismatch = STOP, investigate in-context, report before proceeding.
2. Re-validate each phase's surface against live code before entering it; raise gaps in
   batched blocks, not per-step.
3. Wrap + commit + check in at every phase boundary; progress updates land more often than
   that. This file alone must be enough for a cold context to resume.
4. Public repo: no credentials, tenant names beyond `clinic_3`, internal URLs, or PHI
   posture in anything committed here. Env specifics live in the private test-suite.
5. Dogfood: from Phase 2 on, this scope's own commits go through the codex `/review` gate
   and its phases through `/verify`.

## Resume Context
**Scope:** ~/Projects/ai-skills/plans/5-verify-lever/scope.md
**Last action:** 5.2 Done (2026-09-29): 3 codex review rounds (16 findings, all fixed), `/verify` advisory with 2 blocks accepted by Alex
**Next action:** `/plan 5.3` (Phase 3 — wiring, self-heal, rollout)
**Open blockers:** closeout deferred to scope end (see TO-DO.md)
**Key files changed:** 5.2 — `verify/` (skill, judge, fixtures, demo), `review/` 3.1.0 (rules, review.py), `scripts/codex-exec.py`; full list in `closeout-prep.md` Phase 2 block

---

## Decisions Log
- (2026-09-11) Brief locked: two verification classes, rung not score, feature as the unit,
  codex judge + Claude fallback, lever on second sighting, fail-loud floor. See `artifacts/scope-brief.md`.
- (2026-09-26) Codex is the opposing voice for both `/review` and `/verify`; headless, no herdr.
- (2026-09-26) Every review finding gets a disposition; `/verify` audits rejections.
  Target failure: local maxima (over-building, invented names/contracts/paths).
- (2026-09-26) Review wherever there is a commit; commit-less phases get verify only.
- (2026-09-26) Older scopes self-heal: `/plan` drafts the finish-condition table, Alex confirms once.
- (2026-09-26) Seam: `/verify` defines the adapter contract; the private product test-suite
  fulfils it. Feature map + adapter live in the test-suite, not kalpa-docs.
- (2026-09-26) Test-suite becomes a kalpa-docs program (needs a PRD), scope 89 folded in;
  first member = fail-loud sweep + lints (moved out of this scope, Alex accepted).
- (2026-09-26) Invented-reality check built as a script in this scope (Alex: yes).
- (2026-09-26) `/review` flags dirty comments (workaround / hack / TODO-as-justification).
- (2026-09-26) clinic_3 in dev = temporary trial target; permanent = stood-up tenant per env. *(Superseded 2026-09-29: clinic_3 is not a dev tenant, and the class-A trial moved to test-suite T2 — see the 2026-09-29 entries.)*
- (2026-09-26) Faithful-port rule lives in `/verify`, not global CLAUDE.md.
- (2026-09-26) Brief's credentials redacted (`eaeb441`); brief moved to `artifacts/`.
- (2026-09-26) CEO review: approach C — a deterministic row passes only on runner evidence; the codex judge may only downgrade. Required fail/inconclusive blocks; latest run per check decides; evidence bound to SHAs. Gate enforced by plans-index.py, advisory for 3 clean scopes then blocking. Non-codex judge → ⚠ in PLANS-INDEX (Alex's D3 idea).
- (2026-09-26) Codex CLI upgraded 0.152.1 → 0.157.1 (npm) — the old CLI rejected gstack's model; live evidence for the judge-failure handling (F2).
- (2026-09-26) Phase 1 contracts approved as written: one normative spec (`templates/verify-contracts.md`), `verify-run.py` sole verdict-log writer, table revision bump invalidates verdicts, every row required, message contract = lint-skill's four fields + cause + docs.
- (2026-09-26) Disposition coverage is enforced by `verdict-gate.py`, not `/verify` judgment — so it can't drift.
- (2026-09-26) Evidence from a dirty working tree is accepted: verification is pre-PR. Contract §5.2.
- (2026-09-26) No `/clear` at the 5.1 → 5.2 boundary; proceed straight into Phase 2. Closeout deferred to scope end.
- (2026-09-29) Phase 2 approved at gate A (Alex). **Miss, owned:** Operating Contract #5 (this scope's Phase 2+ commits through the codex `/review` gate, its phases through `/verify`) was not applied to ai-skills' own 5.2 commits. `/review` ran only on the WellMed branch. So 5.2 is not marked Done until both run; the next session does that first. `plans-index.py status` would refuse Done anyway, since 5.2 owns no finish-table rows yet and the gate exits 3.
- (2026-09-29) A dev-tenant identity question was resolved; the per-env tenant allowlist is recorded in test-suite T2 (private), and the tenant-identity-in-header TO-DO is in kalpa-docs `plans/TO-DO.md` (section "Tenant identity is invisible in the app"). *(Redacted 2026-09-29 per review 5.2-r1-01: tenant specifics belong in the private test-suite, Operating Contract #4.)*
- (2026-09-29) Class-A proof (Task 2.4 part B: the three-outcome trial) **moves to the kalpa-docs test-suite program, member T2 (WellMed adapter)**, together with a login/token CLI, as T2 deliverables (kalpa-docs `plans/test-suite-program/T2-wellmed-adapter/NOT-YET-SCOPED.md`; committed there, and pushing kalpa-docs is Alex's call because its `main` carries another session's work. Check with `git -C ~/Projects/wellmed/kalpa-docs status -sb`). Scope 5 proves class B only. Credential model stays open (Alex: no skeleton key; scoped to test/demo DBs).
- (2026-09-29) **Codex model is a family, `sol`, not codex's default** (Alex; supersedes the 2026-09-26 "no pinned model" in scope.md §4.2 / plan 5.2 Task 2.1). The unpinned default had drifted from `gpt-6-sol` to `gpt-6-astra` (frontier) and ran at effort `high`, which burned the workspace's credits. `codex-exec.py` now resolves `VERIFY_CODEX_MODEL` (default `sol`) from codex's model cache to the current `*-sol` slug and follows retirement upgrades. Unresolvable, or a banner naming another model, is `none …`. Effort stays `high` (Alex), since that is what the spike and the demos ran on.
- (2026-09-29) **5.2 `/verify` blocks accepted (Alex).** (a) `p2-fixtures` inconclusive: its row runs without `VERIFY_EVAL=1`, so the live-judge tier is skipped. Not re-run now; **fixture rows must set `VERIFY_EVAL=1` from here on** (TO-DO → 5.3's standard rows). (b) `p2-scope-deliverables` fail on class A via `/browse`: **amended.** Class A runs through adapter commands in runner rows; browser driving belongs to the test-suite T2 WellMed adapter, not to `/verify` (its judge only reads disk and git). (c) Review r3's fix `7ffd7e5` was not re-reviewed by codex; Alex accepted its fixed + tested disposition. 5.2 marked Done with the advisory marker.
- (2026-09-29) **5.3 design answers (Alex).** (1) Scopes already running are never asked to reconcile verify: self-heal writes `**Predates gate:** <done phases>` into the drafted table (`validate` exempts them) and drafts rows only for phases not yet started — "don't give the team a bad taste before they try it". (2) `/closeout` prints a running count of clean gated scopes; **the advisory → blocking flip is at 5, not 3**, and the count line is the reminder to flip `GATE_MODE`. (3) Fresh-clone walkthrough under a throwaway `HOME`, validated. (4) `setup.sh` checks codex installed + logged in only; the live ping stays in `/verify --demo`. (5) Lever candidates carry a required `lever_id` slug (automatic ones `<check_id>-<result>`); second sighting = same `lever_id` from a different scope or run.

---

## Progress Log

| Date | Skill/Action | Status | Notes |
|------|--------------|--------|-------|
| 2026-09-11 | brief | Done | Placeholder brief — pain, pstack take/leave, locked design |
| 2026-09-26 | /research (scope 6 live test) | Done | poteto since 2026-09-11 → `artifacts/research-poteto-2026-09-26.md` |
| 2026-09-26 | /scope | Done | Phased, 3 plans (5.1–5.3), each exits on gate A |
| 2026-09-26 | /plan-ceo-review | Done | HOLD SCOPE; approach C (scripts + runner evidence floor, codex judge downgrade-only). Codex outside voice: 11 findings, 7 new. All 17 accepted → `artifacts/ceo-review-2026-09-26.md` |
| 2026-09-26 | /plan-eng-review | Done | 7 Claude + 9 codex findings, all accepted → `artifacts/eng-review-2026-09-26.md`; test plan → `artifacts/eng-review-test-plan-2026-09-26.md`. CEO + ENG CLEARED |
| 2026-09-26 | /plan-devex-review | Done | Triage. Getting started 3→8 (setup warns, `/verify --demo`, README section), errors 4→8 (message contract with cause class), stale-clone warning → `artifacts/devex-review-2026-09-26.md` |
| 2026-09-26 | Unplanned fix | Done | `scripts/plans-index.py`: `add` accepts per-plan `N.P` numbers; duplicate check compares the exact `#` cell (70d1222). Found by /scope §5.9 — stub rows were refused as non-integer |
| 2026-09-26 | /plan | Done | 5.1-verify-lever-PLAN.md complete — contracts spec + templates, resolve-identifiers.py, verify-run.py, verdict-gate.py, plans-index status/validate, ledger-init base SHA; 62 tests. Alex approved at gate A. TODOs extracted to TO-DO.md (closeout deferral only) |
| 2026-09-29 | /plan | Done | 5.2-verify-lever-PLAN.md complete — /verify, /review 3.1.0 on codex, fixtures + `--demo`, codex model family `sol`; own review r1–r3 (16 findings fixed) and /verify advisory, 2 blocked (Alex accepted). TODOs extracted to TO-DO.md |

---

## Human Steps

| Step | Status | Notes |
|------|--------|-------|
| Approve the Phase 1 contracts (finish table, verdict, disposition log, feature map, adapter) | [x] Done 2026-09-26 | 5.1 exit gate |
| Go/no-go after seeing a real `/verify` verdict (dogfood, class B) | [x] Done 2026-09-29 — go, advisory rollout | 5.2 exit gate; class-A trial moved to test-suite T2 |
| Announce the ai-skills `git pull` to the team after rollout | [ ] Pending | 5.3 exit gate; CLAUDE.md §2.1 |

---

## Plans

| # | Plan File | Phase | Status | Notes |
|---|-----------|-------|--------|-------|
| 5.1 | 5.1-verify-lever-PLAN.md | Phase 1 — Contracts + deterministic scripts | Done | Gate A — approved 2026-09-26 |
| 5.2 | 5.2-verify-lever-PLAN.md | Phase 2 — `/verify` + `/review` on codex | Done | Gate A — approved 2026-09-29; ⚠ verify advisory: 2 blocked |
| 5.3 | 5.3-verify-lever-PLAN.md | Phase 3 — Wiring + self-heal + rollout | Ready to execute | Gate A |

---

## Artifacts
- `artifacts/scope-brief.md` — the 2026-09-11 brief (pain, pstack, locked design)
- `artifacts/research-poteto-2026-09-26.md` — poteto research + Complete Guide Pt. 1 notes
- `artifacts/ceo-review-2026-09-26.md` — CEO review + codex outside voice, 17 accepted findings
- `artifacts/eng-review-2026-09-26.md` — eng review + codex outside voice, 16 accepted findings
- `artifacts/eng-review-test-plan-2026-09-26.md` — test plan (edge cases + critical paths)
- `artifacts/devex-review-2026-09-26.md` — DX triage review, persona, scorecard

---

## Plan 5.1: Contracts + deterministic scripts

### Resume Context (Plan 5.1)
**Last action:** Plan complete — 5/5 tasks done; Alex approved Phase 1 (2026-09-26)
**Next action:** none — continues in Plan 5.2
**Open blockers:** None

### Task Detail
Deepened at start of run (`/markdown-style` §8.9.2), from scope.md §4.1 + eng review. The
plan file is unchanged; where this block and the plan differ, the plan wins, so ask.
- **1.0** — `scripts/tests/` (`_helpers.py` runs scripts as subprocesses or loads them by
  path, since hyphenated names can't be imported) + `test_entrypoint.py` (compile-checks every
  `scripts/*.py`). CLAUDE.md §6 `Test:` line (the field `/closeout` §5.2 detects first);
  scripts/README.md gets a Tests note. **Deviation:** the plan allowed "0 tests is a pass",
  but on Python ≥ 3.12 `unittest discover` exits 5 when no tests run, so the entrypoint ships
  with one real test.
- **1.1** — templates in `templates/`, filled examples in `templates/examples/`. Each contract
  opens with a reader/writer header. Plus `scripts/tests/test_contracts.py`: generate each file
  from its template, assert no example rows. Stop for Alex's review.
- **1.2 `resolve-identifiers.py`** — two input modes: `--range BASE..HEAD` extracts
  references from the added lines of source files, or `--ids FILE` takes JSONL
  `{kind,name,namespace?,file?,line?}` (the judge's feed). References resolve against the
  HEAD tree, so a declaration added in the same diff counts; `--decl-repo` adds cross-repo
  declaration roots. Kinds and namespaces: **env** declared in `.env*.example|sample|template`
  / compose `environment:` in the using file's directory or an ancestor (a sibling service's
  file doesn't count); **ssm** declared in `*.tf` `name =`, `FLEET.md`, or `ssm*` files, with
  segment-placeholder matching; **proto** is Go composite literals and Python `_pb2` kwargs
  against the named message's fields in `*.proto`; **route** covers fetch/axios/http client
  paths against router registrations (gin/echo/express/Laravel/mux); a suffix match under a
  group prefix resolves but is labelled. Comment lines and fixture paths never count as
  declarations or as uses. Any other kind counts as unsupported. Exit codes: 0 all resolved,
  1 anything unresolved or unsupported, 2 usage, 3 git error. Unresolved references print
  per §10.
- **1.3 `verify-run.py`** — subcommands `run` (pending), `judged` (records the judge's JSON
  output), `finalize` (§5.1 authority rule, one `final` line). Parses the finish table with
  `\|` unescaping and blank-cell errors; `--owner` selects rows; each row runs in
  `~/Projects/<repo>/<dir>` with its env overlay and timeout; exit codes map per §4.7.
  Class-A records are refused into a public-denylisted or non-git destination. Every write
  is followed by a read-back.
- **1.4 `verdict-gate.py`** — §5.2 + §5.2.1 (disposition coverage) + §5.3 marker + §5.4
  advisory/skip. `ledger-init.sh --repo PATH` records `base: <repo> <sha>` in the phase
  block. `plans-index.py status` runs the gate before writing Done. `plans-index.py
  validate` checks Done phase rows **only in scopes that have a `finish-conditions.md`** —
  older scopes are exempt until self-heal, or every historical row would fail.
- Tests follow the eng review's coverage map (`artifacts/eng-review-2026-09-26.md` §2).
  Every emitted message is asserted to carry the six §10 fields.

### Session: 2026-09-26 (Alex / Claude)
- **Phase 0** ✅ DONE. Input and related-doc paths all resolve. Status is Ready (Alex's go
  signal, 8173b95). `Executed by` was stamped. Repo Graph check exited 4 because the numbered
  heading doesn't match what the script looks for; this is a single-repo scope with linear
  history, and it's logged as a ledger risk flag. herdr pane present, but Primary repo is none,
  so no worktree. Ledger created. Branch: `main` (direct-to-main per CLAUDE.md §2). Sibling
  plans 5.2 and 5.3 read.
- **Unplanned (before Phase 0):** `/markdown-style` §8.9.2/§11.5.3 contradicted `/plan` §8.1
  on stub deepening. Resolved: detail goes in progress.md. Files: `markdown-style/SKILL.md`,
  `plan/SKILL.md`, `scope/templates/plan-stub.md.template` (e8bdc4d, pushed).

#### Task 1.0: Test entrypoint — ✅ DONE
- **Files created:** `scripts/tests/_helpers.py`, `scripts/tests/test_entrypoint.py`
- **Files modified:** `CLAUDE.md` (§6 `Test:` line + suite note), `scripts/README.md` (Tests note)
- **Verified:** `python3 -m unittest discover scripts/tests` → 1 test OK, exit 0; `grep '^Test:' CLAUDE.md` hits

#### Task 1.1: Contract documents — ⏸️ WAITING_HUMAN (review)
- **Files created:** `templates/verify-contracts.md` (the spec, §1–§10); templates
  `templates/finish-conditions.md.template`, `features-README.md.template`, `feature.md.template`,
  `feature-map-handoff.md.template`; examples `templates/examples/finish-conditions.md`,
  `verify-log.jsonl`, `review-log.jsonl`, `features/README.md`, `features/sign-in.md`,
  `feature-map-handoff.md`; `scripts/tests/test_contracts.py`
- **Verified:** suite 10 tests OK. Mutation check: a planted table row, and a row parked in an
  HTML comment, are both caught by the detector.
- **Design calls for Alex:** one normative spec, with templates only for files that get
  generated per scope. `verify-run.py` is the only writer of the verdict log, for all three run
  states. A table revision bump invalidates earlier verdicts. Every row is required. The message
  contract is lint-skill's four fields plus `cause` and `docs`.

#### Unplanned: `repo-graph-check.py` numbered heading + empty-section false pass (Alex: fix now)
- **Files modified:** `scripts/repo-graph-check.py`, `plan/SKILL.md` (§5.6.1 exit-4 wording, 3.8.2)
- **Files created:** `scripts/tests/test_repo_graph_check.py`
- **Why:** the heading regex missed `## 2. Repo Graph`, the numbering `/markdown-style`
  requires. Fixing only that would have exposed a second defect: a prose-only section parses
  to zero rows and printed "all unchanged — proceed", a false pass. Both are fixed, and both
  are covered by table-driven tests. Scope 5 now returns exit 4, "nothing was checked".
- **Verified:** suite 12 tests OK.

#### Task 1.1 — ✅ DONE (Alex approved contracts 2026-09-26)
- Alex also decided that disposition coverage (every finding ID dispositioned) is enforced in
  `verdict-gate.py` rather than by `/verify` judgment, so it can't drift. Spec §5.2/§6
  updated to match. This adds to Task 1.4.

#### Task 1.2: `scripts/resolve-identifiers.py` — ✅ DONE
- **Files created:** `scripts/resolve-identifiers.py`, `scripts/tests/test_resolve_identifiers.py`
- **Files modified:** `scripts/README.md` (table row)
- **Verified:** suite 19 tests OK. Every acceptance case is covered: comment-only name fails,
  unrelated-proto name fails, same-diff declaration passes, fake env var fails, unsupported
  kind is reported and never green. Also covered: fixture-only declarations, sibling-service
  namespace, SSM placeholders, routes (params / suffix / method), empty range → exit 3,
  cross-repo `--decl-repo`, `--json`, and all six §10 fields on every failure.
- **Smoke against real WellMed history (read-only, last 30 commits, 4 repos):** the first run
  showed two false-positive classes. Gateway env vars are declared as SSM paths in
  `wellmed-infrastructure/ssm/parameters/*.json`, and gateway protos come from generated
  `.pb.go` files whose `.proto` lives in backbone. Both are now declaration sources, the
  SSM one namespaced by service segment or `shared/`. After the fix: 213 references, 207
  resolved. The 6 unresolved are all in `wellmed-cashier/cmd/reproject-ledger/main.go`,
  env vars declared nowhere, so true positives by the rule.

#### Task 1.3: `scripts/verify-run.py` (runner) — ✅ DONE
- **Files created:** `scripts/verify-run.py`, `scripts/verify_lib.py` (shared parser, message
  formatter and verified appender, so the runner and gate can't disagree),
  `scripts/tests/test_verify_run.py`
- **Files modified:** `scripts/resolve-identifiers.py` (uses `verify_lib.message`),
  `templates/verify-contracts.md` (§4.3 `cwd` + `output_tail`; §9 `deployed_version`),
  `scripts/README.md`
- **Verified:** suite 38 OK. Every acceptance case is covered: pass, fail, non-executable,
  timeout, resolved context recorded when run from a foreign cwd, public-repo refusal (plus
  non-git refusal, and class-B-about-another-repo refusal in a public repo), and read-back
  failure → exit 3. Also covered: judged + finalize authority rule (downgrade only, judge row
  takes the judge verdict, lower rung wins, `none` judge), malformed judge output writes
  nothing, double finalize refused, table defects exit 3 with `cause code`. Mutation check:
  letting the judge upgrade a fail is caught by `test_authority_rule`.
- **Note:** I removed an `except: pass` in the first draft, the silent-failure pattern
  Phase 2's `/review` will flag.

#### Task 1.4: `verdict-gate.py` + index enforcement + base SHA — ✅ DONE
- **Files created:** `scripts/verdict-gate.py`, `scripts/tests/test_verdict_gate.py`
- **Files modified:** `scripts/plans-index.py` (`status` command; `validate` catches a Done
  phase row with no passing verdict and no ⚠ marker), `scripts/ledger-init.sh` (`--repo`
  writes `- base: <unit> <repo> <sha>`; the first base is kept on resume), `scripts/verify_lib.py`
  (`GATE_MODE = "advisory"`, `PROJECTS`), `scripts/README.md`
- **Verified:** suite 61 OK. Every acceptance case is covered end to end through the real
  runner: pass, missing, under-rung, fail-then-fixed clears, runner row downgraded blocks,
  judge row passes on the judge verdict, pending blocks, undeclared-unreachable blocks,
  stale SHA rejected (both with and without a base), hand-edited Done caught by validate,
  fallback marker set then cleared, advisory warns without blocking. Also covered: disposition
  coverage (Alex's §5.2.1), table-revision change, skip-verify needing a reason, a scope with
  no table being exempt, blocking `status` refusing and leaving the row untouched, and all six
  §10 fields on the refusal. Mutation checks: disabling the range check or the rung check each
  fails its test.
- **Bugs caught by the fail-loud design, before landing:** (1) ledger-init's read-back grep
  took the `- base:` line as an option and exited 1. The line had landed; the check failed
  loud instead of passing silently. Fixed with `-e`, and the fixture now asserts ledger-init's
  exit code. (2) I wrote a `2>/dev/null` into ledger-init; replaced it with an explicit
  projects-root check. Runs under macOS's bash 3.2.
- **Real index:** `plans-index.py validate plans/PLANS-INDEX.md` is still conformant.

#### Checkpoint prep — live demo + one DX fix
- Demo in scratchpad: a throwaway app plus a finish table with `resolve-identifiers.py` and
  `node --check` rows. A planted `process.env.API_KEY_TYPO` fails the runner, blocks the gate
  (blocking), and is marked `⚠ verify advisory: 1 blocked (names-resolve)` in advisory mode.
- **DX fix:** gate blocks now carry the runner's first `[FAIL]` line, or failing that its last
  output line, in `found`. Before, the output said only "exit 1" and the reason sat in the
  verdict log. Files: `scripts/verdict-gate.py`, `scripts/tests/test_verdict_gate.py`.
  Suite 62 OK.

---

## Plan 5.2: `/verify` skill + `/review` on codex

### Resume Context (Plan 5.2)
**Last action:** Plan complete — 4/4 tasks done; own review + /verify run; marked Done (Alex, 2026-09-29)
**Next action:** none — continues in Plan 5.3
**Open blockers:** None

### Task Detail
Deepened at start of run (`/markdown-style` §8.9.2). Where this block and the plan differ,
the plan wins, so ask — **except where the Decisions Log records a change Alex made**.

**Alex-approved deviations from the plan file** (the plan file is never edited, `/plan` §8.1,
so they live here; `/verify` of 5.2 judges against the plan *as amended here*):
- **Task 2.4 Acceptance is class B only** (Alex, 2026-09-29). "All three trial outcomes observed
  through the runner" on "dev clinic_3" is **removed from 5.2**, and the class-A trial is a
  deliverable of kalpa-docs `plans/test-suite-program/T2-wellmed-adapter/NOT-YET-SCOPED.md`.
  (The target was also wrong: `clinic_3` is not a dev tenant.) The 5.2 finish rows
  record this exemption.
- **The plan file's `Status: Ready to execute` is left as written.** Execution state lives in
  this file and the index. A fresh `/plan 5.2` resumes from the Resume Context above, not from
  Phase 0.
- **2.1** — how codex gets called is shared with 2.2's `/review`, so it's a shared script:
  `scripts/codex-exec.py`.
  - `probe` runs `codex --version`, then a `codex exec` ping with stdin closed (without that,
    codex waits on stdin and a headless run hangs). The model is read from stderr's
    `model:` banner line; the JSON event stream carries none. Output is `codex <model>`, or
    `none <reason>` for each failure mode.
  - `exec` runs a prompt read-only with `--output-schema`, `--ephemeral` and a timeout.
  - `VERIFY_CODEX_BIN` lets the tests supply fake codex binaries for every F2 failure mode.
  - `/verify`-private: `verify/prompts/judge.md`, `verify/schemas/judge-output.schema.json`,
    and `verify/scripts/judge.py`. `prepare` renders the prompt from disk (the run's pending
    records, the unit's range from the ledger bases). `record` validates the judge output
    (every check_id covered, finding shape), writes verdicts through `verify-run.py judged`,
    and keeps the raw output as `artifacts/verify-<unit>-judge-<run_id>.json`.
  - codex and the Claude fallback both go through `prepare` + `record`; only the executor
    differs, so the fallback can't take a different path.
  - `verify/SKILL.md` flow: resolve → empty-range check → runner → probe → judge (codex /
    claude-fallback subagent / none) → finalize → gate → report
    (`artifacts/verify-<unit>-report.md`).
  - Lenses (over-build, invented reality, rejection audit, test plan, faithful port) are
    judged through standard finish-table rows the skill documents; `/scope` emits them in
    5.3.
  - `bases()` moves into `verify_lib`, since both the gate and `judge.py` read it.
- **2.2–2.4** — detail written when each starts.
- **Model (amendment, Alex, 2026-09-29):** Task 2.1's "no pinned model" is replaced by a model
  family (`sol`) resolved from codex's cache. See the Decisions Log.
- **Class A (amendment, Alex, 2026-09-29):** scope §4.2's "drives the product through the adapter +
  `/browse`" is narrowed for 5.2 to adapter commands in runner rows; `/browse` driving is T2's.

### Session: 2026-09-26 (Alex / Claude, continued)
- **Phase 0** ✅ DONE. Status is Ready. `Executed by` was stamped. The ledger phase block
  records `base: 5.2 ai-skills e3b74ec…`, the first real use of `--repo`. Inputs resolve.
  codex-cli 0.157.1 is present; the probe ping answered `pong` on model `gpt-6-sol`. No
  `/clear` at the boundary, per Alex.

#### Task 2.1: `/verify` skill — ✅ DONE
- **Files created:** `verify/SKILL.md` (v0.1.0), `verify/prompts/judge.md`,
  `verify/schemas/judge-output.schema.json`, `verify/scripts/judge.py`, `scripts/codex-exec.py`,
  `scripts/tests/test_codex_exec.py`, `scripts/tests/test_judge.py`
- **Files modified:** `scripts/verify-run.py` (exports `VERIFY_BASE`/`VERIFY_UNIT` from the
  ledger, so a static `names-resolve` row can name the range), `scripts/verify_lib.py`
  (`bases()`), `scripts/verdict-gate.py`, `templates/verify-contracts.md` §4.3,
  `scripts/tests/{_helpers,test_verify_run}.py`, `README.md`, `ARCHITECTURE.md`, `CLAUDE.md`
- **Verified:** `lint-skill.py verify` is clean. `setup.sh` linked
  `~/.claude/skills/verify`, and the skill appears in this session's skill list. Suite 75 OK:
  every F2 codex failure mode ends as a `none …` line (not installed, not authed, model
  unusable, crash, timeout, empty, refusal, malformed, non-object, no model banner), and a
  stale answer file is never reused. judge.py covers prepare from disk, the empty-range and
  no-range refusals, malformed answers recording nothing, and the report's automatic lever
  candidates.
- **Live e2e with real codex (`gpt-6-sol`), scratchpad demo scope:** the runner failed
  `names-resolve` on a planted `API_KEY_TYPO`. Codex, reading only disk and git, confirmed
  it, passed `app-parses`, and independently failed the judge row `scope-deliverables` at
  rung 2, citing `.env.example:1`. Record → finalize → gate reported `ADVISORY — would block
  (2)` with findings ranked. The first real use of `--output-schema` accepted our schema.
- **Found along the way:** codex waits on stdin unless it's closed (a headless hang); the
  model name is only on stderr's banner, not the JSON events. Both handled in
  `codex-exec.py`. I removed a hidden `--allow-empty` flag from my own draft.

#### Task 2.2: `/review` onto codex (spike first) — ✅ DONE (Alex approved 2026-09-26)
- **(a) Spike** → `artifacts/review-codex-spike-2026-09-26.md` (public, so classes and counts
  only). Codex alone on the WellMed 108.6 pre-fix diff (`gpt-6-sol`, 262 s) caught **4/6**
  of the original findings, **including both criticals**. It missed a doc claim and an
  over-broad deletion. It raised 6 findings the original review didn't have (unverified).
  Codex listed what it can't do itself: no network, no live services or browser, no
  write-side tests, no specialists.
- **(b) Migration.** `review/SKILL.md` 2.2.0 → **3.0.0**: codex is the gate, the Claude pass
  (gstack engine + the same rules) is the fallback with a DEGRADED header, an explicit
  range is required (empty = failure), and every finding gets a disposition. §3's domain
  rules moved **verbatim** into `review/rules/domain.md`; §1.1.1–1.1.2 plus the new lenses
  (silent failure, local maxima, dirty comments, and a doc-claim lens added because of the
  spike's miss) are in `review/rules/lenses.md`. `review/scripts/review.py` `prepare` /
  `record` / `dispose` is the review-log writer; `dispose` refuses a `fixed <sha>` that
  doesn't touch the finding's file. Contract §6 updated.
- **Files:** created `review/{rules/domain.md,rules/lenses.md,prompts/review.md,schemas/review-output.schema.json,scripts/review.py}`,
  `scripts/tests/test_review.py`, the spike note. Modified `review/SKILL.md`,
  `templates/verify-contracts.md`, `ARCHITECTURE.md`, `CLAUDE.md`.
- **Acceptance (live, real codex, scratchpad repo on `main`, explicit 1-commit range):**
  the planted `|| true` → blocking silent-failure; the workaround comment → blocking
  dirty-comment; the invented `PAYMENT_KEYZ` → should-fix. Codex also found two unplanted
  real defects (`res.ok` never checked, so a declined charge reads as success; a build step
  with no package.json). The range was reviewed, not reported empty. All 5 IDs were
  dispositioned; a `fixed` claim using a commit that didn't touch the file was refused;
  the gate's coverage check came back empty. `lint-skill.py review` clean. Suite 82 OK.

#### Unplanned (Alex-directed): fix the 6 spike findings in the private infra repo
- Alex, at the Task 2.2 review: "don't TO-DO them — fix them." All 6 were verified before
  fixing, against current `develop` and live data (read-only), and all 6 were real. Fixed on
  a branch in the private infra repo, 4 commits (**superseded 2026-09-29:** pushed, PR opened
  against `develop` with Alex's OK; merge and deploy are Alex's).
   Details stay in that repo's commit messages; this public repo gets classes only:
  3 dashboard fail-open queries (a slot-unaware liveness panel reading a service
  permanently DOWN; empty-vector fallbacks reading green on missing telemetry; a
  vanished-job blind spot), 1 fail-open deploy verification (`rsync | sed` without
  pipefail), and 1 exclude-list packaging hole with a comment claiming otherwise.
- **Dogfood:** new `/review` 3.0.0 on that branch. Round 1 found 1 blocking + 3 should-fix
  *in my fix* (expected state computed from a different tree than the package; per-job
  presence; a lookback-bounded inventory; no regression test). All were addressed, plus a
  new regression test wired into CI. Round 2: **SHIP**, 0 blocking. One follow-up was fixed;
  one (query-level regression tests for dashboard panels) was deferred, since that repo has
  no PromQL panel-test harness.
- **Self-inflicted bug caught before it shipped:** a scripted block move matched the
  heredoc opener `<<SYNC` as its end marker and swallowed the upload step into the remote
  script text. The staged test run exposed it (empty `cat`, wrong step order); it was
  repaired with guarded line moves and re-verified by the full diff and the test. Nothing
  ran against the host.

#### Task 2.3: Verifier fixtures + `/verify --demo` — ✅ DONE
- **Files created:** `verify/tests/fixtures/notes/` (base repo tree, `parts/`, README listing
  the six planted defects), `verify/scripts/fixture.py` (builder: `bad` / `clean` /
  `repaired-<defect>`; every variant differs from the control in exactly the defects it names),
  `verify/scripts/demo.py` (`/verify --demo`; `--check` is the eval),
  `scripts/tests/test_verify_fixtures.py`
- **Files modified:** `verify/SKILL.md` 0.2.0 (§2.0 `--demo`), `ARCHITECTURE.md`, `CLAUDE.md`
- **Planted defects → caught by:** invented env var → `names-resolve` (runner) · over-build →
  `no-overbuild` (judge) · missing evidence → `changelog-entry` (judge) · under-rung → gate ·
  rejection without a reason → gate coverage · dropped finding → gate coverage.
- **Verified:** the deterministic tier (always in the suite) covers bad blocking every
  script-caught defect by name, the control clean, each repaired copy clearing exactly its
  defect, `judge: none` unable to pass the control, an always-failing judge failing the
  control, and `demo.py --check` exiting 1 with no codex. The judge tier (`VERIFY_EVAL=1`),
  run live: **all 6 caught, control passes** (`demo.py --check`, 95 s), and both judge-caught
  repaired copies pass their row (285 s for the tier). Suite 91 OK, 2 skipped (live-judge
  tier, opt-in).

#### Task 2.4: Dogfood + three-outcome trial — ✅ part A done · part B moved to test-suite T2 (Alex, 2026-09-29)
- **Part A — `/verify` class B on Phase 1 (live codex `gpt-6-sol`).** Created
  `finish-conditions.md` (rev 3; the Phase 1 rows are retroactive) and a retroactive ledger
  base for 5.1 (`8173b95`). Three runs; the verdict of record is `5.1-20260926T100859-79e8`:
  **advisory, 4 blocked**, and codex passed `no-overbuild` and `contracts-generate-clean`.
  The dogfood found real Phase 1 defects, **all fixed in 5.2** (`e4aaa0a`, `36625e4`):
  1. `VERIFY_PROJECTS` read but never declared, with CLAUDE.md §5 saying "N/A" →
     `.env.example` plus a corrected §5.
  2. The gate trusted `final.results`, contrary to contract §5.1, so a forged final passed →
     the gate re-checks the authority rule (shared `verify_lib.authority`), and a test forges
     one.
  3. I **invented** the feature-map status vocabulary instead of using scope.md §4.1's → aligned.
  4. The resolver "resolved" a route by assuming an unseen prefix → gin/echo `Group()`
     prefixes are followed and a suffix-only match is unresolved.
  5. Resolver false positives from source embedded in test files → test files skipped for
     every kind.
  Codex also caught me **moving the goalposts** (`--decl-rev HEAD` for a closed unit). That
  was reverted, so Phase 1 is judged against its own declarations. Retroactive runner rows
  ran at today's HEAD and were downgraded to inconclusive; that's correct, and a pinned-SHA
  runner is recorded as a lever candidate.
- **Index enforcement on real data:** with the table present, `plans-index.py validate`
  flagged 5.1's hand-written Done. `status` then wrote `⚠ verify advisory: 4 blocked (…)`,
  and validate is conformant again.
- *(Superseded 2026-09-29: part B moved to test-suite T2 — see the Decisions Log. The record
  below is kept as it was written.)*
- **Part B — class-A trial: BLOCKED, two plan↔reality mismatches** (Operating Contract #1):
  `clinic_3` is not a dev tenant (kalpa-docs scope 89 artifacts); and the login needs a
  gateway credential secret that is **not** in the test-suite (details in the private
  test-suite; redacted per review 5.2-r1-01). Reading
  SSM values is a documented human step for agents. Needs Alex: target confirmation plus the
  secret in a local file outside all repos.
- Suite: 93 OK, 2 skipped (live-judge tier).

### Session: 2026-09-29 (Alex / Claude) — closing 5.2 (Operating Contract #5)
- **Review 5.2-r1** (codex `gpt-6-astra`, `e3b74ec..HEAD`, 58 files): DO NOT SHIP, 5 blocking + 4 should-fix
  → `artifacts/review-5.2-r1.md`. Alex: fix all 9; the leak is redacted in HEAD only (no history rewrite).
  Each fix is its own commit with a regression test that fails on the old code (mutation-checked):
  - r1-01 public-doc leak (tenant identity, env mapping) redacted — `bf210ec`
  - r1-02 resolver group prefixes leaked across functions — `35f8914`
  - r1-03 a `none` judge could pass a judge row — `56c01ae`
  - r1-04 + r1-07 review-ID races / clean reviews reusing IDs; gate blocks duplicate IDs — `4f242fd`
  - r1-05 `judge.py report` swallowed gate errors — `504b542` (`verify` 0.2.1)
  - r1-06 answer writers didn't enforce their schemas — `3dac519` (`verify_lib.schema_problems`)
  - r1-08 fallback-review ⚠ marker never set — `35384dc` (the dispose guard refused my first SHA,
    which didn't touch the cited file; the claim text was made precise in the same commit)
  - r1-09 demo eval counted an inconclusive judge as a catch — `3a6a1f2`
  Gate coverage: 9/9 dispositioned. Suite 100 OK, 2 skipped. Live demo (real codex) after the
  stricter eval: all 6 defects caught, control passes.
- **Finish table rev 4** — 9 rows for 5.2 (6 runner, 3 judge). The revision bump makes 5.1's verdict
  "predates the table" in the gate; 5.1 is already Done with its ⚠ advisory marker, so nothing changes in the index.
- **Runner** `5.2-20260929T021032-cd55`: 6/6 runner rows pass; judge rows pending.
- **Blocked: codex workspace out of credits.** The re-review (5.2-r2 on `c8c049b..HEAD`) returned
  `none codex not authed`, and a direct `codex exec` printed "Your workspace is out of credits".
  **Defect found:** `codex-exec.py` classifies out-of-credits as "not authed" (exec) or "exited 1"
  (probe), so the reported cause is wrong.
- **Model right-sizing (Alex).** The codex default had drifted to Astra at effort `high`, so it now
  resolves a `sol` family from codex's cache, and out-of-credits is classified correctly —
  `0aefa7f`. Live probe: `codex gpt-6-sol`.
  Blocked on Alex: `.env.example` is permission-denied to the agent, so `VERIFY_CODEX_MODEL` and
  `CODEX_HOME` are not declared yet; the resolver flags both (`p2-names-resolve` would fail).
- **Reviews 5.2-r2 / r3** (codex `gpt-6-sol`): r2 found 5 in the r1 fixes, and r3 found 2 in r2's
  coverage fix (immutable SHAs). All were fixed with regression tests that fail on the old code:
  `5136307` `5d0629e` `63f353b` `f4db4b0` `26eed12` `7ffd7e5`. `/review` is now 3.1.0 (`record`
  requires the immutable range from `prepare`). `.env.example` has the two new variables (Alex, `df9f218`).
- **/verify 5.2** run `5.2-20260929T031136-b3a2`, judge `codex gpt-6-sol`: 7/9 pass. `p2-fixtures` is
  inconclusive (live-judge tier skipped) and `p2-scope-deliverables` fails (no `/browse` class-A step),
  so advisory, 2 blocked → `artifacts/verify-5.2-report.md`. Both accepted and amended by Alex
  (Decisions Log). Marked Done.

---

## Plan 5.3: Wiring + self-heal + rollout

### Resume Context (Plan 5.3)
**Last action:** Phase 0 done; Task Detail drafted, awaiting Alex's answers to the design questions
**Next action:** Task 3.3a (ledger-template fix) once Alex confirms the outline
**Open blockers:** Alex — design questions (session 2026-09-29)

### Task Detail
Deepened at start of run (`/markdown-style` §8.9.2). The plan file wins where they differ,
so ask, except where the Decisions Log records a change Alex made.
- **Order:** 3.3a ledger template first (it is standalone and every later ledger inherits it),
  then 3.1 → 3.2 → 3.3 → 3.4.
- **3.1 `/scope`** — new Step 5.10 writes `finish-conditions.md` through a script
  (`scripts/finish-table.py init`, template + the standard rows of `verify/SKILL.md` §4 per
  phase, then `add` for deliverable rows, each bumping Revision + a Changelog line — the
  revision discipline is deterministic, CLAUDE.md §3.6.1). The plan-stub template gains
  `Review` (commit-producing phases only) and `Verify` tasks before the CHECKPOINT; the
  presence of the Review task is the phase's "this commits" declaration, which is what
  makes an empty range a failure rather than an expected nothing. Eval rows set
  `VERIFY_EVAL=1` (5.2 TO-DO).
- **3.2 `/plan`** — §5.13 passes `--repo` for every repo the plan commits to; new section
  for the Review task (explicit `base..HEAD`, `--scope/--unit`, dispose every ID) and the
  Verify task (`/verify N.P`), then Done only via `plans-index.py status` (the gate).
  `--skip-verify "<reason>"` passes through and shows in the §6.7 header. Self-heal in
  Phase 0: no table → `finish-table.py init` draft from the scope's remaining phases + its
  deliverables, one halt for Alex. Already-Done phases are marked as predating the gate so
  `validate` doesn't flag them (see question 2). Recipe 4 in `plan/tests/verification-recipes.md`.
- **3.3 `/closeout`** — new step after tests: `verdict-gate.py --all` over every unit;
  missing/incomplete → `/verify` that unit; blocked → NOT HEALED, archive anyway, index
  `✅ Done — ⚠ verify failed <ids>`, failed checks to TO-DO.md. Feature-map handoff only
  when the scope has a product feature map; otherwise logged as skipped. Lever candidates
  → `## Lever candidates` via a script that dedupes by key and counts a second sighting
  only from a different scope or run.
- **3.4 Rollout** — `setup.sh` prerequisite checks (warn, exit 0); `scripts/clone-behind.sh`
  (one line when behind `origin/main`) called by `/verify` and `/plan`; README Verification
  section; ARCHITECTURE/CLAUDE; fleet lint; announcement draft; herdr-free confirmation.
- **Dogfood (Operating Contract #5):** finish table rev 5 adds 5.3's rows; `/review` on
  `5f06a4c..HEAD` and `/verify 5.3` before Done.

### Session: 2026-09-29 (Alex / Claude)
- **Phase 0** ✅ DONE. Status Ready. `Executed by` stamped (Alex / Claude). Inputs resolve.
  Repo Graph check exit 4 (prose-only section, single-repo scope; same as 5.1/5.2). Ledger
  phase block appended with `base: 5.3 ai-skills 5f06a4c`. Branch `main`, in sync with
  origin, clean. Sibling plans 5.1 and 5.2 read. No herdr worktree (Primary repo none).

#### Task 3.3a: Ledger template carries no examples (inherited research-lanes TO-DO) — ✅ DONE
- **Files created:** `templates/examples/closeout-prep.md` (the worked Chatwoot example, marked EXAMPLE)
- **Files modified:** `templates/closeout-prep.md.template` (every §2–§11 body is `_(none)_`; schema unchanged at 1.0, field shapes didn't move), `scripts/ledger-init.sh` (refuses and removes a new ledger if the template carries an `EXAMPLE` marker), `scripts/tests/test_contracts.py`
- **Verified:** the new tests run the real `ledger-init.sh`: a fresh ledger has zero entries and no example row; a marked template exits 1 and leaves no file. Mutation: restoring the old template fails the fresh-ledger test. Suite OK (2 skipped, live-judge tier).

#### Tasks 3.1–3.3 script layer — ✅ landed (skill wiring follows)
- **Files created:** `scripts/finish-table.py` (`init`: template + `verify/SKILL.md` §4 standard rows per phase, `N.P=repo,…` commits / `N.P` commit-less, `--predates`, `--test-plan-owner`; `add`: rows + Revision bump + Changelog; both read back through `verify_lib.parse_table` and restore on failure), `scripts/tests/test_finish_table.py`
- **Files modified:** `scripts/verify_lib.py` (`parse_table_text`, `**Predates gate:**` parsed and validated — a predating phase may own no rows; `BLOCKING_AFTER = 5`), `scripts/verdict-gate.py` (predating unit → `predates-gate`, exit 0; `--all` closeout view, any block fails, `⚠ verify failed <ids>` marker), `scripts/plans-index.py` (`validate` accepts `predates-gate`; `gate-count` with the 5-scope REMINDER), `scripts/tests/test_verdict_gate.py`, `scripts/README.md`, `templates/verify-contracts.md` §3.1, §5.4, §5.4.1
- **Verified:** suite OK (2 skipped). Mutations: disabling the restore-on-failure fails `test_add_that_would_not_parse_changes_nothing`; disabling the predates exemption fails `test_predating_phase_is_exempt…`. Real data: `gate-count` over the three indexes → `0/5`; `--all` on scope 5 → FAILED, 9 checks (5.1's verdict predates table rev 4; 5.2's two accepted blocks; 5.3 not run yet) — which is what closeout of this scope will face.

#### Task 3.1: `/scope` wiring — ✅ DONE
- **Files modified:** `scope/SKILL.md` 3.8.0 → 3.9.0 (§5.9 Review/Verify tasks in every stub, Review deleted on commit-less phases; new §5.10 writes `finish-conditions.md` through `finish-table.py`, atomic scope = unit `N.1`, deliverable rows prefer rung-4 commands, eval rows set their env flag), `scope/templates/plan-stub.md.template` (`Task {P}.R` Review, `Task {P}.V` Verify), `verify/SKILL.md` §4 (rows come from the script; eval-flag rule — the 5.2 `VERIFY_EVAL=1` TO-DO)
- **Verified (dry run):** `finish-table.py init --phase 7.1=ai-skills --phase 7.2 --test-plan-owner 7.2 --dry-run` on a scratch docs repo emits 6 rows: the four standard rows owned by 7.1, verify-only `p2-scope-deliverables` owned by 7.2 (judged against the docs repo), `test-plan-followed` owned by 7.2; nothing written. The stub template carries both tasks. `lint-skill.py scope` 0 ISSUE.

#### Task 3.2: `/plan` wiring + self-heal — ✅ DONE
- **Files modified:** `plan/SKILL.md` 3.8.2 → 3.9.0 — §5.6.2a self-heal (started phases → `--predates`, rows only for phases not started, dry-run then one halt; all-started scope gets a table with every phase predating), §5.13 `--repo` for every repo the plan commits to, §6.7 `🔎 Verify:` header line, new §6.8 (Review per repo on `base..HEAD`, empty range with a Review task = ❌ FAILED, every ID dispositioned; `/verify`; Done only via `plans-index.py status` — advisory marks, blocking refusal = ❌ FAILED, `--skip-verify` is the user's flag, exit 3 never Done), §11.4 child plans write their `N.P` row through the gate (**fixed a contradiction**: it said child plans update nothing in the index, yet 5.1/5.2 were marked Done there — the gate needs that row). `plan/tests/verification-recipes.md` Recipe 4. Wording aligned in `templates/verify-contracts.md` §3.1 and `scripts/finish-table.py` ("started", not only "Done").
- **Verified — Recipe 4, script half, run as /plan would** (`scratchpad/recipe4.sh`, throwaway plans + `svc` repo on `main`): no table → validate exempt; self-heal dry run drafts 4 rows for 9.2 only with `**Predates gate:** 9.1`; ledger records `base: 9.2 svc …`; after a direct-to-main commit `review.py prepare` resolves `base..HEAD` to two SHAs (not empty) and `HEAD..HEAD` exits 3 `[ERROR] the range is empty`; with a planted failing row, blocking `status` refuses (exit 1, row byte-identical), advisory marks `⚠ judge: none … ⚠ verify advisory: 4 blocked (…, p2-planted)`, `--skip-verify "env down"` writes `⚠ verify skipped: env down`; `validate` conformant each time, including 9.1's pre-gate Done. The halt-once behaviour is skill prose, exercised the first time a real scope self-heals. Suite OK.

#### Task 3.3: `/closeout` wiring + lever backlog — ✅ DONE (3.3a ledger template above)
- **Files created:** `scripts/lever-candidates.py` (upserts `## Lever candidates` in the project's TO-DO.md; one item per `lever_id`; same scope+run = no-op; another run of the same scope adds a line but never counts — tighter than "different scope or run", because re-verifying an unfixed gap would otherwise manufacture its own second sighting; a different scope flips it to BUILD NOW once; read back after write), `scripts/tests/test_lever_candidates.py`
- **Files modified:** `closeout/SKILL.md` 1.3.0 → 1.4.0 (new §5.6 Step 3a: no table → n/a, no self-heal at closeout; `verdict-gate.py --all`; `/verify` only units whose verdict is missing/incomplete, never re-roll a complete fail; failed → NOT HEALED, archive anyway, `✅ Done (date) <--all marker>`, failed checks to TO-DO.md verified vs trunk; levers; feature-map handoff only when the judge's `feature_map` isn't `n/a`, never edits the test-suite; summary lines for 3a and `gate-count --discover`), `scripts/verify_lib.py` (`levers()` + `KEBAB`; a pre-5.3 judge answer without `lever_id` gets the automatic key — **found on real data**: the dry run over scope 5 crashed on 5.1's judge output), `verify/scripts/judge.py` (report uses `levers()`, shows `lever_id`; record rejects a non-kebab `lever_id`), `verify/schemas/judge-output.schema.json` + `verify/prompts/judge.md` (`lever_id` required, named for the gap kind), `scripts/plans-index.py` (`gate-count --discover` walks `VERIFY_PROJECTS` ≤4 levels for `plans/PLANS-INDEX.md`, skipping `archive/`), `templates/verify-contracts.md` §4.9, `scripts/README.md`, tests `test_judge.py`, `test_verdict_gate.py`
- **Verified:** suite OK (2 skipped). Lever mutation (count sightings per run instead of per scope) fails `test_reverifying_the_same_scope_never_counts`. Dry run over scope 5: 2 new candidates (`scripts-tests-green-inconclusive`, `fixtures-inconclusive`), nothing written. Closeout path on the Recipe-4 scratch scope: `--all` → FAILED 4 checks + `n/a 9.1 predates the gate`; archived with `plans-index.py move … --status "✅ Done (2026-09-29) ⚠ verify failed … ⚠ judge: none …"`; `gate-count --discover` then reports it under "with ⚠", 0/5 clean. `--discover` on this machine finds 8 indexes (ai-skills, kalpa-docs, pmg-docs, iris-docs, plus personal ones). `lint-skill.py closeout verify` 0 ISSUE.

#### Task 3.4: Rollout — ⏸️ WAITING_HUMAN (review; dogfood review + verify run first)
- **Files created:** `scripts/verify-prereqs.sh` (Python ≥ 3.9, codex installed + `codex login status`; warn with the fix, always exit 0; no live ping, per Alex), `scripts/clone-behind.py` (fetch ≤ once/hour with a 10 s timeout; one line when behind, one "freshness unknown" line when it can't tell, silent when current), `scripts/tests/test_rollout.py`, `artifacts/rollout-announcement-draft.md`
- **Files modified:** `setup.sh` (step 4 runs the prereqs; `|| echo` so it can never fail setup), `verify/SKILL.md` 0.3.0 (§2.0.1 stale-clone line), `plan/SKILL.md` §6.7 (stale-clone line above the header), `README.md` (§5 Verification: what they do, reading a verdict, every ⚠, advisory vs blocking at 5, skip, `--demo`; prerequisites; **unplanned stale fixes** — the `kalpa/` container row and manual link, `/review` listed as gstack's, `/plan` "single-session"), `ARCHITECTURE.md` (§1.1, §1.4, §2, §6.1 versions), `CLAUDE.md` §4 key files
- **Verified:**
  - Fresh-clone walkthrough under a throwaway `HOME` (real `CODEX_HOME`): clone → `setup.sh` (exit 0, 58 s, gstack cloned + set up, `verify` + `review` linked) → `demo.py` live on `codex gpt-6-sol`: all 6 planted defects caught, control passes — **185 s total**. The Claude restart is not simulated.
  - Setup with codex absent (`VERIFY_CODEX_BIN=codex-not-here`): exit 0, `!! codex not installed …` + `fix: npm i -g @openai/codex && codex login`.
  - Fleet lint: 0 ISSUE across 27 skills. Suite OK (2 skipped).
  - herdr: nothing in `verify/`, `review/` or their scripts references it; `/plan` touches herdr only when `$HERDR_PANE_ID` is set.
  - The live demo also exercised the new `lever_id` schema against real codex; it recorded without error.

#### Dogfood: review 5.3-r1 (codex `gpt-6-sol`, `5f06a4c..5e5d3a2`, 8 commits) — DO NOT SHIP, 3 blocking + 6 should-fix → all 9 fixed
→ `artifacts/review-5.3-r1.md`. Each fix is its own commit with a regression test that fails on the old code (mutation-checked by stashing the fix):
- r1-01 all-started self-heal needed `--phase` → `init` accepts `--predates` alone — `d1d11e5`
- r1-02 commit-less phases could never be judged (prepare required a range) → `judge.py prepare --no-commits`, refused when the ledger shows commits; /scope + /plan say when — `0c354dc`, `5f4f38a` (the dispose guard refused `0c354dc` because it didn't touch the cited `scope/SKILL.md`; it was right, the stub guidance was missing)
- r1-03 a code unit with no `/review` could pass → gate blocks `review:<repo>` when commits in `base..HEAD` have no covering review record; legacy finding-only logs count. **Real data:** 5.1 now shows `review:ai-skills` (true — the owned miss in the Decisions Log); 5.2 is covered by r1–r3 — `617f021`, `/plan` §6.8 `…`
- r1-04 `--all --json` gave closeout no reason per block → blocks carry `what`/`cause`, units carry `needs_verify` — `304b949`
- r1-05 `gate-count` counted any ⚠-free row → a scope counts only if `--all` passes on ≥1 gated unit; `--all` reports `ungated` for an all-predating table; indexes deduped — `3c89a7f`
- r1-06 missing raw judge output read as "no levers" → error when a model judged the run — `e742d9a`
- r1-07 judge levers on invented checks → rejected at record — `30df048`
- r1-08 `FETCH_HEAD` refreshed by any fetch → own stamp for the origin-main fetch — `98f01c2`
- r1-09 `/verify` still said three clean scopes → five — `4e4cfe2`
Suite OK (2 skipped). Lint 0 ISSUE.

#### Dogfood: review 5.3-r2 (codex `gpt-6-sol`, the r1 fixes `5e5d3a2..530874f`) — 3 blocking + 2 should-fix → 4 fixed, 1 rejected
→ `artifacts/review-5.3-r2.md`
- r2-01 **rejected**: its fix ("record a base, require zero commits" for a commit-less unit) would fail every commit-less phase, whose judge rows sit in the docs repo that always carries progress commits; code repos are visible only through declared `--repo` bases, and `--no-commits` already refuses when a declared base has commits
- r2-02 git failure counted as zero commits → a block — `c1cd4f3`
- r2-03 review coverage accepted a discarded-branch head, and nothing enforced "review the fixes of blocking findings again" → reviewed head must be on HEAD's history; every blocking finding's `fixed <sha>` must sit inside a later review — `c1cd4f3` (contract §5.2.1 updated). Real data: 5.2 and 5.3 clear it
- r2-04 unwritable stamp crashed clone-behind → caught; the stamp only rate-limits — `568cd65`
- r2-05 `--predates " , "` passed the empty check → parsed first — `0c6047f`
