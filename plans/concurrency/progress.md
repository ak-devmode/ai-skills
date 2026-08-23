# Progress — /concurrency

## 2026-08-23
- Scope created (session: herdr evaluation → build decision with Alex).
- Pre-scope ground truth established and recorded in scope.md §2: herdr
  installed as brew service, socket CLI chain proven headless, `--source
  recent` trap found, native worktree helper found, codex authed.
- Model roster decided by Alex: Opus 4.8 default / codex GPT-5.6 sol /
  GLM 5.2 via OpenRouter (Z.ai coding plan deferred until volume measured).
- Next action: 6.1 skeleton + dry-run partitioner.

## 2026-08-23 (later, same session)
- Alex approved scope → build. Roster verification during 6.1:
  - codex upgraded 0.139.0 → 0.149.0 (npm global; the brew binary is a
    symlink into npm's tree). `gpt-5.6-sol` live-probed OK ("MODEL-OK").
  - `z-ai/glm-5.2` confirmed on OpenRouter's public models list (1M ctx;
    `:free` variant exists for trials).
  - CORRECTION: `herdr --skill` EXISTS (Alex was right) — emits a 195-line
    agent-facing control skill gated on HERDR_ENV=1. /concurrency delegates
    all CLI mechanics to it instead of duplicating them.
  - `herdr worktree create --cwd --base --branch --label [--env]` surface
    pinned — worktree-per-partition is native.
- **6.1 DONE**: `concurrency/SKILL.md` written (routing table §3, partition
  procedure §4, dry-run format §5, rails §9). Gate artifact:
  `artifacts/gate-6.1-scope91-dryrun.md` — known-answer test over scope 91
  PASSED (91.2 only; 91.1 human-gated; 91.6 correctly excluded by domain
  edges its own stub omits). Two refresh-pass observations filed for 6.5.
- Next action: 6.2 live dispatch, claude-only, cap 2.

## 2026-08-23 (design correction, Alex)
- Two corrections folded into SKILL.md v0.2.0:
  1. §4.0 evidence rules — concurrency has ONE responsibility: the
     parallel/serial map, re-derived from repo ground truth every run; stubs
     are hypotheses, never authority. External gates stamped
     UNVERIFIED-EXTERNAL when not checkable read-only.
  2. §7.2 Claude-to-Claude gate bus — dispatched claude/glm panes report
     GATE-PASSED/GATE-BLOCKED via native SendMessage; supervisor re-verifies
     from the consumer's vantage before releasing downstream; codex seat
     stays on herdr state only.
- Gate 6.1 rerun from scratch under the new rules → v2 artifact. Frontier
  unchanged (91.2 only) but **v1 had the wrong repo in 91.2's touch-set**
  (backbone; truth = wellmed-finance internal/queue/steps/handler.go:50-51)
  — the evidence rules caught a real defect in the skill's own first output.
- Next action: 6.2 live dispatch, claude-only, cap 2 (payload candidate:
  the two read-only 91-refresh checks).

## 2026-08-23 (evening) — 6.2 DONE: first live dispatch, gate passed
- Run "91-refresh" (renamed 91.0 by Alex): two read-only partitions
  (stub-audit, drift-scan), Opus seats, herdr-cut worktrees of
  wellmed-finance @ origin/develop, full pipeline exercised end-to-end.
- BOTH signal paths worked per worker: `herdr agent wait --until done` fired
  AND the §7.2 SendMessage gate bus delivered GATE-PASSED; supervisor
  re-verified every claim independently before accepting (all held; one
  claim — application.go:83-84 — the supervisor had itself missed earlier).
