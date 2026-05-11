# /plan — Verification Recipes

Procedural tests for the three rule additions introduced by the closeout-skills work. These are not automated unit tests — ai-skills is a skills repo, not an executable code repo. Each recipe is a scripted manual verification procedure that Claude follows in a dogfood scope.

These recipes are referenced by:
- closeout-skills-PLAN.md §5.7 (Phase 2 test task)
- closeout-skills-PLAN.md §8.5 (Phase 5 dogfood exercises)

Each recipe is self-contained: setup → action → expected outcome → pass criteria.

---

## Recipe 1 — Ledger restart semantics (Issue 11)

**Tests:** /plan's append-to-ledger rule (§8.9) handles mid-phase interruption correctly. Resumed phases produce a second timestamped block, never an overwrite.

### Setup

1. Create a throwaway scope folder at `~/Projects/ai-skills/plans/test-ledger-restart/`.
2. Inside it, write a minimal `test-ledger-restart-PLAN.md` with Status `Ready to execute`, one phase containing 2 AI tasks.
3. Each task should require writing 1 new method (so it triggers §3 entries in the ledger).
4. Ensure CROSS-REPO.md exists in ai-skills (so Phase 0 doesn't halt).

### Action

1. Invoke /plan on the throwaway plan.
2. Verify Phase 0 completes; Task 1.1 begins.
3. After Task 1.1 completes and the ledger receives its first §3 entry, abort the /plan session deliberately (close terminal, or hit Ctrl-C).
4. Inspect `closeout-prep.md` — it should contain exactly ONE `## Phase 1: ... (started <ts>)` block with one §3 entry.
5. Re-invoke /plan on the same plan.
6. /plan should resume from Task 1.2 (per §6.1 progress-file lookup).
7. After Task 1.2 completes, inspect `closeout-prep.md` again.

### Expected outcome

The ledger now contains TWO timestamped phase blocks:

```
## Phase 1: <name> (started <ts1>)
### §3 Patterns Followed (additional)
- <Task 1.1's method>  ...

## Phase 1: <name> (resumed <ts2> after compaction)
### §3 Patterns Followed (additional)
- <Task 1.2's method>  ...
```

NO content from the first block was overwritten. Both timestamps are preserved.

### Pass criteria

- [x] First block intact, unchanged
- [x] Second block appended with new timestamp containing "resumed"
- [x] Each block's §3 entries reference only the methods written during that specific block's execution

### Failure modes to catch

- Overwriting the first block (the bug this test prevents)
- Mixing entries across blocks (timestamps misattributed)
- Missing the second timestamp entirely

---

## Recipe 2 — Session-scoped pattern approval (Issue 12)

**Tests:** /plan's session-scoped pattern approval (§7.6) auto-applies an approved pattern to subsequent same-shape methods within one session, preventing halt-and-ask fatigue on refactors.

### Setup

1. Create a throwaway scope folder at `~/Projects/ai-skills/plans/test-session-approval/`.
2. Write a minimal plan with one phase containing 3 AI tasks, each task instructed to write a method of identical shape (e.g., three similar webhook validators with different algos).
3. Ensure no existing pattern in this repo or any declared Pattern Source matches the shape — so Task 1.1 will trigger halt-and-ask.

### Action

1. Invoke /plan.
2. When Task 1.1 fires the halt-and-ask (§7.5), select option 2 (write parallel impl). /plan should then offer the session-scoped approval follow-up (§7.6).
3. Answer the follow-up with option 1 (yes — auto-apply).
4. /plan proceeds with Task 1.1, writes the method, logs §4 entry with `alternatives-considered`.
5. Task 1.2 fires. /plan should detect the same shape and auto-apply WITHOUT a second halt-and-ask.
6. Task 1.3 fires. Same auto-apply behavior.

### Expected outcome

Inspect `closeout-prep.md`:

```
§3 Patterns Followed:
- <method-1.1>   ← from §4 entry below (session-scoped approval established)
  (applied via session-scoped approval from <method-1.1>)
- <method-1.2>   ← <method-1.1>:<line>
  (applied via session-scoped approval from <method-1.1>)
- <method-1.3>   ← <method-1.1>:<line>
  (applied via session-scoped approval from <method-1.1>)

§4 Patterns Created:
- <method-1.1>  ...
  alternatives-considered: [...]
  recommendation: [...]
```

Only ONE halt-and-ask interaction occurred (for Task 1.1). Tasks 1.2 and 1.3 were auto-applied.

### Pass criteria

- [x] Exactly 1 halt-and-ask fired (not 3)
- [x] Each subsequent §3 entry carries the "applied via session-scoped approval" note
- [x] §4 entry exists only once (for the original approval)
- [x] Resumed session (kill /plan, re-invoke) does NOT carry the approval forward — fresh halt-and-ask fires if a same-shape method appears

### Failure modes to catch

- Halt-and-ask firing 3 times instead of 1 (session-scope not engaged)
- Auto-application without the §3 audit note (approval applied silently — bad)
- Approval persisting across session boundary (should be session-scoped only)

---

## Recipe 3 — CROSS-REPO.md path validation halt (Issue 17)

**Tests:** /plan's Phase 0 (§5.11) halts cleanly when a declared Pattern Source path doesn't resolve on disk, preventing the silent failure mode where stale CROSS-REPO.md produces false "no pattern found" results.

### Setup

1. Create a throwaway scope folder at `~/Projects/ai-skills/plans/test-pattern-validation/`.
2. Write a minimal plan with one phase containing 1 AI task that requires writing a new method.
3. Manually edit ai-skills's CROSS-REPO.md (or the test scope's working CROSS-REPO.md if scoped) to declare a Pattern Source that doesn't exist:
   ```
   ## Pattern Sources
   - this-repo-does-not-exist
     - adapters/* — deliberately bogus
   ```

