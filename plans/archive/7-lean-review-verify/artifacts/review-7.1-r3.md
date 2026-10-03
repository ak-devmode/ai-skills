# /review — ai-skills @ `64c4a18ba28f6a7ed3497e35888626f4aa5ad4d2..a323fc059288dd98e824cc6013641444cf819972` (3 commits)

**Review:** `7.1-r3` · **Reviewer:** codex gpt-6-sol · **Passes:** engine ✓ · domain n/a — generic repo · lenses ✓
**mode: full (flag)**
**Findings:** 3 — every ID needs a disposition: `review.py dispose --scope <scope> --unit 7.1 --finding <ID> (--fixed <sha> | --rejected "<reason>" | --deferred "<TO-DO>")`

## BLOCKING (1)

- **7.1-r3-01** `review/scripts/review.py:173` (fail-open lenses §2) — A failed `git show` silently drops CLAUDE.md or ARCHITECTURE.md from the lean bundle and its not-covered list. The review can then report coverage without reading a governing document. → Distinguish a document absent at HEAD from a read failure. List absent documents as not covered and fail on other Git errors.

## SHOULD FIX (1)

- **7.1-r3-02** `review/scripts/review.py:172` (fail-open lenses §2) — For a symlinked CLAUDE.md or ARCHITECTURE.md, `git show HEAD:<doc>` returns the link target path, which this code presents as the document's contents. → Check the entry type at HEAD; resolve and read symlink targets safely, or list those documents as not covered.

## NOTE (1)

- **7.1-r3-03** `review/scripts/review.py:348` (doc-claim lenses §6) — The comment says uncovered files come from prepare's sidecar, but this range removes the sidecar and recomputes coverage. → Update the comment to describe recomputation.

## Checked and clear

Engine: shell injection and new-value consumers, Lenses: adjacent code, local maxima, dirty comments, Changed Python files parse successfully

## Not applicable

Domain rules: generic repository, Engine: SQL, ORM, frontend, time windows, and publishing

**Verdict:** DO NOT SHIP

## What this review did not cover

- Could not run the unittest suite: its fixtures create temporary repositories and the filesystem is read-only.
- Could not invoke the changed skill in a live Claude Code session.
- Could not perform write-side verification because the filesystem is read-only.
- Could not perform network-dependent checks because network access is restricted.
- Could not dispatch specialist sub-reviewers because parallel agent work was not authorized.
