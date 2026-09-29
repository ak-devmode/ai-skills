# `/verify` + the verification lever
**Project:** ai-skills  **Branch:** main  **Date:** 2026-09-26
**Created by:** Alex
**Scope folder:** ~/Projects/ai-skills/plans/5-verify-lever/
**Source repo(s):** ~/Projects/ai-skills (skills + scripts) · trial reads ~/Projects/wellmed/wellmed-testsuite
**Primary repo (worktree):** none — skill markdown + scripts in ai-skills, direct-to-main per its CLAUDE.md §2
**Backlog:** none

## 1. Context

Two scopes (pmg-web 64, kalpa-web 128) closed on "it said so" evidence while shortcutting
what the scope asked for; the retro's conclusion was that the instruction was not the gap —
an independent verification loop was. Separately, execution agents drift into local maxima:
over-built abstractions, and names, contracts and paths assumed instead of looked up across
repos. This scope builds `/verify` — an independent judge from the other model family
(codex) that does its own work and reports evidence rungs — rewires `/review` onto the same
opposing voice, and wires both into `/scope`, `/plan` and `/closeout` so every code phase of
every scope is reviewed and verified. Background and the locked design conversation:
`artifacts/scope-brief.md` (2026-09-11) · research: `artifacts/research-poteto-2026-09-26.md`.

## 2. Repo Graph

Single-repo task for the build — ai-skills is a standalone leaf (CROSS-REPO.md: no Pattern
Sources, no Consumers). The trial reads `wellmed-testsuite` and a dev tenant; it changes
nothing there. Snapshot 2026-09-26: ai-skills `main` == `origin/main` at `feaa5a9`.

## 3. ADR Alignment

No ADRs in ai-skills. The trial runs against WellMed dev read-only and touches no ADR'd
surface; ADR checks belong to the test-suite program's member scopes.

## 4. Phases

### 4.1 Phase 1 — Contracts + deterministic scripts (gate A)
The formats everything else reads, and the scripts that enforce them (trust ladder: a gate
is a script, not a paragraph a skill can skip).
- **Finish-condition table** (its own revisioned file, `finish-conditions.md` in the scope
  folder, with a changelog — never inside `scope.md`, which `/ready-to-clear` treats as a
  write-once design record): one row per deliverable → `check_id · owner (phase/unit that
  must pass it) · check (an executable command, or the literal "judge") · repo · working dir
  · env · timeout (default 120 s) · rung required · unreachable-allowed (Alex's reason, or no)
  · evidence artifact`. A checkpoint runs exactly the rows its unit owns; closeout runs all.
- **Verdict artifact** (`artifacts/verify-<phase>.jsonl` — JSONL, written with
  `dispatch-log.py`'s write-then-read-back pattern; free-text evidence breaks TSV): per row
  `ts · run_id · run_state · check_id · deliverable · rung · repo SHA(s) · resolved repo/dir/env
  · deployed version (live rows) · finish-table revision · evidence · judge · result`.
  Append-only for audit. **Runs move `pending → judged → final`**; the judge's verdict is bound
  to its `run_id`; finalization is atomic. **The latest final run of each `check_id` decides
  readiness** (a fixed failure can clear); a pending run blocks. Results `pass | fail |
  inconclusive | verified-unreachable`. The gate prints it as a table for humans.
- **Gate semantics** (approach C, one-way authority): a **runner** row passes only on runner
  evidence; the judge may only downgrade it. On a **`judge`** row the judge's verdict is the
  result, pass or fail. A required row that is `fail` or
  `inconclusive` **blocks**; `verified-unreachable` passes only where the table declared it
  allowed; evidence whose SHA is outside the current unit's range is rejected. The unit's
  range is `base..HEAD` per repo, where `ledger-init.sh` records each repo's base SHA in the
  phase block at phase start.
- **Review disposition log** (`artifacts/review-<phase>.jsonl`): the reviewer's raw output is
  kept with stable finding IDs; the log must cover every ID with `fixed <sha>` or
  `rejected <reason>`. Nothing silently dismissed, nothing silently dropped.
- **Evidence placement:** class-A evidence (URLs, screenshots, command output from a product
  env) is written only to the product's private location (kalpa-docs scope folder or the
  test-suite). Public repos hold class-B verdicts on their own content only; the contract
  lists the fields a public verdict may carry.
