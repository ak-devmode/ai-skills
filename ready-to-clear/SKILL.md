---
name: ready-to-clear
version: 1.0.0
description: |
  Independent clear-readiness validation. Spawns a FRESH subagent that checks disk
  truth (progress files, closeout-prep ledger, PLANS-INDEX) against git truth
  (commits, dirty trees, branches) and runs a cold-resume test before any /clear
  suggestion is allowed. Use when asked "is it safe to clear", "ready to clear",
  "validate resume state", or "can I clear now". Also invoked as a MANDATORY gate
  by /plan (§12.8.4/§12.8.5), /scope (Step 8.4), and after /closeout, before those
  skills suggest /clear. Catches the end-of-context failure mode where the executing
  session believes it is done but progress/ledger/index writes were dropped.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Agent
---

# /ready-to-clear — Clear-Readiness Validator

## 1. Why This Skill Exists

The `/clear` suggestion is emitted by the **most degraded context in the session** —
the end-of-context executing agent assessing its own completeness. That
self-assessment is exactly what fails: progress.md not updated, side-path fixes
unlogged, closeout half-run, PLANS-INDEX stale. The fix is structural, not
motivational: **the verdict must come from a fresh context that reads disk and git
only.** If a cold reader can't reconstruct the resume from disk, the session is not
ready to clear — no matter what the executing context believes.

Two hard rules:

1.1 **The validator never receives conversation narrative.** It gets paths and the
claimed state — nothing else. Passing "what we did" would contaminate the one
property that makes the check valid.

1.2 **The verdict gates the `/clear` suggestion.** `NOT READY` means the calling
context must remediate and re-validate. It must not suggest `/clear` with an
open `NOT READY` verdict — surface the failure list to the user instead.

## 2. Invocation Contexts

- **Standalone** — user asks "ready to clear?" at any point. Run Steps 3–6.
- **From /plan** — at §12.8.4 (A/D/E gate handoff) and §12.8.5 (scope complete),
  before the `/clear` suggestion is emitted.
- **From /scope** — at Step 8.4.3, before telling the user to run `/clear`.
- **After /closeout** — /closeout intentionally leaves an uncommitted working tree
  (its safety boundary). The validator treats that as a **declared exception**
  (§5.6), not a pass — the dirty files must be enumerated in the verdict.

## 3. Input Assembly (calling context does this)

Collect **paths only**:

3.1 The active scope folder or standalone plan folder (scope.md / *-PLAN.md,
progress file, closeout-prep.md, artifacts/).

3.2 The list of repos plausibly touched this session. Union of:
- repos named in closeout-prep.md §2 (Files Changed)
- repos named in the scope.md Repo Graph (if present)
- the CWD repo

3.3 The **claimed state**, as a single factual sentence with no narrative, e.g.:
- "Claim: plan 96.2 tasks 1–4 complete, checkpoint at gate D reached."
- "Claim: scope 92 fully complete and archived."
- "Claim: /closeout ran; user has not yet committed."

3.4 The plans directory root (for PLANS-INDEX.md and TO-DO.md).

## 4. Spawn the Validator

Launch ONE fresh subagent (general-purpose, read-only mandate) with this prompt
shape — paths substituted, nothing added:

```
You are a cold-context auditor. You have NO knowledge of the session that
produced this state — that is deliberate. Read only what is on disk and in git.

Claimed state: {claim sentence}
Scope/plan folder: {path}
Repos to audit: {list of repo paths}
Plans dir: {path}

Run checks A–E below. Do not fix anything. Return the verdict contract in §6.
{paste §5 checks + §6 contract verbatim}
```

Do not summarize the session for the agent. Do not pre-answer any check.

## 5. The Checks

### 5.A Git truth

For each repo in scope:
- `git status --porcelain` — uncommitted changes? Classify each file: plausibly
  session work vs pre-existing.
- `git log --oneline -10` + branch vs the plan's `**Branch:**` field — commits
  present for the claimed completed tasks? Still on the right branch?
- Unpushed commits at a phase boundary (`git rev-list @{u}..HEAD` where an
  upstream exists) — /plan §8.5 requires push at phase end.

### 5.B Progress truth

- Resume Context (scope-level AND active plan subsection) — do "Last action" /
  "Next action" match what git says just happened? A Resume Context pointing at a
  task whose commit already exists = stale.
- Every task the claim says is complete has a ✅ entry in the resolved progress
  file (per /plan §2.3 — child plans write to the scope progress.md subsection,
  NOT a `<plan-stem>-PROGRESS.md`; the presence of an unmigrated stub file is
  itself a FAIL).
- Timestamps are plausible (a "complete" claim with a Resume Context untouched
  for the whole session is a red flag).

### 5.C Side-path capture (dropped-work detector)

Diff the set of files changed in git this session (committed + dirty) against the
union of files listed in the progress entries and closeout-prep.md §2. **Any file
changed on disk but logged nowhere is presumptively dropped side-path work** —
FAIL with the file list. This is the check that catches "I fixed something I
found along the way and it never made it into the record."

### 5.D Completion integrity (only when the claim says complete/archived)

- TODOs extracted to TO-DO.md with a section for this plan (/plan §12.2).
- PLANS-INDEX.md row status matches the claim (plan → Done; scope archival
  repointed paths per /scope Step 7.2).
- Parent scope progress.md: Plans table row updated + scope-level Resume Context
  repointed (/plan §12.5).
- Closeout state is explicit: either /closeout ran (evidence: doc-drift edits,
  summary, archive) or the deferral is durable (TO-DO.md entry + Resume Context
  "Open blockers" line — /plan §12.6). A closeout that is neither run nor
  durably deferred = FAIL.

### 5.E Cold-resume test (the sharpest check)

From disk alone, write the exact resume: the command a fresh session would run
(e.g., `/plan 96.3`) and the first concrete action it would take. If the
validator cannot produce this unambiguously — conflicting Resume Contexts, a
"next action" pointing at a completed task, no obvious entry point — FAIL,
regardless of how the other checks scored.

### 5.6 Declared exceptions

A dirty tree passes ONLY when it is declared: /closeout's intentionally
uncommitted edits, or WIP the user explicitly chose to leave (must appear in the
Resume Context "Open blockers" line). Exceptions are enumerated file-by-file in
the verdict — never silently absorbed.

## 6. Verdict Contract

The validator returns exactly:

```
VERDICT: READY | NOT READY
Resume reconstruction: {command + first action, or "COULD NOT RECONSTRUCT"}
Failures (numbered, empty if READY):
  1. [{check letter}] {what is wrong} → {the specific write/commit that fixes it}
Declared exceptions: {file list + reason, or "none"}
```

## 7. Remediation Loop (calling context)

7.1 On `NOT READY`: perform the listed fixes (these are exactly the writes the
skills already mandate — progress entries, ledger appends, commits, index rows),
then re-run the validator with the same inputs. The fix list is a to-do, not a
debate — do not argue with the cold reader from the degraded context.

7.2 Maximum 3 validation cycles. Still `NOT READY` after 3 → stop, present the
remaining numbered failures to the user inline, and do NOT suggest `/clear`.

7.3 On `READY`: the calling skill may emit its `/clear` suggestion, quoting the
resume reconstruction line so the user sees what the next session will do:

> Validated ready to clear — cold-resume: `{command}` → {first action}.
