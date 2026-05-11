# Plan 1: Closeout Skills + Cross-Repo Self-Healing

**Version:** 0.3
**Date:** 11 May 2026
**Author:** Alex
**ADR:** N/A (design captured in this plan)
**Status:** Ready to execute
**Branch:** feature/closeout-skills
**Plan #:** 1

### Key Changes v0.2 → v0.3
- Renamed `close-out-prep.md` → `closeout-prep.md` (no hyphen, matches /closeout skill name)
- Renamed `close-out-extended-progress.md` → `closeout-extended-progress.md` (same rationale)
- Moved template from `ai-skills/plan/templates/` to `ai-skills/templates/` — shared across /plan, /closeout, /closeout-extended; not bundled with any single skill
- Decision made mid-execution during Task 6.1; references updated across plan, closeout SKILL.md, plan SKILL.md, and verification-recipes.md

### Key Changes v0.1 → v0.2
- Incorporated /plan-eng-review findings: 17 issue decisions + 3 scope reductions
- Phase 4 rewritten: upward traversal uses per-edit user confirmation with rich context (3D); neighbor visits use ephemeral git worktrees on trunk (4D)
- Phase 5 rewritten: full Projects bootstrap checklist (14 repos), sequenced pmg-integrations → docs → wellmed-infrastructure → leaves
- §4.4 (/scope auto-suggest /cross-repo-init) deferred to v1.1
- §5.6 folded into §5.5
- Added schema version field to closeout-prep.md
- Added concrete worked examples in Phase 1 templates
- Added test tasks: ledger restart, refactor-mode approval, upward traversal

## Related Docs

- `markdown-style/SKILL.md` — base style guide (§8 Plan, §10 Progress, §11 Scope formats updated as prep for this plan)
- `plan/SKILL.md` — task-runner (this plan adds: pattern-first grep, halt-and-ask, ledger writes, ARCH+CROSS-REPO load at start)
- `scope/SKILL.md` — orchestrator (§8.2 already updated to invoke /closeout-extended as prep)
- (to be created by Phase 1) — `CROSS-REPO.md` schema and per-repo files
- (to be created by Phase 1) — `ARCHITECTURE.md` stub template

---

## 1. Architecture Overview

```
                 ┌──────────────────────────────────────────┐
                 │   /plan execution                        │
                 │   (appends ledger as it works)           │
                 └────────────┬─────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────────────────┐
                │   closeout-prep.md (ledger)         │
                │   §1 Summary       §2 Files          │
                │   §3 Patterns Followed (w/ deltas)   │
                │   §4 Patterns Created (alts + rec)   │
                │   §5 Cross-repo Touchpoints          │
                │   §6 Docs Read     §7 Docs Affected  │
                │   §8 Assumptions   §9 Deferred       │
                │   §10 Coverage Map §11 Risk Flags    │
                └────────────┬─────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
    ┌──────────────────┐         ┌──────────────────────┐
    │   /closeout      │         │  /closeout-extended  │
    │   local repo     │         │  recursive walk      │
    │   self-heal      │         │  via CROSS-REPO.md   │
    │                  │         │  (max depth 2,       │
    │                  │         │   cycle detection,   │
    │                  │         │   dirty-tree skip)   │
    └────────┬─────────┘         └──────────┬───────────┘
             │                              │
             ▼                              ▼
       ┌──────────────────────────────────────────┐
       │   Healed working trees                   │
       │   (local repo, or local + neighbors)     │
       │   User reviews diffs and commits         │
       └──────────────────────────────────────────┘

CROSS-REPO.md per repo:
  ## Pattern Sources (look HERE before writing methods)
    - kalpa-infrastructure (adapters/*, lib/*)
  ## Consumers (these depend on our contracts)
    - pmg/chatwoot, padmacare-wp, ...
```

## 2. Design Summary

This plan adds three skills and rules to two existing skills to enable repo-level self-healing — keeping documentation, tests, and patterns aligned with code via every pass through /plan.

**New skills:**
- `/cross-repo-init` — bootstrap CROSS-REPO.md + ARCHITECTURE.md for a repo. Idempotent.
- `/closeout` — local repo self-heal. Reads closeout-prep.md ledger, audits patterns, fixes doc drift, runs tests, archives scope.
- `/closeout-extended` — recursive self-heal across CROSS-REPO.md neighbors (max depth 2, cycle detection, dirty-tree skip).

**Rule additions to /plan:**
- Read ARCHITECTURE.md + CROSS-REPO.md + CLAUDE.md at session start; halt if any are missing and suggest /cross-repo-init
- Pattern-first grep before writing any new method (search local repo + Pattern Sources from CROSS-REPO.md)
- Halt-and-ask before creating a new pattern (§4 ledger entry); user must approve or point to a reference
- Append to closeout-prep.md throughout execution (running ledger, timestamped phase blocks)

**Prep already done (this conversation, before plan execution):**
- /markdown-style §8 expanded; §10 (Progress Files) and §11 (Scope Documents) added; version 1.0.0
- /plan trimmed §3, §4 to brief schemas with pointers to /markdown-style; §11.6 prompts /closeout; ai-skills plans dir added; version 3.1.0
- /scope §1/§2 rewritten to open-ended numbered inline questions (no AskUserQuestion); §0 conditional on detected project; §5.4/§5.5/§5.9 trimmed with pointers; §8.2 invokes /closeout-extended; version 3.1.0
- AskUserQuestion removed from allowed-tools in all three skill files
- Status taxonomy reconciled (documents vs PLANS-INDEX rows)
- `~/Projects/ai-skills/plans/PLANS-INDEX.md` created

