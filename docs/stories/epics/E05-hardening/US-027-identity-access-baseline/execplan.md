# Exec Plan

## Goal

Replace the header-based development auth boundary with a real, audited,
tenant-isolated, role-aware identity baseline that downstream member
management, notification, and SSO work can extend without redoing auth.

## Scope

In scope:

- Durable `User`, `OrganizationMembership`, and `Session` ORM models with a
  matching Alembic migration.
- PBKDF2-hashed password storage with per-user salt and constant-time
  verification helpers.
- Opaque session tokens delivered as `HttpOnly`, `SameSite=Lax` cookies, with
  a configured TTL, refresh support, and safe logout that invalidates the
  session row.
- Login, logout, refresh, and `me` routes that emit audit entries for success,
  failure, lockout, and logout outcomes.
- A session-aware `TenantContext` dependency that prefers the real session
  over development headers, while still allowing the existing header path
  under controlled test conditions.
- Backend role enforcement helpers for Owner, Admin, Analyst, Sales/BD,
  Reviewer, and Viewer, applied to the audit log, admin connector, browser
  profile, content review, and lead workflow routes.
- Tenant isolation in audit and admin reads so cross-organization calls fail
  safely with `404` (when the row exists) or `403` (when the role is wrong)
  and a denied audit row is recorded for the unauthorized case.
- Login rate limiting keyed by `client_ip + email_hash` with a configurable
  lockout window after repeated failures.
- First-owner bootstrap on application startup so a fresh install can sign in
  with the seeded `owner@example.com` / `Owner!2345` credentials.
- Frontend sign-in, sign-out, expired-session, and unauthorized states with a
  clear current-user or current-workspace indicator.

Out of scope:

- Member invitation, role-change, or revoke-access UX (US-028).
- Email delivery, password reset, email verification, or account recovery.
- Enterprise SSO, SAML, OIDC federation, or SCIM.
- MFA or step-up authentication.
- Fine-grained permission editing.
- Account deletion or data anonymization workflows.

## Risk Classification

Risk flags:

- Auth.
- Authorization.
- Data model.
- Audit/security.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- Auth and audit/security because the story adds real authentication while
  rewriting the existing header-based boundary.

## Work Phases

1. Discovery: confirm identity, RBAC, tenant, and audit requirements from
   `SPEC.md`, the identity-and-access product doc, the audit-log contract, and
   the existing `tenant_context` boundary.
2. Design: define user, membership, and session shapes, password hashing,
   session cookie contract, role matrix, and audit capture points.
3. Validation planning: design unit, integration, E2E, and platform proof for
   login, lockout, RBAC denial, cross-tenant blocking, and audit capture.
4. Implementation: add the bounded backend auth path, the new dependencies,
   the Alembic migration, the bootstrap seed, the audit integration, and the
   frontend sign-in flow.
5. Verification: run `scripts/verify-us-027.sh` plus the unit, integration,
   and E2E test commands and update the Harness matrix.
6. Harness update: leave a clean handoff for member management, email
   delivery, password reset, and SSO federation stories.

## Stop Conditions

Pause for human confirmation if:

- The first-owner bootstrap credentials need to differ from the documented
  defaults, or the default must persist to a secret store.
- The login contract must change beyond the generic-failure rule, such as
  returning per-account failure details, lockout counters, or MFA prompts.
- The session cookie contract must include cross-site cookies, third-party
  authentication, or browser local-storage tokens.
- A new role or governance rule is required before implementation can be
  complete (such as Sales/BD-only routes or Reviewer-specific features).
- Cross-tenant read responses need to expose existence information, for
  example by returning `404` versus `403` differently from this baseline.