- **Examples live in `templates/examples/`**, never inside a template; a test asserts a
  freshly generated file carries no example rows.
- **Message contract (DX review G1):** every message from the runner, the gate,
  `plans-index.py status` and the judge line carries *what happened · why · cause class
  (code / environment / tooling) · next command · where to read more*, with the actual
  values. The cause class answers a teammate's first question: my code, or the setup?
- **Feature map contract**: `features/README.md` index (feature · status · last verdict date
  + rung) + one file per feature with four H2s (Sub-features · How to get to it · Driving it
  with <cli> · Gotchas). Status vocabulary: roadmap · scoped · in progress · in testing ·
  shipped; `shipped` without an evidence cell renders `shipped (unproven)`. Agents generate
  it by cataloguing the app; nobody hand-writes it.
- **Adapter contract** — what `/verify` consumes from a product's private test-suite:
  `doctor`, an env handle (URL, tenant, credential *pointer*), a verb set; CLI rules:
  `--dry-run` on destructive verbs, subcommands, JSON output, rich `--help`, errors as
  `expected · found · where · next`. Exit codes follow wellmed-testsuite's
  (`0` pass · `1` fail · `2` usage · `3` unreachable → verified-unreachable).
- **`scripts/resolve-identifiers.py`** (invented-reality check): v1 handles named kinds only
  — env var, SSM path, proto field, route — resolved against each kind's authoritative
  declaration files, namespace-aware; hits in comments or fixtures don't count; a real new
  declaration in the same diff resolves. Every run prints `found N · resolved M ·
  unsupported kinds K`; unresolved or unsupported is never a pass.
- **`scripts/verify-run.py`** (the deterministic runner): executes each owned finish-table
  row's command in its declared repo / dir / env with its timeout, writes evidence (command,
  resolved context, exit code, output hash, ts, SHA) as a `pending` run; rows it cannot
  execute become `inconclusive` with the reason; a timeout becomes `inconclusive: timed out
  after Ns`. Refuses to write class-A evidence under a
  public repo (git remote + denylist).
- **`scripts/verdict-gate.py`**: applies the gate semantics above to the latest final run per
  owned check. **Enforced at the index, two layers**: a new `plans-index.py status` command
  runs the gate before writing Done (preventive), and `plans-index.py validate` fails on any
  Done phase row without a passing verdict, which the SessionStart hook surfaces (detective —
  agents can still edit the file directly). When the judge line isn't codex, it appends `⚠ judge: <fallback>` to the
  phase's index status; a later codex verdict clears it.
- **Test entrypoint:** `scripts/tests/test_*.py` (stdlib `unittest`, run with
  `python3 -m unittest discover scripts/tests`) + a `Test:` line in CLAUDE.md §6, so
  `/closeout` Step 3 and `/verify` class B actually run the scripts' tests. ai-skills has none
  today.

### 4.2 Phase 2 — `/verify` skill + `/review` on codex (gate A)
- **`/verify`** (new top skill, generic, public) = the **runner** (`verify-run.py`, executes)
  + the **judge** (codex, reads runner evidence + git only; runs in a read-only sandbox, so it
  never drives an env itself). Never asks the author for data. Its own ~20-line codex probe
  runs fresh every call (`codex --version` + a one-line `codex exec` ping) — never gstack's
  internal probe, which caches failures for an hour. The verdict header records
  `judge: codex <model codex reports> | claude-fallback <reason> | none <reason>`; no model
  is pinned; not-installed / not-authed / model-unusable / timeout / empty / refusal /
  malformed all end as non-codex judge lines and none can produce a pass.
  - Class B conformance: scope deliverables + the `/plan-eng-review` test plan vs what
    landed; audits every review rejection; faithful-port rule (read source → read back from
    destination → diff per unit → done only on empty diff or pre-approved exceptions).
  - Class A behavior: drives the product through the adapter + `/browse`; capped at what
    exists.
  - Local-maxima lenses: over-build (judgment, against `/plan` §7 Pattern-First Rule) and
    invented reality (runs `resolve-identifiers.py`).
  - Reports the rung per check, never a score. Emits lever candidates for every
    `inconclusive` / `verified-unreachable` row (built on the second sighting).
  - Maintain pass on the feature map: exactly `clean | changed | blocked`.
  - Runs codex headless; Claude fallback when codex is unavailable; no herdr required.
