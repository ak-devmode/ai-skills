---
name: closeout
version: 1.0.0
description: |
  Local repo self-heal after a /plan run. Consumes closeout-prep.md and leaves the
  repo healthier than /plan found it: re-runs tests, spot-checks pattern references,
  triages new patterns, repairs doc drift in CLAUDE.md / README / ARCHITECTURE / docs,
  writes cross-cutting memory entries, and archives the scope via /plan's §12 code path.

  Scope is the local repo only — for recursive self-heal across CROSS-REPO.md neighbors,
  use /closeout-extended instead.

  Use when asked to "closeout", "close out the plan", "self-heal this repo",
  "finalize the scope", "wrap up the plan", or as the follow-up prompted by /plan §12.6
  after a plan completes. Also triggers when /plan reports "all tasks complete" and asks
  whether to run closeout now.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
---

# /closeout — Local Repo Self-Heal

This skill is the per-repo engine for the closeout-skills framework. It reads the
closeout-prep.md ledger that /plan appended throughout execution and uses it to
self-heal the local repo: verify pattern references still resolve, apply documentation
drift fixes, run tests, archive the scope.

For cross-repo self-heal (Pattern Sources and Consumers from CROSS-REPO.md),
/closeout-extended wraps this skill — same 11-step engine, applied per repo across
the graph.

The skill **never uses AskUserQuestion** — all user interaction is open-ended numbered
inline questions answered by number.

---

## 1. How It Works

`/closeout` runs eleven steps in order. Each step is conditional — if its inputs are
absent (e.g., no §3 entries in the ledger), the step logs "skipped, no input" and
moves on. The skill is **safe to re-run**: each step is idempotent on healthy state,
so running /closeout twice on a healed repo produces no diff on the second pass.

```
  Step 1  Read closeout-prep.md, verify schema version
  Step 2  Verify scope/plan branch is checked out
  Step 3  Run local test suite (--skip-tests bypasses, with loud flag)
  Step 4  §3 spot-check: do referenced patterns still exist at file:line?
  Step 5  §4 triage: surface "fold into <source>" recommendations
  Step 6  §7 doc drift edits (two-pass: grep-all + LLM-review CLAUDE/ARCH)
  Step 7  ARCHITECTURE.md drift validation + edits
  Step 8  §10 coverage report (read-only — no auto-fix)
  Step 9  Memory writes for cross-cutting findings (auto-write, no prompt)
  Step 10 Invoke /plan §12 archive logic (DO NOT duplicate)
  Step 11 Summary: what changed, what's blocked, where to look
```

All edits land in the working tree. **/closeout never commits.** The user reviews
the diff and commits manually — this is the safety boundary.

## 2. Flags

Read flags from the user's invocation. Default to none if unspecified.

- `--skip-tests` — Step 3 test gate is bypassed. Loudly flagged in summary.
- `--skip-memory` — Step 9 memory writes are skipped. Useful when running closeout
  in a dry-run context.
- `--dry-run` — All steps execute up to but not including any file write or
  `git` mutation. Output what *would* happen.

If a flag is set, log it in §1 of the summary.

## 3. Step 1 — Read closeout-prep.md, Verify Schema Version

3.1 Locate the ledger:
- If invoked from a scope folder (parent has `scope.md`): `{scope-folder}/closeout-prep.md`
- If invoked from a standalone plan folder: `{plan-folder}/closeout-prep.md`
- If neither exists, halt with: "No closeout-prep.md found. /closeout requires a
  populated ledger written by /plan. If /plan was run before the ledger feature
  shipped, run `/review` instead to do an ad-hoc review."

3.2 Read the ledger header. Verify `**Schema version:**` is present. The canonical
template (used for schema reference) lives at `~/Projects/ai-skills/templates/closeout-prep.md.template` — shared across `/plan`, `/closeout`, and `/closeout-extended`.

3.3 Compare the ledger's schema version against this skill's expected version (currently `1.0`):
- **Match:** proceed.
- **Older minor (e.g., `1.0` when skill expects `1.1`):** proceed with a warning logged
  to §1 of the summary — "ledger written by older /plan; some fields may be missing.
  Closeout will skip steps for absent sections."
