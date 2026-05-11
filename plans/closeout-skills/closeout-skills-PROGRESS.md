# Progress Log: Closeout Skills + Cross-Repo Self-Healing

## Resume Context
**Plan:** ~/Projects/ai-skills/plans/closeout-skills/closeout-skills-PLAN.md
**Last action:** Phase 5 §8.1 (pmg-integrations on develop, commit 0befa30) + §8.2 PMG side (pmg-docs on main, commit 19bd2f0) + §8.2 WellMed side (kalpa-docs on main, commits 0950290 + 330bd22 + **4c03f09** fold/archive) + §8.3 (wellmed-infrastructure on develop, commit cd2acac + ca16267 re-trunk-fold + 1b673ac port-fix) + **§8.4 ALL WellMed leaves complete** (wellmed-backbone develop 5758f21+acf2a2d; wellmed-consultation develop d115818; wellmed-cashier develop 16abb9c; wellmed-pharmacy develop 939dd88; wellmed-gateway-go develop 0883e59; wellmed-hq develop 84436af; wellmed-supply-chain develop 7fa0549; wellmed-fe develop aa9ec41; wellmed-hq-fe main b6b8450; wellmed-catalog main e0ab883 STUB; kalpa-company-profile main 319c4ca). §8.3 prep was done in prior session: Kalpa-Health gap analysis + cleanup; wellmed-gateway-go ingarso remote removed; 6 behind-repos fast-forwarded to org defaults; 5 gap repos cloned; wellmed-consultation-shared confirmed retired (memory saved); all 13 local wellmed repos ahead=0 behind=0. The branch-aware surveying logic baked into /cross-repo-init pre-§8.3 paid for itself immediately: wellmed-infrastructure showed +0 on main / +10 on develop with ~19k lines of code (SDK + adapter library + installpb + migration/seeder) absent from main; the §2.2 cascade correctly routed survey to origin/develop. All three feature branches (`feat/sdk-restructure-opsi3`, `feature/shared-go-sdk`, `feat/pharmacy-ssm-parameters`) confirmed fully merged into develop (right-side count = 0) — safe to delete remotely but left for user. Repo now has CROSS-REPO.md (100 lines, trunk archetype with 10 consumers + kalpa-docs docs leaf + 4 external dependents), ARCHITECTURE.md (268 lines with the load-bearing §6 Drift section documenting main-vs-develop), CLAUDE.md (206 lines at repo root, supersedes stale `.claude/CLAUDE.md` from 2026-03). Committed locally on develop only — not pushed per workflow.
**Next action:** New context → finish PMG side. Per user direction "complete one org at a time": only pmg-chatwoot remains in PMG leaves (mcu-status and KP2MI-foreign-workers explicitly skipped — not active parts of repos). pmg-chatwoot needs an assessment-first redo: my earlier attempt (cherry-picked unpushed commit af623b633 on local develop) wrote a `.claude/CLAUDE.md` sidecar without realizing the root CLAUDE.md was already heavily PMG-customized (Sidekiq topology, flag positions, 2026-05-05 staging-Redis incident). Plus husky pre-push blocks direct pushes to develop on that repo. Correct approach next context: (1) read root CLAUDE.md fully; (2) propose targeted section additions (archetype, trio file pointers, cross-repo position) — not a parallel file; (3) feature-branch + PR to develop. User also mentioned "3 chatwoot integrations + docs" remaining — probably pmg-integrations subdir-level docs or PMG-side adjacent work; clarify with user when next session starts. Plus ai-skills itself as a leaf (commit on main).
**Open blockers:** None. WellMed/Kalpa side fully complete and pushed.
**Key calibration findings from §8.4:**
- **Assess-first, don't sidecar-by-default.** Skill design flaw surfaced: when an existing CLAUDE.md / ARCHITECTURE.md is present, /cross-repo-init should ASSESS it against the trio shape and propose targeted edits, not always create a new file. The "fold both stale and rich content into single canonical root CLAUDE.md, then delete `.claude/CLAUDE.md`" pattern worked cleanly across wellmed-infrastructure, wellmed-backbone, wellmed-consultation, wellmed-cashier, wellmed-pharmacy, wellmed-hq, wellmed-supply-chain. Same pattern applied to kalpa-docs (archive wellmed-system-architecture.md, fold agent-critical content inline into ARCHITECTURE.md).
- **Two-trunk model for WellMed:** wellmed-backbone is the application trunk; wellmed-infrastructure is the pattern trunk (Go SDK + adapter library + AWS infra). The trio now reflects this in both repos' ARCHITECTURE.md §7 and CROSS-REPO.md §1/§4. /closeout-extended must walk both edges (contract changes flow through backbone; pattern changes through infrastructure).
- **Port assignment correction (cashier ↔ pharmacy):** confirmed via wellmed-cashier/env.example that cashier is `:50054` and pharmacy is `:50053`. Several `.claude/CLAUDE.md` files had this swapped. Fixed in wellmed-infrastructure root CLAUDE.md §5.3 (commit 1b673ac) and in each service's new trio.
- **`.gitignore *.md` rule** in wellmed-backbone blocked trio commit until force-added. Removed (commit acf2a2d). Scanned other wellmed repos — only wellmed-backbone had this rule.
- **Branch-naming inconsistency** in wellmed-fe (both `develop` and `development` exist, pointing to same commits) and wellmed-hq-fe (no `develop` yet, only `main`). Surfaced as calibration notes in those repos' CROSS-REPO.md / ARCHITECTURE.md; recommend team consolidate to `develop` everywhere.
- **wellmed-catalog stub** has ~2 weeks of uncommitted local work elsewhere; trio explicitly marks it STUB and instructs agents not to fabricate implementation.
- **`.claude/CLAUDE.md` content was richer than root CLAUDE.md in most wellmed code services** — root had shallow content (Bahasa preference, auto-save rules in some; nothing in others), `.claude/CLAUDE.md` had the deep ADR/ULID/env content. Fold direction: bring rich content up to root, delete `.claude/CLAUDE.md`.
**Key files changed (cumulative):** templates/closeout-prep.md.template (moved + renamed), plan/SKILL.md (extended), plan/tests/verification-recipes.md (filenames updated), closeout/SKILL.md (new), closeout-extended/SKILL.md (new), closeout-extended/tests/upward-traversal-recipe.md (new), ~/.claude/skills/{closeout,closeout-extended} (symlinks), plans/closeout-skills/closeout-skills-PLAN.md (v0.2 → v0.3), cross-repo-init/templates/CROSS-REPO.md.examples.md (rewrite — three archetypes), plans/TO-DO.md (v1.1 items + §8.2 WellMed-side items appended). Plus committed: pmg-integrations on develop commit 0befa30; pmg-docs on main commit 19bd2f0; kalpa-docs on main commits 0950290 + 330bd22 (trio + mermaid sweep + ADR renumber); **wellmed-infrastructure on develop commit cd2acac (trio)**.

---

## Decisions Log

