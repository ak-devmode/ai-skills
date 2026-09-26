# Spike — codex as the `/review` gate (Task 2.2a, 2026-09-26)

**Question:** can codex, headless and read-only, carry `/review` — gstack's engine checks
plus the Kalpa domain rules plus the new lenses — on a real diff? What can't it do?

**Setup.** WellMed scope 108.6 (private repo; details stay there). The diff the original
`/review` saw before its fixes landed, reviewed with `scripts/codex-exec.py exec`, a
read-only sandbox, an output schema, and a prompt that names the rule files to read (gstack
`review/checklist.md`; ai-skills `review/SKILL.md` §1.1.1–§1.1.2 and §3) plus three lenses:
local maxima, silent failure, dirty comments. Model reported: `gpt-6-sol`. Wall time 262 s.

## 1. Result against ground truth

The original review recorded 6 findings (2 critical, 4 informational), all fixed in-band.

| Original finding (class) | Codex |
|---|---|
| critical — generator fail-open on an empty cloud describe (fail-open verification) | caught |
| critical — deploy verifies a count, never content (fail-open verification) | caught |
| informational — a `--dry-run` path mutates the destination | caught |
| informational — a committed transform is non-idempotent on re-run | caught (as over-build) |
| informational — over-broad deletion in a generator | missed |
| informational — README documents a trap that no longer exists | missed |

**Recall 4/6, both criticals.** It also raised 6 findings the original review did not have:
four in the silent-failure class (a pipe without `pipefail` in adjacent code; empty-vector
queries that render as healthy; a vanished series that renders as absent rather than down),
one engine and one dirty-comment. Whether those are real is unverified; they are handed to
Alex privately, not recorded here.

## 2. What codex could not do (its own list)

1. Anything needing network: live cloud inventory, account/profile checks, running services.
2. Execute the product's queries or look at a rendered UI — no browser.
3. Run the deploy script or its destination verification.
4. Write-side tests — the sandbox is read-only.
5. gstack's parallel specialist sub-reviews.

## 3. What it changes in the design

1. **codex is the gate; the live half moves to `/verify`.** Items 1–3 are behaviour checks —
   class-A finish-table rows the runner executes. `/review` stays a diff reviewer.
2. **Doc claims need an explicit lens.** Both misses were outside the code's own logic, and one
   was a doc claim contradicted by code. The rules file gets a doc-surface lens ("every claim a
   README / comment / docstring in the range makes, checked against the code").
3. **Specialists are not replicated.** One codex pass covered their classes on this diff. The
   Claude fallback still runs gstack's engine (and its specialists) when codex can't.
4. **codex cannot write.** Completion markers and the disposition log are written by our
   script from codex's JSON, never by codex.
5. **Budget:** ~4–5 min on a mid-size diff. Default timeout 900 s; the Bash call above it.
6. **Stable IDs** come from the output order (`F1…`); the writer prefixes `<unit>-r<n>-`.