## 3. NOT in Scope

- Multi-repo PR creation (closeout-extended only edits working trees; commits/pushes stay manual)
- Numeric drift score / repo health score (explicit decision — invites Goodharting)
- Auto-fixing failing tests (flagged, never modified)
- Fast-path /scope for atomic tasks (deferred to separate work)
- Versioned skill pinning between /plan and /scope (deferred — overkill for one-person workflow)
- AGENTS.md files (left as-is, out of scope per user direction)
- Cross-repo PR opening (recommendations.md style avoided in favor of working-tree edits user reviews manually)

---

## 4. Phase 1 — /cross-repo-init + CROSS-REPO.md schema + ARCHITECTURE.md stub

Goal: bootstrap the per-repo metadata that /plan and /closeout-extended depend on. After Phase 1, any repo can be onboarded to the framework with a single skill invocation.

### 4.1 Define CROSS-REPO.md schema with concrete worked examples

- **Type**: AI
- **Input**: design decisions from this plan's §1 diagram; reference: existing repos in `~/Projects/` for the worked examples
- **Action**: Write the canonical CROSS-REPO.md schema document. Sections: Pattern Sources (with sub-paths and one-line descriptions), Consumers (with which contracts they depend on), Max Depth Override (optional, defaults to 2). Include **two filled-in worked examples**: (a) pmg-integrations as a hub (Pattern Sources: wellmed-infrastructure adapters; Consumers: pmg-chatwoot, padmacare-wp); (b) wellmed-infrastructure as a trunk (Pattern Sources: none; Consumers: wellmed-backbone, wellmed-cashier, wellmed-consultation, etc.). Cycle detection by repo path is enforced by skills, not declared in the file.
- **Output**: `ai-skills/cross-repo-init/templates/CROSS-REPO.md.template` plus inline examples in the skill file
- **Acceptance**: Template renders to a valid CROSS-REPO.md when populated. Worked examples are filled-in, not placeholders.

### 4.2 Define ARCHITECTURE.md stub template with concrete example

- **Type**: AI
- **Input**: read 1-2 existing examples from PMG/WellMed repos if available
- **Action**: Write a minimal ARCHITECTURE.md stub with required sections — Components (one-line per service), Data Flow (ASCII diagram placeholder), Key Decisions, External Integrations. Include **one filled-in worked example** (e.g., pmg-integrations or wellmed-backbone) so the template isn't aspirational. Optimized for agent consumption: short, scannable, refresh-friendly.
- **Output**: `ai-skills/cross-repo-init/templates/ARCHITECTURE.md.template`
- **Acceptance**: Template is short (under 80 lines), uses /markdown-style numbering, has comment placeholders so /cross-repo-init can fill what it can detect. One concrete worked example is present.

### 4.3 Build /cross-repo-init skill

- **Type**: AI
- **Input**: §4.1 and §4.2 templates; `ai-skills/scope/SKILL.md` and `ai-skills/plan/SKILL.md` as structural references
- **Action**: Create `ai-skills/cross-repo-init/SKILL.md`. Skill flow: (1) detect current repo from git remote, (2) check for existing CROSS-REPO.md — if present, audit for drift; if absent, scaffold from template, (3) check for existing ARCHITECTURE.md — same drift-vs-scaffold logic, (4) propose contents to user for review using open-ended numbered inline questions (NO AskUserQuestion), (5) write approved files. Skill is idempotent — re-running on a healthy repo produces no diff.
- **Output**: `ai-skills/cross-repo-init/SKILL.md`, frontmatter with `version: 1.0.0`, `name: cross-repo-init`, description matching trigger patterns ("cross-repo init", "bootstrap cross-repo", "add CROSS-REPO.md"). No AskUserQuestion in allowed-tools.
- **Acceptance**: Skill runs end-to-end on pmg-integrations (first dogfood subject from Phase 5). Idempotent re-run produces no changes when state is healthy.

### 4.4 [DEFERRED to v1.1] Update /scope to recognize ARCHITECTURE.md and CROSS-REPO.md as required reads

- **Status**: deferred per /plan-eng-review R1 — polish, not foundation
- **Note**: This task was originally proposed to nudge /scope to suggest /cross-repo-init when files are missing. Deferred because the skills work fine without this; the nag is noise for repos that haven't been onboarded yet. Re-evaluate after Phase 5 completes and we know whether the gap actually bites in practice.

---
### 🔲 CHECKPOINT: Phase 1 Complete
**Review**: Inspect `ai-skills/cross-repo-init/SKILL.md` and the two template files. Dry-run /cross-repo-init on a sample repo (e.g., pmg-integrations) to confirm scaffold quality before phase 2.
**Resume**: "continue the closeout-skills plan"
---

## 5. Phase 2 — closeout-prep.md schema + /plan rule additions

Goal: turn /plan from a write-then-forget executor into a write-and-record executor. After Phase 2, every /plan run produces a queryable ledger of what it did, why, and where it diverged.

### 5.1 Define closeout-prep.md schema with version field and worked examples

- **Type**: AI
- **Input**: design from this plan §1 diagram and §2 design summary
- **Action**: Write the canonical closeout-prep.md template covering all 11 sections (§1 Execution Summary through §11 Risk Flags). **Include `**Schema version: 1.0**` field in the header so /closeout can detect skew and error clearly on mismatch.** Use timestamped phase block format `## Phase {P}: {name} (started {ISO timestamp})` so resumed plans append without overwriting. Document the sub-field schemas: §3 entries (method-name ← file:line, optional deviation), §4 entries (method-name + location + alternatives-considered + recommendation), §5 entries (contract change → consumer list), §10 entries (business node → test refs).
- **Output**: `ai-skills/plan/templates/closeout-prep.md.template`
- **Acceptance**: Template includes 1-2 worked examples per section so /plan has concrete patterns to follow. Schema version field is present and parseable. Total template under 250 lines.

