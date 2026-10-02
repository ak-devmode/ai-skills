# Lean dry run — measured

**Date:** 2026-10-02 · **Range:** `ai-skills eea708c..45fcd32` (5 commits, 2 files, ~190 changed
lines — the resolver fixes) · **Mode:** `mode: lean (default)` · **Models:** Sonnet subagents
(`model: sonnet`), general-purpose agent type

---

## 1. Numbers

| Step | Bundle | Subagent tokens | Tool uses | Wall time | Outcome |
|---|---|---|---|---|---|
| lean `/review` | 54,397 B (~14k tokens) | 88,142 | 4 | 89 s | 3 findings (1 should-fix, 2 notes), SHIP |
| lean `/verify` judge | 37,194 B (~10k tokens) | 75,032 | 4 | 33 s | 5 verdicts, 4 findings, 0 inconclusive |
| **per unit** | | **~163k** | | **~2 min** | |

**For comparison**, today's codex calls on similar one- or two-commit ranges: 262k, 280k,
358k and 437k input tokens each, 80–87% cached, 2–3.4k output. Those are codex/OpenAI
tokens. Today's no-codex Claude fallback (gstack's 73 KB engine plus up to 8
specialists) was **not measured** in this run.

`subagent_tokens` is the harness's per-agent total. Whether it counts cached re-reads at
full weight against a seat's limit is not known from this run.

## 2. Where the lean tokens go

The bundles are 10–14k tokens; the subagents used 75–88k. The difference is overhead: the
general-purpose agent's own system prompt, plus the whole context re-sent on each of 4
turns (read the bundle, read the schema, write the answer, report back).

Cheap cuts, if needed:
- Inline the JSON schema into the bundle. That saves one turn (about a quarter).
- Tell the subagent to write the file without reporting back first.

## 3. Quality, eyeballed

**Review.** All three findings are real and point at the right code:
- `is_comment(sh=True)` makes `//` lines inside `node -e` bodies count. It's labelled
  `fail-open`, but it's really a false-positive risk.
- The `fetch_external` trade-off. I had already flagged it to Alex.
- The depth drift for a nested `case` on one line. It falls back to fail-closed.

`cannot_do` honestly lists what the bundle couldn't settle. It obeyed the "read no
other file, run no command" rule: 4 tool uses, none outside its files.

**Judge.**
- It confirmed the runner fail on `names-resolve` and named all three unresolved env
  refs. Two of them were real, in `resolve-identifiers.py`'s own docstring (fixed in
  `ca44e9a`). The third, `AI_SKILLS_REVIEW_MODE`, waits on `.env.example`.
- It noticed that the runner scanned to HEAD rather than the unit's range, without
  being told.
- Rejection audit: "no rejections to be wrong" — correct, there were none.

**Not tested here:** a range over the 1,500-line cap; a WellMed repo with domain
sections. The unit tests cover both mechanically.

## 4. Dry-run records

Everything was written to a throwaway scope in the session scratchpad, not to any real
scope's review or verdict log. Nothing to delete from the repo.
