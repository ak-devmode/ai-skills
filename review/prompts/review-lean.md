# Pre-landing review — lean, single pass

Repo: `{{REPO}}` ({{PROJECT}}). Range `{{RANGE}}` ({{COMMITS}} commits). Everything you may
use is in this file. **Read no other file and run no command.** A check this file cannot
settle goes in `cannot_do`, never a guess. That includes every rule below that asks you to
read code outside the diff (the lenses' adjacent-code check): you have only the hunks, so
report what you could not check rather than clearing it.

You are reviewing someone else's change. Find what is wrong; do not praise and do not
summarise what it does. A finding against an accepted rule in the repo's CLAUDE.md is a
finding about that rule, and must say which.

## Commits

```
{{LOG}}
```

{{SECTIONS}}

## Not in this bundle — list each in `cannot_do`

{{NOT_COVERED}}

## The diff

```diff
{{DIFF}}
```
