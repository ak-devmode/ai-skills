---
name: closeout-extended
version: 1.0.0
description: |
  Recursive cross-repo self-heal across the CROSS-REPO.md graph. Walks Pattern Sources
  upward and Consumers outward (default max depth 2, per-repo override available),
  applying /closeout's 11-step engine in an ephemeral git worktree per neighbor repo.
  User reviews each worktree's diff manually — /closeout-extended never commits or
  pushes. Resumable via closeout-extended-progress.md.

  Use when asked to "closeout-extended", "recursive closeout", "self-heal across repos",
  "fan-out closeout", "walk the graph", or after /closeout finishes and there are
  deferred cross-repo recommendations (entries in /closeout's summary under
  "Deferred to /closeout-extended").

  Requires CROSS-REPO.md to exist in the local repo. If missing, halts and suggests
  running /cross-repo-init first.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Write
  - Edit
---

# /closeout-extended — Recursive Cross-Repo Self-Heal

This skill extends /closeout from "local repo only" to "local + declared neighbors."
A neighbor is any repo listed in the local repo's CROSS-REPO.md — either as a
**Pattern Source** (upstream; trunk patterns leaf inherits from) or as a **Consumer**
(downstream; repos depending on this repo's exposed contracts).

The skill's blast radius is intentionally bounded:
- **Max depth 2 by default** — local repo + immediate neighbors + their immediate
  neighbors. Configurable per-repo via CROSS-REPO.md's `max-depth-override` field.
- **One ephemeral worktree per neighbor** — neighbor edits never touch the user's
  primary working tree on that repo.
- **Never commits or pushes** — every edit lands in a worktree that the user reviews
  and commits manually.
- **Cycle detection** — A → B → A is broken at the second visit to A.

The skill **never uses AskUserQuestion** — all interaction is open-ended numbered
inline questions.

---

## 1. How It Works

```
  Step 1   Run /closeout's 11-step engine on the local repo
  Step 2   Read CROSS-REPO.md; validate against current state
  Step 3   Build traversal list (Pattern Sources upward, Consumers outward, depth ≤ 2)
  Step 4   Filter cycle-detection-visited repos
  Step 5   For each neighbor:
              5a  Detect trunk branch (from override or default develop→main)
              5b  Create or reuse ephemeral worktree on neighbor's trunk
              5c  Apply /closeout 11-step engine in worktree
                    - Skip tests if neighbor only received doc-only edits
                    - Surface upward edit proposals (per-edit user confirmation)
              5d  Update closeout-extended-progress.md after each neighbor
  Step 6   Aggregate cross-repo summary with worktree paths per neighbor
  Step 7   Print final report; surface CROSS-REPO drift; list deferred upward edits
```

All neighbor edits live in `/tmp/closeout-<scope-slug>-<neighbor-name>/`. User
reviews each worktree's diff, commits where they want, discards what they don't.
Cleanup is opt-in via `--cleanup-worktrees`.

## 2. Flags

- `--max-depth N` — Override CROSS-REPO.md max-depth-override (and the default 2)
  for this run. Hard cap at 4 to prevent runaway recursion on graphs with bidirectional
  edges that escape cycle detection due to symlink/path differences.
- `--skip-tests` — Bypass tests for every repo visited. Loudly flagged in summary.
- `--dry-run` — Walk the graph and print what would happen but write nothing.
- `--cleanup-worktrees` — After the user has finished reviewing, remove all
  ephemeral worktrees created during the run. (Run AFTER review, not as part of
  the main flow.)
- `--upward-only` / `--outward-only` — Restrict traversal direction. Useful when
  you know only one direction matters (e.g., after a contract change, only Consumers
  need updating).

## 3. Step 1 — Run /closeout Locally

3.1 Invoke /closeout in the current repo. Pass through any relevant flags
(`--skip-tests`, `--dry-run`). Capture the structured summary.

3.2 Read the local closeout's flagged items, especially:
- §4 entries with `recommendation: extend <source>` — these drive upward traversal.
- §5 cross-repo touchpoints — these drive outward traversal.
- Any entries in the "Deferred to /closeout-extended" section of the local summary.

3.3 If /closeout halted (e.g., schema mismatch, missing ledger), /closeout-extended
halts with the same diagnostic. Cross-repo self-heal on top of broken local-repo
state is worse than nothing.

3.4 The local repo counts as `depth 0`. It's marked visited before Step 4 traversal.

## 4. Step 2 — Read and Validate CROSS-REPO.md

4.1 Read `./CROSS-REPO.md` in the local repo. If missing, halt with: "CROSS-REPO.md
missing in `{repo}`. Run `/cross-repo-init` to bootstrap, then re-run /closeout-extended."

4.2 Parse Pattern Sources, Consumers, and optional `max-depth-override`.

4.3 **Validate against current state (Issue 5A):**
- For each Pattern Source `<name>`, verify the repo exists at its declared path
  (or at conventional `~/Projects/<group>/<name>`). Missing → flag as **CROSS-REPO
  drift: Pattern Source `<name>` declared but path missing** and exclude from
  traversal (do not halt).
- For each Consumer `<name>`, perform a best-effort grep in that repo for the
  contracts CROSS-REPO claims it consumes (e.g., an HTTP endpoint name, an event
  topic). If no references found, flag as **CROSS-REPO drift: Consumer `<name>`
  no longer references claimed contracts** and downgrade to advisory (still
  traverse, but flag in summary).

4.4 Surface drift findings in the final summary's "CROSS-REPO drift" section so
the user can decide whether to refresh CROSS-REPO.md via /cross-repo-init.

## 5. Step 3 — Build Traversal List

5.1 Initialize visited set with the local repo's absolute path.

5.2 BFS traversal from the local repo:
- **Upward edges:** local repo's Pattern Sources. Each Pattern Source's own
  CROSS-REPO.md may declare further Pattern Sources at depth 2.
- **Outward edges:** local repo's Consumers. Each Consumer's CROSS-REPO.md may
  declare further Consumers at depth 2 (rare in practice; most graphs are shallow).

5.3 Apply max-depth filter. Default 2. CROSS-REPO.md may override per-repo via
`max-depth-override: N`. CLI flag `--max-depth N` overrides everything. Hard
cap at 4.

5.4 Apply direction filter (`--upward-only` / `--outward-only` if specified).

5.5 Output traversal list ordered: outward repos first (mechanical edits, safer),
then upward repos (require user confirmation per edit). Within each direction,
order by depth ascending (depth 1 before depth 2).

5.6 If traversal list is empty (e.g., trunk repo with no Consumers and no Pattern
Sources), log "no neighbors — local-only closeout was sufficient" and skip to
Step 7 final report.

## 6. Step 4 — Cycle Detection

6.1 Maintain a `visited` set keyed by **canonical absolute repo path** (resolve
symlinks before adding to set).

6.2 Before visiting a neighbor, check membership. If present, log:
`(cycle) repo <name> at <path> already visited at depth <prior-depth>, skipping
back-edge` and append to `closeout-extended-progress.md` as `[skip] <name> — cycle`.

6.3 Cycle resolution is **first-visit wins**. The first visit at the shallowest
depth processes the repo; subsequent traversal attempts skip without revisiting.

6.4 If a graph has bidirectional edges between A and B (A lists B as Pattern Source
AND B lists A as Pattern Source — uncommon but possible), cycle detection breaks
the second visit. Surface in summary as **CROSS-REPO topology warning: bidirectional
edge between `<A>` and `<B>` detected**.

## 7. Step 5 — Visit Each Neighbor (the Core Loop)

For each repo in the traversal list, in order:

### 7.1 Detect trunk branch (§5a)

7.1.1 Read neighbor's CROSS-REPO.md. If it has `trunk-branch: <name>` field, use
that.

7.1.2 Else, check whether `develop` branch exists in the neighbor (`git ls-remote
--heads <neighbor-path> develop`). If yes, use `develop`. Per
`feedback_branch_off_develop.md`, pmg-integrations and similar repos use develop
as the trunk.

7.1.3 Else, fall back to `main`. If neither develop nor main exists (rare),
halt with diagnostic and skip the neighbor (log to progress file).

### 7.2 Create or reuse ephemeral worktree (§5b)

7.2.1 Worktree path: `/tmp/closeout-<scope-slug>-<neighbor-name>/`. Scope slug is
derived from the local repo's plan or scope folder name.

7.2.2 Check if the worktree directory already exists:
- **Doesn't exist:** create with `git -C <neighbor-path> worktree add /tmp/closeout-<slug>-<name> origin/<trunk-branch>`.
  Fetch first if the user's primary checkout is stale — `git -C <neighbor> fetch origin <trunk-branch>` then `worktree add`.
- **Exists, clean (`git status --short` empty):** reuse — log "reusing existing
  clean worktree at <path>".
- **Exists, dirty:** present numbered inline prompt to user:
  ```
  Worktree at <path> already exists and has uncommitted changes
  (last modified <date>).

  Options:
    1. Reuse existing worktree state (continue editing from current state)
    2. Discard and re-create fresh from origin/<trunk-branch> (default)
    3. Skip this neighbor for this run

  Answer by number.
  ```
  Default is 2 (discard + re-create) per plan §7.3.5. Wait for user before proceeding.

7.2.3 cd into the worktree for all subsequent operations on this neighbor. Edits
land in the worktree only — neighbor's primary working tree is untouched.

### 7.3 Apply /closeout 11-step engine in the worktree (§5c)

7.3.1 Invoke /closeout's 11 steps within the worktree. **Two adaptations:**

1. **Test skipping for doc-only edits (Issue 15B):**
   - Before Step 3 (test execution), pre-scan the proposed edits that /closeout
     would make in this worktree. If ALL proposed edits are to markdown files
     (.md, .mdx) — i.e., doc drift fixes only, no code touched — skip Step 3 and
     log "doc-only neighbor — tests skipped per Issue 15B."
   - If ANY edit touches code, run tests normally.

2. **Upward edit proposals require user confirmation (per §7.4):**
   - Step 5 (§4 triage) may produce upward edit proposals. For neighbors visited
     via the **upward** direction, every proposed §4 edit gets the structured
     proposal in §7.4 of this document.

7.3.2 Step 10 (archive) is **skipped** for neighbors — only the local repo gets
its scope archived. Neighbor closeouts are scoped to "make edits in worktree,"
not "complete a scope."

7.3.3 Step 11 (summary) output for each neighbor is captured for aggregation in
Step 6.

### 7.4 Upward Edit Proposal (3D — Rich Context + Per-Edit Confirmation + Leaf-Side Default)

For each §4 edit in an upward neighbor, render this structured proposal:

```
═══════════════════════════════════════════════════════════════════════════════
UPWARD EDIT PROPOSAL — neighbor: <pattern-source-repo>
═══════════════════════════════════════════════════════════════════════════════

  Source       <consumer-repo> §<3 or 4> entry triggering this
  Trigger      <one-line summary of why this is proposed>

  Trunk pattern:           <repo>/<file>:<line>
  Trunk pattern callers:   <N> other consumers
                           - <repo-A> consumes via <function>()
                           - <repo-B> consumes via <function>()
                           ... ({K} more)
  Trunk pattern tests:     <test-file> — <N> tests covering current behavior
                           Tests touch: <one-line summary of test surface>
  Trunk conventions:       <one-line from trunk's CLAUDE.md or ARCHITECTURE.md>

  Proposed trunk diff (would be applied to worktree at <worktree-path>):
  ───────────────────────────────────────────────────────────────────────────
  <unified diff of the proposed extension>
  ───────────────────────────────────────────────────────────────────────────

  Alternative — leaf-side workaround (no trunk edit):
    <one-paragraph description of what the consumer would do locally instead>

  Choose:
    1. Apply trunk extension + add tests (to worktree only — user commits)
    2. Leaf-side workaround (DEFAULT — consumer documents deviation in §3)
    3. Defer — write TODO in trunk repo's TO-DO.md
    4. Describe alternative approach

  Answer by number.
═══════════════════════════════════════════════════════════════════════════════
```

7.4.1 **Rich context loading (mandatory):** before rendering the proposal, /closeout-extended
reads:
1. The trunk pattern file (full file, not just the line range).
2. The trunk pattern's tests — locate test file by convention (Go: `<file>_test.go`,
   JS: `<file>.test.js` / `__tests__/<file>.test.js`, Python: `test_<file>.py`).
   Read the test bodies to understand what invariants the trunk relies on.
