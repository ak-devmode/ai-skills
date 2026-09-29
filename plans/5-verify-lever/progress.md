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
**Last action:** Plan 5.1 complete, Phase 1 approved (2026-09-26)
**Next action:** Plan 5.2 Phase 2 CHECKPOINT (Alex) → then Plan 5.3 (wiring + self-heal + rollout)
**Open blockers:** closeout deferred to scope end (see TO-DO.md)
**Key files changed:** `scripts/plans-index.py` (70d1222 — unplanned fix, see Progress Log)

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
- (2026-09-26) clinic_3 in dev = temporary trial target; permanent = stood-up tenant per env.
- (2026-09-26) Faithful-port rule lives in `/verify`, not global CLAUDE.md.
- (2026-09-26) Brief's credentials redacted (`eaeb441`); brief moved to `artifacts/`.
- (2026-09-26) CEO review: approach C — a deterministic row passes only on runner evidence; the codex judge may only downgrade. Required fail/inconclusive blocks; latest run per check decides; evidence bound to SHAs. Gate enforced by plans-index.py, advisory for 3 clean scopes then blocking. Non-codex judge → ⚠ in PLANS-INDEX (Alex's D3 idea).
- (2026-09-26) Codex CLI upgraded 0.152.1 → 0.157.1 (npm) — the old CLI rejected gstack's model; live evidence for the judge-failure handling (F2).
- (2026-09-26) Phase 1 contracts approved as written: one normative spec (`templates/verify-contracts.md`), `verify-run.py` sole verdict-log writer, table revision bump invalidates verdicts, every row required, message contract = lint-skill's four fields + cause + docs.
- (2026-09-26) Disposition coverage is enforced by `verdict-gate.py`, not `/verify` judgment — so it can't drift.
- (2026-09-26) Evidence from a dirty working tree is accepted: verification is pre-PR. Contract §5.2.
- (2026-09-26) No `/clear` at the 5.1 → 5.2 boundary; proceed straight into Phase 2. Closeout deferred to scope end.
- (2026-09-29) Class-A proof (Task 2.4 part B: the three-outcome trial) **moves to the kalpa-docs test-suite program, member T2 (WellMed adapter)**, together with a login/token CLI, as T2 deliverables (`test-suite-program/T2-wellmed-adapter/NOT-YET-SCOPED.md`, kalpa-docs `af2b8ac`). Scope 5 proves class B only. Credential model stays open (Alex: no skeleton key; scoped to test/demo DBs).

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

---

## Human Steps

| Step | Status | Notes |
|------|--------|-------|
| Approve the Phase 1 contracts (finish table, verdict, disposition log, feature map, adapter) | [ ] Pending | 5.1 exit gate |
| Go/no-go after seeing a real `/verify` verdict (dogfood + clinic_3) | [ ] Pending | 5.2 exit gate |
| Announce the ai-skills `git pull` to the team after rollout | [ ] Pending | 5.3 exit gate; CLAUDE.md §2.1 |

---

## Plans

| # | Plan File | Phase | Status | Notes |
|---|-----------|-------|--------|-------|
| 5.1 | 5.1-verify-lever-PLAN.md | Phase 1 — Contracts + deterministic scripts | Done | Gate A — approved 2026-09-26 |
| 5.2 | 5.2-verify-lever-PLAN.md | Phase 2 — `/verify` + `/review` on codex | Ready to execute | Gate A |
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
**Last action:** Task 2.4 done (part A dogfood; part B moved to test-suite T2) — all 5.2 tasks done
**Next action:** Phase 2 CHECKPOINT (gate A): Alex reads the dogfood verdict, go/no-go on advisory rollout
**Open blockers:** None
**Open blockers:** None

### Task Detail
Deepened at start of run (`/markdown-style` §8.9.2). Where this block and the plan differ,
the plan wins, so ask.
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
  a local branch in the private infra repo, 4 commits, **not pushed** (landing is Alex's
  call). Details stay in that repo's commit messages; this public repo gets classes only:
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
- **Part B — class-A trial: BLOCKED, two plan↔reality mismatches** (Operating Contract #1):
  `clinic_3` is **staging** tenant 6, not dev (kalpa-docs scope 89 artifacts); and the login
  needs the staging gateway's credential secret, which is **not** in the test-suite
  (`/wellmed/testsuite/*` in SSM is empty, and the repo has no clinic_3 reference). Reading
  SSM values is a documented human step for agents. Needs Alex: target confirmation plus the
  secret in a local file outside all repos.
- Suite: 93 OK, 2 skipped (live-judge tier).
