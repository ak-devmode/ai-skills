# Repo Cleanup All Agent

Thin alias for `/repo-cleanup --all`. All logic, config, and safety rules live in
`../repo-cleanup/SKILL.md` and `../repo-cleanup/AGENTS.md` — read those and execute
in `--all` mode. Never duplicate logic here; /repo-cleanup is canonical.

If the user named an owner, pass it through. Otherwise ask which configured owner
(from /repo-cleanup §1.1) to sweep.
