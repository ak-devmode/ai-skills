# /review — ai-skills @ `97b04f7717a7e03593b85ae65338b9f34b55a9c3..95912bd1d213ca4a5c677499b354329180c32c7e` (43 commits)

**Review:** `10.3-r5` · **Reviewer:** claude-fallback codex out of credits · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**DEGRADED:** reviewer is `claude-fallback codex out of credits` — not the codex gate; the gate reports `⚠ judge: review claude-fallback codex out of credits` (and the index carries it) until a codex re-review of this unit.
**Findings:** 4 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.3 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>" | --reframed "<what changed>" --commit <sha> --by judge|user)`

## BLOCKING (0)


## SHOULD FIX (2)

- **10.3-r5-01** `scripts/driver-merge.py:652` (engine correctness) — The merged-elsewhere card's context reads "driver-merge did not merge <label>: merge". On that path (main, MERGED-ELSEWHERE) the PR WAS merged, past the checked head. Context is the field Alex reads on a v2 card; the detail that explains it sits in the collapsed evidence. The card tells him the opposite of what happened. → Let callers pass the context, as they pass title/options: for kind=merge-elsewhere use e.g. "<label> was merged at <sha>, past the head the gate checked: <why>". Class: any v2 field built from a refusal-only template. Check the evaluate-error path's context as well.
- **10.3-r5-02** `scripts/driver-merge.py:654` (silent-failure testing) — The cap slices added in the integration (title[:100], context[:400], evidence[:4000]) are never exercised. The longest test label (test_driver_merge.py:408) gives a 69-char title, and no case gives evidence or context near its cap. Reverting any slice still passes, and emit_packet fails open on a packet.py refusal (prints a warning, returns None), so an over-cap card would just not be written while the merge is still refused. → Add one emit_packet case per field: a ~120-char owner/repo label (title and context), and several failed conditions with ~1500-char details plus floor hits (evidence). Assert the packet is written and each field is within V2_CAPS. Revert each slice and confirm the test fails.

## NOTE (2)

- **10.3-r5-03** `scripts/driver-merge.py:638` (silent-failure correctness) — Evidence is body[:4000] with no truncation marker. Floor-path lines come last in body, so on a one-way card long failed-condition details cut the floor paths first, and those are the evidence the one-way decision rests on. → Put floor-path lines before the per-condition detail, or keep them whole and end a cut body with an explicit '… (truncated)' line.
- **10.3-r5-04** `scripts/driver-merge.py:651` (doc-claim cards-v2) — v2 titles here are labels, not questions ("Floor path: X", "CI change: X", "Not merged: X", "Merged past the checked head: X"). The contract this same merge writes into packet.py usage and /plan §6 is title = the question. Nothing enforces it, but the cards read against the v2 rule. → Phrase each as the decision, e.g. "Merge X by hand? It touches a floor path".

## Checked and clear

v2 caps on every driver-merge refusal path: option labels ≤ 31 chars, whys 50–71 chars (cap 140), no '(recommended)' text, title/context/evidence sliced to 100/400/4000, context always non-empty and single-line (built from fixed condition names), no --body passed on v2, every emit_packet caller passes (label, why) tuples (the evaluate-error, merge-elsewhere and refusal paths; driver-merge.py:816/834/847), merge-elsewhere path writes a valid v2 card (test_refusal_then_merged_elsewhere_is_a_second_packet asserts its title and id), the table test still asserts floor/CI paths in packets[0]['evidence'] (test_driver_merge.py:375-377), and asserting the door list implies a card was written for every refusal case, herdr/SKILL.md conflict resolution keeps the driver registration (Alex 86) and the herdr-agent-view ensure, packet.py merge keeps both lanes: driver_identity/registration docs + v2 usage + stale --reason, plan/SKILL.md one-way recipe moved to v2 with the data-model payload note kept; no v1 --body recipe left in plan/herdr/concurrency

## Not applicable

domain checks: generic repo

**Verdict:** SHIP

## Reframe

None proposed — the reviewer saw no simpler design that removes several findings.

## What this review did not cover

- codex unavailable (out of credits): Claude fallback, single-context pass
- no specialist fan-out: brief scoped the review to the integration hunks of merge 95912bd in a read-only pane
- tests not run (pane is read-only, prepare ran --no-checks)
- the lane commits inside 97b04f7..95912bd were not re-reviewed; the brief says each lane was reviewed separately
- gstack engine telemetry not logged