### 5.2 Add /plan rule: read ARCH+CROSS-REPO+CLAUDE.md at session start

- **Type**: AI
- **Input**: current `ai-skills/plan/SKILL.md` §5 (Phase 0 Pre-flight)
- **Action**: Extend Phase 0 to (1) read CLAUDE.md from the current repo, (2) read ARCHITECTURE.md if present, (3) read CROSS-REPO.md if present, (4) halt and suggest /cross-repo-init if either of ARCHITECTURE.md or CROSS-REPO.md is missing in a repo that's been bootstrapped before, (5) build an in-session map of Pattern Sources from CROSS-REPO.md for §5.3 to use, (6) **validate that each Pattern Source path in CROSS-REPO.md actually exists on disk** — if not, halt and suggest re-running /cross-repo-init to refresh.
- **Output**: edit to `plan/SKILL.md` §5
- **Acceptance**: Phase 0 logs ARCH+CROSS-REPO state. Missing files halt clearly. Missing Pattern Source paths halt clearly (Issue 17 — addresses the critical-gap failure mode where stale CROSS-REPO.md causes spurious halt-and-asks).

### 5.3 Add /plan rule: pattern-first grep before writing new methods

- **Type**: AI
- **Input**: §5.2 in-session Pattern Sources map
- **Action**: Add a new section to `plan/SKILL.md` between current §6 (Execution Rules) and §7 (Important Behaviors): "Pattern-First Rule". Before writing any new method in a known-extensible area (webhook handler, event publisher, FHIR resource, SSM lookup, Notion property write, Zoho function), /plan must (a) grep local repo for prior examples, (b) grep declared Pattern Sources from CROSS-REPO.md, (c) record any found references in closeout-prep.md §3, (d) if no match found, trigger the halt-and-ask flow (§5.4). **Cache scope: per-session, in-memory only. No persistence to ledger.** Resumed sessions re-grep cold — the cost is small and avoids stale-cache failure modes.
- **Output**: edit to `plan/SKILL.md` adding new section
- **Acceptance**: A test run of /plan against a small task with a known existing pattern surfaces the reference and records it in §3 of closeout-prep.md. Cache is not written to disk anywhere.

### 5.4 Add /plan rule: halt-and-ask before creating new patterns, with session-scoped approval and structured §4 prompt

- **Type**: AI
- **Input**: §5.3 pattern search results
- **Action**: When §5.3 grep finds no matching pattern for a method about to be written, /plan must pause and present the user with: method name + location, closest match found (with file:line and delta), and options — (a) extend the closest match in its source repo, (b) write parallel impl here and log to §4, (c) point to a different reference, (d) describe an alternative. User answers by number. **Two extensions:**
  - **Session-scoped pattern approval**: when the user approves a new pattern (option b or d), /plan offers "apply this approved pattern to any matching novel methods later in this session?" If yes, future novel methods that match the same shape get auto-applied with a §3 note "(applied via session-scoped approval from <method>)" — no further halt. Avoids fatigue on refactors.
  - **Structured §4 prompt template** (mandatory format for the §4 entry written to ledger):
    ```
    - {method-name}  {file:line}
      alternatives-considered:
        - {pattern-source-A}: {file:line} — {reason rejected}
        - {pattern-source-B}: {file:line} — {reason rejected}
        - (none found in: local repo, <pattern sources searched>) — if truly novel
      recommendation: extend <source> / accept as new / fold into <doc>
    ```
    /plan must produce at least the "alternatives-considered" field even when truly novel (lists places searched). Entries lacking alternatives-considered are rejected as malformed.
- **Output**: edits to `plan/SKILL.md` "Pattern-First Rule" section
- **Acceptance**: Halt-and-ask prompts include closest match + delta + numbered options. Session-scoped approval works (test in 5.7). §4 entries always have populated alternatives-considered field.

### 5.5 Add /plan rule: append-to-ledger throughout execution + closeout-prep.md location

- **Type**: AI
- **Input**: `ai-skills/plan/SKILL.md`, closeout-prep.md schema from §5.1
- **Action**: Document append points throughout /plan execution. After each task with new methods → §3/§4 entries. When touching a contract → §5 entry. When loading a doc for context → §6 entry. When making a guess without verifying → §8 entry. When skipping/deferring → §9 entry. When uncertain → §11 entry. Phase boundaries get timestamped headers so resumed phases append cleanly. **Document closeout-prep.md location: lives at `{scope-folder}/closeout-prep.md` (child of /scope) or `{plan-folder}/closeout-prep.md` (standalone). /plan creates it on first ledger write.** (Formerly §5.6, folded in here per R2.)
- **Output**: edit to `plan/SKILL.md` integrating append points into existing task execution flow
- **Acceptance**: A test run produces a closeout-prep.md with at least one entry in each applicable section. Resumed/restarted phases produce a second timestamped block, not an overwrite. File location is unambiguous.

### 5.6 [MOVED TO §5.5] — closeout-prep.md location

Folded into §5.5 per R2 / Issue 10A.

### 5.7 Tests for /plan rule additions

