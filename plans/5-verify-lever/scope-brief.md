# Scope 5 — `/verify` + the verification lever

**Status:** 📝 Brief only — NOT scoped. Placeholder. Run `/scope` on this when a free window
opens (likely after Alex's son is born). Written so the moment — pain, solution, inspiration —
is not lost.
**Created:** 2026-09-11 by Alex + Claude
**Origin:** a conversation with a friend (excellent engineer, Cursor/Grok-centric) who pointed
Alex at poteto's **pstack** — *"set up CLI verification to aid and 'build the lever'; a deeper
verification at the end of a scope, a shallower one in CI."*

## 1. The pain

### 1.1 Three instances of one failure

| # | Where | What happened | Rung of evidence accepted |
|---|---|---|---|
| 1 | **Scope 64** padmacare web (`pmg-web`), 2026-09-09 | scope.md said *"follow the export exactly"*; agent extracted copy from the 13 `.dc.html` boards and rebuilt layouts from its own judgment — never opened a board. Reported done. Caught by Alex's eye only. | rung 1 — *"it said so"* |
| 2 | **Scope 128** kalpa-web, 2026-08-24 | Same `.dc.html`→Astro shape. Phase 1 closed on *"9 pages eyeballed against the references (faithful)"*. Two weeks before #1. | rung 1 |
| 3 | WellMed hot-gotcha family (MEMORY.md) | `exit 0 ≠ it ran` · config presence ≠ pipeline proof · FE unit-test gate runs zero tests · SSM change not live until recreate · verify from the consumer's vantage. **~20 recurring verification rules living as prose**, re-derived by hand every session. | n/a — the rules exist, the checks don't |

Plus the drift symptom: `TO-DO.md` **658 never-verified** (kalpa) / **224** (pmg), flat.

### 1.2 The retro's conclusion (memory `feedback_port_from_source_artifact`, pmg)

> **The instruction was NOT the gap.** Alex had written "follow the export exactly" — clear
> and explicit — and the model still freelanced. Compliance comes from a VERIFICATION LOOP
> against the source, not from phrasing — the same way a PR is gated by /review, not by
> trusting the diff.

### 1.3 What actually fixed #1

Not a hand re-port and not a gate: **a lever.** `pmg-web/scripts/transform-boards.py` injects
each board **verbatim** via `set:html`. Twelve of thirteen pages cannot drift because there is
no re-authoring step; only the hand-ported homepage still needs a diff. The "approved copy
overrides" convention in `pmg-web/CLAUDE.md` is the pre-approved exceptions list, unnamed.

## 2. The inspiration — pstack (primary source, not the paywalled articles)

Canonical: `github.com/cursor/plugins` → `pstack/`. Read 2026-09-11:
`docs/guide/06-verify-and-ship.md` · `skills/create-verification-skill/SKILL.md` ·
`skills/maintain-verification-skill/SKILL.md` · `skills/blast-radius/SKILL.md` ·
`skills/show-me-your-work/SKILL.md` · `skills/principle-{prove-it-works,
sequence-verifiable-units,encode-lessons-in-structure,build-the-lever}/SKILL.md` ·
`references/feature-map-example/`. Public worked example: `github.com/poteto/verification-skill-example`.

| Take | Leave |
|---|---|
| **Verification skill = driver CLI + feature map.** One file per feature, four fixed H2s: `Sub-features` / `How to get to it (user POV)` / `Driving it with <cli>` / `Gotchas`; README index doubles as regression sweep order. `disable-model-invocation: true` — invoked deliberately. | `poteto-mode` + 23 playbooks (we have `/scope` `/plan`). |
| **Proof bar:** `doctor` first ("a video against a stale bundle is not evidence"); verify side effects not pixels; mocks only behind a production boundary; unreachable path → name it + what blocks it; cleanup never eats the evidence. | "I don't believe in planning" — we do; `scope.md`-immutable is the better bet for multi-session work. |
| **Evidence ladder** (`blast-radius`): 1 *you said so* · 2 *pointed at the line* · 3 *showed the bad case can't happen* · 4 *ran a script that fails loud* · 5 *reproduced in the running app*. "Find the one fact it's safe because of; prove THAT by running code." | Cursor `control-ui`/`control-cli` — gstack `/browse` is our driver, verified working (§3.9). |
| **Decision trail** (`show-me-your-work`): append-only TSV `ts · phase · decision · why · evidence-pointer · result`; audit the log against the transcript ("fix the log, not the story"); **a different model family reviews the trail**. | Model-panel config — herdr seats already do this. |
| **Maintenance loop:** exactly `clean` / `changed` (one PR, confined to the verify skill's dir) / `blocked`; never edits product code; a live regression is *reported*, not papered over in docs. "The unit of rigor is the feature, not every sentence." | Bulk-authoring ~30 feature files up front. |
| **`encode-lessons-in-structure` routing:** one-off → note · recurring → script/lint · systemic → principle. *This is the workbench's job description in one line.* | |
| "The agent that judges a change is never the one that wrote it." | |

## 3. The design — decisions LOCKED in the 2026-09-11 conversation

### 3.1 Two verification classes, two artifacts — never fused
- **A. Behavior** — *does it work right now.* Feature map + driver, pstack-shaped.
- **B. Conformance** — *did we build what the scope said.* Source = `scope.md` deliverable set;
  output = what landed; one verdict row per deliverable. Alex's faithful-port gate generalised
  (read source → produce → read output back from the destination → diff per unit → done only
  when the diff is empty or every difference is on a pre-approved exceptions list).

### 3.2 Report the rung, never a score
Every check states the ladder rung it reached. **No threshold gating** — a fuzzy score invites
gaming and manufactures confidence. CI-shallow = **rung-4 scripts only**, binary, hard-block on
red. Closeout-deep = rung-5 live drive + the conformance verdict. A "rung 2" proof isn't blocked
by a number; it is visibly weak to a reader.

### 3.3 Unit of rigor = **feature** (locked)
"Behaviors" considered and rejected — vaguer, no upside. Features = the third indexing axis
alongside temporal (scopes) and structural (repo/MS/ADR); neither of those can anchor
verification (scopes end, behavior persists; a user path crosses 4 MSes with no owner of the
join — and the worst bugs ARE joins). Features cover user-facing *and* platform surfaces
(deploy, tenant provision, cred path, AMQP). Doc trio becomes: **ADR = why · ARCHITECTURE =
where · feature map = how it behaves and how to prove it.**

### 3.4 Homes — the split pstack forces
```
dev-workbench/            driver + env/stack-specific verbs (doctor, login, screenshot,
  (the lever CLI)         deploy-sha, ssm-live, amqp-consumers, schema-lag ...)
                          owns JOURNEYS AGAINST A DEPLOYED ENV; later: e2e in staging;
                          lever backlog (§3.7)
        ^ pointed at by
product repo              features/README.md + one file per feature + thin verify-<app>
  (single-repo apps:      skill  — must be found COLD by an agent inside the repo
   pmg-web, kalpa-web)
kalpa-docs                same, for multi-repo WellMed (features span repos; docs graph is
  (WellMed)               the cross-cutting home). Drift handled by the maintain pass, not
                          same-PR (two-repo cost accepted).
```
Repos own their own unit/integration tests. **Workbench never becomes the product test suite.**
Feature-map recipes (rung 5) are the human form of Playwright specs (rung 4) — recipes may
graduate into specs, and those specs live in the product repo.

### 3.5 Skill wiring
- **`/scope`** — a **finish-condition table**: one row per deliverable → `check · rung required ·
  evidence artifact`. The closeout verdict is *generated* from it (the judge fills cells, not
  opinions). 64's row would have read `13 boards · rung 5 · per-board source-vs-rendered diff,
  exceptions = copy-overrides` — "eyeballed" would not have fit the cell.
- **`/verify`** — NEW top skill. Runs the feature-map drive, fills the verdict, reports rungs,
  emits `clean/changed/blocked` on the map. **`/review` untouched** — it is a *diff* reviewer at
  PR time and stays one.
- **`/plan`** — calls `/verify` **per unit at each checkpoint**, not once at the end. (Retro:
  "end-of-phase gates are easy to skip under pressure; cheap per-unit verification beats them.")
- **`/closeout`** — in order: (1) verdict artifact present + complete, else run `/verify` now;
  (2) maintain pass on the feature map → `clean/changed/blocked`; (3) `/cross-repo-init`'s
  trio-sync grows a member (verify skill + map). `closeout-prep.md §6 Docs Loaded` is the
  built-in detector for class B: source artifacts absent from §6 = the port didn't happen →
  **done-blocker**.

### 3.6 Judge
**codex primary, Claude fallback — both in a FRESH context, never the author.**
Kin to `/ready-to-clear` (fresh spawn reading only disk/runtime/git).

### 3.7 YAGNI guard — the lever grows on the second sighting
Every `INCONCLUSIVE` / `verified-unreachable` verdict row is a **lever candidate**; `/closeout`
appends it to a lever backlog in workbench. **A lever is built on the second sighting of the
same gap, never the first.** First = record, second = structure. This is the built-in
"hey, this edge isn't tested — suggest a lever" meta-awareness, without speculative CLIs.

### 3.8 Phase 0 — the fail-loud floor (Lauren's "don't let things exit quietly")
Rung 4 is only possible if the code underneath fails loud; every silent failure turns a rung-4
check into false-green (the whole hot-gotcha family). **Precondition, not a side quest.**
Two pushbacks taken on board:
- **Not codebase-wide.** Targets = **boundaries** (CLI args, config/SSM/env reads, network,
  external APIs, filesystem) + the ~40 `operations/` and CI/deploy shell scripts. Interior code
  trusts its types (pstack `boundary-discipline`).
- **Lint, not sweep.** A one-time pass gets re-silenced by the next agent copying the
  surrounding pattern. `errcheck` (golangci-lint) · `shellcheck` · a CI grep failing on
  `2>/dev/null`, `|| true`, bare `set -e` under `#!/bin/sh` (dash — `pipefail` dies on line 1)
  · no-empty-catch for TS. The sweep fixes today; the lint holds the line.
- **Message pattern:** `expected · found · where · next check` — e.g. `expected SSM param
  /wellmed/staging/gateway-go/X, found nothing (profile=kalpa, region=ap-southeast-1); try:
  aws ssm get-parameters-by-path …`. The reader of stderr is a model.

### 3.9 Driver — gstack `/browse`, verified 2026-09-11
Never used before this date. Smoke test against `https://v2-padmacare.pbmcgroup.com`: daemon
cold-start + `goto` (200) + `text` + `console` (0 messages) + `network` (all 200; R2 posters
`pending` = lazy) + full-page screenshot — **2 s total**. Headless Chromium on bun 1.3.11,
`~/.claude/skills/gstack/browse/dist/browse`. Not a rebuild candidate; the verbs wrap it.
Gotchas from its skill doc: `hover` scrolls target into view (invalidates rest-state shots);
tab persists across sessions → always start with explicit `goto`, never bare `reload`.

## 4. Proposed phases (for `/scope` to re-derive — indicative only)

```
0  Fail-loud floor    boundaries + operations/ + CI scripts; lints wired; message pattern
1  Contracts          scope.md finish-condition table · verdict TSV format ·
                      closeout-prep §6 as done-blocker · feature-map contract (4 H2s + index)
2  /verify skill      rung vocabulary · clean/changed/blocked · driver hooks (/browse, SSM) ·
                      codex judge + Claude fallback · lever-backlog emission
3  Workbench lever    dev-workbench CLI: doctor · login · screenshot · first env-specific verbs;
                      second-sighting rule enforced
4  /plan + /closeout  per-unit /verify call · verdict gate · maintain pass · trio-sync member
   wiring
5  Trial(s)           see §5 — decide at scope time
```
Lever + skills land in `ai-skills` and `dev-workbench`; trials land in their product scopes.

## 5. Trial candidates — decide at scope time

**Port-fidelity is DEAD as a trial** (2026-09-11): 64 and 128 have since taken days of
intentional copy divergence. Do not resurrect it.

- **Primary candidate:** WellMed **staging `clinic_3`** (demo tenant, `testing`/`12345678`;
  ⚠ `clinic_4`/`clinic_5` on staging are REAL patient copies — never drive them) —
  `doctor · login · screenshot · one journey`. This is the e2e-in-staging shape workbench is for.
- **Driver warm-up:** `v2-padmacare` staging — already proven reachable (§3.9); cheapest
  first feature file.
- **Infra flavour:** kalpa read-only wire verbs — `deploy-sha` (image tag CHANGING), `ssm-live`
  (container env vs SSM), `amqp-consumers` (per-queue `consumers==0`), `h2-settings-frame`.
  Each is an existing hot-gotcha turned into a rung-4 script.

## 6. What `/scope` must decide

- [ ] Trial order — clinic_3 journey first, or wire verbs first because Padma go-live risk sits there?
- [ ] Verdict TSV columns (start from `show-me-your-work`: `ts · phase · decision · why · evidence · result`; add `deliverable · rung`).
- [ ] Where the conformance judge reads "what landed" from — `origin/<trunk>` content-grep (memory: *done means written, not landed*), never the working tree.
- [ ] `verify-<app>` skill frontmatter + `disable-model-invocation` equivalent in Claude Code.
- [ ] Which lints are already on per repo (`errcheck` likely on in Go repos — check `.golangci.yml`, don't assume).
- [ ] Workbench repo layout: `dev-workbench` currently holds only `config/` + `install.sh`; the CLI needs its own top-level home and a plans graph or a pointer here.
- [ ] Go single binary vs thin bash/Node for verbs. Lean: Go for wire verbs (table tests), bash wrappers around `/browse` for UI.
- [ ] CI-shallow: which rung-4 verbs are cheap + binary enough to hard-block on.
- [ ] Does the *Faithful-port verification gate* wording (§3.1 B) become a rule in `~/.claude/CLAUDE.md`, or stay encoded only in `/verify`'s class-B check? (Alex's call — it is not on disk today; see §9.)

## 7. Constraints

- **A verification harness that can false-green is worse than none** — it launders drift as
  confidence. Every check asserts at the far/consumer end and emits proof it executed
  (row count at destination, sha delta, SETTINGS frame, consumer count).
- No scoring, no thresholds (§3.2).
- Build lazily (§3.7). One feature file for the trial; the map earns each entry.
- Agent tool blocks: SSM param VALUES + `put-parameter` denied to the agent; `git rebase`,
  `rm -rf` blocked — hand Alex the command.
- `/browse` daemon flags (`--headed`, `--proxy`) only apply on a fresh daemon.

## 8. Not in scope

Migrating the ~20 MEMORY.md hot-gotchas into per-feature `Gotchas` at scale (that is the
follow-on scope once the contract has survived contact) · replacing `/review` · a Playwright
suite for WellMed · Control Tower / Padma go-live work · any codebase-wide error-message sweep.

## 9. Related

- Memory (pmg): `feedback_port_from_source_artifact`, `project_padmacare_web_rebuild`
- Memory (wellmed): `project_verify_lever_scope`, `reference_pstack_source`
- Scopes: `pmg-docs/plans/64-padmacare-web-astro/` · `kalpa-docs/plans/archive/128-kalpa-web-astro/`
- Existing proto-levers to reuse, not rebuild: `wellmed-infrastructure/operations/check-grafana-drift.sh`
  + `grafana-expected-state.py` · `pmg-integrations/operations/audit-*.js` · `pmg-web/scripts/transform-boards.py`
- Class B gate text: Alex drafted a *"Faithful-port verification gate"* rule (read source → produce →
  read back from destination → diff per unit → done only on empty diff or approved exceptions) and pasted
  it into the 2026-09-11 conversation. **It is NOT in `~/.claude/CLAUDE.md` or anywhere on disk** — the
  wording survives only as §3.1 B above and in pmg memory `feedback_port_from_source_artifact`. Whether it
  becomes a global CLAUDE.md rule is Alex's call at scope time (open item for §6).
