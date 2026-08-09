# /scope — why these rules exist

Forensics for rules whose *statement* lives in SKILL.md. Read when you want to know
what a rule cost, or before proposing to relax one. Each entry is a real incident.

## 1. A personal name in a shared template decays in exactly the hands it is wrong for

Until 2026-08-07 the plan-stub template carried the literal string `**Author:** Alex`.
It was silently wrong for every teammate who ran `/scope`, and their sessions responded
by either overwriting it or deleting the line: all 7 plans of scope 102 and all 4 of
scope 110 (Hamzah), and 81.10–81.12 plus 97.2 (Abdul), carry **no author at all**, while
every scope Alex created has one.

Rule: `Created by` and `Executed by` are derived from `git config user.name` at run
time. Never a literal, never copied from an example. (§5.4, and `/plan` §3.1.)

## 2. Scope numbers race, and the skill that mints them read the wrong source

`/scope` §5.2 used to say "read `PLANS-INDEX.md`, find the highest `#`, increment"
against the **local working tree**. `/plan` §11.4 already knew better, saying to read
`git show origin/main:…` "since concurrent sessions race for scope numbers." Two skills,
two answers, and the one that assigns numbers was the wrong one. Scope 110 collided with
a concurrent session and had to be renumbered 111.

Rule: `scripts/claim-scope-number.sh`, which maxes over origin/main's index, the local
index, scope folders on disk, and branch names. (§5.2.)

## 3. An append with no header is not a record; it is a leak

§5.8 used to carry a seven-column row template (`| {n} | {date} | scope | {path} |
{project} | {status} | {desc} |`) and nothing ever wrote a matching header. Those rows
accreted into a 40-row untabled fragment glued to the end of the WellMed index —
invisible as a table, unmaintained, and by 2026-08-07 the *only* index registration for
scopes 101, 106, 107 and 108. Two of those were live with no Active row at all.

The same class, found 2026-08-09 in PMG: an undeclared `Project` column shifted every
cell right in 39 of 52 Active rows, so their descriptions rendered **nowhere** — ~13,900
characters invisible.

Rule: `scripts/plans-index.py` owns every write and refuses a non-canonical header.
(§5.8.)

## 4. Reviewers cannot catch errors about structure they cannot see

The scope-48 retro: a plan silently invented, renamed, and re-owned tables because the
*current* structure was never on the page. Nobody reviewing it could tell.

Rule: Step 4.5's Table Identity Map — the cited current shape first, then a deviation
ledger, deny-by-default, each deviation an explicit approval before it reaches a plan
stub.

## 5. A cap violated 80 times is a wrong rule, not drift

`/markdown-style` §11.7.4 used to cap index Status cells at ~300 characters. The WellMed
index carried 80 cells past it, several over 3,000, and the 2026-08-09 audit proposed
compressing them on the strength of the written rule. Backwards: those descriptions are
Alex's console status tracker, the fastest high-level view he has. The rule was wrong.

Same reasoning had already been applied once, to `@Owner` (§2.2.3): "a rule obeyed
nowhere is worse than no rule, because its presence implies ownership is tracked when it
isn't." Apply it before enforcing any rule this repo states.
