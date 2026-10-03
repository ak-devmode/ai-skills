# /review — ai-skills @ `bff989a7db0b61ac9d232214fc62b9dcd02589cc..e2f327204b4d43feb08dcd2a5e9eecb5d446f4e9` (12 commits)

**Review:** `7.1-r1` · **Reviewer:** codex gpt-6-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (flag)**
**Findings:** 9 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 7.1 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>")`

## BLOCKING (6)

- **7.1-r1-01** `scripts/review-mode.py:44` (local-maxima) — AI_SKILLS_REVIEW_MODE is read but absent from .env.example. The range's own names-resolve check reports it unresolved (found 1, resolved 0), so the approved 7.1 finish condition cannot pass. → Declare AI_SKILLS_REVIEW_MODE in .env.example and rerun names-resolve.
- **7.1-r1-02** `verify/scripts/judge.py:183` (fail-open) — The lean bundle inlines scope.md, but this range's scope.md only points to the plan containing 7.1's deliverables. The judge is forbidden to read that plan, so it cannot verify p1-scope-deliverables from the bundle. → Inline the referenced plan's deliverables, or make scope.md self-contained; return inconclusive when they are unavailable.
- **7.1-r1-03** `review/scripts/review.py:187` (fail-open) — Lean review inlines CLAUDE.md but omits ARCHITECTURE.md. The full review contract requires both to decide correctness, while the lean reviewer is forbidden to open another file. → Inline ARCHITECTURE.md or explicitly mark its checks uncovered and prevent a clean verdict for them.
- **7.1-r1-04** `review/prompts/review-lean.md:4` (fail-open) — The bundle contains diff hunks, yet the inlined lenses require reading each touched file in full and called functions. The no-read instruction makes that mandatory check impossible even when every changed file fits the cap; a clean review can still be recorded. → Include the required adjacent code in the bundle, or make the reviewer report those checks as unperformed and keep them from clearing the gate.
- **7.1-r1-05** `review/scripts/review.py:380` (fail-open) — record accepts any readable --uncovered file without tying it to the prepared range. An empty or stale sidecar passes the check and removes omitted files from the report; reusing an output directory can trigger this accidentally. → Recompute uncovered files from the immutable range during record, or verify a range-bound sidecar digest.
- **7.1-r1-06** `scripts/verify_lib.py:424` (fail-open) — Git quotes unusual filenames in --numstat output. Passing that quoted text as a pathspec makes git diff succeed with an empty patch, while capped_diff counts the file as inlined and never lists it as uncovered. → Use git diff --numstat -z and parse NUL-delimited filenames before requesting each patch.

## SHOULD FIX (3)

- **7.1-r1-07** `verify/scripts/judge.py:173` (silent-failure) — The 40 KB limit is applied to the entire append-only verdict log before filtering to this run. After prior runs grow the log, a small current run is omitted even when its records would fit, making the lean judge lose its primary evidence. → Filter to the requested run first, then apply the size limit to the filtered content.
- **7.1-r1-08** `plans/7-lean-review-verify/7-lean-review-verify-PROGRESS.md:12` (doc-claim) — Resume Context says there is no finish table and no open blocker, but finish-conditions.md is present and the undeclared mode variable fails its names-resolve row. A resumed executor is directed by stale state. → Update Resume Context to reflect the approved table and unresolved declaration.
- **7.1-r1-09** `CLAUDE.md:241` (doc-claim) — This new default-lean claim conflicts with ARCHITECTURE.md's current-component descriptions and version table, which still describe codex as the current review and verify path and list old skill versions. → Update ARCHITECTURE.md's review and verify descriptions and catalog versions for the lean default.

## NOTE (0)


## Checked and clear

engine: new subprocess calls use argument arrays rather than interpolated shells, engine: claude-lean judge value is accepted through the runner and gate consumers, skill frontmatter and changed Python syntax: static checks passed, SKILL.md lint: zero issues

## Not applicable

domain: generic repository; no Kalpa, PMG, or IRIS surface, engine: SQL, ORM, tenant queries, and database races, engine: frontend rendering, time windows, and cross-language JSON coercion, engine: publish pipeline and platform build matrix

**Verdict:** DO NOT SHIP

## What this review did not cover

- Could not run the unittest suite because its fixtures create temporary repositories and this sandbox is read-only.
- Could not run write-side or live-service verification in the read-only sandbox.
- Could not check browser behavior; no browser surface or browser access was available.
- Could not perform network-dependent checks; network access is restricted.
- Could not dispatch specialist sub-reviewers; parallel agent work was not authorized for this review.
