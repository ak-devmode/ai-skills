# Where the friend's herdr tooling plugs in (seams)

Scope #4 deliberately does NOT build colored usage bars, a `model` sidebar token,
or space-level limit reporting — those wait on the friend's custom tool (bars +
diff) or a fork of `jordanhawkes/herdr-metrics`. The lifecycle is complete
without them. This note records the attach points so his tool drops in later
without rework.

## Colored usage bars / metrics
- **Current state:** `jordanhawkes/herdr-metrics` plugin is installed (id
  `herdr-agent-metrics`), reporting `$usage` / `$limit` / `$context` as PANE
  metadata; `setup-claude` bridge feeds Claude usage; Codex reads its rollout
  logs. Rendered via `ui.sidebar.agents.rows` in `~/.config/herdr/config.toml`.
- **Seam:** the sidebar row tokens. His tool reports its own `$name` tokens via
  `herdr pane/workspace report-metadata --token`; point the config rows at them.
  His bars either replace jordanhawkes (uninstall it) or coexist under different
  token names. Bars need per-value color — an undocumented question (ANSI-in-token
  vs per-threshold tokens); his code answers it. Don't re-derive.
- **Do NOT build here:** bars, `$model` token, space-level `$limit` (would need a
  fork of the pane-only jordanhawkes plugin).

## Diff tool
- **Seam:** a diff pane, opened on demand — NOT a reserved tab (Alex owns tabs;
  the concurrency layout is driver-left / workers-right-half-height, no diff tab).
  His diff tool runs as a pane Alex opens, reading **per-worktree** diffs
  (`git -C ~/.herdr/worktrees/<repo>/<branch> diff`) since model-B isolates each
  lane in its own worktree.
- When it lands: review the tool, then wire it as a launchable pane; the worktree
  paths from the `herdr` skill §3 are its inputs.

## Not a blocker
Everything in scope #4 (dispatch one-flow, naming, worktree lifecycle, worker
launch/trust, layout, CLAUDE.md rule) stands without his tool. Integration is a
follow-up scope.
