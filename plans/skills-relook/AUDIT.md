# ai-skills Re-look — Phase 1 Audit

**Version:** 1.0
**Date:** 9 August 2026
**Created by:** Alex Knecht
**Status:** Awaiting review — no skill edits made
**Branch:** `feature/skills-relook-opus5`
**Scope:** 8 core planning skills (5,358 lines) + 2 secondary

---

## 1. Verdict

The skills are not stale-for-the-model. They are **stale-for-their-own-size**: eight
years of incident lore compressed into files that are now too large to be obeyed.

```
                    added   deleted   deletion rate
  scope/SKILL.md    +1426    -312         18%
  plan/SKILL.md      +898    -171         16%
  closeout/          +809     -75          8%
  cross-repo-init/   +814     -48          6%
  markdown-style/    +617     -17          3%
```

Every incident added a rule. Almost nothing was ever removed, promoted out, or turned
into code. The result is 5,358 lines of core skills in which the genuinely load-bearing
insights — gate-based phasing, canonical-sources-before-probing, side-path logging,
the archive gate script, deny-by-default on table deviation — sit at the same visual
weight as a `head -30` and a 2026-05 dogfood recipe for pmg-integrations.

Three consequences, in order of cost:

1.1 **Dilution.** `/scope` + `/plan` is ~25k tokens of instruction before any work
starts. The repo contains its own evidence that adding prose stopped working: four
sections now carry a "> **Why this is a checklist item and not a habit**" preamble,
which is an author noticing that the previous prose was ignored and responding with
more prose.

1.2 **Determinism written as prose.** Only 4 scripts exist in the whole repo. Scope-number
claiming, PLANS-INDEX row mutation, repo-graph snapshotting, and plans-dir resolution
are all prose instructions to an LLM. Two of those have already produced real
data loss (§5.1, §5.2).

1.3 **Live contradictions.** Because nothing is ever deleted, superseded text survives
next to its replacement. `/closeout` currently documents both "never halt on a missing
ledger" and "halt on a missing ledger" — the second being the exact bug that left
scope 99 unarchived (§5.3).

The fix is not "trust the model more." It is: **move determinism into scripts, move
institutional facts into on-demand references, delete what the harness now owns, and
cap the judgment layer at a length that can actually be followed.**

### 1.1 The model already in the repo

