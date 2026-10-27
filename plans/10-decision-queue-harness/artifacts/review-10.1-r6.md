# /review — ai-skills @ `4cdea98569089e565e778d165e36a0ff558a6843..fc51f4a5a274b1b14bb0864a9f9ae6a017c2366a` (3 commits)

**Review:** `10.1-r6` · **Reviewer:** codex gpt-6.1-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (env)**
**Findings:** 3 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 10.1 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>" | --accepted "<process nit>")`

## BLOCKING (1)

- **10.1-r6-01** `concurrency/SKILL.md:313` (engine) — Box lanes write their outboxes on homelab2026, but the driver flushes and validates them as local paths. packet.py has no remote transport: flush silently skips nonexistent directories, and check-reply cannot find the packet. Following this procedure leaves remote one-way lanes unable to resume. → Define remote flush and reply validation against the authoritative remote outbox, preserving driver-only POST ownership and checking the remote lane's HEAD.

## SHOULD FIX (2)

- **10.1-r6-02** `concurrency/SKILL.md:299` (doc-claim) — The command offers --type data-model with --body, which constructs a payload the schema rejects: data-model requires tables and forbids body. The same invalid recipe appears in plan/SKILL.md:507. No packet is created for that branch. → Use --body for generic packets and --payload-file with the required tables structure for data-model packets.
- **10.1-r6-03** `plan/SKILL.md:525` (engine) — Outside herdr, a session without an exported session ID creates a session-none packet, but this reply command always refuses it without --lane. The procedure provides no recovery, so even the numbered inline fallback cannot resume that session. → Document the explicit --lane fallback, taking its value from the original packet's reply line rather than the incoming reply.

## NOTE (0)


## Checked and clear

Exact three-commit range and required repo guidance inspected., Changed skill frontmatter, versions and section numbering: lint passed., Packet schema tests: 7 passed., Range whitespace check passed., Gate integrity: no test, assertion or threshold relaxations in range., Dirty-comment and unnecessary-abstraction lenses., No declared approval classes at the range base.

## Not applicable

Build: repository declares no build., SQL, ORM fields, database repairs and migrations., Async endpoints, frontend rendering and type coercion., Time windows and timing-dependent tests., Distribution and CI/CD changes., Project-specific healthcare domain rules.

**Verdict:** SHIP AFTER BLOCKING

## What this review did not cover

- Full unittest suite attempted but could not complete: read-only sandbox prevents temporary-directory creation.
- Live skill invocation and remote queue round-trip verification require writable sessions and network access.
- Approval-class scanner attempted but rejects the supplied SHA by resolving origin/<SHA>; base declarations were inspected directly instead.
- Independent specialist sub-reviews were not performed; delegation was not authorized.
