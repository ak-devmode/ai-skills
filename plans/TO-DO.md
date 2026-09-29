# Plans — Accumulated TODOs

Items extracted from completed plans during archive, plus deferred design
items surfaced mid-execution. Each item references its source plan or
session. Pick up during sprint planning or task sorting.

---

## Closeout Skills (Plan 1) — v1.1 deferred items

Items surfaced mid-execution (Phase 5 §8.1 dogfood on pmg-integrations).
Not blocking v1.0 ship but worth capturing while context is fresh.

- [ ] **Separate "pattern-grep candidate pool" from "contract-traversal graph".**
      CROSS-REPO.md currently conflates two things: (1) repos /plan greps for
      patterns under the pattern-first rule, and (2) repos /closeout-extended
      walks for outward contract updates. These are different concerns:
      pattern-grep should be willing to pull from a wider pool (e.g., look at
      wellmed-infrastructure for "what does a good Notion adapter look like"
      even though pmg-integrations has no code dependency), while contract
      traversal must stay within a project's graph (PMG ↔ WellMed boundary
      is a hard wall). Proposed v1.1 schema: split into `## Pattern Sources
      (grep-only)` and `## Pattern Sources (traversed)` sections, or a single
      Pattern Sources section with a `grep-only: true` flag per entry.
      User quote: "the cross consumer repo thing shouldn't traverse between
      them, but the pattern matching could/should — perhaps that v1.1 or
      something, but that would be ideal."

- [ ] **Loosen "never auto-generate diagrams" rule for unambiguous happy
      paths.** /cross-repo-init §7.4 currently bans Data Flow diagram
      generation entirely (rationale: "wrong diagram is worse than missing").
      In practice for hub repos like pmg-integrations the happy path is
      unambiguous (webhook → middleware → routes → integrations/<flow> →
      lib/<adapter> → external service → response) and Claude can sketch it
      accurately. Proposal: allow Claude to propose a diagram and ask user to
      confirm/edit rather than forcing user to author from scratch.
      Surfaced when user asked "not sure what that is and why I need to do it
      manually."

- [ ] **Update Phase 5 §8 dogfood checklist** in plan to reflect actual
      sequencing decisions made during §8.1: external dependents go in a
      dedicated sub-section under Consumers; CROSS-REPO.md.examples.md was
      updated to use three archetypes (self-trunk hub, trunk, leaf) instead
      of two (hub-consumer, trunk).

- [ ] **Fix stale CROSS-REPO.md.examples.md before §8.4** — DONE 2026-05-11,
      see closeout-skills progress.md for context.

Source: `closeout-skills/closeout-skills-PROGRESS.md` §8.1

---

## Closeout Skills (Plan 1) — v1.1 deferred items (added §8.2 WellMed side)

Surfaced during the kalpa-docs dogfood (Phase 5 §8.2 WellMed side,
2026-05-11). Not blocking v1.0 ship.