`/ready-to-clear` (176 lines) is what every skill here should look like: one structural
insight stated once ("the verdict must come from a fresh context that reads disk and git
only"), a hard input contract, a delegated subagent, a machine-checkable verdict format,
and no restatement of anything another skill owns. It is the newest skill and the
shortest. That is not a coincidence — it is the target.

---

## 2. Method

2.1 Read in full: `/scope`, `/plan`, `/closeout`, `/closeout-extended`,
`/cross-repo-init`, `/markdown-style`, `/ready-to-clear`. Headings + spot reads:
`/prd`, `/repo-cleanup`, `/scope-review`.

2.2 Cross-checked claims against disk (churn history, duplicate-rule counts, legacy
file presence, index shape conformance) rather than asserting from reading alone.
Where a rule claimed a past failure, the claim was taken at face value — those are
Alex's own postmortems and are the most valuable content in the repo.

2.3 Every section classified into exactly one bucket:

| Bucket | Meaning | Disposition |
|---|---|---|
| **KEEP** | Judgment or anti-tendency gate the model does NOT do by default | Stays in SKILL.md body, verbatim |
| **COMPRESS** | Right rule, 3–5x the words it needs | Stays in body, rewritten shorter |
| **MOVE** | Institutional fact / template / postmortem — load-bearing but not always relevant | `references/` or `templates/`, loaded on demand |
| **SCRIPT** | Deterministic. An LLM following prose is strictly worse than executing code | `scripts/`, called by the body |
| **DELETE — model** | Hand-holding a current-generation model does anyway | Removed |
| **DELETE — harness** | Superseded by Claude Code features that did not exist when written | Removed |
| **DEDUPE** | Same rule stated in 2+ skills | One owner keeps it; others reference by section |

2.4 Bias declared up front, per the brief: aggressive on `DELETE`/`SCRIPT`,
conservative on `KEEP`/`MOVE`. Team use *raises* the bar for keeping institutional
facts and graceful-degradation rules — a teammate on a stale clone or a thinner
context is exactly who those protect — and *lowers* the bar for model hand-holding,
which costs them attention budget for no benefit.

---

## 3. Headline numbers

```
                        now    body after   references   scripts
  scope                1114        ~230         ~380        yes
  plan                  973        ~240         ~260        yes
  cross-repo-init       766        ~180         ~150        yes
  closeout              734        ~200         ~120        yes
  closeout-extended     669        ~150          ~60        yes
  markdown-style        600        ~380            -          -
  prd                   326        ~150           ~40         -
  ready-to-clear        176         176            -          -
                     ------      ------       ------
  total               5358       ~1706        ~1010     ~400 loc
```

Resident cost of a `/scope` → `/plan` session: **2,087 lines → ~470 lines (-77%)**.
Nothing in the "institutional facts" bucket is lost; it becomes retrievable instead
of resident.

---

## 4. Per-skill verdicts

### 4.1 /scope — 1114 lines

| § | Content | Verdict | Note |
|---|---|---|---|
| Phase Boundaries A–F | Gate taxonomy; "token size is NOT a gate" | **KEEP** | The best 30 lines in the repo. Ahead of most published practice. Untouched. |
| Step 0 | 4 prescribed bash blocks with `head -30` | **COMPRESS** 40→10 | Keep the *list of facts to establish*. Drop the commands — a current model gathers context better unprescribed. |
| Step 0.5 | Cross-repo snapshot, per-repo serial loop | **SCRIPT** 70→8 | `repo-graph-snapshot.sh` emits the markdown table. N repos in parallel, not sequential. |
| Step 0.6 | Contract cascade detection | **COMPRESS** 45→15 | The *rule* (contract change ⇒ consumers in-scope by default, deferral is explicit) is load-bearing. The file-glob list is script material. |
| Step 0.7 | ADR-first check | **COMPRESS** 55→15 | Rule is load-bearing: don't re-derive what an ADR already decided. Keyword grep → parallel + script. |
| Step 0.8 | Endpoint map (API-dict gated) | **KEEP** | Non-obvious completeness gate; "3/4-baked scope" is a real failure mode. |
| Step 1 | Round 1 + 10 example questions | **COMPRESS** 30→12 | Keep: single batch, open-ended only, never-ask-what-you-can-read, the conditional leads (cascade/ADR/cross-repo first), the WellMed/PMG angles. Delete the 10 generic examples — the model generates better, task-specific ones. |
| Step 2 | Round 2 + task-type seeds | **COMPRESS** 15→6 | Same reasoning. Keep "skip Round 2 if Round 1 resolved it." |
| Step 3 | Atomic vs phased + gate sanity check | **KEEP** | Pure judgment codification. The "name the gate or merge the phases" check is the anti-over-phasing guard. |
| **Step 4** | 18-skill checklist: N/A table + 4 tables + a "boilerplate collapse" rule to undo its own verbosity | **REPLACE** 90→20 | The single largest joystick. Becomes: skill-family list, the always-YES rule (`/plan-ceo-review`), the N/A-is-per-task rule, and a pointer to `templates/skill-checklist.md`. The 4 tables are a template, not instruction. |
| Step 4.5 | Table Identity Map + deviation ledger | **KEEP** | Deny-by-default on write-ownership deviation. High-value, genuinely non-obvious, and the scope-48 rationale is sound. |
| Step 5.1 | Plans-dir resolution | **SCRIPT + DEDUPE** | Same block exists in 5 skills (`/scope`, `/plan`, `/prd`, `/markdown-style`, `/member-record-amend`). One script. |
| Step 5.2 | Scope-number assignment | **SCRIPT** | **Has an active race** — see §5.1. |
| 5.2.1 | Program-member lifecycle (ADR-029) | **MOVE** 35→3 | `references/plans-conventions.md`. Relevant on maybe 1 scope in 10. |
| 5.3 | Workspace-relative paths | **DEDUPE** | `/markdown-style` §8.8 owns this. Stated in 5 skills, 22 times total. |
| 5.4 | scope.md body template | **MOVE** | `templates/scope.md.template`. |
| 5.4 (cont.) | `Created by` derivation + 20-line postmortem | **KEEP rule (3 lines) + MOVE postmortem** | The rule ("derive from git config, never a literal, never substitute from an example") is the whole lesson and generalizes. The forensics belong in `references/postmortems.md`. |
| 5.5 | progress.md template | **MOVE** | `templates/progress.md.template`. |
| 5.6 | `mkdir artifacts` | **DELETE — model** | One line of the template step. |
| 5.7 | Sweep related files | **SCRIPT** | Four `mv` globs with `2>/dev/null`. |
| 5.8 | PLANS-INDEX update | **SCRIPT** | See §5.2. |
| 5.9 | Plan stubs + sizing rule | **COMPRESS + MOVE template** | Keep: Gate field is required on every checkpoint; the "don't split a phase for size" rule; the table-write-phase gate escalation. Stub shape → template. |
| Step 6 | Handoff summary + gstack targeting | **KEEP** | Short and load-bearing (scope-level vs plan-level review targeting is a real distinction). |
| Step 7 | Archive | **DEDUPE** | Third copy of archive logic (also `/plan` §12.3, `/closeout` §13). One owner. |
| Step 8.1 | "Close background shells" | **DELETE — harness** | Background tasks are harness-tracked and re-invoke on exit. |
| Step 8.2–8.4 | Post-flight + next-scope prompt | **COMPRESS** 50→20 | Keep the `/ready-to-clear` gate and the fallback chain. Drop the ASCII prompt mockups. |
| Ongoing Rules 1–5 | Progress discipline | **DEDUPE** | `/markdown-style` §10 already owns every one of these. |
| Behavior Rules | 8 bullets | **KEEP** | Cheapest high-signal block in the file. |

### 4.2 /plan — 973 lines

| § | Content | Verdict | Note |
|---|---|---|---|
| §1.1 | Canonical sources before probing (anti-archaeology) | **KEEP** | Excellent, and *more* necessary with a more agentic model, not less. Verbatim. |
| §2.1–2.2 | Plan discovery | **COMPRESS + SCRIPT** 30→10 | `find-plan.sh` handles both naming conventions and the multiple-match halt. |
| §2.3 | Progress-file resolution (child vs standalone) | **KEEP** 15 | Fixed a real class of lost writes. Keep the rule. |
| §2.3.1 | Migration of pre-3.3.0 progress files | **DELETE — obsolete** | Verified: **zero** non-archived `*-PROGRESS.md` files across all three plans dirs. The migration has nothing left to migrate. 13 lines of dead branch. |
| §2.5 | Plan folder setup (mkdir/mv/sweep) | **SCRIPT** 45→5 | Same sweep script as `/scope` 5.7. |
| §3 | Plan document format | **DEDUPE** | `/markdown-style` §8 owns the shape. |
| §3.1 | `Executed by` stamping | **KEEP rule + MOVE rationale** | The gate ("never mark Complete while `Executed by` is TBD") stays. |
| §4.1–4.3 | Progress schemas, both modes | **DEDUPE → markdown-style §10** | 90 lines duplicating the style guide. |
| §5.1–5.5 | Phase 0 pre-flight | **KEEP-COMPRESS** | Verification-before-execution is right. Tighten. |
| §5.6.1 | Scope freshness validation (SHA classify) | **SCRIPT** 65→10 | Unchanged / advanced / diverged / missing is a mechanical classification. Script emits it; the model decides the gate. |
| §5.6.2 | Read ALL sibling plan files | **KEEP** | High-value and repeatedly-damaged-by-skipping. Keep the "why" — it's what makes it stick. |
| §5.9–5.11 | Context files + bootstrap-state + Pattern Source validation | **COMPRESS** 25→8 | Keep the halt on partial bootstrap (a missing file silently produces false "no pattern found"). |
| §5.12 | "Build in-session Pattern Sources map: map keys are…, map values are `(repo_path, sub_path_glob)` pairs" | **DELETE — model** | Specifying the model's working-memory data structure. Textbook over-joysticking. |
| §5.13 | Bootstrap closeout-prep.md | **KEEP-COMPRESS** | The hard-step framing is right; the ledger must exist before files are touched. |
| §6 | Execution rules | **KEEP** | Tight already. |
| §7.1 | Pattern-First trigger: 11-bullet list of "known-extensible areas" | **COMPRESS** 20→6 | "Integration surfaces (anything crossing a process, network, or external-system boundary)" covers all 11 and generalizes to the 12th. |
| §7.2 | Two-source grep | **COMPRESS** | Keep the two-source requirement, drop the recipe. |
| §7.3 | "Caching: in-memory per session only, no persistence" | **DELETE — model** | Describes doing nothing. |
| §7.4 | ≥80% match ⇒ use the existing pattern | **KEEP** | This is the actual rule and it fights a live model tendency. |
| §7.5 | Halt-and-ask proposal format | **KEEP-COMPRESS** | Keep the shape; it's a genuine decision handoff. |
| §7.6 | Session-scoped approval state machine | **DELETE — model** | A 2024 workaround for halt-and-ask fatigue. Current models batch same-shape judgment natively. |
| §7.7 | §4 entry template w/ mandatory alternatives-considered | **KEEP** | Forces the justification; drives `/closeout-extended` upward traversal. |
| §7.8 | Bias toward existing imperfect patterns | **COMPRESS** | Restates 7.4. Merge. |
| §8.1–8.9 | Important behaviors | **KEEP** | §8.5 (commit each task, push each phase) and §8.3 (dual-log) are load-bearing. |
| §8.10 | Side-path logging, at the moment it happens | **KEEP** | Names the primary dropped-work class and pairs with `/ready-to-clear` check C. Untouched. |
| §9 | Ralph Loop integration | **DELETE — harness** | Superseded by `/loop`, `ScheduleWakeup`, background tasks, re-invoke-on-completion. |
| §10 | First Run Setup | **MERGE into §5** | Restates §2.3 + §4 + §5 in a third voice. |
| §11 | Document Formatting | **DEDUPE** | `/markdown-style` owns it. |
| §12.1–12.2 | TODO extraction → TO-DO.md | **KEEP-COMPRESS** | Durable-deferral rule is right; drop the two near-identical block templates. |
| §12.3 | Archive | **DEDUPE** | See §5.4 — one owner. |
| §12.4 | PLANS-INDEX row movement + 12-line postmortem | **SCRIPT + MOVE postmortem** | The postmortem's lesson ("an append with no header is not a record; it is a leak") is exactly why this must be a schema-enforcing script. |
| §12.6 | Closeout prompt + durable deferral | **KEEP** | |
| §12.8 | Sibling discovery + gate-keyed `/clear` | **KEEP** | Gate-keyed rather than "context feels heavy" is the correct instinct. |

### 4.3 /closeout — 734 lines

| § | Content | Verdict | Note |
|---|---|---|---|
| §1 | 12-step map + "two steps are NOT conditional" | **KEEP** | |
| §3.1a | LEDGER-LESS MODE, never halt, never fabricate a ledger | **KEEP** | "Absent is absent — say so" is a genuinely good rule. |
| §3.3 | Schema-version gate | **COMPRESS** + fix drift (§5.4) | |
| §4 | Branch verify | **COMPRESS** 27→10 | |
| §5.2 | Test-command detection cascade | **SCRIPT** | Deterministic; also wanted by `/closeout-extended` and `/health`. |
| §6 | §3 spot-check + sampling budget | **KEEP-COMPRESS** | |
| §7 | §4 triage routing | **KEEP** | 4-way routing on the recommendation field is real logic. |
| §8.2–8.3 | Two-pass doc drift (grep-all, then LLM on CLAUDE/ARCH only) | **KEEP** | The explicit cost trade-off ("other docs do NOT get Pass 2") is good engineering. |
| §8.7a | Service-doc sweep for retired contracts | **KEEP** | The scope-57 lesson — "a 14/14 exit code is not evidence the service docs are right, because service docs are not repos" — is one of the sharpest observations in the repo. |
| §8.8 | API-surface delta | **KEEP-COMPRESS** | |
| §9 | ARCHITECTURE.md drift | **COMPRESS** | |
| §10 | Trio sync via `/cross-repo-init` | **COMPRESS** 50→15 | Reuse-not-duplicate is right; the coordination-ordering prose is 3x needed. |
| §11 | Coverage map | **COMPRESS** | |
| §12 | Memory writes | **KEEP-COMPRESS** | |
| §13.0 | **Archive is mandatory** + the scope-99/scope-57 evidence | **KEEP** | |
| §14.0 | **Archive gate script before reporting** | **KEEP + GENERALIZE** | "Prose cannot enforce itself: an agent can believe it archived and be wrong." The best pattern in the repo. Generalize it — see §6.1. |
| §14.1 | Summary block | **MOVE** | Output template. |
| §15 | Resumability | **COMPRESS** 18→6 | |
| §16 | Failure modes | **COMPRESS + FIX** | Contains the live contradiction, §5.3. |
| §17 | Important behaviors | **KEEP** | |
| §18 | Manual first-run recipe | **MOVE → `tests/`** | Also contains the contradiction. |

### 4.4 /closeout-extended — 669 lines

| § | Content | Verdict | Note |
|---|---|---|---|
| §1.1 | Step 1 is a distinct pass, runs FIRST, on the primary tree | **KEEP** | The scope-57 archival-ownership insight ("running the anchor as one of the N leaves nobody holding archival") is deep and unguessable. |
| §1.2 | Docs-hub terminal stop | **KEEP** | The hub isn't a trio neighbour but holds the index and the archive. Correct and non-obvious. |
| §1.3 | Completion gate — "N/N swept" ≠ "closeout complete" | **KEEP** | |
| §2 | Flags | **KEEP-COMPRESS** | |
| §4–§6 | CROSS-REPO validation, BFS, cycle detection | **COMPRESS** 80→25 | Keep first-visit-wins and the bidirectional warning. BFS mechanics are model-native. |
| §7.2 | Ephemeral worktree lifecycle: create / reuse-clean / prompt-on-dirty / `/tmp` paths | **REPLACE — harness** 45→8 | `Agent(isolation: "worktree")` does this natively, including cleanup-if-unchanged. |
| §7.3 | 12-step engine per neighbour, 3 adaptations | **KEEP + PARALLELIZE** | Neighbours are independent by construction. Today: serial. Should fan out. See §6.2. |
| §7.3.2 | Neighbours skip archive (+ the load-bearing-in-one-direction clause) | **KEEP** | |
| §7.4 | Upward edit proposal, 4 mandatory context fields, leaf-side default | **KEEP-COMPRESS** | Keep all four context fields and the default. Compress the box-drawing. |
| §8.1 | Box-drawing aggregate summary | **MOVE** | 40 lines of output template. |
| §10 | `closeout-extended-progress.md` resumability | **COMPRESS** | |
| §11 | Failure modes | **COMPRESS** 30→10 | |
| §13 | 14-step manual recipe | **MOVE → `tests/`** | |

### 4.5 /cross-repo-init — 766 lines

| § | Content | Verdict | Note |
|---|---|---|---|
| §1 | Trio/quartet + assess-first | **KEEP-COMPRESS** | |
| §2.2 | **Branch survey — "the checked-out branch is not the truth"** | **KEEP rule + SCRIPT the loop** 75→20 | The rule is excellent (and the kalpa-docs dogfood that produced it is the right kind of evidence). The 25-line inline `for`-loop over refs is script material. |
| §2.3 | Drift capture + repo-state classification | **COMPRESS** | |
| §2.4 | `.gitignore *.md` audit | **SCRIPT** 10→2 | |
| §3.2 | Auto-detect Pattern Sources / Consumers | **COMPRESS + PARALLELIZE** | Sibling-repo grep is embarrassingly parallel; today serial. |
| §5.1–5.6 | Four near-identical CLAUDE.md location flows | **COMPRESS** 145→40 | Neither / root-only / sidecar-only / both → one fold procedure plus a 4-row disposition table. The *rule* (single canonical at root, delete the sidecar, env.example wins on ports) is what matters. |
| §4.3 | 200-line ARCHITECTURE gate | **KEEP** | Ironic and correct. |
| §4.4 | Long-form fold + archive | **KEEP-COMPRESS** | |
| §6 | Idempotency verification | **KEEP** | |
| §7 (Report) | Output template | **MOVE** | Also a **numbering collision** — see §5.5. |
| §7 (Behaviors) 7.1–7.13 | 100 lines, ~half restating §2–§5 | **COMPRESS/DEDUPE** 100→35 | Keep 7.4 (never auto-generate diagrams), 7.4a (survey the right branch), 7.8/7.9 (single canonical), 7.10 (authoritative sources), 7.13 (two-trunk archetype). Fold the rest. |
| §8 | First-run recipe for pmg-integrations | **DELETE — obsolete** | One-time 2026-05 dogfood, since completed. |
| §9–§10 | Limitations + recovery | **COMPRESS** | |

### 4.6 /markdown-style — 600 lines

**Net grows slightly.** It becomes the single owner of document *shape*, absorbing the
schemas currently duplicated inside `/scope` and `/plan`. Split of responsibility:
**markdown-style owns shape; scope/plan own process.**

| § | Content | Verdict | Note |
|---|---|---|---|
| §1–§7 | Voice, modes, numbering, diagrams, tagging, edit log | **KEEP** | The stable core. |
| §2.2.3 | `@Owner` narrowing + "a rule obeyed nowhere is worse than no rule" | **KEEP** | Best-reasoned edit in the repo; the correct instinct applied to exactly one rule. **The whole point of this audit is applying it at scale.** |
| §8 | Plan documents | **KEEP + become sole owner** | |
| §8.1.3 / §8.4 | "Store plans in `kalpa-docs/plans/[topic]/`", archive to `kalpa-docs/plans/archive/` | **FIX — stale** | Contradicts the `{N}-{slug}` convention and the three-project resolution. WellMed-only text that predates PMG + ai-skills. |
| §8.x (9 places) | "the task-runner skill" | **FIX — stale name** | Skill was renamed `/plan`. Also 2 leaks in `/scope`. See §5.6. |
| §9 | PRD documents | **FIX + KEEP** | "PRDs are authored in claude.ai (Opus) and handed off to Claude Code" predates `/prd` existing. |
| §10 | Progress files | **KEEP + become sole owner** | Absorbs `/plan` §4. |
| §11 | Scope documents | **KEEP + become sole owner** | Absorbs `/scope` §5.4–5.5. |
| §11.7 | PLANS-INDEX conventions | **KEEP + enforce by script** | The four rules are right. They should be executable, not aspirational — see §5.2. |

### 4.7 /prd — 326 lines

Healthy. `COMPRESS` the two question rounds on the same reasoning as `/scope` Steps 1–2;
`MOVE` the PRD body template out; `DEDUPE` the plans-dir block. Target ~150.

### 4.8 /ready-to-clear — 176 lines

**KEEP AS-IS.** No changes proposed. Reference implementation for the target shape.

### 4.9 Secondary

`/repo-cleanup` (447) and `/scope-review` (361) reviewed at heading level only. Both
read as more disciplined than the core eight — `/repo-cleanup` because it is inherently
script-shaped, `/scope-review` because it is recent. Deferred to a Phase 5 pass rather
than pulled into this rewrite.

---

## 5. Defects found

These are not style findings. Each is a live bug or a rule that contradicts another
rule in the same repo.

### 5.1 Scope-number claiming has an active race

`/scope` §5.2 instructs the model to read `PLANS-INDEX.md`, find the highest number,
and increment — from the **local working tree**. `/plan` §12.4 already knows better and
says to read `git show origin/main:{plans_dir}/PLANS-INDEX.md` "since concurrent sessions
race for scope numbers." The two skills disagree, and the one that creates scope numbers
is the one that's wrong.

- [ ] `claim-scope-number.sh` — read from `origin/main`, claim atomically, return `{N}`.
      Both skills call it. This race has already fired (scope 110 collided, renumbered 111).

### 5.2 PLANS-INDEX has three shapes, and ai-skills' own index violates the newest rule

`/markdown-style` §11.7.1 mandates 5 columns: `| # | Status | Folder | Description | Created by |`,
and `/plan` §12.4 says "any row that does not match that shape does not belong in the file."
`ai-skills/plans/PLANS-INDEX.md` — the index this very repo maintains — is 7 columns
(`# | Date | Type | Folder/File | Project | Status | Description`), which is the shape
`/scope` §5.8 still tells you to write.

So: the skill that creates index rows writes shape A, the style guide mandates shape B,
and the repo authoring both uses shape A. The 40-row headerless fragment that hid
scopes 101/106/107/108 in the WellMed index is what this class of drift produces.

- [ ] `plans-index.py {add|move|validate}` — schema-enforcing, single shape, refuses
      malformed rows at write time. `/scope`, `/plan`, `/closeout`, `/repo-cleanup` all call it.
- [ ] Decide the canonical shape (5-col loses `Date` and `Type` — confirm that's intended)
      and migrate all three indexes.

### 5.3 /closeout documents both "never halt on a missing ledger" and "halt on a missing ledger"

`§3.1a` is emphatic — never halt, run LEDGER-LESS MODE, because halting is what left
scope 99 unarchived for days. But the superseded text was never removed:

- `§16.1` — "**Ledger missing or unreadable:** halt with clear message at Step 1."
- `§16.2` — "**Ledger schema mismatch:** halt at Step 3." (§3.3 puts the schema gate at Step 1.)
- `§18` failure-mode tests — "Delete closeout-prep.md and re-run — **expect halt at Step 1**."

An agent reading §16 or §18 reproduces the exact scope-99 bug and has a written test
telling it that's correct.

- [ ] Delete §16.1; rewrite §16.2 to point at the right step; fix §18's expectations.

### 5.4 /closeout schema version is ambiguous

Frontmatter says `version: 1.1.0`. §3.3 says the skill expects `1.0`, then illustrates
with "older minor (e.g., `1.0` when skill expects `1.1`)". The ledger template's own
version isn't quoted anywhere in the skill.

- [ ] Single source: read the expected version from `templates/closeout-prep.md.template`,
      don't restate it in prose.

### 5.5 Two numbering collisions

- `/cross-repo-init` — "Step 5 — Report" and "Important Behaviors" are **both `## 7`**.
- `/closeout` — **two `14.3`** sections (clear-readiness note, and dry-run header).

Both violate `/markdown-style` §3.3.2 (no duplicate numbers), whose §3.3 preamble
calls the numbering audit "the most commonly skipped step." Correct, evidently.

- [ ] Renumber; run the §3.3 audit across every skill body as part of Phase 3.

### 5.6 `/plan` was renamed from `task-runner`; 11 references never followed

9 in `/markdown-style` (§8.2.2, §8.3.1, §8.5.1, §8.5.3, §8.6.2, §8.7.2, §8.9.4, and the
§8 preamble) and 2 in `/scope` (frontmatter description, §407) still name "the
task-runner skill." A teammate grepping for `task-runner` finds a skill that doesn't exist.

- [ ] Global rename in prose.

### 5.7 `/plan` §2.3.1 is dead code

The pre-3.3.0 progress-file migration. Verified: zero non-archived `*-PROGRESS.md` files
exist across `wellmed/kalpa-docs/plans`, `pmg/pmg-docs/plans`, and `ai-skills/plans`.
13 lines of branch that can never execute, read on every Phase 0.

- [ ] Delete.

### 5.8 `/markdown-style` §8.1.3 / §8.4 contradict the plans-directory convention

They say plans live in `kalpa-docs/plans/[topic]/` and archive to
`kalpa-docs/plans/archive/`. The actual convention is `{plans_dir}/{N}-{slug}/` across
three projects, and child plans explicitly **do not** archive individually (`/plan`
§12.3.0, and §8.9.4 four sections later in the same file).

- [ ] Rewrite to the three-project convention; remove the per-plan archive instruction.

---

## 6. Cross-cutting upgrades

### 6.1 Generalize the "prose cannot enforce itself" pattern

`/closeout` §14.0 is the only place in the repo where a skill asserts its end state with
a script instead of confidence, and it exists because two scopes were reported complete
while sitting unarchived. That reasoning is not specific to archiving.

Candidates for the same treatment, each a scripted gate the skill must pass before
reporting success:

- [ ] `/scope` — scope folder exists with scope.md + progress.md + artifacts/, index row
      present and well-formed, number not colliding.
- [ ] `/plan` — every task claimed done has a progress entry and a commit; `Executed by`
      is not TBD.
- [ ] `/cross-repo-init` — the idempotency claim (§6) is *asserted* today; make it a
      re-run that diffs and fails on non-empty.

### 6.2 Fan out what is already independent

Three skills declare `Agent` in `allowed-tools`; only `/ready-to-clear` uses a subagent.
Meanwhile:

- [ ] `/closeout-extended` §7 — neighbour repos are independent by construction
      (that's why each gets its own worktree). Today: serial. Should be parallel agents
      with `isolation: "worktree"`, which also deletes the 45 lines of hand-rolled
      worktree lifecycle in §7.2.
- [ ] `/scope` §0.5 — N-repo snapshot, parallel.
- [ ] `/scope` §0.7 — ADR keyword grep, parallel.
- [ ] `/cross-repo-init` §3.2.4 — sibling-repo consumer detection, parallel.

Explicitly **not** proposed: fanning out judgment. Question rounds, gate decisions,
deviation approvals, and upward-edit proposals stay in the main context.

### 6.3 Consolidate duplicated rules to one owner

Measured across the core skills:

```
  plans-dir resolution block      5 skills
  "never AskUserQuestion"        7 skills, 16 mentions
  workspace-relative paths       5 skills, 22 mentions
  archive logic                  3 skills (scope §7, plan §12.3, closeout §13)
  progress-file schema           2 skills (plan §4, markdown-style §10)
  plan-document schema           2 skills (plan §3, markdown-style §8)
```

- [ ] `AskUserQuestion` ban and workspace-relative paths → stated once in
      `/markdown-style`, and once in `ai-skills/CLAUDE.md` §3.2 / §7 where they already
      live. Skills stop restating them.
- [ ] Archive logic → one owner. `/plan` §12 is already the de-facto one (both others
      say "do not duplicate, follow /plan §12"), so `/scope` §7 and `/closeout` §13
      become pointers plus their genuine deltas (program-member routing; the mandatory-ness).
- [ ] Document schemas → `/markdown-style` sole owner.

### 6.4 Progressive disclosure

Every core skill becomes:

```
  <skill>/
    SKILL.md                  judgment, gates, and the run order. <250 lines.
    references/
      conventions.md          plans-dir, numbering, program members, index shape
      postmortems.md          the "why this rule exists" forensics, verbatim
    templates/
      *.template              output shapes (scope.md, progress.md, summaries)
    scripts/
      *.sh | *.py             everything deterministic
    tests/
      *-recipe.md             the manual verification recipes now inline
```

Nothing in `references/` is lost — it's retrieved when relevant instead of resident
always. This is what makes the 77% resident-cost cut non-destructive.

### 6.5 What the team gets

Team use was the tie-breaker on several calls above, so stated plainly:

- Shorter bodies mean a teammate can read a skill before running it. 1,114 lines is
  not reviewable; 230 is.
- Scripts degrade identically in every hand. Prose degrades per-context — which is the
  `Author: Alex` lesson generalized: **a rule that only works when the reader knows the
  backstory is a rule that fails for everyone but its author.**
- `ai-skills/CLAUDE.md` §2.1 already flags that a merge here is not delivery (the frozen
  `kalpa-docs/claude-skills/` copy, four files, 305 lines vs 548). Phase 4 should either
  refresh or delete that copy — a stale duplicate of a skill that has now changed shape
  is worse than none.

---

## 7. Phase 2–4 work list

Ordered by dependency. Each phase is one reviewable unit.

### 7.1 Phase 2 — extract determinism (scripts first, no body edits)

- [ ] `scripts/resolve-plans-dir.sh` — one owner, 5 callers
- [ ] `scripts/claim-scope-number.sh` — fixes §5.1
- [ ] `scripts/plans-index.py {add|move|validate}` — fixes §5.2
- [ ] `scripts/repo-graph-snapshot.sh` — parallel, emits the markdown table
- [ ] `scripts/find-plan.sh` — both naming conventions, halt on ambiguity
- [ ] `scripts/scope-freshness.sh` — SHA classification for `/plan` §5.6.1
- [ ] `scripts/detect-test-cmd.sh` — `/closeout` §5.2
- [ ] `scripts/branch-survey.sh` — `/cross-repo-init` §2.2, merged-vs-live classification
- [ ] `scripts/sweep-related-files.sh` — `/scope` §5.7 + `/plan` §2.5.5
- [ ] Generalized gate scripts per §6.1
- [ ] Validate each against real data (the three live plans dirs) before any skill calls it

### 7.2 Phase 3 — restructure bodies + fix defects

- [ ] Fix §5.3 through §5.8 (the defects) — these land first, independent of restructuring
- [ ] `markdown-style` becomes sole shape owner; absorb `/plan` §4 and `/scope` §5.4–5.5
- [ ] Split each skill into `SKILL.md` + `references/` + `templates/` + `tests/`
- [ ] Rewrite the 8 bodies to the KEEP/COMPRESS verdicts above
- [ ] Run the `/markdown-style` §3.3 numbering audit across every body
- [ ] Version-bump each SKILL.md; record supersessions in `references/postmortems.md`

### 7.3 Phase 4 — fan-out, deletions, propagation

- [ ] Parallelize per §6.2; replace `/closeout-extended` §7.2 with `Agent(isolation: "worktree")`
- [ ] Delete: `/plan` §9 (Ralph Loop), §5.12, §7.3, §7.6, §2.3.1; `/scope` §5.6, §8.1;
      `/cross-repo-init` §8
- [ ] Refresh or delete the frozen `kalpa-docs/claude-skills/` copy (§6.5)
- [ ] Dogfood: run `/scope` → `/plan` → `/closeout` end-to-end on a real ai-skills task
      and diff the behaviour against the current versions

### 7.4 Deferred

- [ ] `/repo-cleanup` + `/scope-review` deep pass (§4.9)
- [ ] `kalpa/*` sub-skills (6 skills, 719 lines) — small and mostly reference-shaped
- [ ] Consider a SKILL.md length gate as a repo hook — the accretion pattern will
      recur, and `/cross-repo-init` §4.3 already proves Alex believes in length gates
      for docs he asks *other* people's agents to write

---

## 8. Open questions for review

8.1 **PLANS-INDEX canonical shape** — the 5-column form in `/markdown-style` §11.7.1
drops `Date` and `Type`. Intended, or an artifact of compressing an example? All three
indexes need migrating either way, so this decides once.

8.2 **`Created by` in the index** — §11.7.1's 5th column is `Created by`, but the
WellMed index has 61 rows that mostly predate that field. Backfill from git, leave
blank, or drop the column?

8.3 **How much postmortem prose survives.** My default: the *rule* stays in the body
as 1–3 lines, the forensics move to `references/postmortems.md` verbatim. The counter-case
is that the forensics are what make the rule stick — you wrote them for that reason.
Say the word and they stay inline, at a cost of roughly 180 lines across the eight.

8.4 **`/scope` Step 4's 18-skill checklist** — I want to cut ~90 lines to ~20 and move
the four tables to a template. That checklist is the most visible thing `/scope` produces
for your team. Confirm the forcing function survives as "consider all 18, emit only what
applies", or tell me it needs to stay itemized in the body.

8.5 **Scope this as a tracked scope?** This is 3 phases of real work in `ai-skills`. It
should probably have a `plans/{N}-skills-relook/` folder with progress tracking — using
the skills to rebuild the skills. Say go and I'll run `/scope` on it properly.
