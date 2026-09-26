<!-- EXAMPLE — illustrative only; `suite` is a hypothetical test-suite CLI.
     Contract: templates/verify-contracts.md §8.2. -->
# Sign-in

**Status:** working
**Last evidence:** 2026-09-26 · rung 5 · run `5.2-20260926T110000-c3d4` (private)

## Sub-features
- Password sign-in
- Session expiry redirects back to sign-in, keeping the requested page

## How to get to it
Open the app root while signed out; the sign-in form is the landing page.

## Driving it with suite
- `suite sign-in --tenant clinic_3 --json` — signs in as the tenant's test user; exit 0 on a
  landed dashboard, 1 on a rejected login, 3 when the env is unreachable.
- `suite doctor` first when anything returns 3.

## Gotchas
- The test user's credential is a pointer (`credential_ref`), resolved by the suite; never
  paste it into a finish table or a verdict.