- **Older major or unknown:** halt with: "Ledger schema version `{seen}` is incompatible
  with /closeout schema `{expected}`. Either upgrade /plan and re-run, or run `/review`
  to do an ad-hoc review." Do NOT auto-migrate the ledger — schema bumps are
  load-bearing and silent migration would mask real problems.

3.4 Parse the ledger into sections §1–§11 plus any timestamped phase-block headers.
If a section is empty (only the template's HTML comment + `_(none)_` markers),
mark it `EMPTY` in working memory and skip its corresponding step.

3.5 Log to the summary's preamble: "Read ledger from `{path}` — N file entries, M patterns
followed, K patterns created, T cross-repo touchpoints, D docs likely affected."

## 4. Step 2 — Verify Branch

4.1 Read the plan's `**Branch:**` field. If absent, derive `feature/<plan-stem>`
(same rule as /plan §5.7).

4.2 Compare against current git branch (`git rev-parse --abbrev-ref HEAD`).

4.3 Mismatch handling:
- **On the expected branch:** log and proceed.
- **On a different feature branch:** present a numbered inline prompt:
  ```
  Plan branch: <expected>
  Current branch: <current>

  /closeout normally runs on the plan's branch so its edits land where the plan
  work landed. Options:
    1. Checkout <expected> and proceed
    2. Stay on <current> — edits land here (use if you've intentionally moved work)
    3. Abort

  Answer by number.
  ```
- **On main/master:** present the same prompt with option 1 default-highlighted as
  recommended. Per `feedback_branch_workflow.md`, do not silently switch — confirm
  with the user.

4.4 If git is not initialized, log "no git — branch step skipped" and proceed.

## 5. Step 3 — Run Test Suite with Gating

5.1 If `--skip-tests` was passed, log "tests skipped per flag — gap flagged in summary"
and proceed. The summary's §1 will surface this prominently.

5.2 Detect the test command. Order of detection:
- Repo's `CLAUDE.md` has a `Test:` field or `go test` / `npm test` line → use it.
- `package.json` has `"scripts": { "test": ... }` → `npm test`.
- `go.mod` exists → `go test ./...`.
- `pyproject.toml` or `requirements.txt` with pytest installed → `pytest`.
- `Cargo.toml` → `cargo test`.
- Otherwise: log "no test command detected — gap flagged in summary" and proceed.

5.3 Run the detected command. Capture stdout, stderr, exit code.

5.4 Gate logic:
- **Exit 0 (pass):** log "tests passed" and proceed.
- **Non-zero exit (fail):** record failure detail in working memory. Closeout
  **continues** through subsequent steps (doc fixes are still valuable) but the
  final summary will flag "NOT HEALED — tests failing" and step 11 marks the
  scope status as `Tests failing — needs manual fix` rather than `Done`. Do NOT
  modify failing tests — surface and stop.

5.5 If `--dry-run`, skip command execution and log "test command detected: `{cmd}` —
not run in dry-run."

## 6. Step 4 — §3 Spot-Check

6.1 Read §3 (Patterns Followed) entries from the ledger. Each entry has the form:
`method-name() in file:line ← pattern-source-file:line`.

6.2 For each entry, verify two things:
1. The new method still exists at `file:line` in the local repo. If the file was
   subsequently moved or the line numbers shifted, grep for `method-name` in the
   file and use the closest occurrence. If not found at all, flag as **stale §3
   entry — method may have been removed or renamed**.
2. The pattern source still exists at `pattern-source-file:line`. The source
   may be in a different repo (per CROSS-REPO.md's declared Pattern Sources) —
   if so, look up the repo path and grep there. If the source method is gone
   (renamed, deleted, refactored), flag as **stale pattern reference — source
   pattern may have moved**.

6.3 Spot-check budget: by default, verify ALL §3 entries. For large scopes (>50
entries), sample the first 50 entries plus a random 10 from the remainder and
log the sampling decision in the summary. The point is detecting drift, not
exhaustive verification.

6.4 Flagged entries get listed in step 11's summary under "§3 stale references"
with workspace-relative paths to investigate. /closeout does NOT auto-fix these
— renames are user decisions.

## 7. Step 5 — §4 Triage

7.1 Read §4 (Patterns Created) entries from the ledger. Each entry has the form:
```
- method-name  file:line
  alternatives-considered:
    - source-A: file:line — rejected: reason
    - source-B: file:line — rejected: reason
    - (none found in: <places searched>) — when truly novel
  recommendation: extend <source> / accept as new / fold into <doc> / write TODO in <repo>'s TO-DO.md
```

7.2 For each entry, route on `recommendation:` field:

- **`extend <source>`** — this is upward traversal territory. /closeout (local-only)
  does NOT walk to the source repo. Surface in step 11 with: "Pattern `<name>`
  recommends extending `<source>`. Run /closeout-extended to walk to the trunk,
  or open the source repo manually." Mark in summary as **deferred to /closeout-extended**.

- **`accept as new`** — the user (via /plan halt-and-ask) accepted this as a
  legitimate new pattern in the local repo. /closeout's action: add a §3-style
  entry to this repo's `ARCHITECTURE.md` §3 "Key Decisions" if not already present,
  noting the new pattern's location and intent. This makes the pattern discoverable
  by future /plan runs. Apply as proposed edit to ARCHITECTURE.md (user reviews).

- **`fold into <doc>`** — the recommendation specifies a doc to update with the new
  pattern's existence (e.g., "fold into pmg-integrations/README.md adapters section").
  /closeout reads the target doc, finds the appropriate section, proposes an edit
  inserting a one-line reference to the new pattern. Apply as proposed edit.

- **`write TODO in <repo>'s TO-DO.md`** — append to the named repo's TO-DO.md (resolve
  per plans-dir convention). If the named repo is not the local repo, surface in
  step 11 as **deferred to /closeout-extended**.

7.3 Malformed §4 entries (missing `alternatives-considered` or `recommendation`)
get flagged in step 11's summary under "Malformed §4 entries — /plan may have a
bug or the entry was edited manually." Do not auto-fix.

## 8. Step 6 — Doc Drift (Two-Pass)

8.1 Read §7 (Docs Likely Affected) entries from the ledger. The ledger ranks docs
by agent-load-bearing weight: CLAUDE.md > README > ARCHITECTURE.md > docs/*. If
§7 is empty, derive a doc list from `git diff` against the scope's base branch:
any markdown file in the repo whose nearest code-change-by-file is referenced in
that doc (best-effort grep). If still empty, skip step 6.

8.2 **Pass 1 — Deterministic grep (all docs in §7).** For each doc:
- Extract candidate stale references: function names, file paths, env var names,
  CLI flag names, struct/class names mentioned in the doc.
- For each candidate, verify it still exists in the code. Use `Grep` against the
  repo (case-sensitive, word-boundary where appropriate).
- Candidates that no longer exist → drift-flag list with `(doc-file:line) "<text
  context>"` → `<best guess: renamed to X / removed in commit Y / unclear>`.

8.3 **Pass 2 — LLM-review (CLAUDE.md + ARCHITECTURE.md only).** For each of these
two docs:
- Re-read the doc cold (do not anchor on Pass 1 findings).
- Compare narrative claims against the current state of the repo: are the
  described workflows still the workflows the code does? Are example outputs
  still representative? Are referenced sub-systems still named the same? Is
  there a major new component that the doc doesn't acknowledge?
- Surface narrative drift as edit proposals — not just symbol drift.
- Other docs (README, docs/*) do NOT get Pass 2. Narrative-drift review on the
  long tail is expensive and lower-value; the trade-off is intentional.

8.4 **Apply edits in priority order:** CLAUDE.md first, then README, then
ARCHITECTURE.md (handled in step 7 separately), then docs/*. Use Edit tool with
narrow `old_string` / `new_string` to avoid unintended changes. Each edit lands
in the working tree.

8.5 If a doc has >10 candidate edits, batch them — propose them all in one Edit
sequence and log "doc <name> had N edits applied" in the summary, rather than
prompting per-edit. /closeout is not interactive on doc fixes; the user reviews
the diff at the end.

8.6 If `--dry-run`, log proposed edits to working memory and don't write.

## 9. Step 7 — ARCHITECTURE.md Drift Validation

9.1 If `ARCHITECTURE.md` doesn't exist in the repo root, log "no ARCHITECTURE.md
— consider running /cross-repo-init" and skip this step.

9.2 Read ARCHITECTURE.md cold. Walk its sections per the template's structure:
Components, Data Flow, Key Decisions, External Integrations, Cross-Repo Position.

9.3 For each section, audit against current repo state:
- **Components:** does every named component still exist as a top-level dir or
  service? Are there new top-level dirs not listed?
- **Data Flow:** flag stale references in the ASCII diagram if any of the named
  services/components have been renamed or removed. Do NOT auto-regenerate the
  diagram — wrong diagrams are worse than missing ones (per /cross-repo-init §7.4).
- **Key Decisions:** scan for decisions that contradict current code (e.g., "we
  use NAMED template parameters" — verify code actually does). LLM-judge here
  since it's narrative.
- **External Integrations:** for each named integration, verify SSM parameter
  paths still exist (best-effort — call out as advisory, not blocker), and
  client imports/packages still match.
- **Cross-Repo Position:** cross-check against CROSS-REPO.md. If ARCHITECTURE says
  this is a Pattern Source but CROSS-REPO.md says no Consumers, flag inconsistency.

9.4 Surface drift as proposed edits to ARCHITECTURE.md. Apply to working tree.

9.5 Step 5 may have added an "accept as new" pattern entry to ARCHITECTURE.md
§3 Key Decisions — coordinate so the same line isn't proposed twice.

## 10. Step 8 — Coverage Map (Read-Only)

10.1 Read §10 (Coverage Map) entries from the ledger. If empty, derive a coverage
report from §2 (Files Changed) — for each modified `.go`/`.js`/`.ts`/`.py` file,
check whether a corresponding `_test.go`/`.test.js`/`.test.ts`/`test_*.py` was
also modified or created in §2.

10.2 Categorize:
- **Covered:** code change has corresponding test change.
- **Uncovered:** code change with no test change.
- **Test-only:** test change with no code change.

10.3 Surface in summary under "Coverage Map" — counts plus an inline list of
uncovered files (up to 20, then summarize). Do NOT auto-write tests. The output
is informational; the user decides whether to backfill tests, accept the gap,
or open a follow-up plan.

10.4 If §10 entries reference business nodes from the PRD (e.g., "User Story 3.2 —
covered by `test/sla_escalation_test.go`"), include those mappings in the summary
to give the user a feature-level view in addition to file-level.

## 11. Step 9 — Memory Writes for Cross-Cutting Findings

11.1 If `--skip-memory` was passed, skip this step.

11.2 Scan §4 (Patterns Created) for entries with `fold into <source>` recommendations
where the source is a different repo from the local repo. These are the
"newly-discovered pattern source" findings worth remembering across sessions.

11.3 Scan §11 (Risk Flags) for entries that look like recurring failure modes —
indicators are: phrases like "discovered that X always fails when Y", "third time
seeing this in <repo>", or risk flags that reference systemic issues (auth
flakiness, deploy ordering, contract drift).

11.4 For each cross-cutting finding, write a memory entry per the conventions in
the user's auto memory rules (see CLAUDE.md system reminder):
- Type: `reference` (for pattern sources) or `feedback` (for recurring failure
  modes) — choose based on whether the finding is a pointer to a place or a rule
  to apply.
- Path: `{memory-dir}/{type}_{slug}.md` with `name`, `description`, `type`
  frontmatter, body lead with rule + **Why:** + **How to apply:** lines.
- Update `MEMORY.md` index with a one-line pointer.

11.5 Auto-write — no prompt. Per Issue 13B (plan v0.2), de-dup gap is accepted —
observe in practice, don't pre-emptively engineer. If a duplicate memory is later
flagged by the user, that's the signal to add de-dup logic.

11.6 Log written memory entries in step 11's summary under "Memory writes" with
paths so the user can audit.

## 12. Step 10 — Archive Scope via /plan §12 Code Path

12.1 **Do NOT duplicate /plan's archive logic.** Read /plan/SKILL.md §12 (Plan
Completion & Archive) and follow that procedure verbatim:
- §12.1 Extract deferred TODOs
- §12.2 Append to TO-DO.md
- §12.3 Archive the plan (child plans stay in scope folder; standalone plans
  move to `archive/`)
- §12.4 Update PLANS-INDEX.md
- §12.5 Update parent scope (if applicable)
- §12.7 Print completion summary
- §12.8 Sibling plan discovery

12.2 Skip §12.6 (the "prompt for /closeout") since /closeout is what's running.

12.3 If the scope is at the scope level (not a single plan), invoke /scope §7
archive procedure additionally — when ALL plans in a scope are complete, archive
the scope folder itself.

12.4 If `--dry-run`, log "would archive scope folder to `{archive-path}`" and
don't move files.

12.5 **Reuse, do not re-implement.** If /plan §12 changes shape in a future
version, /closeout follows automatically. The point of factoring archive logic
into /plan §12 is exactly to avoid two skills having drifting implementations.

## 13. Step 11 — Summary

13.1 Print a structured summary to the user:

```
✅ /closeout complete — {repo-name}

📋 Scope: {plan-or-scope-name} (Plan {N})
🌿 Branch: {branch}
🏥 Health: HEALED | NOT HEALED ({reason})

📊 Steps:
  [✓] 1  Ledger read: {N} files, {M} patterns followed, {K} patterns created
  [✓] 2  Branch: {branch}
  [✓] 3  Tests: PASSED | FAILED ({N} failing) | SKIPPED (--skip-tests)
  [✓] 4  §3 spot-check: {N} verified, {S} stale references flagged
  [✓] 5  §4 triage: {A} accepted, {F} fold-into edits proposed, {D} deferred to /closeout-extended
  [✓] 6  Doc drift: {N} docs edited ({L} CLAUDE/README/docs)
  [✓] 7  ARCHITECTURE.md: {edits or "no drift"}
  [✓] 8  Coverage: {C} covered, {U} uncovered, {T} test-only
  [✓] 9  Memory: {M} entries written
  [✓] 10 Archived: {archive-path}
  [✓] 11 Summary (this)

📝 Edits in working tree (review before commit):
  - {file} — {one-line intent}
  - {file} — {one-line intent}
  ... ({N} more)

⚠ Flags:
  - {stale §3 reference}
  - {malformed §4 entry}
  - {uncovered code path}

🔗 Deferred to /closeout-extended:
  - {pattern <name>} — extend wellmed-infrastructure/adapters/event.go:42
  - {repo <name>} — TODO write-up

📋 TODOs extracted: {N} items → {plans_dir}/TO-DO.md
📊 PLANS-INDEX: Plan {N} → Done

Next:
  - Review the diff: `git diff`
  - Commit when satisfied
  - For cross-repo healing: `/closeout-extended`
```

13.2 If any step had a failure (e.g., tests failing), make the failure prominent
in the header. Don't bury it.

13.3 If `--dry-run`, header changes to "🔍 /closeout dry-run complete — no files
written" and the "Edits in working tree" section becomes "Edits that WOULD be applied"
with the same content.

## 14. Resumability

/closeout is not multi-session by design — one run, one summary. If a run fails
mid-way (e.g., tests hang and user kills it), there's no "resume from step 7"
state file. Re-running /closeout from the top is safe because:

- Step 1 reads the same ledger.
- Step 6/7 doc edits use Edit with exact `old_string` match — if a prior partial
  run already applied an edit, the second run's Edit will fail-clean (no match)
  and log "already applied" rather than corrupt.
- Step 9 memory writes check for existing entry by file path before writing.
- Step 10 archive checks PLANS-INDEX status before mutating (skips if already Done).

For genuinely long runs where re-running is wasteful, /closeout-extended (which
wraps this skill) provides resumability via `closeout-extended-progress.md`.
For a single repo, just re-run /closeout from the top.

## 15. Failure Modes & Recovery

15.1 **Ledger missing or unreadable:** halt with clear message at Step 1. User
options: run /plan to populate, or run `/review` for ad-hoc review without ledger.

15.2 **Ledger schema mismatch:** halt at Step 3. User options: upgrade /plan or
run `/review`.

15.3 **Tests fail:** continue but mark NOT HEALED. User fixes tests then re-runs
/closeout (or skips with `--skip-tests` for a doc-only closeout).

15.4 **Pattern source path missing during §3 spot-check:** flag in summary, do
not halt. The pattern source may be in a Pattern Source repo that the local repo
doesn't have checked out. /closeout-extended (which walks Pattern Sources) is the
right place to verify these — local /closeout just flags.

15.5 **Doc edit conflict** (Edit's `old_string` doesn't match): log "skipped
edit on `{doc}:{line}` — content changed since /plan ran" in summary. User
manually applies or re-runs after fixing.

15.6 **Archive step fails** (e.g., target archive dir already exists): halt at
step 10 with diagnostic. /plan §12 archive is the load-bearing operation — better
to surface and let user resolve than to half-archive.

## 16. Important Behaviors

16.1 **Never modify the ledger.** closeout-prep.md is read-only to /closeout.
The ledger is the audit trail of what /plan did; /closeout records its own work
in the final summary and in commit messages (when the user commits), not in the
ledger.

16.2 **Never commit.** /closeout writes to working tree only. The user reviews
the diff and commits manually. This is the safety boundary that distinguishes
"healed" from "auto-pushed and broken."

16.3 **Never auto-fix tests.** Test failures are surfaced, not patched.
Auto-test-fixing is too easy to get wrong and easy to mask real bugs.

16.4 **Workspace-relative paths everywhere.** Every file reference in the summary
uses paths relative to the repo root.

16.5 **Be loud about flags.** `--skip-tests` and `--skip-memory` always appear
in the summary header. The user should never have to hunt for "did I run with
skip-tests?"

16.6 **Stay local.** If the ledger or any step would require touching another
repo (Pattern Source updates, Consumer code mods), defer to /closeout-extended.
/closeout is the local-scope skill; cross-repo is /closeout-extended's job.

16.7 **Numbered inline questions only.** Per the closeout-skills framework rules,
AskUserQuestion is banned. Step 2 branch confirmation and any other interactive
moments use numbered options answered by number.

## 17. Recipe — First Run

Manual verification recipe for confirming /closeout works end-to-end on a real
scope. To be exercised in plan Phase 5 §8.6.

1. cd into a repo that has a completed /plan with populated closeout-prep.md.
2. `/closeout`
3. Observe Step 1 reads the ledger and reports counts.
4. Observe Step 2 confirms branch (or prompts if mismatch).
5. Observe Step 3 runs the test suite and reports pass/fail.
6. Observe Steps 4-9 surface drift, propose edits, and write memory entries.
7. Observe Step 10 invokes /plan §12 — scope folder moves to `archive/`,
   PLANS-INDEX status flips to Done, TO-DO.md is appended.
8. Observe Step 11 summary lists all edits with workspace-relative paths.
9. `git diff` — verify edits are sensible. `git status` — verify scope folder
   is in archive.
10. Re-run `/closeout` — observe idempotency: no new edits proposed on healthy
    state, summary reports "no changes needed."

Failure modes to test:
- Delete closeout-prep.md and re-run — expect halt at Step 1.
- Edit the ledger to set schema version `99.0` — expect halt at Step 3.
- Break a §3 pattern source reference (move the source file) — expect flag in
  summary, no halt.
