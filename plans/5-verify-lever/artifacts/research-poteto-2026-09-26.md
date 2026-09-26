# Research report — poteto on verification since 2026-09-11

**Run:** `poteto-verify-r1` · pane mode · 3 angle lanes + 1 verify lane · 2026-09-26
**Question:** What has Lauren Tan (@poteto) published on agent verification, feature maps,
verification skills and pstack since 2026-09-11 — and what does it change for `/verify`?
**Coverage:** 19 claims extracted, 19 verified (cap 24) · 18 confirmed · 1 refuted · 0 unconfirmed

## 1. Summary

Nothing she published after 2026-09-11 changes the verification model: pstack's changes in
that window are maintenance (model defaults moved to Opus 5.5 / Grok 4.7, 19 instructions
cut as unnecessary for Opus 5.5, a model-rule consistency fix, a reasoning-budget selector).
Two statements sharpen the design question rather than the mechanism: the README's "i don't
believe in planning. the best spec is code", and a 2026-09-19 post arguing that a codebase
that can formally verify itself makes "code review solved". Her feature map's concrete
contents are now pinned down (routes, DOM selectors, keyboard shortcuts, interaction flows,
kept in the skill directory and auto-updated). The biggest gap: a2 found her two-part
"Complete Guide to pstack" X articles but extracted nothing from them.

## 2. Findings

### 2.1 pstack changes since 2026-09-11 are maintenance, not new concepts — high
- 2026-09-13: `setup-pstack` gains a reasoning-budget ask (max/xhigh/high/medium). (#366)
- 2026-09-23: default agents move to Opus 5.5 and Grok 4.7, "port skill updates". (#414)
- 2026-09-23: "cut 19 more instructions Opus 5.5 does not need". (#419)
- 2026-09-23: "resolve rule conflicts and read the model rule the same way". (#422)
- Source: github.com/cursor/plugins/commits/main/pstack (primary; verifier confirmed via gh api)

### 2.2 "No planning; the best spec is code" — high
pstack README, section "why are there no planning skills?": "personally, i don't believe in
planning. the best spec is code." Primary, verified verbatim.

### 2.3 "Code review is solved" once the codebase formally verifies itself — high
X post 2026-09-19 (x.com/poteto/status/2101384547543978195), about the Bend language: "when
you have a codebase that can formally verify itself, you can ship at an incredible pace. code
review is solved." A stronger stance than the talk's trust ladder.

### 2.4 Feature map contents and structure — high
- Talk (her words): a machine-readable map of features, their routes, keyboard shortcuts, DOM
  selectors and interaction flows, stored in the skill directory and automatically updated.
- `poteto/verification-skill-example`: each feature file answers four questions — what exists,
  how a user reaches it, how to drive it with the harness, what usually lies; ~30 files; README
  gives a top-to-bottom regression order.

### 2.5 Multi-model diff review exists in pstack as `/interrogate` — medium
One reviewer per configured model, adversarial review of the diff, synthesized verdict,
**do not auto-apply** (pstack/skills/interrogate/SKILL.md). Third-party coverage frames it as
a cheap supplementary check, not a substitute for human review on risky changes.

### 2.6 Throughput figures are self-reported and inconsistent — high
Cursor's Compile London programme lists the talk as "I Shipped 2,000 PRs Last Month"; the
video says 2,500. No independent audit. Two other repeated claims ("Chief of Staff"
agent-to-agent coordination, "85% of SpaceXAI engineers run 10+ bots") have no first-party
source (folkfox).

### 2.7 Adoption evidence is thin — medium
One public third-party application (GitHub issue, 2026-09-25) applying the techniques to two
internal repos. A mirror (`backnotprop/pstack`) advertises it for Claude Code and Codex too.

## 3. Refuted

- **"automate-me is a new skill since 2026-09-11"** — refuted: present in pstack's first commit
  (2026-05-23), stable since 2026-09-08.

## 4. What it changes for `/verify` (driver synthesis, not a research finding)

- **`/interrogate` is the codex-review design already built.** It supports the disposition
  rule: findings are not auto-applied; each is dispositioned. Where she synthesizes across
  models, we use one opposing family (codex) — cheaper, same independence from the author.
- **"The best spec is code" is a deliberate divergence, not an oversight.** Her verification
  checks behavior only (class A). Our conformance class (did we build what the scope said)
  exists because the scope is where Alex holds the product vision. Record it in scope 5 as a
  rejected alternative with that reason.
- **"Code review is solved" needs formal verification we don't have.** It is the far end of
  her ladder, not a present option for WellMed. Keep review.
- **Instruction trimming for Opus 5.5** mirrors scope 2's accretion work — no action.
- **Feature file shape** is settled: four questions + regression-order index.

## 5. Caveats

- Verification was a single independent verifier, weaker than the workflow's 3-vote panel.
- **Missing coverage:** her "Complete Guide to pstack" Pt. 1 and Pt. 2 (X articles
  2094457600259842065, 2097732320606507506) were found but yielded no claims — likely
  unfetchable X article pages. Probably the most relevant primary material in the window.
- Several sources predate the cutoff (2026-08-21, 2026-09-05) and are tangential by design.
- No angle lane was interrupted in this run; the failed-lane path was tested in a separate
  throwaway run (`interrupt-test-r1`).

## 6. Open questions

- What do the Complete Guide Pt. 1 / Pt. 2 articles say about verification and feature maps?
- Does `/interrogate` record per-finding dispositions, or only a synthesized verdict?
- Has "code review is solved" changed how pstack's own review skills are positioned?
