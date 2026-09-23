export const meta = {
  name: 'deep-research-lean',
  description: 'Cost-tuned deep research harness — same fan-out/verify/synthesize architecture as the built-in deep-research, but each phase runs on the right-sized model (grunt work on Haiku/Sonnet, synthesis on Opus). ~70% cheaper per run.',
  whenToUse: 'When the user wants a deep, multi-source, fact-checked research report on any topic. BEFORE invoking, check if the question is specific enough to research directly — if underspecified (e.g., "what car to buy" without budget/use-case/region), ask 2-3 clarifying questions to narrow scope. Then pass the refined question as args, weaving the answers in.',
  phases: [{"title":"Scope","detail":"Decompose question (from args) into search angles (default 5, 3-8) · Sonnet"},{"title":"Search","detail":"One parallel WebSearch agent per angle · Haiku"},{"title":"Fetch","detail":"URL-dedup, fetch top 15 sources, extract falsifiable claims · Sonnet"},{"title":"Verify","detail":"3-vote adversarial verification per claim (need 2/3 refutes to kill) · Haiku"},{"title":"Synthesize","detail":"Merge semantic dupes, rank by confidence, cite sources · Opus"}],
}

// deep-research-lean: Scope → pipeline(Search → URL-dedup → Fetch+Extract) → 3-vote Verify → Synthesize
//
// Faithful copy of the BUILT-IN `deep-research` workflow (compiled into the Claude Code
// binary), with one change: per-phase model overrides. The built-in sets no `model:` on any
// agent() call, so every one of its ~95 sub-agents inherits the session model (Opus) — that's
// what makes a run expensive. ~77% of those calls are the single-claim adversarial verify votes,
// the most mechanical task in the pipeline. Here we right-size each phase:
//
//   Scope     → Sonnet  (1 call · sets the run's direction; cheap to keep capable)
//   Search    → Haiku   (~5 calls · run a query, rank 4-6 URLs)
//   Fetch     → Sonnet  (≤15 calls · WebFetch a page, pull 2-5 quoted claims; Sonnet for quote fidelity)
//   Verify    → Haiku   (3 × verifyCap calls · ONE claim + ONE quote, skeptic web-check, supported/refuted/unconfirmed)
//   Synthesize→ Opus    (1 call · merge dupes, group findings, score confidence, write the report)
//
// Tune the dial below. The only step that benefits from Opus-grade reasoning is Synthesize;
// Verify stays a 3-independent-voter panel, just with Haiku voters, so it still kills bad claims.
//
// Invoked as Workflow({name: 'deep-research-lean', args: {question: '<question>', verifyCap: <n>}}).

// ─── Model tiering (edit to taste) ───
const MODEL_SCOPE  = "sonnet"
const MODEL_SEARCH = "haiku"
const MODEL_FETCH  = "sonnet"
const MODEL_VERIFY = "haiku"
const MODEL_SYNTH  = "opus"

const VOTES_PER_CLAIM = 3
const REFUTATIONS_REQUIRED = 2
const MAX_FETCH = 15
// MAX_VERIFY_CLAIMS is a required run argument (args.verifyCap), not a constant: a fixed
// global cap let the first angles consume every verify slot and starve the rest.

