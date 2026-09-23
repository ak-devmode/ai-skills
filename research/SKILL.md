---
name: research
version: 0.2.0
description: >-
  Cost-tuned deep research in two modes. PANE mode (default, inside herdr): one
  visible Sonnet lane per search angle in a fresh herdr tab, an independent verify
  lane, Opus synthesis in this session — watchable and interruptible. WORKFLOW
  mode: the background deep-research-lean workflow (Scope→Search→Fetch→Verify→
  Synthesize, each phase on a right-sized model, ~70% cheaper than the built-in
  deep-research) for unattended or non-herdr runs. Use when asked to "research",
  "deep research", "research report", "deeply research X", or "/research <topic>".
allowed-tools:
  - Workflow
  - Bash
  - Read
  - Write
---

# Deep research (cost-tuned)

The user wants a multi-source, fact-checked research report. Do NOT answer from
memory and do NOT fan out a bare Agent swarm — run pane mode (§3) or the tuned
workflow (§2).

## 1. Scope before spending

1. Restate the research question in one sentence as you understood it.
2. If it is underspecified (missing budget / region / timeframe / use-case /
   comparison set), ask 2–3 clarifying questions **inline as plain text** (Alex
   prefers text over the structured selector). Fold the answers into the question.
3. **Set the verify cap with the user.** `verifyCap` is required — the number of
   extracted claims that get adversarial verification (Workflow: 3 Haiku votes
   each, the dominant cost; panes: one independent verifier pass each). It is split evenly across the search angles, so
   size it to the question: ~25 for one focused area, ~50 for a multi-area brief
   (~10 per angle). Propose a number with that arithmetic; don't pick silently.
   `angles` is optional (3-8): omit it and the scope agent defaults to 5, going
   higher only when the question names more distinct sub-areas. Pass it
   explicitly when the brief already enumerates its areas — one angle each.
   **Fit the run to the session's web-search budget.** WebSearch is capped per
   session (`CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`, default 200; Alex's is
   set to 500). A run spends roughly `angles + 3 × verifyCap` searches — the
   verify voters dominate — so a cap of 40 costs ~125. Subtract earlier runs in
   the same session; if the next run won't fit, say so and suggest a fresh
   session rather than launching into a silent empty result.
   In pane mode each lane is its own session with its own budget, so this limit
   binds only Workflow mode.
4. **Pick the mode and confirm in one line** — deep research costs real money.
   Default to **panes** (§3) when `HERDR_ENV=1`; offer Workflow (§2) as the
   alternative. Outside herdr, say pane mode is unavailable and offer Workflow
   only. One line: the scoped question + verifyCap + angles + "run in panes, or
   as a background workflow?"

## 2. Workflow mode — run the tuned workflow

Once confirmed, invoke:

```
Workflow({
  name: "deep-research-lean",
  args: {
    question: "<the final scoped question, with clarifications woven in>",
    verifyCap: <the number agreed in §1.3>,
    angles: <optional, 3-8; omit for the default of 5>
  }
})
```

Invoke **by `name`**, not `scriptPath`. The tool does not expand `~`, and it
rejects an absolute `scriptPath` outside the working directory unless that file
was read first this session. The name resolves via the
`~/.claude/workflows/deep-research-lean.js` symlink.

