# Validation

## Proof Strategy

This story is done only when LiveLead can authenticate a real user, resolve
the actor to one organization and one role from durable data, enforce that
role and organization scope on implemented governance surfaces, fail
cross-tenant or unauthorized access safely, and record the relevant audit
events without leaking credentials, tokens, or account-existence details.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | PBKDF2 hashing and verification, generic-failure normalization, role matrix checks, session token generation, and rate-limit window logic. |
| Integration | Login, refresh, logout, `me` round-trip, session-cookie round-trip, RBAC denial on audit log and admin connector, cross-tenant blocking, and lockout after repeated failures. |
| E2E | Sign-in via the web UI, expired-session and unauthorized redirects, sign-out, and the admin audit log picking up the new login and denial events. |
| Platform | Story verify command keeps auth APIs, the bootstrap seed, the FE sign-in flow, and the audit integration wired into the Harness matrix. |
| Performance | Login and audit reads remain responsive in local proof conditions and the new dependency layer does not regress the existing endpoints. |
| Logs/Audit | Login success, login failure, lockout, refresh, logout, and denied access events are recorded with redacted metadata and the request id used by the request logging middleware. |

## Fixtures

- Seeded multi-tenant workspace with at least one owner, one admin, one
  analyst, and one disabled user in separate organizations.
- A configured bootstrap owner so a fresh install can sign in with the
  documented credentials.
- A locked-out fixture that has reached the failed-attempt threshold and
  remains locked until the cooldown expires.
- Cross-tenant read fixture and unauthorized viewer fixture for negative
  path proof.

## Commands

```text
- ./scripts/verify-us-027.sh — story verification chain for identity access baseline
- frontend/e2e/identity-access.spec.ts — browser proof for sign-in, sign-out, expired-session, and audit log integration
```

## Acceptance Evidence

- `tests/unit/test_passwords.py` — PBKDF2 hashing, verification, and rejection rules
- `tests/unit/test_sessions.py` — token generation, hashing, and constant-time checks
- `tests/unit/test_roles.py` — role matrix and RBAC policy helpers
- `tests/integration/test_auth_api.py` — login, refresh, logout, me, and audit capture
- `tests/integration/test_auth_rbac_and_tenant_isolation.py` — cross-tenant blocking, role denial, and lockout
- Frontend sign-in and sign-out flow
- `scripts/bin/harness-cli story verify US-027` — pass after the verify command is added