// ─── Schemas ───
const SCOPE_SCHEMA = {
  type: "object", required: ["question", "angles", "summary"],
  properties: {
    question: { type: "string" },
    summary: { type: "string" },
    angles: { type: "array", minItems: 3, maxItems: 8, items: {
      type: "object", required: ["label", "query"],
      properties: {
        label: { type: "string" },
        query: { type: "string" },
        rationale: { type: "string" },
      },
    }},
  },
}
const SEARCH_SCHEMA = {
  type: "object", required: ["results"],
  properties: {
    error: { type: "string" },
    results: { type: "array", maxItems: 6, items: {
      type: "object", required: ["url", "title", "relevance"],
      properties: {
        url: { type: "string" },
        title: { type: "string" },
        snippet: { type: "string" },
        relevance: { enum: ["high", "medium", "low"] },
      },
    }},
  },
}
const EXTRACT_SCHEMA = {
  type: "object", required: ["claims", "sourceQuality"],
  properties: {
    sourceQuality: { enum: ["primary", "secondary", "blog", "forum", "unreliable"] },
    publishDate: { type: "string" },
    claims: { type: "array", maxItems: 5, items: {
      type: "object", required: ["claim", "quote", "importance"],
      properties: {
        claim: { type: "string" },
        quote: { type: "string" },
        importance: { enum: ["central", "supporting", "tangential"] },
      },
    }},
  },
}
// Three-way verdict. The old boolean with "default to refuted if uncertain" killed true claims
// the voter merely couldn't corroborate (WHO's 2021 CAD-for-TB guidance went 0-3). Absence of
// evidence is now its own outcome, reported as an unconfirmed tier rather than as refuted.
const VERDICT_SCHEMA = {
  type: "object", required: ["verdict", "evidence", "confidence"],
  properties: {
    verdict: { enum: ["supported", "refuted", "unconfirmed"] },
    evidence: { type: "string" },
    confidence: { enum: ["high", "medium", "low"] },
    counterSource: { type: "string" },
  },
}
const REPORT_SCHEMA = {
  type: "object", required: ["summary", "findings", "caveats"],
  properties: {
    summary: { type: "string" },
    findings: { type: "array", items: {
      type: "object", required: ["claim", "confidence", "sources", "evidence"],
      properties: {
        claim: { type: "string" },
        confidence: { enum: ["high", "medium", "low"] },
        sources: { type: "array", items: { type: "string" } },
        evidence: { type: "string" },
        vote: { type: "string" },
      },
    }},
    caveats: { type: "string" },
    openQuestions: { type: "array", items: { type: "string" } },
  },
}

// ─── Phase 0: Scope — decompose question into search angles ───
phase("Scope")
// args = { question: string, verifyCap: number }. verifyCap is required and is split evenly
// across search angles (round-robin), so every angle gets verified claims.
const USAGE = "Pass args as an object: Workflow({name: 'deep-research-lean', args: {question: '<question>', verifyCap: <claims to verify, e.g. 25-50>, angles?: <3-8>}})."
const QUESTION = (args && typeof args.question === "string" && args.question.trim()) || ""
const MAX_VERIFY_CLAIMS = args && Number.isInteger(args.verifyCap) && args.verifyCap > 0 ? args.verifyCap : 0
if (!QUESTION) {
  return { error: "No research question provided. " + USAGE }
}
// angles is optional. Given: used exactly. Omitted: scope agent chooses, defaulting to 5.
const ANGLES = args && Number.isInteger(args.angles) ? args.angles : 0
if (ANGLES && (ANGLES < 3 || ANGLES > 8)) {
  return { error: "angles must be an integer 3-8 (or omitted to let scope choose, default 5). " + USAGE }
}
const ANGLE_RULE = ANGLES
  ? "Generate exactly " + ANGLES + " distinct web search queries"
  : "Generate 5 distinct web search queries by default. Use fewer (min 3) only if the question is genuinely narrow, or more (max 8) only if it names more than 5 distinct sub-areas that each need their own search; state the reason in the summary"
