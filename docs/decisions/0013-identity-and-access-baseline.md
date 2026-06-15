# 0013 Identity and Access Baseline

Date: 2026-06-15

## Status

Accepted

## Context

`SPEC.md` requires the system to authenticate human users, enforce a
role-based access control matrix, isolate one organization from another, and
record login, logout, and denied-access events in the audit log. The
repository currently trusts development headers (`X-Organization-Id` and
`X-Actor-Role`) at the HTTP boundary, has no durable user record, no session
lifecycle, and no real RBAC check. The audit log can describe governance
actions but cannot describe who actually performed them, because the caller
is whoever sets the header. The architecture decision `0009` names
identity and tenancy as a first-class core domain, and the
`docs/product/identity-and-access.md` product doc records the same
requirement as the first identity and access baseline before member
management, email delivery, or SSO federation work can land.

## Decision

US-027 introduces the first real identity and access boundary for LiveLead:

- A durable `User` table with a PBKDF2-HMAC-SHA256 password hash, per-user
  salt, and a disabled flag.
- A durable `OrganizationMembership` table that links one user to one
  organization with one role, so the role matrix and tenant scope are
  enforced from data rather than headers.
- A durable `Session` table holding a salted token hash, the owning user and
  organization, a role snapshot, and explicit `rotated_at` and `revoked_at`
  markers. Cleartext session tokens are never persisted.
- Server-issued opaque session tokens delivered as `HttpOnly`, `SameSite=Lax`
  cookies, with a default eight-hour TTL and explicit refresh and logout
  endpoints.
- A login contract that always returns the same generic failure body for
  unknown email, wrong password, disabled account, or lockout, while
  recording the precise reason in the audit log.
- Backend-enforced RBAC for the existing `owner`, `admin`, `analyst`,
  `sales_bd`, `reviewer`, and `viewer` roles across the audit log, admin
  connector, browser profile, content review, and lead workflow surfaces.
- Backend-enforced tenant isolation: every protected read or write resolves
  to one organization, and cross-organization calls fail with `404` for
  read-by-id and `403` for RBAC denial while still leaving a denied audit
  row when the access check is invoked.
- A small in-process login rate limiter keyed by `client_ip + email_hash`
  with a configurable threshold and cooldown, designed to be replaced by a
  Redis-backed limiter later without changing the public contract.
- A one-shot `BootstrapOwnerUseCase` that creates a seeded owner in the dev
  organization on application startup so a fresh install can sign in
  without a separate CLI step.
- A new `LIVELEAD_AUTH_ALLOW_DEV_HEADERS` setting (default `true` in tests,
  `false` elsewhere) that gates the legacy header path so the new dependency
  layer can ship alongside the existing routes without breaking unit and
  integration tests.

The session-aware `TenantContext` dependency prefers the real session when a
valid cookie is present and falls back to the development headers only when
the setting above allows it. The boundary still reads `X-Organization-Id`
and `X-Actor-Role` for callers that do not have a session, which preserves
the existing verification scripts and the rest of the e2e suite until the
later member-management, notification, and SSO stories rewrite them.

## Alternatives Considered

1. Keep the header-based dev boundary and only add an audit log for it.
   Rejected because the SPEC requires real authentication and tenant
   isolation, and the existing header path is not a safe production
   boundary.
2. Use a third-party identity provider for the first slice. Rejected
   because the SPEC allows the first slice to keep an internal identity
   model, and because introducing a third-party provider would force a
   decision the repo has not yet made.
3. Use JWT for the session token. Rejected for the first slice because the
   baseline needs an authoritative server-side revoke, and JWTs without a
   persistent server-side index make that harder to enforce and audit.
4. Add role enforcement only on the admin routes and leave the other
   endpoints header-driven. Rejected because the SPEC requires backend
   enforcement across the implemented governance surfaces, and because
   leaving headers authoritative would create a hidden second trust path.

## Consequences

Positive:

- Future member management, password reset, email verification, and SSO
  federation work can build on a stable identity model instead of starting
  from headers.
- Audit entries now describe real actors, real organizations, and real
  roles, so governance, retention, and compliance workflows can rely on
  them.
- Cross-tenant reads and writes are no longer dependent on the caller
  picking the right header.

Tradeoffs:

- The dependency layer must keep a small fallback path for the development
  headers, which means the boundary has two entry modes (session cookie and
  header) and operators must remember to disable the header path in
  production.
- The first slice uses an in-process rate limiter; multi-process or
  multi-node deployments will need a Redis-backed replacement later.

## Follow-Up

- US-028 member management baseline should consume the same
  `OrganizationMembership` and `User` tables and should call
  `RevokeSession` whenever access is removed.
- A future password reset and email verification story should reuse the
  password verifier and the generic-failure rule.
- A future SSO federation story should issue `Session` rows through the
  same service rather than introducing a parallel auth path.
- A future retention and deletion story should be able to use the
  `revoked_at` column to decide which session rows to keep.