3. Other callers of the trunk pattern — grep the trunk repo's own source for
   imports/calls. Best-effort enumeration; cap at 10 callers in the prompt and
   summarize the rest as "(K more)".
4. Trunk's CLAUDE.md or ARCHITECTURE.md — extract any relevant "Key Decisions"
   entries that touch this pattern area.

If rich context loading fails for any field (file not found, no tests, etc.),
proceed with the proposal but mark the field as `(unavailable — <reason>)`.
Don't halt for incomplete context — the user can still make a decision.

7.4.2 **Default direction is leaf-side workaround:** if user picks 2, no response,
or anything ambiguous, the consumer's §3 ledger gets a `deviation:` entry
explaining the leaf-side workaround, and the trunk stays untouched. Future
/plan runs may surface the pattern again at a moment of the user's choosing.

7.4.3 **Per-edit, not batched:** each upward edit gets its own proposal and its
own answer. Do not batch upward edits — they require individual judgment.

7.4.4 **Confirmation is explicit, not implicit:** even when the user picks
option 1 (apply trunk extension), /closeout-extended writes the diff to the
worktree only. The user reviews and commits manually. /closeout-extended never
commits cross-repo edits.

### 7.5 Update closeout-extended-progress.md (§5d)

After each neighbor completes (or is skipped), append to
`{local-scope-folder}/closeout-extended-progress.md` (see §10).