if (!MAX_VERIFY_CLAIMS) {
  return { error: "verifyCap is required (positive integer); cost scales ~" + VOTES_PER_CLAIM + " agent calls per claim. " + USAGE }
}
const scope = await agent(
  "Decompose this research question into complementary search angles.\n\n" +
  "## Question\n" + QUESTION + "\n\n" +
  "## Task\n" +
  ANGLE_RULE + " that together cover the question from different angles. Pick angles that suit the question's domain. Examples:\n" +
  "- broad/primary  · academic/technical  · recent news  · contrarian/skeptical  · practitioner/implementation\n" +
  "- For medical: anatomy · common causes · serious differentials · authoritative refs · red flags\n" +
  "- For tech: state-of-art · benchmarks · limitations · industry adoption · cost/tradeoffs\n\n" +
  "Make queries specific enough to surface high-signal results. Avoid redundancy.\n" +
  "Return: the question (verbatim or lightly normalized), a 1-2 sentence decomposition strategy, and the angles.\n\nStructured output only.",
  { label: "scope", schema: SCOPE_SCHEMA, model: MODEL_SCOPE }
)
if (!scope) {
  return { error: "Scope agent returned no result — cannot decompose the research question." }
}
// The prompt asks for exactly ANGLES, but a prompt is not enforcement (a 3-angle request came
// back with 5) — trim here so the caller's number is what actually runs.
if (ANGLES && scope.angles.length > ANGLES) scope.angles = scope.angles.slice(0, ANGLES)
log("Q: " + QUESTION.slice(0, 80) + (QUESTION.length > 80 ? "…" : ""))
log("Decomposed into " + scope.angles.length + " angles: " + scope.angles.map(a => a.label).join(", "))

// ─── Dedup state — accumulates across searchers as they complete ───
const normURL = u => {
  try {
    const p = new URL(u)
    return (p.hostname.replace(/^www\./, "") + p.pathname.replace(/\/$/, "")).toLowerCase()
  } catch { return u.toLowerCase() }
}
const seen = new Map()
const dupes = []
const budgetDropped = []
const searchErrors = []
const relRank = { high: 0, medium: 1, low: 2 }
let fetchSlots = MAX_FETCH

// ─── Prompts ───
const SEARCH_PROMPT = (angle) =>
  "## Web Searcher: " + angle.label + "\n\n" +
  "Research question: \"" + QUESTION + "\"\n\n" +
  "Your angle: **" + angle.label + "** — " + (angle.rationale || "") + "\n" +
  "Search query: `" + angle.query + "`\n\n" +
  "## Task\nUse WebSearch with the query above (or a refined version). Return the top 4-6 most relevant results.\n" +
  "Rank by relevance to the ORIGINAL question, not just the search query. Skip obvious SEO spam/content farms.\n" +
  "Include a short snippet capturing why each result is relevant.\n" +
  "If WebSearch itself fails or refuses (e.g. a session search budget is exhausted), return results: [] and put the tool's message verbatim in `error`.\n\nStructured output only."

const FETCH_PROMPT = (source, angle) =>
  "## Source Extractor\n\n" +
  "Research question: \"" + QUESTION + "\"\n\n" +
  "Fetch and extract key claims from this source:\n" +
  "**URL:** " + source.url + "\n**Title:** " + source.title + "\n**Found via:** " + angle + " search\n\n" +
  "## Task\n1. Use WebFetch to retrieve the page content.\n" +
  "2. Assess source quality: primary research/institution? secondary reporting? blog/opinion? forum? unreliable?\n" +
  "3. Extract 2-5 FALSIFIABLE claims that bear on the research question. Each claim must:\n" +
  "   - be a concrete, checkable statement (not vague generalities)\n" +
  "   - include a direct quote from the source as support\n" +
  "   - be rated central/supporting/tangential to the research question\n" +
  "4. Note publish date if available.\n\n" +
  "If the fetch fails or the page is irrelevant/paywalled, return claims: [] and sourceQuality: \"unreliable\".\n\nStructured output only."

