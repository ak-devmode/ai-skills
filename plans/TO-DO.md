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