- **`/review`** — codex becomes the gate, fed gstack's engine checks + the Kalpa domain rules
  (extracted from `review/SKILL.md` §3 into a file both passes read) + the local-maxima
  lens + two new flags: silent-failure patterns (`|| true`, `2>/dev/null`, empty catch) and
  dirty comments (workaround / hack / TODO-as-justification). Claude pass is fallback only.
  Writes the disposition log. **Starts with a capability spike**: codex on one real past
  diff (108.6 if available) with the engine checks + domain rules; record what codex cannot
  do (specialists, browser, completion markers) and design around it.
- **Verifier fixtures:** a known-bad scope under `verify/tests/fixtures/` (invented env var,
  over-built abstraction, rejection with no reason, missing evidence, row under its rung,
  dropped finding ID) where `/verify` must produce a finding naming each planted defect, plus
  clean control fixtures and repaired copies that must pass. `judge: none` fails the suite.
  Over-building is judged on the pattern, not a caller count. Runs from the test entrypoint
  on any change to `/verify`, its scripts or contracts.
- **Proof before the gate:** dogfood `/verify` on Phase 1's outputs (class B), then a live
  class-A trial on dev `clinic_3` through the runner (temporary; permanent = a stood-up test
  tenant) that produces **three outcomes**: a real end-to-end pass, a planted behavior
  failure that blocks the checkpoint, and an unavailable env that comes out
  unreachable/inconclusive, never pass. Trial evidence stays private.

### 4.3 Phase 3 — Wiring + self-heal + rollout (gate A)
- **`/scope`**: emits the finish-condition table; every phase that produces commits carries
  review + verify tasks ("if there is a commit, review runs"); phases with no commit
  (wiring inside third-party apps) carry verify only.
- **`/plan`**: runs `/review` on each commit-producing unit and `/verify` per unit at
  checkpoints, passing both the unit's exact revision range (`base..HEAD` per repo); an
  unexpectedly empty diff is a failure, not a clean review (direct-to-main repos like
  ai-skills leave nothing for a branch diff). The gate is enforced through `plans-index.py`. **Advisory first**: the gate
  warns + marks the index but doesn't block until 3 real scopes pass through cleanly, then
  flips to blocking. `--skip-verify "<reason>"` exists, loud in the header and the index. **Self-heal**: on a scope with no
  finish-condition table, draft one from the scope's deliverables and ask Alex to confirm
  once before proceeding.