const VERIFY_PROMPT = (claim, v) =>
  "## Adversarial Claim Verifier (voter " + (v + 1) + "/" + VOTES_PER_CLAIM + ")\n\n" +
  "Be SKEPTICAL: try to refute this claim, but judge only on what you actually find. ≥" + REFUTATIONS_REQUIRED + "/" + VOTES_PER_CLAIM + " refutations kill it; ≥" + REFUTATIONS_REQUIRED + " supports confirm it; anything else is reported as unconfirmed.\n\n" +
  "## Research question\n" + QUESTION + "\n\n" +
  "## Claim under review\n\"" + claim.claim + "\"\n\n" +
  "**Source:** " + claim.sourceUrl + " (" + claim.sourceQuality + ")\n" +
  "**Supporting quote:** \"" + claim.quote + "\"\n\n" +
  "## Checklist\n" +
  "1. Is the claim actually supported by the quote, or is it an overreach/misread?\n" +
  "2. WebSearch for contradicting evidence — does any credible source dispute or heavily qualify this?\n" +
  "3. Is the source quality sufficient for the claim's strength? (extraordinary claims need primary sources)\n" +
  "4. Is the claim outdated? (check dates — old claims about fast-moving fields are suspect)\n" +
  "5. Is this a marketing claim / press release / cherry-picked benchmark / forum speculation?\n\n" +
  "## Verdict — pick exactly one\n" +
  "**refuted** — you have a POSITIVE reason: the quote does not say what the claim says / a credible source contradicts it (name it in counterSource) / it is superseded by newer evidence / it is a vendor or marketing claim stated as independent fact.\n" +
  "**supported** — the quote supports the claim, it is current, and source quality matches its strength (a primary source stating its own result counts; independent corroboration strengthens it).\n" +
  "**unconfirmed** — you could neither corroborate nor contradict it: search found nothing, the source was unreachable or paywalled, or the evidence is mixed.\n" +
  "Failing to find corroboration is **unconfirmed, never refuted**. Refuted requires a specific reason you can state.\n\nStructured output only. Evidence MUST be specific."

// ─── Pipeline: search → dedup → fetch+extract (no barrier) ───
const searchResults = await pipeline(
  scope.angles,

  angle => agent(SEARCH_PROMPT(angle), {
    label: "search:" + angle.label, phase: "Search", schema: SEARCH_SCHEMA, model: MODEL_SEARCH
  }).then(r => {
    if (!r) return null
    log(angle.label + ": " + r.results.length + " results")
    if (r.error) searchErrors.push(angle.label + ": " + r.error)
    return { angle: angle.label, results: r.results }
  }),

  searchResult => {
    const sorted = [...searchResult.results].sort((a, b) => relRank[a.relevance] - relRank[b.relevance])
    const novel = sorted.filter(r => {
      const key = normURL(r.url)
      if (seen.has(key)) {
        dupes.push({ ...r, angle: searchResult.angle, dupOf: seen.get(key) })
        return false
      }
      if (fetchSlots <= 0 && relRank[r.relevance] >= 1) {
        budgetDropped.push({ ...r, angle: searchResult.angle })
        return false
      }
      seen.set(key, { angle: searchResult.angle, title: r.title })
      fetchSlots--
      return true
    })
    if (novel.length < searchResult.results.length) {
      log(searchResult.angle + ": " + novel.length + " novel (" + (searchResult.results.length - novel.length) + " filtered)")
    }
    return parallel(
      novel.map(source => () => {
        let host = "unknown"
        try { host = new URL(source.url).hostname.replace(/^www\./, "") } catch {}
        return agent(FETCH_PROMPT(source, searchResult.angle), {
          label: "fetch:" + host,
          phase: "Fetch",
          schema: EXTRACT_SCHEMA,
          model: MODEL_FETCH,
        }).then(ext => {
          // User-skip → null; drop it (filtered by searchResults.flat().filter(Boolean))
          // rather than throwing into .catch() and mislabeling it "unreliable".
          if (!ext) return null
          return {
            url: source.url, title: source.title, angle: searchResult.angle,
            sourceQuality: ext.sourceQuality, publishDate: ext.publishDate,
            claims: ext.claims.map(c => ({ ...c, sourceUrl: source.url, sourceQuality: ext.sourceQuality, angle: searchResult.angle })),
          }
        }).catch(e => {
          log("fetch failed: " + source.url + " — " + (e.message || e))
          return { url: source.url, title: source.title, angle: searchResult.angle, sourceQuality: "unreliable", claims: [] }
        })
      })
    )
  }
)