- (2026-05-11) Branch override: plan specifies `feature/closeout-skills` but executing on `main` per `feedback_branch_workflow.md` (work on current branch, don't create new). All recent ai-skills commits on main; solo-dev repo. Plan Branch field treated as advisory.
- (2026-05-11) Session scope: targeting Phase 1 completion (3 active tasks: 4.1, 4.2, 4.3). §4.4 deferred per plan v0.2.
- (2026-05-11) All eng-review decisions baked into plan v0.2 before execution begins — see §9 Key Decisions in plan file.
- (2026-05-11) Mid-Task-6.1 user feedback: rename `close-out-prep.md` → `closeout-prep.md` (match /closeout skill name, no hyphen) and move template from `plan/templates/` to `ai-skills/templates/` (shared across all three closeout-framework skills, not bundled in /plan). Plan bumped v0.2 → v0.3. References updated across plan/SKILL.md, closeout/SKILL.md, plan/tests/verification-recipes.md, the plan file itself, and the template's internal title.

---

## Session: 2026-05-11

### Phase 0: Pre-flight
- **Status**: ✅ DONE
- **Completed**: 2026-05-11
- **Paths verified**: markdown-style/SKILL.md, plan/SKILL.md, scope/SKILL.md (all exist)
- **Parent scope**: standalone
- **Branch**: main (deviation from plan's `feature/closeout-skills` field — see Decisions Log)
- **Issues**: None

### Task 4.1: Define CROSS-REPO.md schema with concrete worked examples
- **Status**: ✅ DONE
- **Completed**: 2026-05-11
- **What was done**: Created `cross-repo-init/templates/` directory. Wrote `CROSS-REPO.md.template` — the canonical shell with `{{placeholders}}` for /cross-repo-init to substitute, plus HTML comments documenting purpose, format, and maintenance triggers. Wrote `CROSS-REPO.md.examples.md` with two filled-in worked examples: pmg-integrations (hub archetype: consumes wellmed-infrastructure patterns, exposed contracts feed 4 PMG consumers) and wellmed-infrastructure (trunk archetype: empty Pattern Sources since it IS the trunk, 7 wellmed/pmg consumers). Notes section documents how /cross-repo-init should propose contents when scaffolding new repos.
- **Files modified**: cross-repo-init/templates/CROSS-REPO.md.template, cross-repo-init/templates/CROSS-REPO.md.examples.md
- **Issues**: None
- **Acceptance verified**: Template has unambiguous placeholder syntax; renders to valid CROSS-REPO.md when filled. Both examples use real repo names and real contract descriptions, not placeholders.

### Task 4.2: Define ARCHITECTURE.md stub template with concrete example
- **Status**: ✅ DONE
- **Completed**: 2026-05-11
- **What was done**: Wrote `ARCHITECTURE.md.template` — 67-line shell (under the 80-line target) with five sections (Components, Data Flow, Key Decisions, External Integrations, Cross-Repo Position), all with HTML comment guidance for /cross-repo-init scaffolding. Wrote `ARCHITECTURE.md.examples.md` with one filled-in worked example (pmg-integrations) drawing on actual project context: SSM secret patterns, idempotency rules, WhatsApp NAMED templates, develop-branch convention, Chatwoot deploy gotchas, Xendit pre-settlement refund handling, Grafana wildcard config. Notes section documents auto-detection heuristics and tier-specific guidance (hub vs trunk vs leaf vs docs-only).
- **Files modified**: cross-repo-init/templates/ARCHITECTURE.md.template, cross-repo-init/templates/ARCHITECTURE.md.examples.md
- **Issues**: None
- **Acceptance verified**: Template is 67 lines (under 80-line target). Uses /markdown-style hierarchical numbering (1, 1.1, etc., implicitly via section headers). Has HTML-comment placeholders for /cross-repo-init to detect and fill. One concrete worked example present with real project-specific Key Decisions and External Integrations drawn from memory.

### Task 4.3: Build /cross-repo-init skill
- **Status**: ✅ DONE
- **Completed**: 2026-05-11
- **What was done**: Wrote `cross-repo-init/SKILL.md` (~200 lines, 10 sections) implementing the full bootstrap flow: Step 0 detect repo + git state; Step 1 CROSS-REPO.md handling (scaffold-if-absent / drift-audit-if-present with deterministic-first then LLM-judge passes); Step 2 ARCHITECTURE.md handling (same flow); Step 3 idempotency verification; Step 4 report. Skill explicitly bans AskUserQuestion — all interaction is numbered inline options. Auto-detection rules: Pattern Sources from package.json/go.mod/imports; Consumers via best-effort grep across `~/Projects/*` (acknowledged approximate); Components from top-level dirs; Key Decisions lifted from CLAUDE.md + memory; External Integrations from SSM patterns and API client imports. Data Flow diagrams never auto-generated (rule §7.4 — wrong diagram worse than missing). Documented known limitations + recovery from interrupted runs + first-run recipe targeting pmg-integrations as Phase 5 dogfood subject. Symlinked `~/.claude/skills/cross-repo-init -> ~/Projects/ai-skills/cross-repo-init` so the skill is registered with Claude Code.
- **Files modified**: cross-repo-init/SKILL.md (new), ~/.claude/skills/cross-repo-init (new symlink)
- **Issues**: None
- **Acceptance verified**: Skill loaded into Claude Code (visible in skill list — confirmed via system reminder). Full end-to-end dogfood verification deferred to Phase 5 §8.1 per plan.

### Task 4.4: Update /scope to recognize ARCHITECTURE.md and CROSS-REPO.md as required reads
- **Status**: ⏭️ SKIPPED (deferred to v1.1 per /plan-eng-review R1A)
- **Completed**: 2026-05-11
- **What was done**: Per plan v0.2 §4.4, this task is explicitly deferred to a follow-up plan. Reason: /scope auto-suggesting /cross-repo-init is polish, not foundation. The closeout skills work without it. Re-evaluate after Phase 5 completes.
- **Files modified**: None
- **Issues**: None — intentional skip per plan

### Task 5.1: Define close-out-prep.md schema with version field and worked examples
- **Status**: ✅ DONE
- **Completed**: 2026-05-11
- **What was done**: Wrote `plan/templates/close-out-prep.md.template` — 220 lines (under 250 target). Includes `**Schema version: 1.0**` field at top for forward compat detection. All 11 sections present (Execution Summary, Files Changed, Patterns Followed, Patterns Created, Cross-Repo Touchpoints, Docs Loaded, Docs Likely Affected, Assumptions, Deferred, Coverage Map, Risk Flags) with worked examples per section drawn from a plausible Chatwoot webhook scenario. Phase-blocks section at end uses timestamped headers (`## Phase {P}: {name} (started {ISO})`) so resumed phases append rather than overwrite. HTML comments document append-point triggers for each section.
- **Files modified**: plan/templates/close-out-prep.md.template
- **Issues**: None
- **Acceptance verified**: Template is 220 lines (under 250 target). Schema version field is present and parseable. Each section has 1-2 worked examples.

### Task 5.2: Add /plan rule: read ARCH+CROSS-REPO+CLAUDE.md at session start
- **Status**: ✅ DONE
- **Completed**: 2026-05-11
- **What was done**: Extended `plan/SKILL.md` §5 Phase 0 Pre-flight with four new subsections (5.9–5.12): 5.9 reads CLAUDE.md/ARCHITECTURE.md/CROSS-REPO.md at session start; 5.10 bootstrap-state check distinguishes unbootstrapped vs partial-bootstrap (latter halts with /cross-repo-init suggestion); 5.11 Pattern Source path validation per Issue 17 critical-gap mitigation — halts cleanly when a declared Pattern Source path doesn't exist on disk, preventing the silent-failure mode where stale CROSS-REPO.md produces spurious "no pattern found" results; 5.12 builds in-session Pattern Sources map for use by §7 Pattern-First Rule (in-memory only per Issue 1B, no ledger persistence). Also relaxed 5.8's "never main/master" rule when recent commit history shows main is active development branch (e.g., solo-dev repos) — references `feedback_branch_workflow.md`.
- **Files modified**: plan/SKILL.md (§5 Phase 0 Pre-flight)
- **Issues**: None
- **Acceptance verified**: Phase 0 now logs ARCH+CROSS-REPO state; missing files trigger appropriate halts; Pattern Source path validation is explicit and addresses Issue 17.

### Task 5.3: Add /plan rule: pattern-first grep before writing new methods
- **Status**: ✅ DONE (combined with Task 5.4 implementation — same Pattern-First Rule section)
- **Completed**: 2026-05-11
- **What was done**: Inserted new top-level section §7 "Pattern-First Rule" in `plan/SKILL.md` between §6 (Execution Rules) and §8 (formerly §7, now renumbered) Important Behaviors. Subsections 7.1–7.4 cover the grep-first behavior: 7.1 when the rule fires (12-item list of known-extensible areas: webhook handlers, event publishers, FHIR resources, SSM readers, Notion writers, Zoho Deluge, signature verification, retry logic, logger wrappers, config loaders, DB adapters); 7.2 what gets grepped (local repo + declared Pattern Sources from CROSS-REPO.md, both with relevant sub-paths); 7.3 caching (in-memory per-session only, no ledger persistence per Issue 1B); 7.4 when a match is found (≥80% match → use existing pattern + document deviation; inventing parallel requires §7.5 halt-and-ask with explicit user OK). Renumbered downstream sections §7→§8, §8→§9, §9→§10, §10→§11, §11→§12 along with all subsection references (~25 edits).
- **Files modified**: plan/SKILL.md (new §7 inserted, §8-§12 renumbered with all sub-subsection refs updated)
- **Issues**: None
- **Acceptance verified**: Rule fires on the 12 declared known-extensible areas. Cache rule is explicit. Pattern Source paths come from §5.12 map.

### Task 5.4: Add /plan rule: halt-and-ask with session-scoped approval and structured §4 prompt
- **Status**: ✅ DONE (in same Pattern-First Rule section as Task 5.3)
- **Completed**: 2026-05-11
- **What was done**: Wrote §7.5–§7.8 of the new Pattern-First Rule section: 7.5 halt-and-ask flow (numbered inline options 1-4, explicitly bans AskUserQuestion); 7.6 session-scoped pattern approval (follow-up question after user approves a parallel impl — yes auto-applies same-shape methods within session with §3 audit note, no halts each time; approvals expire at session end per Issue 2A); 7.7 §4 entry template requiring alternatives-considered field even when truly novel (must list places searched; recommendation field drives /closeout-extended's upward traversal); 7.8 bias toward existing imperfect patterns (parallel requires explicit user decision + populated §4 + recommendation closing the loop).
- **Files modified**: plan/SKILL.md (§7.5–§7.8 of new Pattern-First Rule)
- **Issues**: None
- **Acceptance verified**: Halt-and-ask format is explicit and numbered. Session-scoped approval mechanism is documented with expiry rule. §4 entry template is mandatory (alternatives-considered required).

### Task 5.5: Add /plan rule: append-to-ledger throughout execution + close-out-prep.md location
- **Status**: ✅ DONE (Task 5.6 folded in per R2/Issue 10A)
- **Completed**: 2026-05-11
- **What was done**: Added §8.9 "Append to close-out-prep.md throughout execution" to renumbered §8 Important Behaviors. Documents all append points: §2 after file mods; §3/§4 per Pattern-First Rule outcomes; §5 on contract touches; §6 from §5.9 Phase 0 reads; §7 incremental as files change (ranked by agent-load-bearing weight); §8 on unverified assumptions; §9 on skips; §11 on uncertainty. Phase boundaries get timestamped headers for resumability. Schema version field check enforced. close-out-prep.md location documented: `{scope-folder}/close-out-prep.md` (child of /scope) or `{plan-folder}/close-out-prep.md` (standalone). Template path: `~/.claude/skills/plan/templates/close-out-prep.md.template`.
- **Files modified**: plan/SKILL.md (new §8.9)
- **Issues**: None
- **Acceptance verified**: All 11 append points documented with their triggers. Schema version field reference present. Template path is unambiguous.

### Task 5.6: Update /plan §3 schema reference to include close-out-prep.md location
- **Status**: ⏭️ SKIPPED (folded into Task 5.5 per /plan-eng-review R2/Issue 10A)
- **Completed**: 2026-05-11
- **What was done**: Per plan v0.2 §5.6, this micro-task was folded into §5.5 to eliminate task-list padding. Content is in §8.9 (location field).
- **Files modified**: None (covered by 5.5)
- **Issues**: None — intentional fold per plan

### Task 5.7: Tests for /plan rule additions
- **Status**: ✅ DONE (signed off 2026-05-11)
- **Completed**: 2026-05-11

---

## Phase 3 — /closeout skill

### Task 6.1: Build /closeout skill — main flow
- **Status**: ✅ DONE
- **Completed**: 2026-05-11
- **What was done**: Wrote `closeout/SKILL.md` (~510 lines) implementing the full 11-step flow described in plan §6.1. Frontmatter: `name: closeout`, `version: 1.0.0`, allowed-tools without AskUserQuestion. Sections: §1 How It Works (11-step diagram + idempotent-on-rerun guarantee), §2 Flags (`--skip-tests`, `--skip-memory`, `--dry-run`), §3 Step 1 ledger-read + schema-version verification (halts on incompatible version, warns on older minor, parses sections + phase blocks), §4 Step 2 branch verification (mismatch → numbered inline prompt, never silent switch off main), §5 Step 3 test execution + gating (Continues past test failure with NOT-HEALED flag rather than halting — doc fixes still valuable; never auto-fixes failing tests), §6 Step 4 §3 spot-check (verifies both new method and pattern source still exist; sample budget for >50 entries), §7 Step 5 §4 triage (routes on recommendation field: extend / accept-as-new / fold-into / write-TODO; upward routes deferred to /closeout-extended), §8 Step 6 doc drift two-pass (Pass 1 deterministic grep all docs; Pass 2 LLM-review CLAUDE+ARCHITECTURE only per Issue 9A), §9 Step 7 ARCHITECTURE.md validation (Components/DataFlow/KeyDecisions/Integrations/CrossRepo audit; never auto-regenerates diagrams), §10 Step 8 coverage read-only report (categorizes covered/uncovered/test-only; never auto-writes tests), §11 Step 9 memory writes (auto-write per user preference; de-dup gap accepted per Issue 13B), §12 Step 10 archive — explicitly invokes /plan §12 code path, does NOT duplicate, §13 Step 11 structured summary template, §14 Resumability (no resume-state by design; idempotent re-run instead), §15 Failure modes & recovery, §16 Important Behaviors (never modifies ledger, never commits, never auto-fixes tests, workspace-relative paths, loud-flag policy, stay-local), §17 First-run recipe for Phase 5 §8.6 dogfood. Mid-task user feedback baked in: ledger renamed to `closeout-prep.md` (no hyphen), template path is `~/Projects/ai-skills/templates/closeout-prep.md.template` (shared, not bundled in /plan). Symlink to ~/.claude/skills/ pending end-of-Phase-3 (defer until Phase 3 checkpoint passes user review).
- **Files modified**: closeout/SKILL.md (new), templates/closeout-prep.md.template (moved from plan/templates/, internal title updated), plan/SKILL.md (template path reference updated to shared location), plan/tests/verification-recipes.md (filename rename), plans/closeout-skills/closeout-skills-PLAN.md (rename + v0.2 → v0.3 bump + changelog)
- **Issues**: None
- **Acceptance verified**: 11-step flow present and correctly numbered. Frontmatter has no AskUserQuestion. Archive logic invokes /plan §12 (not duplicated). All five "renaming/move" references updated cleanly. /closeout-extended deferral surfaces are explicit (step 5 routes upward edits to /closeout-extended).

### Task 6.2: Implement two-pass drift detection (grep-all + LLM-review CLAUDE/ARCH only)
- **Status**: ✅ DONE (implemented in Task 6.1 — §8 Step 6 of closeout/SKILL.md)
- **Completed**: 2026-05-11
- **What was done**: Pass 1 (deterministic grep) walks every doc in §7 of ledger, extracts candidate symbols (functions, paths, env vars, flags, struct/class names), verifies each against current code. Pass 2 (LLM-review) is restricted to CLAUDE.md + ARCHITECTURE.md only — narrative-drift review on lower-tier docs intentionally skipped per Issue 9A. Edits applied in priority order CLAUDE > README > ARCH > docs/*. Batching policy: docs with >10 candidates apply all edits in one sequence (not per-edit prompts).
- **Files modified**: covered by Task 6.1 (closeout/SKILL.md §8)
- **Acceptance verified**: Pass-1-only on long-tail docs is explicit ("Other docs (README, docs/*) do NOT get Pass 2"). Pass 2 enumerates the two-doc whitelist clearly.

### Task 6.3: Implement test execution + gating
- **Status**: ✅ DONE (implemented in Task 6.1 — §5 Step 3 of closeout/SKILL.md)
- **Completed**: 2026-05-11
- **What was done**: Test command detection cascades CLAUDE.md → package.json → go.mod → pyproject/requirements → Cargo.toml → "no test command" fallback. Pass = continue; fail = closeout continues through remaining steps but final summary marks NOT HEALED and PLANS-INDEX status becomes `Tests failing — needs manual fix` rather than `Done`. `--skip-tests` flag bypasses with loud flag in summary §1. Never modifies failing tests — surfaces and stops on that file.
- **Files modified**: covered by Task 6.1 (closeout/SKILL.md §5)
- **Acceptance verified**: Test gate blocks "healed" status on failure (status diverges from Done). --skip-tests path is documented and surfaces in summary.

### Task 6.4: Implement scope archive integration
- **Status**: ✅ DONE (implemented in Task 6.1 — §12 Step 10 of closeout/SKILL.md)
- **Completed**: 2026-05-11
- **What was done**: Step 10 explicitly invokes /plan §12 (Plan Completion & Archive) — does NOT duplicate logic. Reuses §12.1 TODO extraction, §12.2 TO-DO.md append, §12.3 archive (child-plans-stay-in-scope rule preserved), §12.4 PLANS-INDEX update, §12.5 parent scope progress.md update, §12.7 completion summary, §12.8 sibling plan discovery. Skips §12.6 (the "/closeout prompt") since /closeout itself is what's running. Scope-level archive (all plans complete) additionally invokes /scope §7. Dry-run path logs intent without moving files.
- **Files modified**: covered by Task 6.1 (closeout/SKILL.md §12)
- **Acceptance verified**: Reuse, not re-implement, is explicit. Path through /plan §12 is documented step-by-step. Future /plan §12 changes propagate to /closeout automatically.

### Task 6.5: Memory write integration
- **Status**: ✅ DONE (implemented in Task 6.1 — §11 Step 9 of closeout/SKILL.md)
- **Completed**: 2026-05-11
- **What was done**: Step 9 scans §4 for cross-repo fold-into recommendations (memory type: `reference`) and §11 for recurring failure modes (memory type: `feedback`). Writes follow auto-memory conventions in CLAUDE.md (frontmatter with name/description/type, body with rule + Why + How-to-apply lines, MEMORY.md index updated). Auto-write, no prompt (per user preference). `--skip-memory` flag opts out. De-dup gap accepted per Issue 13B (observe in real use before engineering). Written entries listed in summary §1 with paths for user audit.
- **Files modified**: covered by Task 6.1 (closeout/SKILL.md §11)
- **Acceptance verified**: Fold-into-cross-repo entries produce a `reference` memory pointing at source repo + pattern. Recurring failure modes produce a `feedback` memory with rule/why/how-to-apply structure.

### Skill registration
- **Status**: ✅ DONE
- **Completed**: 2026-05-11
- **What was done**: Symlinked `~/.claude/skills/closeout -> ~/Projects/ai-skills/closeout` so the skill is registered with Claude Code. (Same pattern as cross-repo-init from Task 4.3.)
- **Files modified**: ~/.claude/skills/closeout (new symlink)

---

## Phase 4 — /closeout-extended skill

### Task 7.1: Build /closeout-extended skill — main flow
- **Status**: ✅ DONE
- **Completed**: 2026-05-11
- **What was done**: Wrote `closeout-extended/SKILL.md` (~430 lines) implementing the recursive cross-repo self-heal flow described in plan §7. Frontmatter: `name: closeout-extended`, `version: 1.0.0`, allowed-tools without AskUserQuestion. Sections: §1 How It Works (7-step diagram + worktree/never-commits/cycle-detection guarantees), §2 Flags (`--max-depth`, `--skip-tests`, `--dry-run`, `--cleanup-worktrees`, `--upward-only` / `--outward-only`), §3 Step 1 local /closeout invocation (captures structured summary, halts on local halt), §4 Step 2 CROSS-REPO.md read + drift validation per Issue 5A (missing Pattern Source paths excluded from traversal but surfaced as drift; missing Consumer references downgrade to advisory), §5 Step 3 traversal list build (BFS, default depth 2 with hard cap 4 to mitigate path-canonicalization cycle-escape edge cases), §6 Step 4 cycle detection (visited-set keyed by canonical path; first-visit-wins; bidirectional-edge warning), §7 Step 5 the core neighbor loop (split into §7.1 trunk-branch detection per `feedback_branch_off_develop.md`, §7.2 ephemeral worktree creation with dirty-tree numbered prompt default 2, §7.3 /closeout 11-step engine in worktree with doc-only test skip Issue 15B + Step 10 archive skipped for neighbors, §7.4 the 3D upward edit proposal with rich context loading mandatory and default-to-leaf-side fallback, §7.5 progress file append), §8 Step 6 aggregate cross-repo summary template (outward/upward/skipped/drift sections with worktree paths), §9 Step 7 final report + opt-in cleanup, §10 closeout-extended-progress.md resumability schema, §11 Failure modes & recovery (missing CROSS-REPO, missing paths, worktree-add failure, Ctrl-C, parallel-run collisions), §12 Important Behaviors (never commits/pushes, worktrees are user property, leaf-side default, doc-only test skip, numbered-inline only, paths conventions, /closeout reuse), §13 First-run recipe.
- **Files modified**: closeout-extended/SKILL.md (new), ~/.claude/skills/closeout-extended (new symlink)
- **Issues**: None
- **Acceptance verified**: Skill loaded into Claude Code (confirmed via system reminder showing /closeout-extended in skill list). Traversal default 2 with per-repo override + CLI override documented. Worktree-based isolation documented. Cycle detection mandatory. Doc-only neighbors skip tests.

### Task 7.2: Smart upward traversal (3D) — rich context + per-edit confirmation + leaf-side default
- **Status**: ✅ DONE (implemented in Task 7.1 — §7.4 of closeout-extended/SKILL.md)
- **Completed**: 2026-05-11
- **What was done**: §7.4 fully specifies the upward edit proposal: §7.4.1 mandatory rich context loading (trunk pattern file, tests by convention Go/JS/Python, callers via grep capped at 10 + "(K more)", trunk CLAUDE.md/ARCHITECTURE.md conventions); §7.4.2 default-to-leaf-side workaround on skip/no-response/ambiguous-input (consumer documents deviation in §3, trunk untouched); §7.4.3 per-edit not batched (individual judgment required); §7.4.4 confirmation-explicit-not-implicit (even option 1 writes to worktree only, never auto-commits). Proposal template renders with all 4 fields populated. Numbered options 1-4 with leaf-side as DEFAULT.
- **Files modified**: covered by Task 7.1 (closeout-extended/SKILL.md §7.4)
- **Acceptance verified**: Rich context loading is explicit and mandatory. Default-to-leaf-side documented. Per-edit (not batched) specified. AskUserQuestion banned, numbered inline only.

### Task 7.3: Worktree-based neighbor visits (4D) + cycle detection
- **Status**: ✅ DONE (implemented in Task 7.1 — §7.2 + §6 of closeout-extended/SKILL.md)
- **Completed**: 2026-05-11
- **What was done**: §7.2 specifies ephemeral worktree creation: path `/tmp/closeout-<slug>-<neighbor>/`; create fresh if missing, reuse if clean, prompt with numbered options (default 2: discard + re-create) if dirty. Trunk branch detection (§7.1) per CROSS-REPO `trunk-branch` field, falls back to develop then main. Cycle detection (§6) keyed by canonical absolute path (symlinks resolved), first-visit-wins, bidirectional edges surface as CROSS-REPO topology warning. Cleanup opt-in via `--cleanup-worktrees`. User's primary working tree on neighbor never touched.
- **Files modified**: covered by Task 7.1 (closeout-extended/SKILL.md §6 + §7.2)
- **Acceptance verified**: Worktree creation isolates from primary working tree. Cycle detection has explicit canonical-path resolution. Bidirectional-edge warning specified. Dirty-tree numbered prompt with leaf-side-style default. Cleanup is opt-in not automatic.

### Task 7.4: Resumable progress via closeout-extended-progress.md
- **Status**: ✅ DONE (implemented in Task 7.1 — §10 of closeout-extended/SKILL.md)
- **Completed**: 2026-05-11
- **What was done**: §10 specifies the closeout-extended-progress.md schema: sibling to closeout-prep.md in local scope folder. Sections: Visited (per-neighbor `[✓]` / `[skip]` / `[ ]` entries with depth + worktree path + timestamp), Upward proposals reviewed (per-proposal outcomes), CROSS-REPO drift findings. Append-as-you-go semantics. Re-run reads file, resumes from first `[ ]` entry, reuses existing worktrees if present or rebuilds fresh per §10.4. Footer gets Completed timestamp on full pass; file travels with scope to archive.
- **Files modified**: covered by Task 7.1 (closeout-extended/SKILL.md §10)
- **Acceptance verified**: Resumability via stable file path. Re-runs skip completed entries. Worktree reuse rules documented.

### Task 7.5: Test for upward traversal flow (AI+HUMAN_REVIEW)
- **Status**: ✅ DONE (awaiting Phase 4 checkpoint review)
- **Completed**: 2026-05-11
- **What was done**: Wrote `closeout-extended/tests/upward-traversal-recipe.md` with three manual verification recipes for Issue 14A: Recipe 1 (rich context proposal — verifies all 4 context fields rendered, unified diff format, numbered options, no AskUserQuestion in trace); Recipe 2 (default-to-leaf-side on skip — verifies no-response / Ctrl-C path falls through to leaf-side workaround, consumer §3 deviation recorded, trunk worktree empty); Recipe 3 (cycle detection on bidirectional CROSS-REPO — verifies no infinite loop, cycle log entry, topology warning surfaced). Each recipe self-contained with setup / action / pass criteria / failure modes. Exercised in Phase 5 §8.7 against pmg-integrations dogfood scope.
- **Files modified**: closeout-extended/tests/upward-traversal-recipe.md (new)
- **Issues**: None
- **Acceptance verified**: Three recipes present (rich context, default-to-leaf-side, cycle detection). Pass criteria explicit. AskUserQuestion ban included in verification.

---

## Phase 5 — Dogfood pass (partial)

### Task 8.2 (PMG side): Run /cross-repo-init on pmg-docs
- **Status**: ✅ DONE (PMG side only — kalpa-docs deferred to its own context per user request)
- **Completed**: 2026-05-11
- **What was done**: Executed the /cross-repo-init flow against `~/Projects/pmg/pmg-docs`. Detected: on `main` branch (unlike pmg-integrations which uses develop — pmg-docs is the exception in the PMG graph), no existing CROSS-REPO/ARCHITECTURE/CLAUDE. pmg-docs is a docs-only leaf: no source code, no runtime contracts, no Pattern Sources to inherit, no Consumers in the contract graph. Reverse Edges (informational): pmg-integrations + pmg-chatwoot reference this repo's `plans/` directory and infrastructure docs operationally — those edges are declared in THEIR CROSS-REPO.md files, not duplicated here. Wrote CROSS-REPO.md (42 lines), ARCHITECTURE.md (113 lines — 11 components, human+agent workflow diagram showing /scope+/plan+/closeout flow into plans/, 7 key decisions including central-plans-dir + ASCII-only-no-Mermaid + archive-append-only + ADR/postmortem conventions), CLAUDE.md (90 lines — docs-editing conventions: numbered headings, checkbox TODOs, ASCII diagrams, `docs:`/`plans:` commit prefix not `feature:`, plans dir layout, when-to-use-which-skill, ADR + postmortem conventions, memory pointers). Committed all three on main in single commit `19bd2f0 — docs: bootstrap CROSS-REPO + ARCHITECTURE + CLAUDE for closeout-skills`.
- **Files modified**: ~/Projects/pmg/pmg-docs/{CROSS-REPO.md,ARCHITECTURE.md,CLAUDE.md} (all new, committed to main)
- **Calibration finding**: pmg-docs uses `main` as trunk, not `develop` (exception within the PMG graph). Documented in its CROSS-REPO.md and CLAUDE.md so /plan and /closeout don't mis-derive branch. /closeout-extended's trunk-branch detection (cross-repo-init/templates default to develop then main fallback) will pick this up via the explicit `trunk-branch: main` field in CROSS-REPO.md.
- **Deferred**: kalpa-docs (Phase 5 §8.2 WellMed side). User chose to defer to its own context window — kalpa-docs is a public Kalpa-Health repo with separate trunk semantics worth focused attention.
- **Acceptance verified**: Three files committed on main. /cross-repo-init re-run would report HEALTHY (idempotency).

### Task 8.3 prep — Kalpa-Health org gap analysis
- **Status**: ✅ DONE
- **Completed**: 2026-05-11
- **What was done**: Per user instruction, surveyed `Kalpa-Health` GitHub org (gh CLI via ak-devmode account, then restored to ak-padma) and compared against `~/Projects/wellmed/` local clones. The plan §8.3-§8.4 sequence anticipated 6 wellmed leaves (backbone, cashier, consultation, fe, gateway-go, pharmacy) plus wellmed-infrastructure trunk. Reality is broader: 14 non-`.github` active repos in the org, 6 NOT cloned locally.
- **Gap (not cloned locally)**:
  - **wellmed-hq** — HQ management microservice (tenant/product/licensing). Pushed 2026-03-31.
  - **wellmed-hq-fe** — HQ dashboard frontend (Nuxt 4, multi-clinic ops). Pushed 2026-04-09.
  - **wellmed-supply-chain** — SCM microservice (Go). Pushed 2026-03-31.
  - **wellmed-catalog** — fresh repo, pushed 2026-05-04, sparse.
  - **wellmed-consultation-shared** — shared libs for consultation services (secondary trunk, not anticipated in plan). Pushed 2026-03-06.
  - **kalpa-company-profile** — KalpaHealth corporate website. Pushed 2026-04-09.
- **Remote anomalies**:
  - `wellmed-gateway-go` (local) tracks `ingarso/kalpa-gateway.git` — a personal fork. Canonical repo is `Kalpa-Health/wellmed-gateway-go`. Remote should likely be updated.
  - `satu-sehat-scraper` (local) has NO git remote — local-only artifact or pulled from a third-party.
- **Implication for Phase 5 §8.3/§8.4**: Original sequence (6 leaves) is incomplete. wellmed-consultation-shared is a *secondary trunk* for consultation-domain repos that should be onboarded BEFORE wellmed-consultation (its consumer). Plan §8.4 leaves list needs expansion. Defer the decision on which gap-repos to clone + onboard to the kalpa-docs session per user pacing.

### Task 8.2 (WellMed side): Run /cross-repo-init on kalpa-docs
- **Status**: ✅ DONE
- **Completed**: 2026-05-11
- **What was done**: Executed the /cross-repo-init flow against `~/Projects/wellmed/kalpa-docs`. Detected: on `main` (same as pmg-docs; unlike most wellmed-* code repos which use develop), no existing trio. kalpa-docs is a docs-only leaf: no source code, no runtime contracts, no Pattern Sources to inherit, no Consumers in the contract graph. Reverse Edges list 12 wellmed-* repos that reference kalpa-docs operationally (wellmed-catalog deliberately excluded — fresh+sparse, no references yet). Wrote CROSS-REPO.md (54 lines), CLAUDE.md (97 lines), and ARCHITECTURE.md (385 lines — much richer than pmg-docs's 113-line ARCH because Alex repositioned it mid-session as the **WellMed-system root entry point** for all Kalpa-Health code repos, not just an info-architecture rehash). ARCHITECTURE.md has 11 sections: Overview, Tech Stack, MS Inventory (14 services + variants with doc-gap markers), Three-Tier Taxonomy, Networking & Communication (with ASCII topology diagram), Product Releases (Lite/Plus/E/HQ), 13 Key Principles (including new #12 canonical-record encoder and #13 factory/warehouse data-access fabric), ADR Index, Document Map, Cross-Repo Position, and §11 "Current Code State vs Target Architecture" drift section.

  **Folded-in cleanup (in same commits):**
  1. **ADR-004 numbering collision resolved.** Two files had been numbered ADR-004 since 2026-04-08 (Tenant Isolation Jan 2025 + Secret Management Apr 2026). Renamed `ADR-004-secret-management-ssm.md` → `ADR-015-secret-management-ssm.md`; updated all 15 in-repo references (ARCHITECTURE.md Principle #10 + Tech Stack + ADR Index, plans/archive/36-ssm-secret-management/{PLAN,PROGRESS}, plans/pending/PLANS-INDEX.md, plans/pending/TO-DO.md (item marked done), development/new-service-ssm-checklist.md, operations/secret-rotation-runbook.md). ADR-004 retained for Tenant Isolation per existing citation pattern. Cross-repo follow-up: `wellmed-fe/docs/15-cicd-plan.md:78` references ADR-004 in SSM context, needs separate commit on wellmed-fe — captured in TO-DO.md §8.2.
  2. **ADR-014 added as Draft placeholder** for "Shared Data Access Fabric (Infrastructure Adapter Pattern)". 54-line stub references `wellmed-infrastructure/ADAPTER-EXTRACTION.md` on `develop` as the current canonical reference pending formalization.
  3. **ASCII-only-no-Mermaid policy declared repo-wide.** README §8 Diagrams section removed (pointed at phantom `diagrams/system-topology.mermaid` that never existed on disk); repo-governance.md mermaid text mentions cleaned (3 lines, both narrative and directory-tree examples); 16 existing mermaid fenced blocks across 4 active docs (saga-backlog, saga-pattern-extended-PRD, wellmed-cd-plan-v1, implementation-the-kalpa-way-PLAN) left for next-edit conversion per the CLAUDE.md rule (user picked Option Y: don't force-convert this session, let next edits do it naturally — option 3 "full sweep" recalibrated to a more honest scope after re-counting blocks).
  4. **Dup architecture file deleted.** `wellmed-system-architecture copy 2.md` was a 708-line v1.5 snapshot from 2026-04-10 left behind by a teammate (Indonesian commit message "plan adapter untuk semua microservice", author `= <=>` with broken git config — confirmed NOT Alex). Canonical `wellmed-system-architecture.md` is v2.0 dated 2026-04-15. Git history preserves v1.5.
  5. **Two byte-identical artifact dupes deleted** under `plans/pending/*/artifacts/` — both 832-line files (`implementation-the-kalpa-way-v0.1-original.md` and `implementation-the-kalpa-way-v0.1.md`) were bit-identical (`diff` returned 0 differences) to `implementation-the-kalpa-way-PLAN.md`. Not functioning as historical snapshots; deleting cut 14 redundant mermaid blocks out of the sweep scope.

- **Files modified**: ~/Projects/wellmed/kalpa-docs/{CROSS-REPO.md, ARCHITECTURE.md, CLAUDE.md, adrs/ADR-014-shared-data-access-fabric.md} (all new); adrs/ADR-004-secret-management-ssm.md → adrs/ADR-015-secret-management-ssm.md (rename + content); README.md, repo-governance.md, development/new-service-ssm-checklist.md, operations/secret-rotation-runbook.md, plans/archive/36-ssm-secret-management/{ssm-secret-management-PLAN.md,ssm-secret-management-PROGRESS.md}, plans/pending/PLANS-INDEX.md, plans/pending/TO-DO.md (modified); wellmed-system-architecture copy 2.md, plans/pending/implementation-the-kalpa-way/artifacts/implementation-the-kalpa-way-v0.1-original.md, plans/pending/kalpa-migration-service/artifacts/implementation-the-kalpa-way-v0.1.md (deleted). Two commits on main: 0950290 (main bootstrap + cleanup) and 330bd22 (continuation: ADR-015 in-file title rename that didn't get re-staged before the first commit).

- **Calibration findings added to ai-skills/plans/TO-DO.md §8.2 WellMed side:**
  1. **Branch-aware code surveying** — /cross-repo-init currently assumes the checked-out branch reflects code state. Real-world: many repos hold their actual current state on `develop` or feature branches (wellmed-infrastructure adapter framework is on `develop` + `feat/sdk-restructure-opsi3`, not `main`). When `origin/HEAD` points at `main` but `origin/develop` exists with divergence, the skill should scan both. Same applies to /closeout-extended worktree-base detection.
  2. **ARCHITECTURE.md template needs §N Drift section by default** — the §11 "Current Code State vs Target Architecture" pattern from kalpa-docs/ARCHITECTURE.md should become standard scaffolding. Retro-add to pmg-integrations and pmg-docs in small follow-up commits (separate work).
  3. **/cross-repo-init could audit ADR numbering for collisions** — ADR-004 collision was outstanding for ~5 weeks. Low-priority polish.
  4. **wellmed-fe ADR-004 cross-repo follow-up** — separate commit needed.

- **Deferred**: §8.3 (wellmed-infrastructure trunk on develop) — separate session per pacing decision. §8.4 leaves list correction (11 leaves not 6) will inform §8.3 scoping.

- **Acceptance verified**: Three trio files + ADR-014 stub committed on main. ADR-004 collision fully resolved (re-grep returns zero stale SSM refs in kalpa-docs). /cross-repo-init re-run on a healthy repo would now report HEALTHY (idempotency).

### Task 8.3 prep — local wellmed/ sync + gap-repo clone
- **Status**: ✅ DONE
- **Completed**: 2026-05-11
- **What was done**: Per user direction:
  1. **Removed `ingarso` remote from `wellmed-gateway-go`**. The local repo now tracks only `origin = Kalpa-Health/wellmed-gateway-go`. Previous setup had both remotes; the ingarso/kalpa-gateway fork was a stale relic. FF pull picked up 2 missing satusehat-related proto commits from the org canonical.
  2. **Fast-forward synced all existing local wellmed repos to their org defaults**. Zero local commits ahead anywhere → safe FF pulls. Repos updated: kalpa-docs (+7), wellmed-backbone (+54 ← largest sync, mostly proto regen), wellmed-cashier (+3 — dirty `.claude/logs/task-history.log` did not conflict), wellmed-consultation (+16 — includes proto deletions), wellmed-fe (+1 — pnpm-lock + sentry plugin), wellmed-gateway-go (+2). All thirteen local wellmed repos now ahead=0 behind=0.
  3. **Cloned 5 gap repos to `~/Projects/wellmed/`** (via `git@github-akdevmode:Kalpa-Health/` SSH alias): wellmed-hq, wellmed-hq-fe, wellmed-supply-chain, kalpa-company-profile, wellmed-catalog. All landed on `main`. User priorities (in their reply): #4 (wellmed-catalog) "really hoped to see"; #3 (kalpa-company-profile) "want to add anyway"; #2 batch (hq/hq-fe/supply-chain) standard adds.
  4. **wellmed-consultation-shared NOT cloned**. User confirmed retirement — work moved to `wellmed-infrastructure/adapters/`. Saved memory `project_wellmed_consultation_shared_retired.md` so future framework decisions don't re-propose it as a Pattern Source for wellmed-consultation or any other consultation-domain repo.
  5. **satu-sehat-scraper left alone** — local-only, no git remote, per user "local only no worries there".
- **Files modified**: ~/Projects/wellmed/{wellmed-gateway-go (remote pruned), wellmed-hq, wellmed-hq-fe, wellmed-supply-chain, kalpa-company-profile, wellmed-catalog (clones)}; existing repos FF-synced. Memory: `project_wellmed_consultation_shared_retired.md` (new) + MEMORY.md index update.
- **Plan §8.4 leaves list correction**: should now read 9 wellmed leaves (excluding the trunk wellmed-infrastructure and the docs leaf kalpa-docs): wellmed-backbone, wellmed-cashier, wellmed-consultation, wellmed-fe, wellmed-gateway-go, wellmed-pharmacy, wellmed-hq, wellmed-hq-fe, wellmed-supply-chain, plus kalpa-company-profile (marketing site, could be docs-leaf shape), plus wellmed-catalog (fresh, sparse). Original plan listed 6; reality is 11. Defer authoring the corrected §8.4 list to the kalpa-docs session.

### Task 8.1: Run /cross-repo-init on pmg-integrations (validation pass)
- **Status**: ✅ DONE
- **Completed**: 2026-05-11
- **What was done**: Manually executed the /cross-repo-init flow against `~/Projects/pmg/pmg-integrations` (skill installed but exercised inline so calibration findings could be captured live rather than after-the-fact). Detected repo state: on `develop` branch, no existing CROSS-REPO/ARCHITECTURE/CLAUDE. Pattern-source detection: zero imports from any other ~/Projects repo — pmg-integrations is a self-trunk, NOT the hub-consumer of wellmed-infrastructure that plan §8.1 had anticipated. Consumer detection: pmg-chatwoot (high-confidence — 7 doc/code references), pmg-docs (docs consumer, no code refs but operationally load-bearing). Four production dependents documented but not traversable: Grafana, pbmcgroup.com, padmacare.pbmcgroup.com, narawangsa webcam. Wrote CROSS-REPO.md (69 lines), ARCHITECTURE.md (178 lines — 15 components, happy-path data flow diagram with full ASCII trace through middleware → routes → integrations/<flow> → lib/<adapter> → bus/SNS → CloudWatch → Grafana, 8 key decisions lifted from project memory, 13 external integrations), CLAUDE.md (112 lines — agent-focused: build/test/lint, branch workflow, SSM-only secrets, idempotency rule, WhatsApp NAMED templates, Xendit pt/pm/pr invariant + pre-settlement refund gotcha, Sonnet 4.6 default, production deploy facts, pattern-reading guidance, plans dir pointer, memory pointers). Committed all three on develop in single commit `0befa30 — feature(docs): bootstrap CROSS-REPO + ARCHITECTURE + CLAUDE for closeout-skills`. Skill registration confirmed (cross-repo-init listed in active skills).
- **Files modified**: ~/Projects/pmg/pmg-integrations/{CROSS-REPO.md,ARCHITECTURE.md,CLAUDE.md} (all new, committed to develop)
- **Calibration findings (added to ai-skills/plans/TO-DO.md for v1.1)**:
  - **Pattern-grep candidate pool ≠ contract-traversal graph.** CROSS-REPO.md currently conflates two concerns. Cross-trunk contract traversal (PMG ↔ WellMed) should NOT happen — independent application graphs. But cross-trunk pattern-grep COULD — looking at wellmed-infrastructure for "what does a good Notion adapter look like" is valuable even without a code dependency. v1.1 schema proposal: split into `Pattern Sources (grep-only)` and `Pattern Sources (traversed)`, or add `grep-only: true` flag per entry. User quote captured verbatim in TO-DO.
  - **Never-auto-generate-diagrams rule is too strict** for hub repos where happy path is unambiguous. /cross-repo-init §7.4 should propose-and-confirm rather than placeholder-and-defer. Surfaced when user asked "not sure what that is and why I need to do it manually" — fair pushback.
  - **Stale CROSS-REPO.md.examples.md fixed.** The original modeled pmg-integrations as consuming wellmed-infrastructure. Rewrote with three archetypes (self-trunk hub, trunk-with-consumers, leaf) and made explicit that pmg/wellmed are separate trunks.
- **Memory written**: `~/.claude/projects/-Users-alexknecht-Projects-pmg/memory/project_pmg_wellmed_trunks.md` documents the independent-trunks rule so future framework work doesn't re-propose the same stale coupling. Index updated.
- **Files modified (ai-skills, uncommitted)**: cross-repo-init/templates/CROSS-REPO.md.examples.md (rewrite), plans/TO-DO.md (new — v1.1 deferred items + this scope's TODOs).
- **Issues**: None
- **Acceptance verified**: Both files committed on develop. /cross-repo-init re-run on a healthy repo would now report HEALTHY (idempotency). Calibration findings captured for v1.1.
- **What was done**: Created `plan/tests/verification-recipes.md` with three scripted manual verification recipes: Recipe 1 (Ledger restart semantics, Issue 11) — kill /plan mid-phase, resume, verify two timestamped phase blocks; Recipe 2 (Session-scoped pattern approval, Issue 12) — three same-shape novel methods, verify exactly 1 halt-and-ask fires and subsequent are auto-applied with audit note; Recipe 3 (CROSS-REPO.md path validation halt, Issue 17) — deliberately break a Pattern Source path, verify Phase 0 halts cleanly with re-init suggestion. Each recipe is self-contained (setup / action / expected / pass criteria / failure modes). Recipes will be exercised in Phase 5 §8.5 against pmg-integrations.
- **Files modified**: plan/tests/verification-recipes.md (new)
- **Issues**: None
- **Acceptance verified**: Three recipes present, each maps to its issue number, each has explicit pass criteria. Per AI+HUMAN_REVIEW type, paused for user review before Phase 3.

### Task 8.3: Run /cross-repo-init on wellmed-infrastructure (Pattern Source trunk)
- **Status**: ✅ DONE
- **Completed**: 2026-05-11
- **What was done**: Executed /cross-repo-init flow against `~/Projects/wellmed/wellmed-infrastructure` on `develop` (per user direction "focus on develop across repo"). Repo state probe confirmed the §8.2 calibration prediction in spades: local on `main`, `origin/HEAD → main`, but `origin/develop` is +10 commits ahead with ~19,053 lines of code absent from main. The §2.2 branch-survey cascade (baked into /cross-repo-init pre-§8.3) routed correctly: trunk-branch field unknown → check origin/develop ≥5 commits ahead → YES → survey on develop. All three feature branches (`feat/sdk-restructure-opsi3`, `feature/shared-go-sdk`, `feat/pharmacy-ssm-parameters`) detected via the feature-branch heuristic but confirmed fully merged into develop (right-side count = 0 for all three) — surfaced as "merged, safe to delete" not "active drift". Wrote:
  - **CROSS-REPO.md** (100 lines, trunk archetype): empty Pattern Sources (this IS the trunk); 10 consumers in dependency-density order (wellmed-backbone heaviest with 30+ adapters, then consultation/cashier/pharmacy/gateway-go/hq/supply-chain Go services, fe/hq-fe consuming only SSM manifests, catalog sparse); kalpa-docs as documentation consumer; 4 external dependents (AWS SSM/IAM/CloudWatch + GitHub org for bootstrap-repo.sh) listed as non-traversable. trunk-branch field set to develop explicitly. wellmed-consultation-shared listed in Retired section per `project_wellmed_consultation_shared_retired.md`.
  - **ARCHITECTURE.md** (268 lines, load-bearing §6 Drift): 7 sections following the template (Overview / Components / Data Flow / Key Decisions / External Integrations / **§6 Drift** / Cross-Repo Position). §6 is the heaviest section in any ARCH.md I've written so far because main-vs-develop drift IS the story for this repo (main = IAM-only origin shape; develop = canonical SDK + adapter library + installpb + migration/seeder tools). §3 Data Flow has three ASCII diagrams: tenant provisioning fan-out via InstallService, request path through go-sdk middleware + adapter pattern, and the service-side ResolveDB + ULID + delegate-to-infra-repo idiom. §4 has 8 Key Decisions including the two-modules-in-one-repo decision, the "adapters are dumb GORM repos" rule, the InstallService canonical-bootstrap contract, and the develop-is-trunk reversal.
  - **CLAUDE.md** (206 lines at repo root, supersedes stale `.claude/CLAUDE.md`): agent context calling out the trunk-branch reversal up front, Go 1.26 build/test/lint for both modules, the load-bearing adapter pattern with concrete code example, SSM secret rules + decryption gotcha pointer, pattern-grep target areas (which go-sdk packages / which go/adapter shapes to reference), bootstrap-repo.sh runbook, gotchas (.bak files from Phase 2 extraction, lowercase kalpa-health import path, conventional commit prefix differences from PMG), cross-repo position, plans+memory pointers.
- **Files modified**: ~/Projects/wellmed/wellmed-infrastructure/{CROSS-REPO.md, ARCHITECTURE.md, CLAUDE.md} (all new, committed to develop in single commit `cd2acac — docs: bootstrap CROSS-REPO + ARCHITECTURE + CLAUDE for closeout-skills`).
- **Calibration findings (new — add to ai-skills/plans/TO-DO.md)**:
  1. **Branch-survey cascade worked on first contact.** This was the dogfood the §2.2 logic was written for, and it ran clean — no manual override needed. Strong signal the §2.2 cascade is correctly shaped. Mark item 1 in TO-DO §8.2 WellMed side as fully verified.
  2. **Stale `.claude/CLAUDE.md` collision.** Repo had an existing `.claude/CLAUDE.md` (2026-03 era, IAM-only scope) that contradicted what the new repo-root CLAUDE.md would say. /cross-repo-init currently neither detects this nor proposes reconciliation — it silently creates the root file. v1.1 polish: scan for `.claude/CLAUDE.md` during Step 2 ARCH/CLAUDE handling; if present and contradicts proposed root content, surface as drift with numbered reconciliation options (delete .claude/ copy / keep both with explicit scope split / merge into root).
  3. **`.bak` files in `go/adapter/*/repository/`** — leftovers from Phase 2 extraction (2026-04-21), tracked in CLAUDE.md §8.3 as cleanup candidates. Not a /cross-repo-init concern but worth flagging for the eventual /closeout dogfood pass.
  4. **Feature-branch heuristic surfacing was useful but verbose.** All three matched-name branches turned out to be fully merged. The cascade should still surface them (transparency > silence), but could note "merged into develop, safe to delete" inline rather than treating them as live drift. Minor polish, not blocking.
- **Pre-existing skill updates that paid for themselves**: §2.2 branch-survey cascade (correctly routed survey to develop), §7.4a explicit single-branch ban (prevented the main-vs-develop blunder from §8.2 recurring), ARCHITECTURE.md.template §6 Drift section (§7.4b mandatory — this dogfood is the canonical example of why the section is needed).
- **Issues**: None. Push to origin pending user confirmation.
- **Acceptance verified**: All three files committed on develop in single commit (cd2acac). Files validate as well-formed (line counts 100/268/206). /cross-repo-init re-run against this repo would now report HEALTHY. trunk-branch explicitly declared as develop in CROSS-REPO.md so /closeout-extended's trunk-branch detection cascade lands on the right base.