- Findings (feed the 91.2 stub correction, wellmed side):
  1. Rename touch-set is WIDER than the stub: handler.go:50-51 +
     internal/app/application.go:83-84 + hardcoded literal at
     topology_integration_test.go:72 (test 4 skip-gated; breaks silently on
     rename unless :72 updated).
  2. MISMATCH: integration.go / GetTenantIntegrationConfig exist NOWHERE in
     wellmed-finance — stale cross-repo citation in the stub.
  3. Stub's "Phase 1" heading (~line 24) = stale copied 91.1 content.
  4. drift-scan: develop frozen at 1d86b2b (08-13); saga participant shell
     commits are 91.2 substrate; 91.2 PREMISE HOLDS, work not started.
- Layout rules added at Alex's direction (SKILL.md §6 1b): one workspace per
  run, primaries stacked via pane move --split down 0.5 (verified safe on
  running agents); helper panes split RIGHT 0.5 from the worker's own pane;
  short pane names "<scope>.<phase> <task>". herdr config.toml created:
  ui.window_title="{workspace} · herd", theme.auto_switch=true.
- Worktrees left in place (§8); zero commits on either branch (read-only).
- Next: 6.3 multi-model seats (codex + glm panes).

## 2026-08-23 (night) — 6.3 DONE: multi-model seats, both passed
- Run "91-seats", tab-per-run layout exercised (tab `91.0 seats` in the herd
  workspace): codex/gpt-5.6-sol on the 91.2 rename map (wellmed-finance
  worktree), GLM 5.2 via OpenRouter on the 91.6 citation check (gateway-go
  worktree). OpenRouter key lives in macOS Keychain
  (`openrouter-api-key`), resolved inline at spawn — never in transcripts,
  herdr env state, or the dispatch log.
- GLM seat: launch recipe debugged live (base `/api` not `/api/v1`;
  bearer-only) → SKILL.md §2/§3. Result: 3/3 in-repo citations VERIFIED
  (route routes.golden:358, JURNAL_FORWARD_URL env.go, commit 7092647
  2026-03-02), 4 out-of-repo claims correctly refused as NOT-CHECKED.
  **Gate bus WORKS under foreign auth** — GATE-PASSED arrived over the
  native cross-session socket from a non-Anthropic model.
- codex seat: complete rename map delivered — 5 textual edit sites
  (handler.go:50-51; topology_integration_test.go:72-73;
  handler_test.go:30), ~9 constant usage sites needing no edit, zero refs in
  docs/config/migrations; verification rg + go test commands; skip-gate
  removal via RABBITMQ_TEST_URL against a DISPOSABLE broker only (test
  declares the real `wellmed.saga` exchange). New OPEN ITEMS beyond 91.2's
  stub: old trigger/compensate bindings on finance.steps + DLQ must be
  explicitly removed post-cutover, and in-flight postfinancejournal
  messages need a drain/replay/dual-support decision.
- Trap found: codex completion maps to herdr state `idle`, never `done` —
  primary wait is now `pane wait-output --match "PARTITION-DONE"` (§7.1).
- 6.4 (overnight profile) and 6.5 (register + dogfood proper) remain.

## 2026-08-23 (late) — 6.4 DONE; run cleanup; 6.5 gated on Alex
- Cleanup: all 4 run branches verified 0 commits vs base → panes closed,
  worktrees removed, branches deleted (were at 1d86b2b / 4c44e73).
- 6.4 overnight tier written (SKILL.md §11): dedicated workspace in the
  default session (deviation from scope.md's named-session idea — one brew
  service to keep alive, reattach shows everything), watcher pane with
  marker-wait + blocked-wait → toasts, no gate bus overnight, morning-review
  checklist. Verified live: `pane wait-output --match` chain works;
  `[ui.toast] delivery="herdr"` added to herdr config (default was off →
  reason:disabled; while user is focused it reports reason:busy by design).
- 🔴 `herdr integration install claude|codex` exists (official state
  reporting?) — install BLOCKED by permission classifier (edits
  ~/.claude/settings.json). Handed to Alex; backups in scratchpad. If
  installed, may fix codex idle-vs-done at the source — re-test then.
- 6.5 remains: land feature/concurrency-skill → main (push gated on Alex),
  re-run setup.sh, restart session, then scope-91 dogfood proper.