## 8. Step 6 — Aggregate Cross-Repo Summary

8.1 Collect per-neighbor summaries from Step 5 into a single report:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  /closeout-extended summary                                               ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  Local repo:    <name> ({edits, status})                                  ║
║  Direction:     upward + outward | upward-only | outward-only             ║
║  Max depth:     {N}                                                       ║
║  Neighbors:     {visited} visited, {skipped} skipped, {cycles} cycles     ║
║                                                                           ║
║  ─── Outward (Consumers) ────────────────────────────────────────────     ║
║                                                                           ║
║    [✓] <repo-A>  (depth 1) — <N> edits in /tmp/closeout-<slug>-<A>/       ║
║         status: HEALED | NOT HEALED (<reason>) | DOC-ONLY                 ║
║    [✓] <repo-B>  (depth 1) — no edits needed                              ║
║    [✓] <repo-C>  (depth 2) — <N> edits in /tmp/closeout-<slug>-<C>/       ║
║                                                                           ║
║  ─── Upward (Pattern Sources) ───────────────────────────────────────     ║
║                                                                           ║
║    [✓] <trunk-A>  (depth 1) — <N> trunk extensions in <worktree-path>     ║
║         <K> upward proposals reviewed: <A>=applied, <B>=leaf-side,        ║
║         <C>=deferred-to-TODO                                              ║
║                                                                           ║
║  ─── Skipped ───────────────────────────────────────────────────────      ║
║                                                                           ║
║    [skip] <repo-D> — dirty worktree, user chose option 3                  ║
║    [skip] <repo-E> — cycle (already visited at depth 1)                   ║
║                                                                           ║
║  ─── CROSS-REPO drift ──────────────────────────────────────────────      ║
║                                                                           ║
║    - Pattern Source `<X>` declared but path missing                       ║
║    - Consumer `<Y>` no longer references claimed contract `<contract>`    ║
║                                                                           ║
║  Suggested next: /cross-repo-init in <repo>                               ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