- **Type**: AI+HUMAN_REVIEW
- **Input**: §5.2–§5.5 implementation
- **Action**: Add three explicit tests to /plan's test surface:
  1. **Ledger restart semantics**: kill /plan mid-phase, resume, verify closeout-prep.md has a second timestamped phase block, not an overwrite (Issue 11).
  2. **Session-scoped pattern approval**: simulate 3+ novel methods of the same shape; verify first triggers halt-and-ask, subsequent are auto-applied with §3 session-scoped note (Issue 12).
  3. **CROSS-REPO.md path validation halt**: deliberately break a Pattern Source path; verify /plan Phase 0 halts with re-init suggestion (Issue 17).
- **Output**: test cases in ai-skills test surface (location TBD per ai-skills test conventions)
- **Acceptance**: All three tests pass on a clean dogfood scope.

---
### 🔲 CHECKPOINT: Phase 2 Complete
**Review**: Inspect `plan/SKILL.md` for the new sections. Dry-run /plan on a small test plan (could be a placeholder file) to confirm the pre-flight halt and ledger appends. Verify the ledger structure matches §5.1 template.
**Resume**: "continue the closeout-skills plan"
---

## 6. Phase 3 — /closeout skill (local self-heal)

Goal: ship the local-scope self-healing skill that consumes closeout-prep.md and leaves the repo healthier than /plan found it.

### 6.1 Build /closeout skill — main flow