const allSources = searchResults.flat().filter(Boolean)
if (seen.size === 0) {
  // Every searcher came back empty: a tool failure, not a research result. Most often the
  // per-session WebSearch budget (CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION, default 200).
  return {
    error: "Search phase returned no results for any angle — treat as a tool failure, not an empty literature. " +
      (searchErrors.length ? "Searcher errors: " + searchErrors.join(" | ") : "No searcher reported an error; likely cause is the session WebSearch budget.") +
      " Fix: start a fresh session or raise CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION, then re-run.",
    stats: { angles: scope.angles.length, sources: 0 },
  }
}
if (searchErrors.length) log("Searcher errors: " + searchErrors.join(" | "))
const allClaims = allSources.flatMap(s => s.claims)
const impRank = { central: 0, supporting: 1, tangential: 2 }
const qualRank = { primary: 0, secondary: 1, blog: 2, forum: 3, unreliable: 4 }

// Rank within each angle, then take round-robin across angles until the cap is spent,
// so an angle with many strong claims cannot starve the others.
const claimRank = (a, b) => (impRank[a.importance] - impRank[b.importance]) || (qualRank[a.sourceQuality] - qualRank[b.sourceQuality])
const byAngle = new Map()
for (const c of allClaims) {
  if (!byAngle.has(c.angle)) byAngle.set(c.angle, [])
  byAngle.get(c.angle).push(c)
}
const queues = [...byAngle.values()].map(q => [...q].sort(claimRank))  // copy: draining must not shrink byAngle counts
const rankedClaims = []
while (rankedClaims.length < MAX_VERIFY_CLAIMS && queues.some(q => q.length)) {
  for (const q of queues) {
    if (q.length && rankedClaims.length < MAX_VERIFY_CLAIMS) rankedClaims.push(q.shift())
  }
}
const unverified = queues.flat()
const perAngle = [...byAngle.keys()].map(a => a + ": " + rankedClaims.filter(c => c.angle === a).length + " verified / " + byAngle.get(a).length + " extracted")

log("Fetched " + allSources.length + " sources → " + allClaims.length + " claims → verifying " + rankedClaims.length + " (cap " + MAX_VERIFY_CLAIMS + ", split across " + byAngle.size + " angles)")
perAngle.forEach(line => log("  " + line))

if (rankedClaims.length === 0) {
  return {
    question: QUESTION,
    summary: "No claims extracted. " + allSources.length + " sources fetched, all empty/failed. " + dupes.length + " URL dupes, " + budgetDropped.length + " budget-dropped.",
    findings: [], refuted: [], sources: allSources.map(s => ({ url: s.url, quality: s.sourceQuality })),
    stats: { angles: scope.angles.length, sources: allSources.length, claims: 0, dupes: dupes.length },
  }
}

