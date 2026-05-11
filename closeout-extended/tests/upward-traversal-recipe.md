# /closeout-extended — Upward Traversal Verification Recipe

Issue 14A manual verification. Exercised in plan Phase 5 §8.7. Confirms:
1. Upward proposal renders with all 4 context fields (callers, tests, conventions, diff)
2. Numbered options 1-4 present, **no AskUserQuestion**
3. Default-to-leaf-side fires when user skips / doesn't respond

This is a manual recipe — not an automated test. Run it before declaring
/closeout-extended v1.0 shipped.

---

## Recipe 1 — Upward proposal with rich context

**Setup:**

1. Choose a consumer repo with a populated CROSS-REPO.md declaring a Pattern Source.
   Default: `pmg-integrations` declaring `wellmed-infrastructure` as Pattern Source
   for adapters.

2. Create a small /plan in the consumer that deliberately writes a new method
   similar-but-not-identical to an existing wellmed-infrastructure adapter.
   Example: `eventPublisher.publishAuditTrail()` in pmg-integrations that resembles
   `wellmed-infrastructure/adapters/event.go:publishEvent()` but adds an
   audit-trail field.

3. Execute the plan via `/plan`. When the Pattern-First Rule §7.5 halt-and-ask
   fires, choose **option 2 (write parallel impl)** to populate a §4 ledger entry
   with `recommendation: extend wellmed-infrastructure/adapters/event.go`.

4. Verify closeout-prep.md §4 has the entry with `alternatives-considered` and
   `recommendation: extend <source>` fields populated.

**Action:**

5. `/closeout-extended` in pmg-integrations.

6. Local /closeout runs (Step 1). Observe the §4 entry surfaces as "Deferred to
   /closeout-extended" in the local summary.

7. CROSS-REPO.md validates (Step 2). Traversal list (Step 3) includes
   wellmed-infrastructure as upward depth 1.

