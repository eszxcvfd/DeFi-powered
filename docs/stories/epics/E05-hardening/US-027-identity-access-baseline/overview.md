# Overview

## Current Behavior

LiveLead already exposes role-aware governance surfaces (admin connector and
policy operations, browser-profile management, audit-log access, content
review, and lead workflow actions) but every endpoint resolves the calling
actor and organization through development headers (`X-Organization-Id`,
`X-Actor-Role`, `X-Actor-Label`). There is no durable user record, no session
lifecycle, no password verification path, no real tenant membership boundary,
and no recorded login or denial event. Existing audit and RBAC checks are
advisory: the boundary still trusts whatever header the caller sent.

## Target Behavior

This story should establish the first real identity and access boundary for
LiveLead so every product action runs as an authenticated actor inside one
organization scope:

- A durable `User` table with PBKDF2-hashed password material, per-user salt,
  and a disabled flag.
- An `OrganizationMembership` table that links users to one organization with
  one role each, so the role matrix and tenant scope can be enforced from data
  rather than headers.
- A time-bounded, opaque, server-issued `Session` table accessed through an
  `HttpOnly`, `SameSite=Lax`, `Secure`-when-TLS cookie. Sessions support safe
  refresh, explicit logout, and reuse blocking.
- A login contract that always returns the same generic failure body for
  invalid credentials, unknown email, or disabled account, and that records
  the outcome in the audit log without leaking account-existence details.
- Backend-enforced baseline RBAC for Owner, Admin, Analyst, Sales/BD,
  Reviewer, and Viewer across already implemented governance surfaces,
  including the audit log, admin connector operations, browser-profile
  management, campaign and discovery editing, content review, and lead
  workflow actions.
- Backend-enforced tenant isolation: every protected read or write resolves to
  one organization, and cross-organization access fails with `404` or
  `403` while still leaving a denied audit row.
- Login rate limiting and a temporary lockout window after repeated failures
  from the same client.
- Minimal first-owner bootstrap so a fresh install can sign in without
  requiring a separate CLI step.
- Frontend sign-in, sign-out, and session bootstrap flow that can render an
  expired-session or unauthorized state for protected routes.

## Affected Users

- Owners and admins who need trustworthy identity, role enforcement, and audit
  capture for their actions.
- Analysts, Sales/BD users, Reviewers, and Viewers who need a deterministic
  sign-in surface and predictable unauthorized responses.
- Future implementation agents extending member management, notification, or
  SSO federation work, which must build on this baseline.

## Affected Product Docs

- `docs/product/identity-and-access.md`
- `docs/product/audit-log-and-governance.md`
- `docs/product/overview.md`
- `docs/product/platform-and-automation-policy.md`
- `docs/ARCHITECTURE.md`

## Non-Goals

- Member invitation, role-change, or access-revocation UX (US-028).
- Email delivery, password reset, email verification, or account recovery.
- Enterprise SSO, SAML, OIDC federation, or SCIM lifecycle.
- MFA, step-up authentication, or WebAuthn.
- Fine-grained permission editing below the baseline role matrix.
- Persistent Redis-backed rate limiting (the first slice keeps an in-process
  limiter; the design should still leave room for a Redis-backed upgrade).
- Account deletion or data anonymization workflows.
