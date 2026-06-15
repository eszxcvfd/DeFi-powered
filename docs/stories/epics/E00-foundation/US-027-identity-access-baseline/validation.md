# Validation

## Proof Strategy

This story is done only when LiveLead can authenticate a human user, derive the
correct organization-scoped role context, protect representative implemented
surfaces with backend RBAC, reject cross-tenant access safely, and emit
secret-safe auth audit events without relying on the current header-based dev
contract as the primary product path.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Password verification, role-policy evaluation, generic failure messaging, session expiry or rotation, and lockout threshold rules. |
| Integration | `POST /auth/login`, `GET /auth/me`, logout or refresh behavior, protected-route `401/403` responses, cross-tenant blocking, and seeded-membership role access for representative campaign, admin, reviewer, and lead routes. |
| E2E | User signs in through the web UI, loads an allowed route, is denied from a restricted route for the wrong role, and recovers from an expired session by signing in again. |
| Platform | Story verification command proves frontend, backend, seeded dev fixtures, and auth-aware route wiring succeed without the old header-only path as the primary proof chain. |
| Performance | Repeated failed login attempts trigger bounded rate limiting or temporary lockout without destabilizing the app. |
| Logs/Audit | Login success, login failure, logout, and representative authorization denial create redacted audit records and structured diagnostics without leaking passwords or session secrets. |

## Fixtures

- At least two organizations with deterministic seeded users.
- One user each for Owner, Admin, Analyst, Sales/BD, Reviewer, and Viewer.
- One protected admin surface, one reviewer-only or reviewer-sensitive flow, and
  one standard analyst or sales flow already implemented in the repo.
- One cross-tenant record fixture proving valid IDs from another organization
  still fail safely.

## Commands

Add commands after scripts exist.

```text
TBD
Suggested: ./scripts/verify-us-027.sh
Suggested: scripts/bin/harness-cli story verify US-027
```

## Acceptance Evidence

Add results after verification.