Worktrees to review:
  /tmp/closeout-<slug>-<A>/
  /tmp/closeout-<slug>-<C>/
  /tmp/closeout-<slug>-<trunk-A>/

To inspect: `cd <worktree-path> && git diff`
To commit:  inside worktree, normal git commit/push
To clean up after review: /closeout-extended --cleanup-worktrees
```

8.2 If any neighbor failed in a non-recoverable way (e.g., test suite hung and
was killed), surface in the summary's header as **NOT HEALED — <repo> incomplete**.

## 9. Step 7 — Final Report and Cleanup

9.1 Print the aggregated summary from Step 6.

9.2 If `--cleanup-worktrees` was passed AFTER the user has reviewed, remove all
worktrees created in this run: `git worktree remove <path>` per neighbor. (When
invoked without prior worktree creation, this flag is a no-op.)

9.3 If the local repo's /closeout step 10 archived the local scope, the scope
folder is no longer at its original path. /closeout-extended's worktrees reference
the local scope only by name — they don't depend on the original path.

## 10. Resumability via closeout-extended-progress.md

10.1 Sibling file to the local scope's closeout-prep.md and scope.md:
`{local-scope-folder}/closeout-extended-progress.md`.

10.2 Format:

```markdown
# /closeout-extended progress — {scope-slug}

