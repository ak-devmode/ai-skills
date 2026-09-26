# Review rules — lenses (every repo)

Read by both `/review` executors. These apply to any repo, domain or not. Each is a
class of defect that passed a diff-scoped review at least once.

## 1. Read the adjacent code, not only the diff

For every file the range touches, read the whole file; for every script or module it
calls into, read the function it calls. A diff-scoped review cannot see a caller that was
already wrong, and that is where the expensive findings live — on WellMed 108.6 both
critical findings were in pre-existing code adjacent to the change.

## 2. Fail-open verification

Any command whose failure mode is "succeeds and returns empty" — a cloud describe/list
call, a count-based check, a grep whose miss is indistinguishable from absence — is a
finding whenever something downstream treats its output as proof. Ask of every
verification in the range: what does this do when its input is *wrong* rather than
missing? A check that verifies a count but never content is this class.

## 3. Silent failure

Flag, with `file:line`: `|| true`; `2>/dev/null` (or `&>/dev/null`) on a command whose
failure matters; an empty `catch` / `except: pass` / `rescue nil`; a pipeline without
`pipefail`; `set -e` under `#!/bin/sh` relied on for pipes; an error logged and then
execution continued as if it succeeded; a default value that masks a missing config.

## 4. Local maxima

- **Over-build** — abstraction the change did not need: a registry, plugin layer, factory
  or config system with one caller; a parallel implementation of a pattern that already
  exists in the repo (search for it before accepting a new one).
- **Invented reality** — names, paths, env vars, SSM keys, routes, proto fields, table
  columns, CLI flags used as if they exist without being declared anywhere. Look each one
  up; "it reads plausibly" is not a lookup.

## 5. Dirty comments

A comment that justifies a workaround instead of fixing it: `workaround`, `hack`, `for
now`, `temporary`, `TODO` used as the reason the code is acceptable, `should never
happen`, `ignore errors`. The finding is the thing the comment excuses; quote it.

## 6. Doc claims

Every claim a README, doc, comment, docstring or help text in the range makes about
behaviour — checked against the code at HEAD. A doc that describes a trap, flag, default
or guarantee the code no longer has is a finding (on 108.6 this was one of the two
findings codex missed).