- [x] **/cross-repo-init must survey active branches, not just the
      checked-out branch.** ✅ DONE 2026-05-11. Updated `cross-repo-init/SKILL.md`:
      added §2.2 Branch survey (cascade: CROSS-REPO trunk-branch field →
      origin/develop if ≥5 commits ahead → origin/HEAD default), §2.3 Drift
      signal capture, branch-aware semantics in §3.2.3 / §3.2.4 / §4.1
      (all auto-detection runs `git show origin/$SURVEY_BRANCH:<path>`
      / `git ls-tree -r origin/$SURVEY_BRANCH` rather than `cat` / `ls`),
      and new behavior rule §7.4a explicitly forbidding single-branch
      auto-detection. Feature-branch heuristic surfaces names matching
      `*adapter*`, `*restructure*`, `*architecture*`, `*shared*`, `*sdk*`,
      `*infra*` for user review.
      Still open as a separate item: /closeout-extended worktree-base
      detection probably needs the same treatment (probe origin/develop
      when CROSS-REPO doesn't pin a trunk-branch). Not part of this
      session's fix.
      **§8.3 verification 2026-05-11:** cascade ran clean on
      wellmed-infrastructure (origin/develop +10 vs main with ~19k LOC
      of canonical SDK + adapter code absent from main). No manual
      override needed. Closed as verified.

- [x] **ARCHITECTURE.md template should include a Drift section by
      default.** ✅ DONE 2026-05-11. Updated
      `cross-repo-init/templates/ARCHITECTURE.md.template` to add §6
      "Current Code State vs Target Architecture" with `{{CODE_STATE_DRIFT}}`
      placeholder. Skill §4.1 has assembly logic; §7.4b makes the section's
      presence mandatory (empty table → render the green-check line, not
      omit the section).
      Still open: retro-add §6 to pmg-integrations/ARCHITECTURE.md
      (commit on develop) and pmg-docs/ARCHITECTURE.md (commit on main) —
      small follow-up commits per repo, not skill work.

- [ ] **/cross-repo-init could audit ADR numbering for collisions.** The
      kalpa-docs adrs/ directory had two files numbered ADR-004
      (Tenant Isolation since Jan 2025; Secret Management added Apr 2026).
      Outstanding for ~5 weeks before this commit caught + resolved it.
      Heuristic: regex `ADR-(\d{3})-` over `adrs/*.md`, group by number,
      flag any duplicate. Low-priority polish, not a v1.0 blocker.

- [ ] **wellmed-fe/docs/15-cicd-plan.md:78** — references "ADR-004" in
      SSM/CI-CD context (i.e., the renumbered Secret Management ADR,
      now ADR-015). Needs a separate commit on wellmed-fe to update.
      Cross-repo follow-up; not part of kalpa-docs commit.

Source: `closeout-skills/closeout-skills-PROGRESS.md` §8.2 WellMed side

---

## Closeout Skills (Plan 1) — v1.1 deferred items (added §8.3 WellMed trunk)

Surfaced during the wellmed-infrastructure dogfood (Phase 5 §8.3,
2026-05-11). Not blocking v1.0 ship.

- [ ] **/cross-repo-init should detect stale `.claude/CLAUDE.md` collisions.**
      wellmed-infrastructure had an existing `.claude/CLAUDE.md` from 2026-03
      that described the repo as "infrastructure-as-code, NOT application
      code." That was true for the `main` branch at the time and remains
      true for `main` today, but is wrong for `develop` (the active trunk
      since the 2026-04-15 architecture refactor brought in the Go SDK +
      adapter library + installpb). The skill silently created a fresh
      `CLAUDE.md` at repo root without surfacing the collision. Proposed
      v1.1 polish: during Step 2 ARCH/CLAUDE handling, scan for
      `.claude/CLAUDE.md`; if present AND contradicts proposed root
      content, surface as drift with numbered reconciliation options
      (1: delete .claude/ copy, 2: keep both with explicit scope split
      in headers, 3: merge into root and delete .claude/).

- [ ] **Feature-branch surfacing could note "merged" status inline.**
      The new feature-branch heuristic in /cross-repo-init §2.2
      correctly surfaced `feat/sdk-restructure-opsi3`,
      `feature/shared-go-sdk`, and `feat/pharmacy-ssm-parameters` for
      review. All three turned out to be fully merged into develop
      (`git rev-list --right-only --count develop...<branch>` returned 0).
      Skill should still surface them (transparency > silence), but
      could compute the merged-status check inline and note "merged
      into develop, safe to delete" rather than treating all matched
      branches as potentially-live drift. Minor polish.

- [ ] **`.bak` files in `go/adapter/*/repository/`** are leftovers from
      the 2026-04-21 Phase 2 extraction in wellmed-infrastructure.
      Tracked in that repo's CLAUDE.md §8.3 as cleanup candidates.
      Not a /cross-repo-init concern but worth flagging for the
      eventual /closeout dogfood pass on that repo.

Source: `closeout-skills/closeout-skills-PROGRESS.md` §8.3

---

## Closeout Skills (Plan 1) — v1.1 deferred items (added §8.4 WellMed leaves)

Surfaced during the WellMed-leaves cascade (Phase 5 §8.4, 2026-05-11).
Not blocking v1.0 ship.

- [ ] **Assess-first principle, not sidecar-by-default.** /cross-repo-init
      should, when an existing CLAUDE.md / ARCHITECTURE.md is present,
      produce a delta proposal (sections to add to the existing file)
      before creating any new file. Currently the §3 ARCH/CLAUDE handling
      treats "file exists" as "do drift-audit" but drift-audit isn't
      strong enough to detect "this file already covers what the trio
      needs — propose targeted additions instead of a parallel file."
      The fold pattern that worked across all wellmed code repos (read
      `.claude/CLAUDE.md` content + read root CLAUDE.md content +
      author single canonical root that combines both + delete the
      `.claude/` copy) is the right default for the assess-first redo.

- [ ] **Single canonical CLAUDE.md / ARCHITECTURE.md per repo; archive
      previous versions in-place.** "We don't need two — 1 will just get
      stale" (Alex, 2026-05-11). Applied: stale `.claude/CLAUDE.md` files
      folded + deleted across wellmed code repos; wellmed-system-architecture.md
      (kalpa-docs) folded into ARCHITECTURE.md + moved to
      `archive/wellmed-system-architecture-v2.0.md`. Don't archive old
      CLAUDE.md files — only preserve freshest thinking; CLAUDE.md
      versions don't carry historical weight the way long-form ARCH docs
      do.

- [ ] **Two-trunk-archetype support** for WellMed-shaped systems.
      wellmed-backbone is the application trunk; wellmed-infrastructure is
      the pattern trunk. They have different roles in /closeout-extended
      fan-out: contract changes terminate in the application trunk;
      pattern changes terminate in the pattern trunk. CROSS-REPO.md
      template might benefit from an explicit `application-trunk` /
      `pattern-trunk` field for clarity.

- [ ] **Bootstrap-repo.sh `.gitignore` audit.** wellmed-backbone had
      `*.md` + `*.sh` + `!README.md` in its .gitignore — blocked the
      trio commit until force-added (commit acf2a2d removed those
      rules). /cross-repo-init should scan `.gitignore` for `*.md` rules
      and propose removal — markdown files should be tracked by default.

- [ ] **Branch-naming consolidation findings:**
      - `wellmed-fe` has both `develop` and `development` pointing at
        identical commits — recommend deleting `development`.
      - `wellmed-hq-fe` has no `develop` yet, only `main` — recommend
        creating `develop` to match the wellmed-* convention.
      These surfaced as calibration notes in those repos' trios; team
      action item, not skill action.

- [ ] **Stub-trio convention** (used for wellmed-catalog). When a repo
      is intentionally a stub (work-in-progress on someone's uncommitted
      local), the trio should mark it explicitly: ARCHITECTURE.md §
      "Current Code State" lists what's NOT there; CLAUDE.md leads with
      a STUB warning. /cross-repo-init could detect "stub-like" repos
      (only README.md, only `main` branch, minimal commit history) and
      offer to scaffold a stub trio with these markers.

- [ ] **Port-assignment audit.** Many `.claude/CLAUDE.md` files had
      cashier/pharmacy ports swapped. Authoritative source for ports is
      each service's own `env.example` — /cross-repo-init's port survey
      should grep `env.example` (or the SSM manifest in
      wellmed-infrastructure) rather than trusting `.claude/CLAUDE.md`
      assertions.

Source: `closeout-skills/closeout-skills-PROGRESS.md` §8.4

---

## Closeout Skills (Plan 1) — v1.1 deferred items (added §8.5 PMG-side assessment + ai-skills leaf)

Surfaced during the PMG-side assessment-pass redo + ai-skills bootstrap
(Phase 5 §8.5, 2026-05-11). Not blocking v1.0 ship.

- [ ] **/closeout: synthesize ledger from PROGRESS.md when closeout-prep.md
      absent.** Real cold-start gap surfaced when running /closeout on the
      closeout-skills scope itself: /plan §8.9 was added in Phase 2 of this
      scope, but Phases 3-5 were driven conversationally rather than through
      a fresh /plan invocation, so no closeout-prep.md was ever written. The
      framework's own meta-scope can't close out under strict ledger-required
      rules. Proposal: /closeout Step 1 should check for closeout-prep.md;
      if absent but PROGRESS.md exists, offer a "ledger-bypass mode" that
      derives §1/§2/§7/§10/§11 fields from PROGRESS.md content, with a
      loud flag in the summary header noting the synthesis. Schema-strict
      mode stays the default for plans run under newer /plan.

- [ ] **/cross-repo-init: assess-first detection of symlinked CLAUDE.md.**
      pmg-chatwoot had CLAUDE.md as a symlink to AGENTS.md, with AGENTS.md
      itself heavily PMG-customized (Sidekiq topology, PMG flag positions,
      2026-05-05 staging-Redis incident). The earlier bootstrap incorrectly
      treated both as "pristine upstream — do not modify" and created a
      sidecar. v1.1 detection: when CLAUDE.md is a symlink, follow it;
      if the target file contains repo-project-specific content (grep for
      org-name markers — PMG, WellMed, Kalpa, etc.), surface the symlink
      arrangement as a question rather than defaulting to sidecar creation.

- [ ] **/cross-repo-init: recognize parallel agent docs (CLAUDE.md +
      AGENTS.md).** Some repos use CLAUDE.md for Claude Code and AGENTS.md
      for non-Claude agents (Codex, Cursor). They are independent files,
      may diverge in detail, and both may be PMG-customized. The skill
      should detect when both exist (or when one is a symlink to the
      other) and ask whether they should remain separate, be re-symlinked,
      or merged. Currently the skill has no concept of AGENTS.md as a
      sibling doc.

- [ ] **Update memory `feedback_pr_titles.md`: pmg-chatwoot vs
      pmg-integrations commitlint asymmetry.** Memory currently says
      "Chatwoot's commitlint enforces `feature:` (spelled out)." That is
      WRONG for pmg-chatwoot: its `amannn/action-semantic-pull-request`
      Action uses standard Conventional Commits short forms (`feat`,
      `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`,
      `chore`, `revert`). pmg-integrations may still use `feature:`
      long-form (confirm). Surfaced when PR #115 title `feature(docs):`
      failed Validate PR title check; fixed to `docs:`.

- [ ] **WellMed/Kalpa branch protection follow-up.** During §8.4 and the
      prior session's batch, every WellMed/Kalpa repo accepted direct
      pushes to develop or main without resistance — no branch protection
      rules were enforced. If the team wants the same PR-gated workflow
      as pmg-chatwoot (which has husky pre-push + the Validate-PR-title
      Action), enable Branch Protection Rules on origin/develop in each
      Kalpa-Health repo (require PR, require CI pass, optionally require
      review). Operational task, not skill work.

- [ ] **/closeout: surface "ledger-bypass mode" as a flag.** Pair with
      the first item above: `--ledger-from-progress` flag explicitly opts
      into PROGRESS.md synthesis. Useful for meta-scopes and for legacy
      plans that pre-date the ledger feature.

Source: `closeout-skills/closeout-skills-PROGRESS.md` §8.5 (PMG-side
assessment + ai-skills leaf)

## Herdr Agent Workflow (Plan 4)
Source: plans/4-herdr-agent-workflow/progress.md
Touches: ai-skills · concurrency/SKILL.md · herdr/SKILL.md · scope + plan + closeout SKILL.md · ~/.claude/CLAUDE.md

- [x] **Dedup the `/concurrency` §3 routing table.** Done 2026-09-23 (v0.3.1) — §3 is now a pointer to `herdr` §6.
- [x] **Ratify the CLAUDE.md wording.** Kept as written (Alex, 2026-09-23) — the enforcement-hook item filed alongside it was dropped as a misdiagnosis (8ad8305); the rule's research carve-out landed in scope 6.
- [x] **Dogfood the new `/concurrency` flow (Phase 1 gate A).** Met 2026-09-23 by the 137.2 / 137.2w2 runs (09-07) in the dispatch log.
- [ ] **Re-test codex idle-vs-done after the herdr v9 hook.** `/concurrency`
      §10 has codex completion mapping to `idle`, never `done`. Once Alex runs
      `herdr integration install claude` (v8 → v9; codex already current),
      check whether `agent wait --until done` fires for codex. If it does,
      simplify the §7.1 marker-wait.
- [ ] **Integrate the friend's bars/diff tool** (follow-up scope). Attach points
      in `plans/4-herdr-agent-workflow/artifacts/friend-tool-seams.md`. Do NOT
      build bars / model-token / space-level-limit before his repo lands.

## skills-relook — fleet CLAUDE.md memory pointers (Scope 2, Plan 2.3)
Source: plans/archive/2-skills-relook/progress.md (Plan 2.3)
Touches: cross-repo-init/templates/CLAUDE.md.template · 13 repo CLAUDE.md files (§8.2 + §9 "Plans and memory")
- [ ] **Strip the pmg memory path from 13 repos' CLAUDE.md** — the trio template wrote
      `~/.claude/projects/-Users-alexknecht-Projects-pmg/memory/` (+ `memory/…` citations) into
      every scaffolded CLAUDE.md; it dead-ends outside the pmg store (ai-skills CLAUDE.md §9.3).
      Template fixed 2026-09-25 (cross-repo-init 1.4.0). Repos: wellmed/{kalpa-company-profile,
      wellmed-fe, wellmed-backbone, wellmed-cashier, wellmed-hq, wellmed-consultation,
      wellmed-supply-chain, wellmed-hq-fe, wellmed-gateway-go, wellmed-pharmacy},
      pmg/{pmg-docs, pmg-chatwoot, pmg-integrations}. Inline any rule a pointer carried before
      deleting it. Next `/closeout` trio sync per repo will propose it, or do a sweep.

## skills-relook — follow-ups (Scope 2, Plan 2.3)
Source: plans/archive/2-skills-relook/progress.md (Plan 2.3)
Touches: scripts/lint-skill.py · all SKILL.md
- [ ] **Paraphrased cross-skill duplicates** are invisible to the linter (e.g. GLM traps /concurrency vs
      herdr were found by reading). Second sighting of a drift from one → build the deferred eval pass.

## research-lanes — /research pane mode (Scope 6, Plan 6.1)
Source: plans/archive/6-research-lanes/progress.md (Plan 6.1)
Touches: research/SKILL.md · research/scripts/lanes.py · templates/closeout-prep.md.template · scripts/ledger-init.sh
- [x] **Done 2026-09-29 (plan 5.3 Task 3.3a, `4037593`).** **Closeout ledger template ships fake example entries.** `templates/closeout-prep.md.template`
      carries worked examples (Chatwoot webhook, `validateWebhookSignature`, SSM token assumptions)
      as section *bodies*, not inside HTML comments, and `scripts/ledger-init.sh` copies it whole —
      so every new ledger opens with invented §3/§4/§5/§8/§10/§11 entries a /closeout could read as
      real. Scope 6's ledger had them (only its phase blocks were real). Fix: move examples into
      comments or `_(none)_` placeholders; have ledger-init fail if an example marker survives.
- [ ] **X pages yield nothing to research lanes** (first sighting, 2026-09-26): a2 found poteto's
      "Complete Guide to pstack" X articles but WebFetch extracted no claims. On a second sighting,
      add to research/SKILL.md §3.3 brief: X/paywalled pages → record the URL as missing coverage and
      ask the driver to request a paste.
- [ ] **Lane-inferred dates** (first sighting, 2026-09-26): a2 dated an X article "after 2026-09-21"
      by guessing from its status ID and got the comparison backwards (it was 2026-09-01). On a
      second sighting, tell lanes to report only dates read on the page and leave `publishDate` null
      otherwise.

## plan §11 archive — stale paths inside archived scopes (seen at scope 6 closeout)
Source: plans/5-verify-lever/progress.md (ready-to-clear audit, 2026-09-26)
Touches: plan/SKILL.md §11.3 · closeout/SKILL.md §13 · plans/archive/{2,4,6}-*/
- [ ] **Archiving leaves pre-archive paths inside the moved docs.** After `mv` to `archive/`,
      progress.md `**Scope:**`, the plan's `**Parent scope:**`, and closeout-prep's `**Plan:**`
      still point at `plans/<N>-<slug>/`, and closeout-prep's header still reads
      `Status: in-progress`. Seen in archived scopes 2, 4 and 6. Not a resume blocker (closed
      scopes aren't resumed), but a cold reader following those lines hits nothing. Fix in
      /plan §11.3: repoint the three lines and flip the ledger status in the same commit as the move.

## Contracts + deterministic scripts (Plan 5.1)
Source: plans/5-verify-lever/progress.md (## Plan 5.1)
Touches: scripts/{resolve-identifiers,verify-run,verdict-gate,plans-index}.py · scripts/ledger-init.sh · templates/verify-contracts.md
- [x] Run /closeout for plan 5.1 — deferred at completion on 2026-09-26 (Alex: straight into
      5.2); fold into the scope-level closeout after 5.3. **Done 2026-09-29 (scope closeout).**
Nothing else deferred: the pending wiring (`ledger-init.sh --repo` from /plan §5.13,
advisory → blocking flip) is planned work in 5.3 Tasks 3.2/3.4, not a residual.

## /verify skill + /review on codex (Plan 5.2)
Source: plans/5-verify-lever/progress.md (## Plan 5.2)
Touches: verify/ · review/ · scripts/{codex-exec,verify-run,verdict-gate,verify_lib}.py · templates/verify-contracts.md · plans/5-verify-lever/finish-conditions.md
- [x] **Done 2026-09-29 (5.3: `/verify` §4 + `/scope` §5.10 rule; `p3-fixtures-live` uses it).** Fixture/eval finish rows set `VERIFY_EVAL=1` in their `env` cell so the live-judge tier runs
      under the runner — `/verify` 5.2 found `p2-fixtures` inconclusive without it (Alex: skip now,
      use from now on). Natural home: 5.3's standard rows that `/scope` emits (`verify/SKILL.md` §4).
- [ ] Class-A browser driving (`/browse`) is a T2 WellMed-adapter deliverable, not `/verify`'s
      (Alex, 2026-09-29) — add it to kalpa-docs `plans/test-suite-program/T2-wellmed-adapter/NOT-YET-SCOPED.md`
      when T2 is scoped.
- [x] Run /closeout for plan 5.2 — deferred to scope end (fold into the scope-level closeout after 5.3). **Done 2026-09-29 (scope closeout).**

## repo-graph-check.py false DRIFT — found by WellMed scope 149 (2026-09-29)
Source: ~/Projects/wellmed/kalpa-docs/plans/149-fail-loud-sweep/closeout-prep.md §11
Touches: scripts/repo-graph-check.py · /plan §5.6.1 · /scope Repo Graph snapshot

- [ ] **VERIFIED STILL TRUE 2026-09-29:** **`repo-graph-check.py` compares the snapshot SHA to local `HEAD`, but `/scope` records `origin/<trunk>`** (the WellMed Repo Graph column is literally "HEAD SHA (origin/develop)"). A local checkout a few commits behind its remote reads every repo as `diverged` → exit 3 → /plan STOPs. Scope 149's Phase 0 reported all 14 repos diverged; checked against `origin/<trunk>`, every recorded SHA was an ancestor (9 unchanged, 4 advanced). Fix: resolve the snapshot's column (origin/trunk) — `git fetch` then compare to `origin/<trunk>` — and keep local-HEAD/dirty as a separate advisory line.
      **Correction (2026-09-29, scope 5 review 5.3-r3-03, checked against the code):** the writer,
      `scripts/repo-graph-snapshot.sh:34`, records local `HEAD` (`git rev-parse --short HEAD`), not
      `origin/<trunk>`. The WellMed table's "HEAD SHA (origin/develop)" column label is what claims origin.
      So the snapshot and the checker agree on local HEAD. The defect is the label, or the local checkouts
      scope 149 snapshotted differing from those its /plan later read. Before fixing, decide which ref
      the contract means, then make the writer, the column label and `repo-graph-check.py` all use it.

## Wiring + self-heal + rollout (Plan 5.3)
Source: plans/5-verify-lever/progress.md (## Plan 5.3)
Touches: scripts/{resolve-identifiers,verdict-gate,finish-table,lever-candidates,clone-behind,plans-index,verify_lib}.py · review/ · verify/ · scope/ · plan/ · closeout/
- [ ] **Shell env scan: false alarm on a backgrounding line** (review 5.3-r12-01, rejected; `/verify 5.3` judged the rejection wrong).
      `A=1; sleep 0 & echo $A` reports `A` as undeclared, because a line that backgrounds anything binds nothing
      (`resolve-identifiers.py` `shell_commands`). Fix: exclude only the backgrounded AND/OR list (back to the previous
      `;`/newline), and keep continued lines fail-closed. Needs one codex re-review. Deferred: Alex's codex quota was out (2026-09-29).
- [x] **Dropped 2026-09-29 (Alex: "if we're done we're done").** **Commits after review r12 were not codex-reviewed**: effort scaling (`2963216`) and the 5.3 closeout commits.
      Codex quota was out; Alex said move on. Run `/review --scope plans/5-verify-lever --unit 5.3` on `01af243..<closeout HEAD>` when quota allows.
- [ ] **15 undeclared env reads in older ai-skills shell scripts**, surfaced by the new shell scan over all history: `grafana-remediate/`
      (`GRAFANA_BASE/FROM/TO/TOKEN/TOKEN_SSM`, `ALARM_CW_HEARTBEAT/CW_NAMESPACE/HEARTBEAT_LOG/WT_MAX_AGE_S/WT_ROOT`, `FROM`),
      `GEMINI_API_KEY`, and herdr's `HERDR_ENV`/`HERDR_WORKSPACE_ID`. Declare them in `.env.example`, or mark them as
      provided by the platform. `python3 scripts/resolve-identifiers.py --repo . --range <root>..HEAD` lists them.

## Lever candidates

<!-- Written by scripts/lever-candidates.py (verify-contracts.md §4.9). One item per
     lever_id; a lever is built on its second sighting, from a different scope. -->
- [ ] **`scripts-tests-green-inconclusive`** — Run the unittest entrypoint in an isolated disposable checkout of e3b74ec and retain its exit code and output. · gap: The available test run used a later, dirty revision.
      Touches: ai-skills · scripts-tests-green
      Sighting: ai-skills/5-verify-lever · run 5.1-20260926T100859-79e8 · 2026-09-29
- [ ] **`fixtures-inconclusive`** — Run the existing fixture test entrypoint with VERIFY_EVAL=1 and retain its exit status and output against ac3869d. · gap: The recorded fixture run skipped the live-judge cases, leaving two planted defects and their repaired copies unverified at the final SHA.
      Touches: ai-skills · p2-fixtures
      Sighting: ai-skills/5-verify-lever · run 5.2-20260929T031136-b3a2 · 2026-09-29
- [ ] **`external-announcement-receipt`** — Attach a dated link or delivery receipt for the sent team announcement to the scope artifacts. · gap: The rollout announcement's delivery cannot be checked from the repository artifacts.
      Touches: ai-skills · p3-scope-deliverables
      Sighting: ai-skills/5-verify-lever · run 5.3-20260929T065028-d319 · 2026-09-29


## /verify + the verification lever — scope closeout (Scope 5)
Source: plans/archive/5-verify-lever/progress.md · `verdict-gate.py --scope plans/archive/5-verify-lever --all`
Touches: scripts/verdict-gate.py · scripts/verify_lib.py · scripts/finish-table.py · templates/verify-contracts.md §5.2
- [ ] **A finish-table revision bump invalidates every unit's verdict** (`verdict-gate.py`: "verdict predates the current
      finish table"). Adding 5.3's rows (rev 5, 6) made 15 complete 5.1/5.2 checks read as failed at closeout. Fix: bind a
      verdict to the revision of the rows *it owns* (e.g. a per-row revision, or the changelog's last change touching that
      owner), so appending a later phase's rows doesn't expire earlier phases. This is the main reason scope 5 archived `⚠ verify failed`.
- [ ] verify failed at closeout (all complete verdicts; none re-run, per closeout §5.6.2):
      - 15 × "verdict predates the current finish table" — 5.1: scripts-tests-green, names-resolve, contracts-generate-clean,
        gate-semantics-tested, scope-deliverables, no-overbuild · 5.2: p2-tests-green, p2-names-resolve, p2-skills-lint,
        p2-codex-failure-modes, p2-review-log, p2-fixtures, p2-scope-deliverables, p2-no-overbuild, p2-rejections-justified (item above)
      - `review:ai-skills` (5.1): 5.1's commits were never codex-reviewed (the owned miss in the Decisions Log, 2026-09-29)
      - `p3-scope-deliverables` (5.3): inconclusive, no delivery receipt for the announcement (Alex: his word is the evidence; accepted)
      - `p3-rejections-justified` (5.3): the r12-01 rejection (see "Shell env scan: false alarm" under Plan 5.3 above)
- [x] Run /closeout for plans 5.1 and 5.2 — folded into this scope closeout (2026-09-29)