- **`/closeout`**: verdict present + complete, else run `/verify` now. A failing or blocked
  final verdict means closeout cannot report HEALED; the scope still archives (closeout's
  archive-anyway rule stands), the index row reads `✅ Done — ⚠ verify failed <check_ids>`,
  and the failed checks go to TO-DO.md. Closeout never edits the private test-suite: it
  writes a feature-map maintenance handoff (`clean | changed | blocked` + the change list) to
  the scope's artifacts, applied in the test-suite repo or via `/closeout-extended`. Lever
  candidates go to a `## Lever candidates` section of the project's `plans/TO-DO.md` with
  `Touches:`, originating `run_id` and scope; only a match from a different scope or run is
  the second sighting → "build the lever now" (a re-run can't manufacture one).
- Fold in the ledger-template defect (see §8).
- **Onboarding (DX review):** `./setup.sh` checks Python ≥ 3.9 and codex (installed, logged
  in, able to run) and **warns** with the exact fix commands (never fails the pull);
  `/verify --demo` runs the fixture scope in ~1 minute and shows a failing verdict naming the
  planted defects plus a passing control; a README "Verification" section orients (what
  `/review` + `/verify` do, prerequisites, what each ⚠ means, advisory vs blocking,
  `--skip-verify`, reading a verdict). Target: `git pull && ./setup.sh` → restart →
  `/verify --demo`, under 5 minutes. `/verify` and `/plan` print one line when the local
  ai-skills clone is behind `origin/main`.
- Rollout per ai-skills CLAUDE.md §2.1: announce the `git pull`; team works without herdr.

## 5. Architecture

```
   /scope --- finish-conditions.md (check_id · owner · command|judge · repo/dir/env · timeout · rung · unreachable-ok)
      |
   /plan  --- per commit-producing unit -------------------------------------+
      |                                                                      |
      |   /review (codex, fresh)                /verify                      |
      |     engine checks + Kalpa rules           verify-run.py (RUNNER)     |
      |     + local-maxima + silent-fail            runs each row's command  |
      |     + dirty comments                        -> evidence: exit, hash, |
      |     raw findings (stable IDs)                  SHA, deploy ver, ts   |
      |     -> review-<phase>.jsonl               codex JUDGE (read-only)    |
      |        every ID: fixed <sha> |              reads evidence + git     |
      |        rejected <why>                       may only DOWNGRADE rows  |
      |                                             + over-build, rejections |
      |                                           -> verify-<phase>.jsonl    |
      |                                              latest run per check_id |
      |                                                                      |
      +---- verdict-gate.py: required fail|inconclusive blocks; stale SHA rejected
      |       enforced by plans-index.py (no Done without a pass); judge != codex -> ⚠ in index
      |       advisory for the first 3 scopes, then blocking
      |
   /closeout --- verdict complete? else /verify · feature-map maintain (clean|changed|blocked)
                 lever candidates -> plans/TO-DO.md "Lever candidates" (2nd sighting = build)

   public (ai-skills)                 private (product test-suite, e.g. wellmed-testsuite)
   ------------------                 ---------------------------------------------------
   /verify engine, scripts,   uses->  adapter: doctor · env handle · verbs (CLI contract)
   contracts                          features/README.md + per-feature files (status+evidence)
```

## 6. What Already Exists

- `review/SKILL.md` — two-pass review (gstack engine §2, Kalpa domain §3); becomes the codex gate.
- gstack `/codex` (`~/Projects/gstack/codex/`) — headless codex review with a pass/fail gate;
  codex-cli 0.152.1 installed. Reuse, don't rebuild.
- `ready-to-clear/SKILL.md` — the fresh-context-reads-only-disk-and-git pattern `/verify` copies.
- `plan/SKILL.md` §7 — Pattern-First Rule, the over-build lens's yardstick.
- `scripts/edit-guard.py`, `scripts/lint-skill.py` — fail-loud levers from scope 2 (prior art
  for the script-enforced gate).
- `templates/closeout-prep.md.template` §6 Docs Loaded — the class-B "source never read" detector.
- gstack `/browse` — headless driver, smoke-tested 2026-09-11.
- `~/Projects/wellmed/wellmed-testsuite` — lane runner with exit codes already matching the
  adapter contract (0/1/2/3); read-only lane live.

## 7. Table Identity Map

No DB write/DDL surface — Step 4.5 N/A.

## 8. Inherited TO-DOs

| TO-DO item | Origin section | In / Out | Phase | Why |
|---|---|---|---|---|
| Closeout ledger template ships fake example entries | research-lanes (Scope 6) | In | 3 | /closeout wiring edits the ledger template anyway; §6 is the class-B detector, so a ledger that lies undermines /verify |
| Re-test codex idle-vs-done after herdr v9 hook | herdr-agent-workflow (Scope 4) | Out | — | Only matters for codex in herdr panes; /verify runs codex headless |
| Paraphrased cross-skill duplicates invisible to linter | skills-relook (Scope 2) | Out | — | Linter eval pass, unrelated surface |

## 9. NOT in Scope

- **The test-suite program** (kalpa-docs, next): tenant stand-up/teardown per `{env}`, the
  synthetic/demo seeder (scope 89 folds in), greenmask masked restore, the WellMed CLI and
  adapter, and the **fail-loud sweep + CI lints** across WellMed repos (its first member —
  housekeeping before the renovation). This scope defines the contract they fulfil.
- `pmg-testsuite` — mirrors the WellMed one later; `/verify` must work against it unchanged.
- IRIS — consumes the same test-suite later.
- Formal verification; best-of-N fan-out; cloud agents.
- Migrating MEMORY.md hot-gotchas into feature-file Gotchas at scale.

## 10. Skill Sequence

### 10.1 Plan Reviews

| # | Skill | Apply? | When | Notes |
|---|-------|--------|------|-------|
| 1 | /plan-ceo-review | **YES** | 1st | Challenge the premise: is a second-family judge worth the cost vs stronger scripts? |
| 2 | /plan-eng-review | YES | 2nd | Contracts, script boundaries, codex invocation, fallback behavior |
| 3 | /plan-design-review | N/A | — | No UI |
| 4 | /plan-devex-review | YES | 2nd | Team-facing skills + the adapter CLI contract are developer-facing |

### 10.2 Implementation Support

N/A x4 — not a bug fix, no UI design (`/investigate`, `/design-consultation`, `/design-html`, `/design-shotgun`).

### 10.3 Review & QA

| # | Skill | Apply? | When | Notes |
|---|-------|--------|------|-------|
| 9 | /review | YES | Each phase | Dogfooded: from Phase 2 on, the codex gate reviews its own build |
| 10 | /health | N/A | — | No test suite in ai-skills; lint-skill.py covers skill bodies |
| 11 | /qa | N/A | — | No web app of our own |
| 12 | /qa-only | N/A | — | No test command |
| 13 | /browse | YES | Phase 2 | Class-A trial against dev clinic_3 |
| 14 | /devex-review | OPTIONAL | Phase 3 | After rollout, if the team hits friction |
| 15 | /setup-browser-cookies | OPTIONAL | Phase 2 | Only if the clinic_3 login needs a session |

### 10.4 Ship & Post-ship

| # | Skill | Apply? | When | Notes |
|---|-------|--------|------|-------|
| 16 | /ship | **N/A always** | — | Not in use; promotion is /review → PR → merge → /closeout |
| 17 | /document-release | N/A | — | README/ARCHITECTURE rows handled in-phase |
| 18 | /retro | OPTIONAL | End | Worth one: first scope run under its own gate |

## 11. Key Decisions Captured

- **Codex is the standing opposing voice** for both `/review` and `/verify`, in a fresh
  context, never the author; Claude is fallback only. Headless — no herdr panes; most of the
  team doesn't use herdr.
- **Every review finding gets a recorded disposition** (fixed / rejected + reason); `/verify`
  audits rejections. The primary failure these skills target is local maxima: over-built
  abstractions and invented names/contracts/paths.
- **`/verify` does its own work** from disk, git and runtime; checks scope conformance and
  adherence to the `/plan-eng-review` test plan.
- **Review runs wherever there is a commit**; commit-less phases (third-party wiring) get
  verify only.
- **Older scopes self-heal**: `/plan` drafts the missing finish-condition table and asks once.
- **Report the rung, never a score.** A lever is built on the second sighting of a gap.
- **Seam**: `/verify` defines a contract; the private product test-suite fulfils it.
  `/verify` + scripts are public in ai-skills; env details, credentials and the feature map
  live in the private test-suite (smaller distribution than kalpa-docs).
- **Feature map, not a module grid**, organised per feature with status + evidence; agents
  generate and maintain it.
- **Test-suite becomes a program** in kalpa-docs with scope 89 folded in as a member (its
  reviewed decisions kept); the program needs a PRD. Its first member is the fail-loud sweep
  + lints.
- **clinic_3 in dev is a temporary trial target**; permanent is a stood-up test tenant per env.
- **Dogfood**: `/verify` runs on this scope's own phases.
- **Faithful-port rule lives in `/verify`**, not global CLAUDE.md.
- **CEO review 2026-09-26 (HOLD SCOPE, approach C):** scripts + runner evidence set the
  floor; the codex judge has one-way authority (downgrade only). Codex's outside voice
  independently matched three of Claude's findings and added seven, two of which broke the
  first draft of C (downgrade-to-inconclusive passed; one failure could never clear). All
  seventeen accepted — full record in `artifacts/ceo-review-2026-09-26.md`.
- **Eng review 2026-09-26:** 7 Claude findings (own codex probe, JSONL artifacts, two-layer
  index enforcement, per-repo base SHA, finish table in its own file, a real test entrypoint,
  per-row timeouts) + 9 from codex's outside voice (judge rows can pass, run states with
  atomic finalization, per-unit check ownership, execution context per row, explicit unit
  revision range, closeout on a failing verdict, feature-map handoff, lever dedupe by run,
  fixtures that can't be passed by failing everything). All accepted —
  `artifacts/eng-review-2026-09-26.md`.
- **DX review 2026-09-26 (triage):** persona = a teammate who didn't ask for the gate and
  meets it inside paid work. Getting started 3 → 8 (setup check that warns, `/verify --demo`,
  README orientation); errors 4 → 8 (one message contract with a cause class); stale-clone
  warning. `artifacts/devex-review-2026-09-26.md`.
- **Deliberate divergence from pstack**: poteto verifies behavior only ("the best spec is
  code"); we add conformance because the scope is where Alex holds the product vision.
  Her verification is the author closing its own loop; ours adds the independent judge —
  one CLI + feature map serves both.