**Started:** {ISO timestamp}
**Local repo:** {name} ({absolute path})
**Direction:** upward + outward | upward-only | outward-only
**Max depth:** {N}

## Visited

- [✓] {repo-name} (depth {N}) — {M} edits in {worktree-path}
      finished {ISO timestamp}
- [✓] {repo-name} (depth {N}) — no edits
- [skip] {repo-name} — cycle (already visited at depth {prior})
- [skip] {repo-name} — dirty worktree, user chose discard
- [ ] {repo-name} (depth {N}) — pending

## Upward proposals reviewed

- {proposal-id}: {applied | leaf-side | deferred-to-TODO | alternative}
  - trunk: {repo}/{file}:{line}
  - consumer: {repo} §{3 or 4} entry {N}
  - worktree: {path or "(none — leaf-side / deferred)"}

## CROSS-REPO drift findings

- {finding}
- {finding}
```

10.3 Append entries as neighbors complete. On re-run of /closeout-extended (e.g.,
after a killed session), read this file, identify the first `[ ] pending` entry,
and resume from there. Already-completed `[✓]` entries are skipped — their
worktrees are preserved.

10.4 If a re-run finds existing worktrees that match the closeout-extended-progress.md
record, reuse them. If they're missing (user already cleaned them up), re-create
fresh from origin trunk.

10.5 Once all neighbors are `[✓]` or `[skip]`, the file's footer is updated with
**Completed:** {ISO timestamp} and the file remains in the scope folder as audit
trail. It travels with the scope to `archive/` when /closeout archives the local
scope.

## 11. Failure Modes & Recovery

11.1 **CROSS-REPO.md missing in local repo:** halt at Step 2 with "Run /cross-repo-init
in `<repo>` to bootstrap." This is the on-ramp.

11.2 **CROSS-REPO.md missing in a neighbor:** log warning, traverse the neighbor
with default depth-2 assumption (no further hops from that neighbor), skip Pattern
Source resolution within it. Surface in CROSS-REPO drift findings.

11.3 **Neighbor repo path missing on disk:** log skip, surface in drift findings.
Common cause: neighbor was moved or never cloned locally.

11.4 **`git worktree add` fails** (e.g., remote not accessible, branch missing):
log error, mark neighbor `[skip] <name> — worktree add failed (<reason>)`, move
to next. Do not halt the entire run.

11.5 **User Ctrl-C mid-run:** /closeout-extended has no graceful shutdown hook
(can't run finally-blocks reliably from a skill). On re-invocation, the
closeout-extended-progress.md file is the recovery state. Worktrees from the
killed run remain — re-run reuses or rebuilds them per §10.4.

11.6 **Worktree already exists from a parallel run** (rare — user invoked
/closeout-extended twice in different terminals): the second invocation's
"dirty worktree" prompt fires per §7.2.2. User can skip to avoid stepping on
the other run's work.

11.7 **`--max-depth` set higher than 4:** clamp to 4 with a warning. Cycles in
graphs with subtle path differences (symlinks vs absolute) can escape detection
at deep depths; the cap is a safety net.

## 12. Important Behaviors

12.1 **Never commit, never push.** Edits land in worktrees only. Cross-repo
commits are explicit user actions.

12.2 **Worktrees are user property after creation.** /closeout-extended does
not auto-remove them — the user reviews on their own timeline. `--cleanup-worktrees`
is opt-in.

12.3 **Cycle detection mandatory.** Never loop on cyclic CROSS-REPO.md. First-visit
wins.

12.4 **Default direction is leaf-side workaround on upward edits.** Trunk leads,
leaves inherit. Inverting that direction requires deliberate user OK.

12.5 **Doc-only neighbors skip tests** (Issue 15B). Tests on a neighbor that only
had a CLAUDE.md or README edit are wasted effort.

12.6 **Numbered inline questions only.** Like /closeout and /plan, AskUserQuestion
is banned. Every interactive moment uses numbered options answered by number.

12.7 **Workspace-relative paths in summaries; absolute paths for worktrees.**
Edits-by-file are easier to read with relative paths within each neighbor; worktree
paths must be absolute (`/tmp/...`) since they're outside any repo.

12.8 **/closeout, not re-implementation, is the per-repo engine.** Every neighbor
visit invokes /closeout's 11 steps. /closeout-extended's job is graph walk +
upward proposal flow, not per-repo healing logic.

## 13. Recipe — First Run

Manual verification recipe for confirming /closeout-extended works end-to-end.
Exercised in plan Phase 5 §8.7 against a deliberately-shaped pmg-integrations
scope.

1. Set up test scope: in pmg-integrations, create a small /plan that (a) touches
   a contract consumed by pmg-chatwoot (outward case), AND (b) creates a §4 entry
   with `recommendation: extend wellmed-infrastructure/adapters/event.go:42`
   (upward case). Populate closeout-prep.md by executing the plan.

2. `/closeout-extended` in pmg-integrations.

3. Observe Step 1: local /closeout runs first, summary captures §4 fold-into
   recommendations and §5 cross-repo touchpoints.

4. Observe Step 2: CROSS-REPO.md validation. Deliberately break a Pattern Source
   path (rename ~/Projects/wellmed/wellmed-infrastructure temporarily) and verify
   the drift finding appears.

5. Observe Step 3: traversal list shows pmg-chatwoot at depth 1 outward, and
   wellmed-infrastructure at depth 1 upward.

6. Observe Step 5 outward visit (pmg-chatwoot):
   - Worktree created at `/tmp/closeout-<slug>-pmg-chatwoot/` on `develop`
   - /closeout 11-step engine applied in worktree
   - Doc-only edits → tests skipped (verify in summary)

7. Observe Step 5 upward visit (wellmed-infrastructure):
   - Worktree created at `/tmp/closeout-<slug>-wellmed-infrastructure/` on
     `develop` (or `main` per its CROSS-REPO trunk-branch field)
   - Upward proposal rendered with all 4 context fields (callers, tests,
     conventions, diff)
   - Numbered options 1-4 present, NO AskUserQuestion
   - Skip the prompt without answering → verify default-to-leaf-side fires

8. Observe Step 6 aggregate summary:
   - Worktree paths listed with absolute paths
   - Outward and Upward sections both populated
   - CROSS-REPO drift finding from step 4 surfaces in drift section

9. Inspect each worktree's diff: `cd /tmp/closeout-<slug>-pmg-chatwoot && git diff`.
   Verify edits are sensible.

10. Inspect `closeout-extended-progress.md` in the scope folder. Verify all
    visited neighbors marked `[✓]` and upward proposal outcomes recorded.

11. Kill /closeout-extended mid-run (e.g., Ctrl-C during upward proposal). Re-run
    `/closeout-extended`. Verify it resumes from the first `[ ]` entry and reuses
    existing worktrees.

12. Test cycle detection: temporarily edit pmg-chatwoot's CROSS-REPO.md to declare
    pmg-integrations as a Pattern Source (creating A→B→A cycle). Re-run
    /closeout-extended. Verify it logs `(cycle) pmg-integrations already visited
    at depth 0, skipping back-edge` and doesn't loop.

13. `/closeout-extended --cleanup-worktrees`. Verify all worktrees removed.
