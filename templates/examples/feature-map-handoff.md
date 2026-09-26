<!-- EXAMPLE — illustrative only. Contract: templates/verify-contracts.md §8.3. -->
# Feature-map handoff — 5.2

**Schema version:** verify/1
**Result:** changed
**Test-suite:** wellmed/wellmed-testsuite
**Verdict log:** artifacts/verify-5.2.jsonl

`Result` is exactly one of `clean | changed | blocked`. `clean` has no rows; `blocked` names
what stopped the maintain pass in the first row.

| Feature | Change | What | Evidence |
|---|---|---|---|
| Sign-in | update | Status unknown → working; add the session-expiry sub-feature | run `5.2-20260926T110000-c3d4`, rung 5 |