### Action

1. Invoke /plan.
2. /plan begins Phase 0 pre-flight.
3. /plan reaches §5.11 (Pattern Source path validation).
4. /plan attempts to resolve `~/Projects/<group>/this-repo-does-not-exist/` — fails.

### Expected outcome

/plan halts with a clear message:

```
CROSS-REPO.md declares Pattern Source `this-repo-does-not-exist` at
`~/Projects/<group>/this-repo-does-not-exist/` but the path doesn't exist.

Run /cross-repo-init to refresh CROSS-REPO.md, then resume.
```

/plan does NOT proceed to Task 1.1. Phase 0 logs ❌ FAILED in the progress file.

### Cleanup

Restore CROSS-REPO.md to its correct state after the test. Re-run /plan to confirm it now succeeds and proceeds to Task 1.1 (and that the new method, if one is written, triggers correct pattern-first behavior).

### Pass criteria

- [x] /plan halts at Phase 0 §5.11 before any task executes
- [x] Halt message names the missing repo and the expected path
- [x] Halt message suggests /cross-repo-init as the fix
- [x] After restoring CROSS-REPO.md, /plan resumes cleanly with no manual state cleanup

### Failure modes to catch

- /plan continues past Phase 0 silently (the critical bug Issue 17 prevents — would produce spurious halt-and-asks indistinguishable from genuinely novel methods)
- Halt message is generic ("file not found") without naming the source of the misconfiguration
- /plan errors but in a way that requires manual progress-file cleanup before retry

---

## Notes for Phase 5 dogfood execution

These recipes are run in Phase 5 §8.5 of closeout-skills-PLAN.md against the real pmg-integrations repo after Phase 1-4 are complete. Until Phase 5, this file is a spec — the recipes describe the behavior the implementation must deliver.

If a recipe fails during Phase 5 execution, the implementation has a bug. The plan does NOT continue to subsequent phases until the failing recipe passes.

When a recipe passes, log the pass in closeout-prep.md §10 (Test Coverage Map) with a reference to this recipe file.
