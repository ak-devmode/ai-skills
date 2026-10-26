---
name: review
version: 3.8.0
description: |
  Pre-landing code review with codex as the gate: the opposing model family, headless
  and read-only, reviews an explicit revision range against gstack's review checklist,
  the domain rules per project (WellMed: SATU SEHAT + FHIR, ADR conformance, table
  write-ownership; IRIS: its own invariants, never WellMed's ADRs; PMG; shared: tenant
  isolation, PHI/credential leakage, stack footguns) and the lenses every repo gets —
  fail-open verification, silent failure, local maxima, dirty comments, doc claims.
  Every finding is logged under a stable ID and must be dispositioned (fixed in a commit
  that touches it, rejected with a reason, accepted as a non-blocking process nit, or — past
  a lineage's round 3, non-blocking — deferred to a written TO-DO item). Loops run under a
  standing policy: fix and re-review through round 3, SHIP proceeds to /verify with the
  outcomes recorded by `accept`; the user is asked only on a design decision, a repeat, no
  SHIP by round 3, or an edge-case cascade ([CONVERGENCE] / [CASCADE] signals). When codex cannot run, a Claude pass (gstack's engine + the same rules) is the
  fallback, and the report says so in its header.

  **Lean is the default** (plan 7): one packed bundle — the diff capped at 1,500 lines,
  only this project's rules — read by one Sonnet subagent, with no codex, engine load or
  specialists. That fits a regular Claude seat. `AI_SKILLS_REVIEW_MODE=full` or `--full`
  restores the codex gate above; `--lean` forces lean. Every report header names the mode.

  Use when asked to "review", "review this PR", "review the diff", "pre-landing
  review", "check my diff before merge", or before opening any PR. Also invoked by
  /scope's skill checklist (Review & QA) and by /plan on each commit-producing unit.

  `--kalpa-only` skips the generic checklist; `--engine-only` skips the domain rules.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Agent
---

# /review — Pre-Landing Review, codex as the Gate

The reviewer should not be the author's model family. On the first real run (WellMed
108.6) the Claude checklist pass missed two fail-open bugs that codex's cross-model pass
caught; a spike re-running codex alone on that diff found both again
(`plans/5-verify-lever/artifacts/review-codex-spike-2026-09-26.md`). So codex is the gate,
and the Claude pass is what runs when codex can't.

**Reuse, don't reimplement.** The rules live in files both executors read —
`review/rules/domain.md` (Kalpa/PMG groups) and `review/rules/lenses.md` (every repo) —
plus gstack's `review/checklist.md`. The deterministic steps are `review/scripts/review.py`
and `scripts/codex-exec.py`. This file is the procedure; it never restates a rule.

---

## 1. Resolve Target and Project

1.1 **An explicit revision range, always.** `BASE..HEAD` in the repo being reviewed:
- a `/plan` unit → the base SHA the ledger recorded for that repo
  (`- base: <unit> <repo> <sha>` in the scope's `closeout-prep.md`) `..HEAD`;
- a branch → `$(git merge-base origin/<trunk> HEAD)..HEAD`;
- a PR → its base and head SHAs.

**An empty range is a failure, never a clean review.** On a direct-to-main repo a branch
diff is empty by construction — which is exactly why the range is explicit.
`review.py prepare` exits 3 on an empty range; report it, don't work around it.

1.2 **Project** is detected from the repo path — a worktree's primary checkout
(`review.py` does it): `~/Projects/wellmed/kalpa-iris` → the IRIS groups, never
WellMed's ADR checks · `~/Projects/wellmed/*` → all WellMed groups · `~/Projects/pmg/*`
→ §3.1, §3.5, §3.6, §3.7 · anything else → domain checks `n/a` (never invented).
`rules/domain.md` lists the groups per project.

1.3 **Scope and unit.** When the work belongs to a `/plan` unit, pass `--scope <scope
folder> --unit <N.P>` to `record` so findings are logged to
`artifacts/review-<unit>.jsonl` and tracked for dispositions. Ad-hoc reviews without a unit
print the report and log nothing — say so.

```bash
S=~/Projects/ai-skills/scripts; RV=~/Projects/ai-skills/review/scripts/review.py
REPO=<repo>; RANGE=<BASE>..HEAD
```

1.4 **Mode — before anything else.** `MODE=$($S/review-mode.py [--full|--lean])`, passing
the user's flag through if they gave one. It prints one line, `mode: <lean|full> (<flag|env|
default>)`. Keep it for `record --mode` and the report's first lines. Exit 2 (both flags, or
a bad `AI_SKILLS_REVIEW_MODE`) is a stop: report its message and don't pick a mode yourself.
`full` → §2, and §3 when codex can't run. `lean` → §7, with no codex probe.

---

## 2. The Gate — codex

2.1 **Render.** `$RV prepare --repo $REPO --range $RANGE [--kalpa-only|--engine-only]` →
prints `prompt:`, `schema:`, a `passes:` line, a `range:` line — the range resolved to
full SHAs, which the prompt uses — and an `effort:` line; keep all five, pass that `range:`
to §2.4 and that effort to §2.3.

2.1.1 **Checks, run for the reviewer.** `prepare` also runs the repo's declared checks and
puts each one's command, exit status and the end of its output in the prompt; its last
line is `checks: …`. A repo declares them in `.review-checks` at its root, one
`name | shell command` per line, run from the root (build, vet, lint, tests — whatever
the reviewer would otherwise report it could not run). They run only when the working
tree is the range's head with no tracked change; otherwise the line says `not run — <why>`
and the prompt tells the reviewer so. A failing check does not stop `prepare`: it is
evidence. `--no-checks` skips them; `REVIEW_CHECK_TIMEOUT` (seconds, default 900) bounds
each. A repo with no `.review-checks` gets `checks: none declared` — add the file rather
than read "could not build" in every report.

2.2 **Probe, fresh.** `$S/codex-exec.py probe` — last line `codex <model>` → §2.3;
`none <reason>` → §3. Never reuse an earlier probe, never gstack's (it caches failures).

2.3 **Review.** Bash tool timeout above 900 s:
```bash
$S/codex-exec.py exec --prompt $PROMPT --schema $SCHEMA --out $WORK/answer.json --cd $REPO --timeout 900 --effort $EFFORT
```
The prompt's directory is `$WORK`. Last line `codex <model>` → §2.4 with that exact line as
the reviewer. `none <reason>` → §3 with that reason.

2.4 **Record.** `$RV record --repo $REPO --range <the range: line> --reviewer "<line>" --input
$WORK/answer.json --passes "<passes line>" --mode "$MODE" [--scope $SCOPE --unit $UNIT]`. It assigns
`<unit>-r<n>-NN` IDs in severity order, appends the raw findings, and writes
`artifacts/review-<unit>-r<n>.md` — including **what the review did not cover** (codex's
own `cannot_do` list plus skipped passes). Exit 3 → the answer was malformed and nothing
was recorded: re-run once, then fall back (§3).

2.5 **What codex cannot do** (from the spike, and its own `cannot_do`): no network, no
running services or browser, no write-side tests, no specialist fan-out. Its sandbox is
read-only, so it cannot build, vet, lint or test either — §2.1.1 is how it gets those
results, from the runner. Behaviour
checks belong to `/verify`'s runner rows, not here; this is a diff reviewer.

---

## 3. Fallback — a Claude pass

Runs only when §2.2 or §2.3 returned `none <reason>`. The reviewer line is
`claude-fallback <that reason>`; `record` puts a **DEGRADED** line in the report header and
the index carries `⚠ judge:` until a codex review clears it.

3.1 Read `~/.claude/skills/gstack/review/SKILL.md` and execute it against the range (skip on
`--kalpa-only`), then apply `review/rules/domain.md` (skip on `--engine-only` or a generic
repo) and `review/rules/lenses.md`. That path is the gstack repo root symlink, stable
regardless of which skill owns the bare `/review` name — do not reach for
`~/.claude/skills/review/SKILL.md`, which is this skill.

**Its assets are all under `~/.claude/skills/gstack/review/`** — `checklist.md`,
`greptile-triage.md`, `design-checklist.md`, `specialists/*.md`. If a path in that engine
404s, resolve it there before concluding anything is stale.

> **Why that warning is here.** gstack's `review/SKILL.md` is inconsistent with itself: 8
> of its asset paths use `~/.claude/skills/gstack/review/...`, but 2 — `checklist.md` and
> `greptile-triage.md` — use `~/.claude/skills/review/...`, which only worked while gstack
> owned the bare name. `setup.sh` shims both into `~/.claude/skills/review/` so either path
> resolves; gstack is upstream-tracking and is never edited to fix this.

3.2 **Dispatch the specialists — invoking this skill is the authorization.** This skill
declares `Agent`, and gstack's engine has specialist passes (`specialists/*.md`: security,
performance, testing, red-team, maintainability, data-migration, api-contract). If dispatch
is genuinely unavailable, add it to `cannot_do` so the report's header-adjacent coverage
section shows it — a single-context pass is materially narrower than a fan-out.

3.3 **Render decisions as numbered inline options.** `AskUserQuestion` is banned in
ai-skills-authored skills (`ai-skills/CLAUDE.md` §3.2), including inside the engine.

3.4 **Verify the engine's telemetry actually wrote — exit 0 is not proof.**
`gstack-review-log` derives `SLUG` and `BRANCH` from the **current working directory**.
Read back with `~/.claude/skills/gstack/bin/gstack-review-read`; `NO_REVIEWS` after a log
call means it wrote to a path derived from the wrong cwd. Re-run the log from **inside the
repo being reviewed** — `cd` is correct here, the documented exception to the never-`cd`
rule. (The first real run hit exactly this and moved on because the exit code was clean.)

3.5 **Record through the same writer.** Write the fallback's findings as JSON matching
`review/schemas/review-output.schema.json` and run §2.4 with the `claude-fallback …`
reviewer line. The fallback never gets its own log format.

---

## 4. Report

4.1 Lead with the mode line, the reviewer line and the passes; a fallback or lean review
says **DEGRADED** in the first lines, never only at the bottom. Then `BLOCKING` → `SHOULD FIX` → `NOTE`, each finding with
its ID and `file:line`, then checked-clear, not-applicable, the verdict, and what was not
covered. `record` renders exactly this; present it, don't re-rank it.

4.2 **`Not applicable` is not `clear`.** A group with no surface in the range and a group
verified clean are different results; collapsing them overstates coverage.

4.3 Log the report path in the scope's `progress.md` Artifacts section.

---

## 5. Dispositions — every finding, recorded

Each finding ID gets exactly one current disposition, through the script only:

```bash
$RV dispose --scope $SCOPE --unit $UNIT --finding <ID> --fixed <sha>          # the fixing commit
$RV dispose --scope $SCOPE --unit $UNIT --finding <ID> --fixed <sha> --fixed-in <repo path>   # fixed in another repo
$RV dispose --scope $SCOPE --unit $UNIT --finding <ID> --rejected "<why the finding is wrong>"
$RV dispose --scope $SCOPE --unit $UNIT --finding <ID> --accepted "<the process nit, noted>"   # non-blocking only, §5.1
$RV dispose --scope $SCOPE --unit $UNIT --finding <ID> --reframed "<what changed>" --commit <sha> --by judge|user   # §5.1
```

**A fix in another repo** — at the source the finding traces to, or a hand-back file in a
docs repo — is `--fixed-in <repo path>`: a repo under `~/Projects` (`VERIFY_PROJECTS`), the
SHA must exist there, and the record carries that repo. It is the finding's own repo only
by git identity (its primary checkout), never by a matching name. A fix there is always
off the anchor (below), even when it touches a file of the same path, and is re-reviewed in
the repo that holds it, by a review recorded after the finding's.

**One rule for a fix.** `--fixed` is accepted on its own only when that commit touches the
finding's file in the finding's own repo, after the head its review saw. Anything else — a
test-only commit for a missing-coverage finding, a fix in another file, a fix in another
repo — needs `--off-anchor "<how this commit fixes it>"`; the record carries `via`
(`anchor | off-anchor`) and the reason, `/verify` audits it, and the gate wants every
off-anchor fix, at any severity, inside a later review's range. No guessing which tests or
which directories count: each guess was a new way through (review r1/r2 on this tool).
**The reviewed code is never its own fix:** the commit that introduced a finding touches its
file, so `dispose` refuses an ancestor of the head that review saw (in another repo, a commit
older than the review), with or without `--off-anchor`, and the gate blocks one — and blocks
a fix not reachable from HEAD in the repo holding it, until its branch merges.
`--rejected` is refused without a reason — never use it to record a fix the tool refused.
The latest disposition decides, so a fix logged as a rejection is corrected by disposing it
again: `$RV misfiled --scope $SCOPE --unit $UNIT` lists every rejection whose reason says
it was fixed (`fixed` or `resolved`, any case) and prints the `dispose` line for each SHA in
an affirmative claim's clause that resolves (here or in a repo beside it) — a negated `not
fixed` gets no line, nor a SHA cited for anything else;
it writes nothing — fill each `--off-anchor` reason yourself, then re-`accept`. When every ID has one, the outcomes are recorded with
`$RV accept --scope $SCOPE --unit $UNIT --by "<name>"` (`verify-contracts.md` §6.4) — by
the session under the §5.1 standing policy on a SHIP, otherwise on the user's yes. `verdict-gate.py` refuses Done while any ID lacks one, and `/verify`
audits whether each rejection was *right*. Nothing silently dismissed, nothing silently
dropped.

**Scaffolding never blocks** (`rules/lenses.md` §7). A finding whose only target is a check,
a finish-table row, progress/plan notes or procedure prose the session added is capped at
`should-fix` by `record` (shown as "scaffolding, capped from blocking"), and the gate never
wants it re-reviewed. Shipped code is still held to `blocking`.

5.1 **The loop — standing policy, and where it stops.** Every repo, every unit. Review
loops run without a per-round check-in (Alex's standing approval):

- **Rounds 1–3:** fix every finding you do not disagree with, dispose it, review the fix
  commits again, keep going. Reject, with the reason, what you do disagree with.
- **SHIP proceeds.** A round whose verdict is `SHIP`, once every finding is dispositioned
  and `verdict-gate.py` wants nothing re-reviewed (`rereview:` — an off-anchor fix still
  needs its round), goes straight to `/verify`. Record the outcomes yourself:
  `review.py accept --by "<owner> (standing policy)"`. `accept` prints every rejection and
  every accepted nit; put both in the unit's closing summary.
- **Process nits are noted, never another round.** A finding that is only process — a
  comment that doesn't match, a stale table, a timestamp more than an hour old, doc wording —
  is `dispose --accepted "<the nit>"`. It counts as dispositioned, the gate never wants it
  re-reviewed, `/verify` never audits it as a rejection, and reports list it apart.
  `dispose` refuses it on a `blocking` finding.

**Stop and bring it to the user only for:**
1. **A design decision** — a finding against an accepted ADR (§6.4), a contract with two
   readings, a trade-off that is the user's.
2. **The same thing blocking across rounds** — the same defect back after its fix, or a
   file drawing findings in each of its lineage's last three rounds (`[CONVERGENCE] <file>`):
   a design that is wrong, not a patch that is incomplete. Raise it as one design finding:
   replace it, narrow what it promises, or cut it. Findings that argue opposite sides
   (fixing one reopens another) are this too: ask which side the user wants.
3. **No SHIP by round 3** — `record` prints `[CONVERGENCE] <repo> round 3 of 3: STOP`. Ask,
   inline: `1.` another round, or `2.` stop here. Show the open `rereview:` blocks with the
   question. On "stop", `accept` ends the loop: the gate lets it stand in for the re-review
   of fixes disposed before it (`verify-contracts.md` §5.2.1). Ask again before each further
   round.
4. **An edge-case cascade** — a fix for one edge case raises another, sequential or net
   new. `record` prints `[CASCADE] <file>` when a new finding lands on a line an earlier
   finding's fix commit in the unit last changed. That is a local maximum: a better way to
   think about the original solution exists. Stop fixing and bring the user a proposed
   reframe. You may propose a reframe at any time, cascade or not.

**A reframe that is taken** — accepted by the fresh judge (`--by judge`) or by the user at
a stop (`--by user`) — is recorded on each finding it replaced: `dispose --reframed "<what
changed>" --commit <the replacing commit>`, at any round and any severity. Never `--rejected`
(the finding was not wrong) and never a stale `--fixed` (a reverted fix: `dispose` warns when
a `--fixed` commit has been reverted on HEAD). The gate counts it like a deferral, `/verify`
never audits it as a rejection, and the gate wants the replacing commit inside a later
review's range: review it as its own range (old head..replacing commit), which starts a new
lineage at round 1.

**Rounds count per review lineage, not per repo.** IDs number every review of the unit
(`<unit>-r<n>`); `record` prints `round: <k> of <repo>` for this review's lineage. A review
whose range shares a commit with an earlier one continues that review's count, and so does a
fix re-review: a range starting at an earlier review's head that contains a commit a `fixed`
disposition named for a finding of that lineage — so dispose the fixes before re-reviewing
them. Starting at a review's head alone is not enough: a lane's next unit starts there too
(WellMed 171.2 counted new code as round 4–5). `record --continues <review id>` names the
parent outright when no disposition ties the range to it. Anything else starts at round 1
(when git cannot tell, the repo's highest round continues, with a `[WARN]`). A repo is its
primary checkout, worktrees included. **A lineage keeps the rules it started under:** every
`review` record carries `rules_version`, and the rules here that changed in scope 10 (the
findings budget, the `reopens` chain stop, the effort trial) apply only to lineages whose root
was recorded at version 2 or later (`verify-contracts.md` §6.0).

**Round cap.** Past round 3 of a lineage (only on the user's "another round"), only
`blocking` findings are fixed in the loop. `should-fix` and `note` go to the project's
`TO-DO.md` and are recorded `dispose --deferred "<TO-DO item>"` — never `--rejected`,
because a deferral is not a claim that the finding is wrong. Write the item first, carrying
the finding ID as its leading marker — `- [ ] [review <ID>] <what is left>`; the marker is
the link, and an ID mentioned elsewhere on a line or a marker with no text is not. `dispose`
refuses a deferral with no open item naming the ID, one from round 3 or earlier of its
lineage, and any blocking finding.

**Verification scaffolding is review surface.** A checker, generator or script a session
adds to verify its own deliverable is code, and every round reviews it. On a docs scope,
bias against adding one: prefer a `judge` row or a one-line `grep`/`test` row over a new
script, and when a finding lands on scaffolding the session added, ask whether the
scaffolding should exist before patching it.

Why: scope 5.3 ran twelve rounds, eight of them patching one heuristic shell scanner,
ending with two findings on opposite sides — the local-maxima failure this skill exists
to catch, inside the skill. kalpa-iris 1.1 (a docs scope) ran five codex rounds and four
verify runs; round 1 found the real defects and every later round found holes in checkers
the session had added.

> **Why a standing policy (Alex, 2026-10-18, WellMed scope 171).** A per-round hard stop and
> a per-unit outcome checkpoint put the user in every loop, mostly to say "yes, continue";
> 171.2 also hit the round-3 cap on a first review of new code, because rounds counted per
> repo and two lanes shared one. The user is now asked only where their judgment changes
> the outcome: design, a repeat, no SHIP, a cascade. Process nits stopped earning rounds.

---

## 6. Behaviors

6.1 **Never commit, never push, never open the PR.** This skill reports. Landing is `git`,
by hand, after the user reads the verdict.

6.2 **Never fix in-band by default.** On an explicit "fix them" (or `--fix`), apply fixes in
their own commits, then `dispose --fixed` each.

6.3 **Cite `file:line` or don't raise it.** `record` rejects a finding without one.

6.4 **A finding against an accepted ADR is a finding about the ADR.** Say which ADR and route
it as a design decision.

6.5 **Numbered inline questions only.** Never `AskUserQuestion`.

6.6 **Report the cost when it's high.** codex takes ~2–5 minutes on a mid-size range; the
fallback loads a large engine. For a quick look, say that `--kalpa-only` exists. Lean is the
cheap path; when a lean report lists uncovered files that matter, say that `--full` exists.

---

## 7. Lean — one Sonnet pass (the default)

Runs when §1.4 printed `mode: lean (…)`. The rules are the same files; what changes is
who reads them and how much. The reviewer gets one packed file and no tools.

7.1 **Render the bundle.** `$RV prepare --repo $REPO --range $RANGE --lean [--kalpa-only|--engine-only]`
prints `prompt:` (the bundle), `schema:`, `passes:`, `range:` and an `uncovered:` count;
keep them all. The bundle inlines the commits, the repo's CLAUDE.md and ARCHITECTURE.md at
the range's head (≤ 24 KB each), gstack's checklist, only this project's `domain.md`
sections, the lenses, and the diff. The diff is capped at 1,500 changed lines. Files are
inlined whole while they fit, and a file that doesn't fit is listed as not covered, never
cut. Code adjacent to the diff is always listed as not covered.

7.2 **One Sonnet subagent — dispatch is pre-authorized** (this skill declares `Agent`).
Spawn it with `model: sonnet`. Its entire prompt: "Read `<prompt>` and follow it exactly.
Write only the JSON object it asks for, matching `<schema>`, to `<WORK>/answer.json`. Read
no other file, run no command, modify nothing else." Nothing else — no narrative, no
summary of the change.

7.3 **Record through the same writer.** `$RV record --repo $REPO --range <the range: line>
--reviewer "claude-lean $MODE" --input <WORK>/answer.json --passes "<passes line>" --mode
"$MODE" [--scope $SCOPE --unit $UNIT]`. For a `claude-lean` reviewer, `record` recomputes
the not-covered list from the range itself, so nothing the caller passes can drop it. Exit 3 (a malformed answer) → re-run the subagent once, then stop and report.
Never escalate to `full` on your own: that is the user's `--full`.

7.4 **What lean does not do,** and says so in the report: no codex, no gstack engine
load, no specialist fan-out (§3.2), no reads outside the bundle, nothing past the cap.
`record` puts that in the DEGRADED header and the uncovered files under "What this review
did not cover". The gate marks the unit `⚠ judge: review claude-lean …` until a codex
review covers it.

7.5 **Everything after recording is unchanged.** §4 reporting, §5 dispositions,
`accept`, and the §5.1 loop (standing policy, stop on no SHIP by round 3) apply as written. A re-review
round is another lean pass on its range. §3.4's telemetry check doesn't apply: lean never
runs gstack's engine.
