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