The workflow runs in the background and returns a task notification when done —
do not re-invoke or poll it; relay the report when it lands. It returns
**structured output only and writes no file** — if the user wants the report on
disk, write it yourself from the result, and keep file-path/format instructions
out of `args` (they reach only the agents, which can't honour them).

The result carries `coverage` (verified / extracted per angle) and
`unverified` (claims extracted with a quote but never checked because the cap
was spent). An under-sampled angle is **not** refuted: report its `unverified`
claims as a separately labelled tier, never as findings and never as "nothing
survived". If an angle matters and came back thin, offer a targeted re-run.

Every checked claim lands in one of three tiers. **confirmed** → findings.
**refuted** → needs a stated counter-reason (carried in `reasons`); report as
contradicted. **unconfirmed** → voters could neither corroborate nor
contradict; report as *could not confirm*, never as false. Absence of
corroboration is not refutation — collapsing the two killed a well-documented
WHO guideline 0-3 under the old "default to refuted" verifier.

If the result carries `error` (every searcher empty) or non-empty
`searchErrors`, that is a tool failure — report it as one, never as "no
literature found".

## 3. Pane mode — visible research lanes

One Sonnet session per angle, each in its own pane of a fresh herdr tab, runs
search → fetch → extract for its angle in a single context. A separate **verify
lane** that never saw the sources checks the claims. You (the driver, this
session) scope, supervise, and synthesize. Deterministic steps go through
`~/.claude/skills/research/scripts/lanes.py` (call it `LANES` below); its
docstring lists the commands and exit codes.

### 3.1 Preconditions

- `HERDR_ENV=1`. Otherwise Workflow mode only (§1.4).
- `~/.cache/research-lanes` is a trusted Claude Code folder. `LANES open` checks
  and prints the one-time fix if not. Lanes start there because Claude Code shows
  its folder-trust dialog in any untrusted folder, even under
  `--dangerously-skip-permissions`, and you never answer another agent's dialog.

### 3.2 Scope the angles yourself

Write the angles in-context, following the workflow's scope rules: exactly the
agreed `angles` when given, else 5 by default (3–8, with a stated reason to leave
5). Each angle gets a short kebab-case lane name (`a1-regulatory`, …), a query,
and a one-line rationale. Pick the run folder:
`<your scratchpad>/research/<slug>-r<k>/`, where `k` increments on every
refine-and-rerun — **every run gets a fresh tab**, including reruns.

### 3.3 Open the tab and launch the angle lanes

```bash
LANES open --run-dir "$RUN" --label "research <slug> r<k>" --lanes <a1,...,aN>,verify
```

For each angle, write `$RUN/brief-<lane>.md` from the template below, then
`LANES launch --run-dir "$RUN" --lane <lane>`. Do not launch `verify` yet.

```
# Research lane: <lane>
Research question: <question, clarifications woven in>
Your angle: <label> — <rationale>. Starting query: `<query>`
Run folder: <$RUN, absolute>

Work in this one session. Do not spawn subagents. Write only inside the run folder.
1. Search: WebSearch the query (refine it if the results are poor). Keep the 4-6
   results most relevant to the ORIGINAL question; skip SEO spam and content farms.
   If WebSearch fails or refuses, write {"angle": "<lane>", "error": "<tool message
   verbatim>", "sources": [], "claims": []} to <run>/<lane>.json, print
   LANE-DONE <lane>, and stop.
2. Fetch: WebFetch each kept result (max 4). Rate sourceQuality:
   primary | secondary | blog | forum | unreliable. Note publishDate if shown.
   A failed, paywalled, or irrelevant page yields no claims.
3. Extract 2-5 FALSIFIABLE claims per source that bear on the question. Each is a
   concrete, checkable statement with a direct supporting quote, rated
   central | supporting | tangential.
4. Write <run>/<lane>.json:
   {"angle": "<lane>", "sources": [{"url", "title", "sourceQuality", "publishDate"}],
    "claims": [{"claim", "quote", "importance", "sourceUrl", "sourceQuality"}]}
5. Print exactly: LANE-DONE <lane>. Then stop.
```

### 3.4 Supervise by state

Run `LANES wait --run-dir "$RUN" --lanes <a1,...,aN>` as a **background** Bash
call. It exits on the first state change and prints the events; tell Alex in one
line (`a3 done`, `a2 failed — agent idle with no a2.json`, `a4 stalled 15 min`),
then start it again until `remaining` is empty.

- **done** — the lane's JSON is written.
- **failed** — pane closed, or the agent went idle/blocked without writing its
  file (an Esc interrupt lands here). Never retry on your own; that angle becomes
  missing coverage.
- **stall** — no pane output for 15 minutes. Flag it once; never kill it.

A lane whose JSON carries `error` is a tool failure. Report it as one, never as
"no literature found".

### 3.5 Verify lane

```bash
LANES claims --run-dir "$RUN" --cap <verifyCap> --lanes <a1,...,aN>
```

This ranks claims within each angle and takes them round-robin up to the cap, as
the workflow does. It writes `$RUN/claims.json` with `claims` (each with an `id`),
`unverified` (over the cap), and per-angle `coverage`. Write
`$RUN/brief-verify.md`, then `LANES launch --lane verify` and
`LANES wait --lanes verify`.

```
# Research lane: verify
Research question: <question>
Claims: <run>/claims.json — verify every entry in .claims. You did NOT see these sources.

For each claim, be SKEPTICAL: try to refute it, but judge only on what you find.
1. Does the quote actually support the claim, or is it an overreach or misread?
2. WebSearch for contradicting evidence. Does a credible source dispute or heavily qualify it?
3. Does source quality match the claim's strength? Extraordinary claims need primary sources.
4. Is it outdated? Old claims about fast-moving fields are suspect.
5. Is it a marketing claim, press release, cherry-picked benchmark, or forum speculation?

Verdict, exactly one:
- refuted: a POSITIVE reason. The quote does not say it, a credible source
  contradicts it (name it in counterSource), newer evidence supersedes it, or it
  is a vendor claim stated as independent fact.
- supported: the quote supports it, it is current, and source quality matches its strength.
- unconfirmed: you could neither corroborate nor contradict it.
Failing to find corroboration is unconfirmed, NEVER refuted.

Write <run>/verify.json as {"complete": false, "verdicts": [{"id", "verdict",
"evidence", "confidence": "high|medium|low", "counterSource"}]}, rewriting it after
every 5 claims. After the last claim, write it with "complete": true, print
LANE-DONE verify, and stop.
```

The verdict rules mirror `deep-research-lean.js` at `3bf467b`. One independent
verifier is weaker than the workflow's 3-vote panel; say so in the report's
caveats. The verify step is deliberately separate so the verify-lever work
(ai-skills scope 5) can replace it. If the verify lane fails, its partial
`verify.json` still counts: claims it never reached join the unverified tier.

### 3.6 Synthesize and report

Map verdicts to tiers: supported → **confirmed**, refuted → **refuted**,
unconfirmed → **unconfirmed**. Claims never reached → **unverified**. Then do what
the workflow's synthesis step does:

1. Merge claims that say the same thing, combining their sources.
2. Group confirmed claims into findings that answer the question.
3. Give each finding a confidence: high (primary sources, several agree), medium
   (secondary sources), or low (single source or blog-quality).
4. Write a 3–5 sentence summary.
5. Write caveats. Name failed and under-sampled angles as missing coverage, never
   as "nothing found". Note that verification was a single independent verifier.
6. List 2–4 open questions.

Never build findings from unconfirmed or unverified claims. Never call either one
false.

Write `$RUN/report.md`, give Alex the summary inline plus the path, and offer to
copy it somewhere durable: the scratchpad dies with the session. Offer a targeted
rerun (a new `r<k+1>` tab) for failed or thin angles.

**Leave the tab and every pane open.** Alex closes them by hand.

## 4. Architecture (for reference)

`Scope (Sonnet) → Search (Haiku, default 5 angles) → Fetch (Sonnet, ≤15 sources) →
Verify (Haiku, 3 votes: supported / refuted / unconfirmed; 2 refutes kill, 2 supports confirm) →
Synthesize (Opus, merge dupes, rank by confidence, cite sources)`.

## 5. Tuning the cost/quality dial

Edit the `MODEL_*` constants at the top of
`~/.claude/workflows/deep-research-lean.js`:
`MODEL_SCOPE`, `MODEL_SEARCH`, `MODEL_FETCH`, `MODEL_VERIFY`, `MODEL_SYNTH`
(plus `VOTES_PER_CLAIM`, `MAX_FETCH`; the verify cap is a per-run argument). Only Synthesize
genuinely benefits from Opus; push the rest cheaper for faster/cheaper runs.