8. Worktree created at `/tmp/closeout-<slug>-wellmed-infrastructure/` on develop
   (or whatever wellmed-infrastructure's trunk is).

9. /closeout 11-step engine runs in worktree. Step 5 (§4 triage) reaches the
   upward edit. **The upward proposal is rendered.**

**Expected proposal output:**

```
═══════════════════════════════════════════════════════════════════════════════
UPWARD EDIT PROPOSAL — neighbor: wellmed-infrastructure
═══════════════════════════════════════════════════════════════════════════════

  Source       pmg-integrations §4 entry "eventPublisher.publishAuditTrail"
  Trigger      Consumer wrote parallel impl; recommendation says extend trunk

  Trunk pattern:           wellmed-infrastructure/adapters/event.go:42
  Trunk pattern callers:   <K> other consumers
                           - wellmed-backbone consumes via publishEvent()
                           - wellmed-cashier consumes via publishEvent()
                           - <list continues, or "(K more)">
  Trunk pattern tests:     adapters/event_test.go — 7 tests covering current behavior
                           Tests touch: event payload validation, retry behavior, ...
  Trunk conventions:       From wellmed-infrastructure/ARCHITECTURE.md §3 —
                           "All adapter methods must validate payload before publish"

  Proposed trunk diff (would be applied to worktree at /tmp/closeout-<slug>-wellmed-infrastructure/):
  ───────────────────────────────────────────────────────────────────────────
  --- a/adapters/event.go
  +++ b/adapters/event.go
  @@ -42,7 +45,15 @@
   func publishEvent(e Event) error {
       if err := validate(e); err != nil {
           return err
       }
  +    // New field: audit trail support per pmg-integrations request
  +    if e.AuditTrail != nil {
  +        if err := writeAuditEntry(e.AuditTrail); err != nil {
  +            return err
  +        }
  +    }
       return publish(e)
   }
  ───────────────────────────────────────────────────────────────────────────

  Alternative — leaf-side workaround (no trunk edit):
    pmg-integrations keeps its parallel publishAuditTrail() locally and documents
    the deviation in its §3 ledger. wellmed-infrastructure stays unchanged. If
    other consumers later need audit-trail support, the pattern can be folded
    upward at that time.

  Choose:
    1. Apply trunk extension + add tests (to worktree only — user commits)
    2. Leaf-side workaround (DEFAULT — consumer documents deviation in §3)
    3. Defer — write TODO in trunk repo's TO-DO.md
    4. Describe alternative approach

  Answer by number.
═══════════════════════════════════════════════════════════════════════════════
```

**Pass criteria:**

- [x] All 4 context fields present and populated:
  - Trunk pattern file/line
  - Trunk pattern callers (with enumerated names, capped at 10)
  - Trunk pattern tests (test file + behavior summary)
  - Trunk conventions (one line from CLAUDE.md or ARCHITECTURE.md)
- [x] Proposed diff is a unified diff format, not pseudocode
- [x] Alternative (leaf-side workaround) is a one-paragraph description
- [x] Options numbered 1-4
- [x] **No `AskUserQuestion` tool call in the trace** (verify in transcript)

**Failure modes:**

- Context field shows `(unavailable — file not found)` → context loading failed
  somewhere; check whether trunk repo path resolves and the pattern file exists
  at the line ledger claims.
- Diff is shown as prose ("we'd add a check for audit trail") → SKILL.md §7.4 not
  followed; proposal should be unified diff.
- Options shown via AskUserQuestion → SKILL.md ban violated; investigate.

---

## Recipe 2 — Default-to-leaf-side on skip

**Setup:** same as Recipe 1, through step 8.

**Action:**

9. When the upward proposal renders, **do not answer**. Wait a beat, then send
   any unrelated message OR Ctrl-C the proposal.

**Expected behavior:**

- /closeout-extended treats no-response as option 2 (leaf-side workaround).
- pmg-integrations' worktree gets a §3 deviation entry added to its closeout-prep.md
  (in the appropriate ledger).
- wellmed-infrastructure worktree is created BUT no trunk edits are applied to it.
- Final summary's "Upward proposals reviewed" line shows
  `<proposal-id>: leaf-side`.
- Final summary's "Worktrees to review" lists wellmed-infrastructure's worktree
  but the diff is empty (or only contains unrelated drift fixes from /closeout's
  other steps, not the upward edit).

**Pass criteria:**

- [x] Trunk repo's worktree has empty diff for the upward-edit case
- [x] Consumer repo's §3 deviation is recorded
- [x] `closeout-extended-progress.md` "Upward proposals reviewed" shows
      `leaf-side` outcome

**Failure modes:**

- Trunk worktree has the diff applied without confirmation → SKILL.md §7.4.2
  (default-to-leaf-side) not implemented correctly.
- /closeout-extended halts waiting for input → §7.4.2 not implemented; should
  default after a brief wait or on any non-1/3/4 input.

---

## Recipe 3 — Cycle detection on bidirectional CROSS-REPO

**Setup:**

1. Same as Recipe 1, but additionally:
2. Temporarily edit `wellmed-infrastructure/CROSS-REPO.md` to declare
   `pmg-integrations` as a Pattern Source (creating A→B→A bidirectional edge).

**Action:**

3. `/closeout-extended` from pmg-integrations.

**Expected behavior:**

- Step 4 visits wellmed-infrastructure at depth 1.
- When traversing wellmed-infrastructure's CROSS-REPO.md to find its Pattern
  Sources at depth 2, pmg-integrations appears.
- Cycle detection (§6.2) catches: `(cycle) pmg-integrations at /Users/.../pmg-integrations
  already visited at depth 0, skipping back-edge`.
- Summary's "Skipped" section includes `[skip] pmg-integrations — cycle (already
  visited at depth 0)`.
- Summary's "CROSS-REPO topology warning" section flags the bidirectional edge.

**Pass criteria:**

- [x] No infinite loop
- [x] Cycle log entry present
- [x] Topology warning surfaced
- [x] closeout-extended-progress.md records the cycle skip

**Failure modes:**

- Infinite recursion → §6.1 visited-set tracking broken (likely path canonicalization
  issue — symlinks resolving inconsistently).
- Cycle detected but not surfaced as topology warning → §6.4 not implemented.

**Cleanup:** revert the temporary edit to wellmed-infrastructure/CROSS-REPO.md
after the test.

---

## Logging

When all three recipes pass on a clean dogfood scope (per plan Phase 5 §8.7),
log the pass in the scope's closeout-prep.md §10 (Coverage Map) with references
to this recipe file.
