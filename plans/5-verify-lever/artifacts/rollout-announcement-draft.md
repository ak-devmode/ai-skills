# Rollout announcement — draft for Alex (plan 5.3)

Paste-ready. Alex sends; nothing here has been posted.

---

**ai-skills update: `/review` and `/verify` now run on every phase (advisory for now)**

Please update your ai-skills clone:

```
git -C ~/Projects/ai-skills pull
~/Projects/ai-skills/setup.sh
```

Then restart Claude Code and run `/verify --demo`. It takes about 2 minutes and shows a
fixture with six planted defects, every one caught by name, plus a clean control that
passes. The whole path took 3 minutes on a fresh clone.

What changes for you:

- **`/review` uses codex.** codex (the other model family) reviews each phase's exact
  commit range, not your own model. Every finding has to be marked fixed (with the commit)
  or rejected (with a reason).
- **`/verify` checks each phase against the scope's finish conditions.** A script runs
  the checks, and codex can only confirm or downgrade what the script found. `/plan` runs
  both at every checkpoint. `/closeout` checks the whole scope.
- **It's advisory.** A problem shows up as a ⚠ on the phase's PLANS-INDEX row, but
  nothing is held back. It becomes blocking after 5 scopes pass cleanly.
- **Scopes you already have in progress:** the phases you've already started are marked
  as predating the gate, so they are never checked after the fact. Only phases you start
  from now on get finish conditions.
- **Set up codex** (`npm i -g @openai/codex && codex login`). Without it everything still
  runs on a Claude fallback, but your verdicts carry a `⚠ judge:` marker in the index.
  `setup.sh` warns you with the fix if codex is missing or logged out.
- **No herdr needed.** Everything runs in a normal Claude Code session.
- **If your clone falls behind**, `/plan` and `/verify` print one line telling you to pull.

The README's "Verification" section explains what each ⚠ means and how to read a verdict.