// ─── Verify: 3-vote adversarial ───
// Barrier here is intentional — claim pool must be fully assembled before ranking/verification.
phase("Verify")
const voted = (await parallel(
  rankedClaims.map(claim => () =>
    parallel(
      Array.from({ length: VOTES_PER_CLAIM }, (_, v) => () =>
        agent(VERIFY_PROMPT(claim, v), {
          label: "v" + v + ":" + claim.claim.slice(0, 40),
          phase: "Verify",
          schema: VERDICT_SCHEMA,
          model: MODEL_VERIFY,
        })
      )
    ).then(verdicts => {
      // A vote can be null (user-skip or agent error) — treat as abstain.
      const valid = verdicts.filter(Boolean)
      const supportedVotes = valid.filter(v => v.verdict === "supported").length
      const refutedVotes = valid.filter(v => v.verdict === "refuted").length
      const unconfirmedVotes = valid.filter(v => v.verdict === "unconfirmed").length
      // Outcome: ≥REFUTATIONS_REQUIRED refutes → refuted; ≥REFUTATIONS_REQUIRED supports →
      // confirmed; otherwise (incl. too many abstentions) → unconfirmed. Only confirmed claims
      // become findings; an all-abstain claim can never pass as confirmed.
      const abstained = VOTES_PER_CLAIM - valid.length
      const outcome = refutedVotes >= REFUTATIONS_REQUIRED ? "refuted"
        : supportedVotes >= REFUTATIONS_REQUIRED ? "confirmed" : "unconfirmed"
      const vote = supportedVotes + "S-" + refutedVotes + "R-" + unconfirmedVotes + "U"
      log("\"" + claim.claim.slice(0, 50) + "…\": " + vote + (abstained > 0 ? " (" + abstained + " abstain)" : "") + " → " + outcome)
      return { ...claim, verdicts: valid, supportedVotes, refutedVotes, vote, outcome }
    })
  )
)).filter(Boolean)

const confirmed = voted.filter(c => c.outcome === "confirmed")
const killed = voted.filter(c => c.outcome === "refuted")
const unconfirmed = voted.filter(c => c.outcome === "unconfirmed")
log("Verify done: " + voted.length + " claims → " + confirmed.length + " confirmed, " + killed.length + " refuted, " + unconfirmed.length + " unconfirmed")
const refutedOut = () => killed.map(c => ({ claim: c.claim, vote: c.vote, source: c.sourceUrl,
  reasons: c.verdicts.filter(v => v.verdict === "refuted").map(v => v.evidence + (v.counterSource ? " [" + v.counterSource + "]" : "")) }))
// Checked but neither confirmed nor refuted — a lead with a quote, not a finding and not a falsehood.
const unconfirmedOut = () => unconfirmed.map(c => ({ angle: c.angle, claim: c.claim, quote: c.quote, source: c.sourceUrl, vote: c.vote }))

if (confirmed.length === 0) {
  return {
    question: QUESTION,
    summary: "No claim confirmed: " + killed.length + " refuted (with stated reasons), " + unconfirmed.length + " unconfirmed (could not corroborate). Unconfirmed is not false — see the unconfirmed tier.",
    coverage: perAngle,
    findings: [],
    refuted: refutedOut(),
    unconfirmed: unconfirmedOut(),
    sources: allSources.map(s => ({ url: s.url, quality: s.sourceQuality, claimCount: s.claims.length })),
    stats: { angles: scope.angles.length, sources: allSources.length, claims: allClaims.length, verified: voted.length, confirmed: 0, refuted: killed.length, unconfirmed: unconfirmed.length },
  }
}

// ─── Synthesize ───
phase("Synthesize")
const confRank = { high: 0, medium: 1, low: 2 }
const block = confirmed.map((c, i) => {
  const best = c.verdicts.filter(v => v.verdict === "supported").sort((a, b) => confRank[a.confidence] - confRank[b.confidence])[0]
  return "### [" + i + "] " + c.claim + "\n" +
    "Vote: " + c.vote + " · Source: " + c.sourceUrl + " (" + c.sourceQuality + ")\n" +
    "Quote: \"" + c.quote + "\"\nVerifier evidence (" + best.confidence + "): " + best.evidence + "\n"
}).join("\n")

const killedBlock = (killed.length > 0
  ? "\n## Refuted claims — positive counter-evidence (for transparency)\n" +
    killed.map(c => "- \"" + c.claim + "\" (" + c.sourceUrl + ", vote " + c.vote + ")").join("\n")
  : "") + (unconfirmed.length > 0
  ? "\n\n## Unconfirmed claims — voters could neither corroborate nor contradict\n" +
    unconfirmed.map(c => "- \"" + c.claim + "\" (" + c.sourceUrl + ", vote " + c.vote + ")").join("\n")
  : "")

