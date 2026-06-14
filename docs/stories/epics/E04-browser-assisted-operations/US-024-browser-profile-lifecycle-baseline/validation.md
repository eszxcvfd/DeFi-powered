# Validation

## Proof Strategy

This story is done only when LiveLead can govern browser-profile lifecycle
state, store consented browser-state material safely, block ineligible profile-
backed sessions, and preserve tenant-scoped audit visibility without exposing
raw secrets.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Profile-state transitions, consent gating, expiry calculation, delete or lock rules, and secret-safe serialization. |
| Integration | Profile persistence, encrypted state-material handling, profile-backed session launch, blocked lock or expiry states, and delete or revoke effects. |
| E2E | Admin creates or renews a profile, sees consent and expiry status, launches a supervised session with an eligible profile, and sees blocked behavior for an expired or locked profile. |
| Platform | Story verify command keeps browser-profile APIs, session-launch checks, and admin lifecycle surfaces wired into the Harness matrix. |
| Performance | Profile list and lifecycle transitions remain responsive in local proof, and expiry handling does not leave stuck active profiles or orphaned state references. |
| Logs/Audit | Profile creation, consent recording, session use, lock, expiry, renew, and delete remain diagnosable with actor, tenant, profile, policy result, and terminal status. |

## Fixtures

- Seeded tenant with admin role and one governed connector or source policy that
  allows profile-backed sessions.
- Deterministic supervised-session fixture that can capture consent for stored
  browser state.
- Locked-profile, expired-profile, and deleted-profile fixtures for safe-failure
  proof.
- Unauthorized actor fixture and policy-denied retention fixture for negative-
  path coverage.

## Commands

```text
- ./scripts/verify-us-024.sh — planned story verification chain for browser profile lifecycle coverage
- frontend/e2e/browser-profile-lifecycle.spec.ts — planned browser proof for admin profile lifecycle and governed session use
```

## Acceptance Evidence

- `tests/unit/test_browser_profile_lifecycle.py` — state transitions, consent, expiry, and secret-safe serialization
- `tests/integration/test_browser_profiles_api.py` — profile CRUD lifecycle, session launch checks, and revoke handling
- Admin UI with governed browser profile lifecycle and blocked-state feedback
- `scripts/bin/harness-cli story verify US-024` — pass after the verify command is added
