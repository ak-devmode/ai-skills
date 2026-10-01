---
name: review
version: 3.4.0
description: |
  Pre-landing code review with codex as the gate: the opposing model family, headless
  and read-only, reviews an explicit revision range against gstack's review checklist,
  the domain rules per project (WellMed: SATU SEHAT + FHIR, ADR conformance, table
  write-ownership; IRIS: its own invariants, never WellMed's ADRs; PMG; shared: tenant
  isolation, PHI/credential leakage, stack footguns) and the lenses every repo gets —
  fail-open verification, silent failure, local maxima, dirty comments, doc claims.
  Every finding is logged under a stable ID and must be dispositioned (fixed in a commit
  that touches it, rejected with a reason, or — past a repo's round 3, non-blocking — deferred to
  a written TO-DO item); the loop stops on [CONVERGENCE] signals, and the user's yes to
  the outcomes is recorded with `accept` before the unit can be marked Done. When codex cannot run, a Claude pass (gstack's engine + the same rules) is the
  fallback, and the report says so in its header.

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

---

## 2. The Gate — codex

2.1 **Render.** `$RV prepare --repo $REPO --range $RANGE [--kalpa-only|--engine-only]` →
prints `prompt:`, `schema:`, a `passes:` line, a `range:` line — the range resolved to
full SHAs, which the prompt uses — and an `effort:` line; keep all five, pass that `range:`
to §2.4 and that effort to §2.3.

2.2 **Probe, fresh.** `$S/codex-exec.py probe` — last line `codex <model>` → §2.3;
`none <reason>` → §3. Never reuse an earlier probe, never gstack's (it caches failures).

2.3 **Review.** Bash tool timeout above 900 s:
```bash
$S/codex-exec.py exec --prompt $PROMPT --schema $SCHEMA --out $WORK/answer.json --cd $REPO --timeout 900 --effort $EFFORT
```
The prompt's directory is `$WORK`. Last line `codex <model>` → §2.4 with that exact line as
the reviewer. `none <reason>` → §3 with that reason.

2.4 **Record.** `$RV record --repo $REPO --range <the range: line> --reviewer "<line>" --input
$WORK/answer.json --passes "<passes line>" [--scope $SCOPE --unit $UNIT]`. It assigns
`<unit>-r<n>-NN` IDs in severity order, appends the raw findings, and writes
`artifacts/review-<unit>-r<n>.md` — including **what the review did not cover** (codex's
own `cannot_do` list plus skipped passes). Exit 3 → the answer was malformed and nothing
was recorded: re-run once, then fall back (§3).

2.5 **What codex cannot do** (from the spike, and its own `cannot_do`): no network, no
running services or browser, no write-side tests, no specialist fan-out. Behaviour
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

4.1 Lead with the reviewer line and the passes; a fallback says **DEGRADED** in the first
lines, never only at the bottom. Then `BLOCKING` → `SHOULD FIX` → `NOTE`, each finding with
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
```

**A fix in another repo** — at the source the finding traces to, or a hand-back file in a
docs repo — is `--fixed-in <repo path>`: the SHA must exist there, and the record carries
that repo. The finding's file reaches into that repo only when it is absolute under it or
leads with its directory name (`kalpa-docs/plans/...`); a bare relative path never matches
a same-named file elsewhere (bpjs's `go.mod` is not gateway-go's), so a source fix
normally also needs `--off-anchor`. A blocking finding's fix is re-reviewed in the repo
that holds it.

`--fixed` is accepted when that commit touches the finding's file, or a test file in the
same directory as it — a missing-coverage finding is fixed by a test-only commit. Any other
commit is refused unless `--off-anchor "<how this commit fixes it>"` says why; the record
carries `via` (`anchor | test | off-anchor`) and the reason, so `/verify` can audit it.
`--rejected` is refused without a reason — never use it to record a fix the tool refused.
The latest disposition decides, so a fix logged as a rejection is corrected by disposing it
again: `$RV misfiled --scope $SCOPE --unit $UNIT` lists every rejection whose reason says
`FIXED` and prints the `dispose` line for each SHA it resolves (here or in a repo beside it);
it writes nothing — fill each `--off-anchor` reason yourself, then re-`accept`. When every ID has one, the user's yes is recorded with
`$RV accept --scope $SCOPE --unit $UNIT --by "<name>"` (`verify-contracts.md` §6.4) —
never on their behalf. `verdict-gate.py` refuses Done while any ID lacks one, and `/verify`
audits whether each rejection was *right*. Nothing silently dismissed, nothing silently
dropped.

5.1 **Convergence — a review loop must end.** Every repo, every unit. `record` prints a
`[CONVERGENCE]` line when either trips; act on it, don't re-run past it.

**Rounds count per repo.** Review IDs number every review of the unit (`<unit>-r<n>`),
but each rule below counts the reviews of *that repo* within the unit — `record` prints
`round: <k> of <repo>`. A unit spanning 13 repos (149.2) otherwise hit the cap on a lane's
first review.

- **Round cap.** Past round 3 of one repo in a unit, only `blocking` findings are fixed in the loop.
  `should-fix` and `note` go to the project's `TO-DO.md` and are recorded
  `dispose --deferred "<TO-DO item>"` — never `--rejected`, because a deferral is not a
  claim that the finding is wrong. Write the item to `TO-DO.md` first, carrying the finding
  ID as the item's leading marker — `- [ ] [review <ID>] <what is left>`; the marker is
  the link, and an ID mentioned elsewhere on a line or a marker with no text is not. `dispose` refuses a deferral
  with no open item naming the ID, one from its repo's round 3 or earlier, and any blocking finding.
- **Same place, three rounds.** A file drawing findings in each of the repo's last three rounds
  is a design that is wrong, not a patch that is incomplete. Stop fixing it and raise it to
  the user as one design finding: replace it, narrow what it promises, or cut it.
- **Findings that argue opposite sides** (fixing one reopens another) mean the contract is
  ambiguous. Stop and ask which side the user wants; don't pick one and reject the other.

Why: scope 5.3 ran twelve rounds, eight of them patching one heuristic shell scanner,
ending with two findings on opposite sides — the local-maxima failure this skill exists
to catch, inside the skill. Review outcomes are a human checkpoint (`/plan` §6.8).

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
fallback loads a large engine. For a quick look, say that `--kalpa-only` exists.