const report = await agent(
  "## Synthesis: research report\n\n" +
  "**Question:** " + QUESTION + "\n\n" +
  confirmed.length + " claims survived " + VOTES_PER_CLAIM + "-vote adversarial verification. Merge semantic duplicates and synthesize.\n\n" +
  "## Verification coverage per angle\n" + perAngle.join("\n") + "\n" +
  "An angle with few or zero verified claims is UNDER-SAMPLED, not refuted — say so in caveats; never report it as 'nothing survived'.\n\n" +
  "## Confirmed claims\n" + block + "\n" + killedBlock + "\n\n" +
  "## Instructions\n" +
  "1. Identify claims that say the same thing — merge them, combine their sources.\n" +
  "2. Group related claims into coherent findings. Each finding should directly address the research question.\n" +
  "3. Assign confidence per finding: high (multiple primary sources, unanimous votes), medium (secondary sources or split votes), low (single source or blog-quality).\n" +
  "4. Write a 3-5 sentence executive summary answering the research question.\n" +
  "5. Note caveats: what's uncertain, what sources were weak, what time-sensitivity applies.\n" +
  "6. List 2-4 open questions that emerged but weren't answered.\n" +
  "   Never build findings from unconfirmed claims, and never describe them as false. If an unconfirmed claim bears on the question, name it in caveats as unconfirmed.\n" +
  "7. CRITICAL: your StructuredOutput call MUST include every required property — summary (string), findings (array of {claim, confidence, sources, evidence}; use [] only if truly nothing survived), caveats (string). Even a thin or inconclusive result goes in this exact shape; never omit findings or caveats.\n\nStructured output only.",
  { label: "synthesize", schema: REPORT_SCHEMA, model: MODEL_SYNTH }
)

if (!report) {
  // Synthesis skipped/errored — salvage the verified claims raw rather
  // than throwing on report.findings and discarding the whole run.
  return {
    question: QUESTION,
    summary: "Synthesis step was skipped or failed — returning " + confirmed.length + " confirmed claims unmerged.",
    coverage: perAngle,
    findings: [],
    confirmed: confirmed.map(c => ({ claim: c.claim, source: c.sourceUrl, quote: c.quote, vote: c.vote })),
    refuted: refutedOut(),
    unconfirmed: unconfirmedOut(),
    sources: allSources.map(s => ({ url: s.url, quality: s.sourceQuality, claimCount: s.claims.length })),
    stats: { angles: scope.angles.length, sources: allSources.length, claims: allClaims.length, verified: voted.length, confirmed: confirmed.length, refuted: killed.length, unconfirmed: unconfirmed.length, afterSynthesis: 0 },
  }
}

return {
  question: QUESTION,
  ...report,
  coverage: perAngle,
  searchErrors,
  // Extracted but not adversarially checked (cap spent). Report these as an unverified tier, never as findings.
  unverified: unverified.map(c => ({ angle: c.angle, claim: c.claim, quote: c.quote, source: c.sourceUrl, quality: c.sourceQuality, importance: c.importance })),
  refuted: refutedOut(),
  unconfirmed: unconfirmedOut(),
  sources: allSources.map(s => ({ url: s.url, quality: s.sourceQuality, angle: s.angle, claimCount: s.claims.length })),
  stats: {
    angles: scope.angles.length,
    sourcesFetched: allSources.length,
    claimsExtracted: allClaims.length,
    claimsVerified: voted.length,
    confirmed: confirmed.length,
    refuted: killed.length,
    unconfirmed: unconfirmed.length,
    afterSynthesis: report.findings.length,
    urlDupes: dupes.length,
    budgetDropped: budgetDropped.length,
    agentCalls: 1 + scope.angles.length + allSources.length + (voted.length * VOTES_PER_CLAIM) + 1,
    modelTiers: { scope: MODEL_SCOPE, search: MODEL_SEARCH, fetch: MODEL_FETCH, verify: MODEL_VERIFY, synthesize: MODEL_SYNTH },
  },
}