- **Type**: AI
- **Input**: closeout-prep.md schema (§5.1), `ai-skills/plan/SKILL.md` §11 (archive sequence) as structural reference
- **Action**: Create `ai-skills/closeout/SKILL.md`. Implement the 11-step flow: (1) read closeout-prep.md and **verify schema version matches** (or degrade gracefully if absent), (2) verify scope branch, (3) run local test suite (with `--skip-tests` flag), (4) §3 spot-check (do referenced patterns still exist at file:line?), (5) §4 triage (apply recommendations as proposed edits in working tree), (6) §7 doc drift edits, ranked by agent-load-bearing weight (CLAUDE.md > README > ARCHITECTURE > docs/*), (7) ARCHITECTURE.md drift validation + edits, (8) §10 coverage report (no auto-fix), (9) memory writes for cross-cutting findings (auto-write, no prompt — accept de-dup gap per Issue 13B), (10) **invoke /plan §11 archive logic** (do NOT duplicate; reuse the same code path: extract TODOs → archive scope folder → update PLANS-INDEX → update parent scope progress.md), (11) summary with what changed + what's blocked. Skill must not use AskUserQuestion — open-ended numbered inline questions only.
- **Output**: `ai-skills/closeout/SKILL.md`, frontmatter with `name: closeout`, `version: 1.0.0`. No AskUserQuestion in allowed-tools.
- **Acceptance**: Skill runs end-to-end on a sample scope with a populated closeout-prep.md. Output summary lists every edit by file. Failing tests block "healed" status unless `--skip-tests` was passed. Archive logic is invoked via the same code path as /plan §11, not re-implemented.

### 6.2 Implement two-pass drift detection (grep all + LLM-review top-tier only)

- **Type**: AI
- **Input**: list of docs in §7 from closeout-prep.md + ARCHITECTURE.md per Issue 9A
- **Action**: Two-pass drift detection:
  - **Pass 1 (deterministic, all docs)**: grep every doc in §7 for stale symbol references — function names, file paths, env var names, flag names — that no longer exist in code. Surface candidates as drift-flag-list.
  - **Pass 2 (LLM-review, top-tier only)**: re-read CLAUDE.md + ARCHITECTURE.md cold and judge narrative drift (outdated explanations, missing new fields, wrong example output). Other docs only get Pass 1 — narrative-drift review in lower-tier docs is too expensive vs. value.
  - Combine: apply edits to working tree, ranked CLAUDE > README > ARCH > docs/*.
- **Output**: drift-detection logic in `closeout/SKILL.md` step 6 + step 7
- **Acceptance**: (a) Deliberately-stale symbol reference in any doc is caught by Pass 1. (b) Deliberately-misleading narrative in CLAUDE.md or ARCHITECTURE.md is caught by Pass 2. (c) Other docs are NOT LLM-reviewed (verify by checking the log).

### 6.3 Implement test execution + gating

- **Type**: AI
- **Input**: current repo's test command (detected from package.json, go.mod, etc.)
- **Action**: /closeout step 3 detects the test command and runs it. Pass = continue. Fail = block "healed" status, surface failures in summary. `--skip-tests` flag bypasses the gate but flags the gap loudly. Skill does not modify failing tests.
- **Output**: test execution logic in `closeout/SKILL.md` step 3
- **Acceptance**: Test gate blocks completion on failure. `--skip-tests` flag works and is reflected in the summary.

### 6.4 Implement scope archive integration

- **Type**: AI
- **Input**: /plan §11 (archive sequence) and /scope §7 (archive)
- **Action**: /closeout step 10 archives the scope folder using the same conventions as /plan §11 (move to archive/, update PLANS-INDEX status to Done). For standalone plans (no scope), archive the plan folder directly. Update parent scope's progress.md if applicable.
- **Output**: archive logic in `closeout/SKILL.md` step 10
- **Acceptance**: After /closeout runs, the scope folder is in `{plans_dir}/archive/`, PLANS-INDEX status is `Done ({date})`, and parent scope progress.md (if any) reflects the closure.

### 6.5 Memory write integration

- **Type**: AI
- **Input**: §3, §4, §11 from closeout-prep.md
- **Action**: /closeout step 9 reviews findings for cross-session relevance. If a §4 entry was accepted as "legitimately new pattern, fold into kalpa-infrastructure," write a memory entry. If a §11 risk flag was confirmed as a recurring failure mode, write a memory entry. Auto-write (per user preference), no prompt.
- **Output**: memory write logic in `closeout/SKILL.md` step 9
- **Acceptance**: A sample run with a §4 "fold into pattern source" recommendation produces a memory entry pointing at the source repo and pattern.

---
### 🔲 CHECKPOINT: Phase 3 Complete
**Review**: Run /closeout on a sample populated closeout-prep.md in a test scope. Verify all 11 steps execute, doc edits appear in working tree, scope is archived, summary is accurate. Inspect a memory entry written during the test.
**Resume**: "continue the closeout-skills plan"
---

## 7. Phase 4 — /closeout-extended skill (recursive self-heal)

Goal: extend self-healing across the repo graph defined by CROSS-REPO.md.

### 7.1 Build /closeout-extended skill — main flow

- **Type**: AI
- **Input**: `ai-skills/closeout/SKILL.md` from Phase 3 as the per-repo engine
- **Action**: Create `ai-skills/closeout-extended/SKILL.md`. Flow: (1) run /closeout's 11 steps locally, (2) read CROSS-REPO.md, **validate it against current state — flag any declared Pattern Source paths that no longer exist on disk, flag any Consumers that no longer reference contracts they claim to consume (Issue 5A)**, (3) build traversal list (Pattern Sources upward, Consumers outward), (4) apply max-depth=2 default with per-repo override support, (5) for each neighbor repo: use worktree-based visit (§7.3) to operate on neighbor's trunk; apply /closeout's 11 steps in that worktree's context; **skip test execution for neighbors that only received doc-only edits (Issue 15B)**, (6) aggregate cross-repo summary listing edits per repo and worktree paths for user review, (7) write resume-friendly `closeout-extended-progress.md` sibling for graceful resume.
- **Output**: `ai-skills/closeout-extended/SKILL.md`, frontmatter with `name: closeout-extended`, `version: 1.0.0`. No AskUserQuestion in allowed-tools.
- **Acceptance**: Skill walks CROSS-REPO.md, applies per-repo healing in worktrees, produces aggregated summary with per-repo worktree paths. CROSS-REPO drift detected and reported. Doc-only neighbors skip tests.

### 7.2 Implement smart upward traversal (3D) — rich context + per-edit confirmation + leaf-side default

- **Type**: AI
- **Input**: §1 architecture; upward = leaf → Pattern Source direction (inverts natural inheritance and requires extra care)
- **Action**: Encode 3D upward semantics. **Outward traversal (to Consumers)** is mechanical: §5 contract changes → update consumer code calls if needed; consumer docs/READMEs refreshed to reflect new contract. Apply edits in worktree.

  **Upward traversal (to Pattern Sources)** requires user confirmation per edit:
  1. **Rich context loading first**: when considering an upward edit (typically from a §4 entry with "fold into <source>" recommendation, or a §3 deviation that hints at extending the source), /closeout-extended reads the trunk pattern's full context — the pattern file, its tests (to understand invariants), its other callers (to know what extending the signature would break), the trunk's CLAUDE.md / ARCHITECTURE.md (to respect conventions).
  2. **Structured proposal** shown to user inline (numbered options, NOT AskUserQuestion):
     ```
     UPWARD EDIT PROPOSAL — neighbor: <pattern-source-repo>
     Source: <consumer-repo> §3 / §4 entry triggering this
     Trigger: <one-line summary of why this is proposed>
     Trunk pattern: <repo>/<file>:<line>
     Trunk pattern callers (audit): N other consumers, behavior summary
     Trunk pattern tests: <test-file> — N tests covering current behavior
     Proposed trunk diff:
       <unified diff showing the proposed extension>
     Alternative — leaf-side workaround (no trunk edit):
       <description of what the consumer would do locally instead>
     Choose:
       1. apply trunk extension + add tests
       2. leaf-side workaround (default if unsure)
       3. defer — write TODO in trunk's TO-DO.md
       4. describe alternative
     ```
  3. **Default direction is leaf-side workaround**, not trunk edit. If the user skips, doesn't respond, or picks 2, the consumer documents the deviation in its §3 ledger entry and the trunk stays untouched. Future runs may surface the pattern again — the user can fold up at a moment of their choosing.
  4. **Confirmation explicit, not implicit**: even if user picked option 1, /closeout-extended writes the trunk edit to the worktree only; the worktree is left for the user to review-and-commit on their own.

- **Output**: traversal-mode logic in `closeout-extended/SKILL.md`
- **Acceptance**: A test scope with both an outward case (consumer contract update) and an upward case (trunk extension proposal) produces the right behavior in each direction. Upward proposal includes all 4 context fields (callers, tests, conventions, diff). Default-to-leaf-side workaround verified by simulating a no-response.

### 7.3 Implement worktree-based neighbor visits (4D) + cycle detection

- **Type**: AI
- **Input**: list of repos to visit from traversal list
- **Action**: For each neighbor repo to visit:
  1. **Detect trunk branch** from neighbor's CROSS-REPO.md (`max-depth-override` may include `trunk-branch: develop`), or default to `develop` if unset, or fall back to `main` if `develop` doesn't exist.
  2. **Create ephemeral worktree**: `git worktree add /tmp/closeout-<scope-slug>-<neighbor-name> origin/<trunk-branch>` — gives an isolated fresh checkout of neighbor's trunk. No interference with whatever's in user's primary working tree on that repo.
  3. **Apply /closeout 11-step engine in the worktree**. Edits land in the worktree only.
  4. **Cycle detection**: track visited repo paths in a Set. Before visiting any neighbor, check membership — if already visited, skip with log entry "(cycle) repo X already visited, skipping back-edge."
  5. **Per-file dirty skip (within the worktree)**: worktrees start clean, but in the rare case the worktree directory already exists from a prior aborted run, check `git status --short` in the worktree; if non-empty, prompt user inline: "(1) reuse existing worktree state, (2) discard and re-create fresh, (3) skip this neighbor." Default 2.
  6. **Cleanup is opt-in**: at end of /closeout-extended, summary lists all worktrees created with absolute paths. User reviews each and commits/merges/discards. /closeout-extended does NOT auto-remove worktrees (user might need time). A separate `--cleanup-worktrees` flag exists to remove them in bulk after review.
- **Output**: worktree + traversal-guard logic in `closeout-extended/SKILL.md`
- **Acceptance**: (a) Visiting pmg-chatwoot as a neighbor creates `/tmp/closeout-<slug>-pmg-chatwoot/` containing clean develop checkout, edits applied there only. (b) Cycle detection prevents A→B→A loops (tested with deliberately cyclic CROSS-REPO.md). (c) User's primary working tree on neighbor is untouched. (d) Summary lists worktree paths for user review.

### 7.4 Resumable progress via closeout-extended-progress.md

- **Type**: AI
- **Input**: design from §5 (Closeout's own resumability)
- **Action**: As each repo is processed (or skipped), append an entry to a sibling `closeout-extended-progress.md` in the scope folder. Format: `[x] repo-name (depth N) — N edits in worktree <path>` for completed, `[ ] repo-name (depth N) — cycle | skipped (reason) | pending` for not-yet-done. On re-run, /closeout-extended reads this and picks up at the first unchecked entry.
- **Output**: progress-tracking logic in `closeout-extended/SKILL.md`
- **Acceptance**: Killing /closeout-extended mid-run and re-invoking it resumes from the right repo, doesn't re-process completed ones, doesn't re-create existing worktrees unnecessarily.

### 7.5 Test for upward traversal flow

- **Type**: AI+HUMAN_REVIEW
- **Input**: §7.2 implementation
- **Action**: Create a deliberately upward-flowing test scope: a small change in a consumer repo that would benefit from a trunk extension. Run /closeout-extended on it. Verify the upward proposal is rendered with all 4 context fields, options are numbered 1-4 (no AskUserQuestion), and default-to-leaf-side fires when user skips. (Issue 14A).
- **Output**: test case in dogfood
- **Acceptance**: All three behaviors verified.

---
### 🔲 CHECKPOINT: Phase 4 Complete
**Review**: Run /closeout-extended on a sample scope that touches two repos. Verify both repos get healed, dirty-tree skip works, cycle detection works (test by temporarily creating a cyclic CROSS-REPO.md). Inspect closeout-extended-progress.md after a deliberately-killed run.
**Resume**: "continue the closeout-skills plan"
---

## 8. Phase 5 — Dogfood pass

Goal: prove the system works end-to-end on real repos before declaring complete. Bootstrap CROSS-REPO.md/ARCHITECTURE.md on a small subset of real PMG repos and run a closeout cycle.

### 8.1 Run /cross-repo-init on pmg-integrations (validation pass)

- **Type**: AI+HUMAN_REVIEW
- **Input**: `~/Projects/pmg/pmg-integrations`
- **Action**: cd into pmg-integrations, invoke /cross-repo-init. Review the proposed CROSS-REPO.md and ARCHITECTURE.md inline. Refine. Commit on the repo's current branch (or develop per user's branch_workflow preference). This is the *validation* repo for /cross-repo-init — if anything in the skill is wrong, it surfaces here before propagating across the rest.
- **Output**: CROSS-REPO.md + ARCHITECTURE.md committed in pmg-integrations
- **Acceptance**: Files exist, content is accurate, /cross-repo-init re-run is idempotent. User confirms skill quality before proceeding to §8.2.

### 8.2 Run /cross-repo-init on overarching docs repos

- **Type**: AI+HUMAN_REVIEW
- **Input**: `~/Projects/pmg/pmg-docs`, `~/Projects/wellmed/kalpa-docs`
- **Action**: Onboard the two docs repos. These hold cross-cutting documentation, plans, indexes — they're load-bearing for the whole framework. CROSS-REPO.md here declares "Pattern Sources: none (docs-only); Consumers: all repos in their respective project" (or similar — refine in execution). ARCHITECTURE.md describes how the plans/scopes/index live.
- **Output**: CROSS-REPO.md + ARCHITECTURE.md in both docs repos
- **Acceptance**: Both files committed. Docs repos correctly modeled as load-bearing leaves (not contract-bearing consumers).

### 8.3 Run /cross-repo-init on wellmed-infrastructure (Pattern Source trunk)

- **Type**: AI+HUMAN_REVIEW
- **Input**: `~/Projects/wellmed/wellmed-infrastructure`
- **Action**: This is the critical trunk for WellMed adapters and shared infra. CROSS-REPO.md here declares "Pattern Sources: none (this IS the trunk); Consumers: every wellmed-* repo." Onboard this before the wellmed leaves so they have a target to reference.
- **Output**: CROSS-REPO.md + ARCHITECTURE.md committed in wellmed-infrastructure
- **Acceptance**: Files committed. Listed as Pattern Source (not Consumer) of any wellmed repo.

### 8.4 Run /cross-repo-init on remaining repos in sequenced order

- **Type**: AI+HUMAN_REVIEW
- **Input**: remaining repos in dependency order:
  ```
  PMG leaves:
  [ ] ~/Projects/pmg/pmg-chatwoot
  [ ] ~/Projects/pmg/KP2MI-foreign-workers
  [ ] ~/Projects/pmg/mcu-status

  WellMed leaves (after wellmed-infrastructure from §8.3):
  [ ] ~/Projects/wellmed/wellmed-backbone
  [ ] ~/Projects/wellmed/wellmed-cashier
  [ ] ~/Projects/wellmed/wellmed-consultation
  [ ] ~/Projects/wellmed/wellmed-fe
  [ ] ~/Projects/wellmed/wellmed-gateway-go
  [ ] ~/Projects/wellmed/wellmed-pharmacy

  ai-skills:
  [ ] ~/Projects/ai-skills
  ```
- **Action**: cd into each, invoke /cross-repo-init, review/refine, commit. Each WellMed leaf should declare wellmed-infrastructure as Pattern Source. PMG leaves should declare pmg-integrations as Pattern Source / contract source. ai-skills is a leaf (no consumers).
- **Output**: CROSS-REPO.md + ARCHITECTURE.md across all 10 repos
- **Acceptance**: All files committed. Cross-references bidirectional where expected (wellmed-infrastructure's Consumers list includes wellmed-backbone, etc., AND wellmed-backbone's Pattern Sources list includes wellmed-infrastructure). Excluded: gstack (third-party), archive, bernard (inactive), satu-sehat-scraper (inactive), narawangsa/* (inactive).

### 8.5 Sample /plan run with new rules — exercise the three test cases

- **Type**: AI+HUMAN_REVIEW
- **Input**: a deliberately-shaped test plan in pmg-integrations (small scope, exercises ledger appends and one halt-and-ask)
- **Action**: Execute a /plan run with the new rules active. Verify: (a) Phase 0 reads ARCH+CROSS-REPO+CLAUDE.md, (b) Phase 0 halts cleanly when a Pattern Source path is deliberately broken (Issue 17 test from §5.7), (c) pattern-first grep fires before writing a new method, (d) halt-and-ask triggers on a deliberately-novel method, (e) session-scoped approval auto-applies the same pattern to subsequent novel methods of the same shape (Issue 12 test from §5.7), (f) closeout-prep.md is appended throughout — kill /plan mid-phase, resume, verify timestamped second block (Issue 11 test from §5.7).
- **Output**: a populated closeout-prep.md in the test scope folder
- **Acceptance**: All six behaviors verified. Ledger has entries in §2, §3, §6, §7 at minimum.

### 8.6 Run /closeout on the dogfood scope

- **Type**: AI+HUMAN_REVIEW
- **Input**: scope from §8.5 with its closeout-prep.md
- **Action**: Invoke /closeout. Verify 11 steps execute, doc edits propose in working tree (CLAUDE.md / README / ARCH ranked), tests run + gate works (and `--skip-tests` works), scope archives via /plan §11 code path, summary is accurate. User reviews diff and either commits or discards.
- **Output**: archived scope, healed working tree with reviewed edits
- **Acceptance**: Working tree has only intentional, reviewable edits. Scope is in archive. Summary matches reality. Archive logic invoked the same code path as /plan §11 (verify by inspection).

### 8.7 Run /closeout-extended on an upward-flowing dogfood scope

- **Type**: AI+HUMAN_REVIEW
- **Input**: a small scope in pmg-integrations that (a) touches a contract consumed by pmg-chatwoot AND (b) creates a §4 entry with "fold into <trunk>" recommendation pointing at wellmed-infrastructure (deliberately upward-flowing — Issue 14 test)
- **Action**: Invoke /closeout-extended. Verify:
  - Outward traversal to pmg-chatwoot creates an ephemeral worktree on chatwoot's develop, applies consumer-side updates there
  - Upward traversal to wellmed-infrastructure renders the structured proposal with all 4 context fields (callers, tests, conventions, diff), numbered options, default-to-leaf-side workaround on skip
  - Cycle detection works (test with deliberately cyclic CROSS-REPO.md temporarily)
  - Doc-only neighbors skip tests
  - closeout-extended-progress.md is created and is resumable
- **Output**: healed worktrees in both pmg-chatwoot (outward) and wellmed-infrastructure (upward, if user approved option 1) plus aggregated summary
- **Acceptance**: All five behaviors verified. User can review each worktree's diff and commit/discard independently.

### 8.8 Capture findings and decide ship-or-iterate

- **Type**: HUMAN
- **Input**: experience from §8.1–§8.7
- **Action**: Note any rough edges, gaps, or misfires. Decide: ship as v1.0.0, or open a follow-up plan for tweaks. Update memory with anything cross-session-relevant (e.g., "the upward proposal flow needs tighter context loading on test files larger than X" or "ephemeral worktree path collision when running /closeout-extended twice in quick succession" — whatever surfaces).
- **Output**: decision logged in progress.md; optional follow-up plan if needed
- **Acceptance**: Either skills are declared complete and Status flips to Complete in plan + PLANS-INDEX, or a v1.1 follow-up plan is scoped with clear remaining work.

---
### 🔲 CHECKPOINT: Phase 5 Complete (plan complete)
**Review**: All five phases done. /cross-repo-init bootstrapped across 14 active repos. /plan has the new rules. /closeout + /closeout-extended exercised end-to-end with upward and outward flows. Run /closeout on this very plan to self-heal the ai-skills repo (recursive dogfood — eat your own dog food).
**Resume**: "run /closeout on the closeout-skills scope"
---

## 9. Key Decisions Captured

### From design dialogue (v0.1)

- **Self-healing framing** (not audit-and-report): both /closeout and /closeout-extended make edits in working trees. User reviews diffs and commits. No PRs across repos.
- **/closeout local-only vs /closeout-extended recursive**: the only real difference is blast radius. Both use the same 11-step engine.
- **Method-level pattern granularity** in §3/§4: not contract-level, not line-level. Newly-written methods get §3 entries (with deviation field) or §4 entries (with alternatives-considered + recommendation).
- **Halt-and-ask before §4 creation**: this is the single highest-leverage moment in the system — where Claude either follows the kalpa/wellmed-infrastructure adapter pattern or doesn't. Worth the friction.
- **Bias toward existing imperfect patterns**: ≥80% match → use it + document deviation. Inventing a parallel requires explicit user OK.
- **Max depth 2** for /closeout-extended traversal: covers Alex's actual repo graph; per-repo override available.
- **Cycle detection mandatory**: never loop on cyclic CROSS-REPO.md.
- **Test execution gates "healed" status** with `--skip-tests` escape hatch.
- **No drift score / no auto-fix tests / no cross-repo PRs**: explicit non-goals to prevent Goodharting and unsafe automation.
- **One closeout-prep.md per scope** (not per phase), with timestamped phase blocks for append-only resume semantics.
- **Memory writes auto on cross-cutting findings**: per user preference for auto-write over prompt-for-write.
- **Skill location**: all three live in `~/Projects/ai-skills/`, symlinked into `~/.claude/skills/` per existing convention.

### From /plan-eng-review (v0.2)

- **Issue 1 (1B)**: pattern-first grep is per-session in memory only — NO ledger persistence. Resumed sessions re-grep cold. Cost is small, avoids stale-cache failure modes.
- **Issue 2 (2A)**: session-scoped pattern approval — once user approves a novel pattern in a session, subsequent matching methods auto-apply. Avoids halt-and-ask fatigue on refactors.
- **Issue 3 (3D)**: upward traversal uses rich context loading (trunk pattern + tests + callers + conventions) + per-edit user confirmation + default-to-leaf-side workaround on skip. Trunk leads; leaves inherit. Upward edits invert that direction so they require extra justification.
- **Issue 4 (4D)**: neighbor visits use ephemeral `git worktree add origin/<trunk>` to operate in isolation. User's primary working tree on neighbor is never touched. Worktrees left for user review, opt-in cleanup via flag.
- **Issue 5 (5A)**: /closeout-extended validates CROSS-REPO.md as part of its run — flags missing Pattern Sources, stale Consumer references. Closes the drift-detection loop.
- **Issue 6 (6A)**: `**Schema version: 1.0**` field on closeout-prep.md so /closeout can detect skew and error clearly on mismatch.
- **Issue 7 (7A)**: Phase 1 templates include concrete worked examples (pmg-integrations as hub, wellmed-infrastructure as trunk) — not aspirational placeholders.
- **Issue 8 (8A)**: §4 entries require alternatives-considered field even when truly novel (must list places searched). Malformed §4 entries are rejected.
- **Issue 9 (9A)**: two-pass drift detection — Pass 1 (grep) all docs; Pass 2 (LLM-review) only CLAUDE.md + ARCHITECTURE.md (the highest agent-load-bearing).
- **Issue 10 (10A)**: §5.6 folded into §5.5 — eliminates micro-task.
- **Issue 11/12/14 (A)**: explicit tests for ledger restart, session-scoped pattern approval, and upward traversal flow added to §5.7 + §8.5 + §8.7.
- **Issue 13 (13B)**: memory write de-dup is accepted as a gap — observe in real use, don't pre-emptively engineer.
- **Issue 15 (15B)**: doc-only neighbors skip test execution in /closeout-extended (cheap, high-value).
- **Issue 16 (16B)**: §3/§4 LLM calls stay per-method — don't batch. Defer optimization until cost is felt.
- **Issue 17 (17A)**: CROSS-REPO.md path validation runs in /plan Phase 0 + /closeout pre-flight. Critical-gap mitigation — without this, stale CROSS-REPO.md triggers spurious halt-and-asks indistinguishable from "novel method" cases.
- **R1 (A)**: §4.4 deferred to v1.1. /scope auto-suggesting /cross-repo-init is polish, not foundation.
- **R3 (expanded)**: Phase 5 dogfood is the full 14-repo bootstrap pass across active ~/Projects repos, sequenced pmg-integrations → docs → wellmed-infrastructure → leaves. Excluded: gstack (third-party), archive, bernard, satu-sehat-scraper, narawangsa/* (all inactive).
- **AskUserQuestion banned**: all three new skills (/cross-repo-init, /closeout, /closeout-extended) use open-ended numbered inline questions, not AskUserQuestion — matches user's stated preference and matches recent gstack v1.25/v1.31 direction.

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | skipped | user declined outside voice (OV: N) |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR | 17 issues found, all resolved; 3 scope reductions agreed (R1 defer, R2 fold, R3 expand to 14-repo bootstrap); 1 critical gap (Issue 17) addressed; mode: FULL_REVIEW |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | N/A | no UI scope |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | could run — these skills are developer-facing |

**UNRESOLVED:** 0
**VERDICT:** ENG CLEARED — ready to implement. /plan-devex-review optional given developer-facing skill output, but not gating.
