# Identity And Access

Source: `SPEC.md` sections 2.3, 5.1, 6.2, 8.1, 10.3, 10.4, 12, 14.3, and open question 22.6.

## Product Goal

Owners, admins, and end users need a trustworthy identity and access boundary so
every LiveLead action runs as an authenticated actor inside the correct
organization scope. The MVP already depends on organization scoping, role-based
surfaces, audit logging, and secret-safe governance, but the current repo still
uses development headers as a temporary boundary. This slice defines the first
real login, session, RBAC, and tenant-isolation contract that later member
management, notification, and SSO work can extend.

## MVP Scope

This product slice covers:

- Email-and-password sign-in for human users.
- A durable user identity and organization-membership model that replaces the
  current header-based development context.
- Time-bounded sessions with safe refresh or rotation behavior.
- Backend-enforced baseline roles for Owner, Admin, Analyst, Sales/BD,
  Reviewer, and Viewer across already implemented product surfaces.
- Tenant isolation rules that prevent cross-organization reads or writes.
- Generic login-failure responses, rate limiting, and temporary lockout or
  equivalent protection after repeated failed sign-in attempts.
- Minimal UI session handling for sign-in, sign-out, expired-session, and
  unauthorized states.
- Audit capture for login success, login failure, logout, denied access, and
  other authentication-relevant session events.

This product slice does not yet cover:

- Member invitation, disablement, role change, or access removal UX.
- Enterprise SSO, SAML, OIDC federation, or SCIM lifecycle management.
- MFA or step-up authentication.
- Password reset, email verification, or account-recovery workflows.
- Fine-grained permission editing beyond the baseline role matrix.

## Contract Rules

- Every API request and user-visible action must resolve to one authenticated
  actor and one active organization scope before business behavior runs.
- Backend authorization is the source of truth. UI route guards and hiding
  buttons are supportive only and must not be treated as sufficient protection.
- Authentication failures must stay generic and must not reveal whether an
  email exists, whether a password was close, or which organizations a person
  belongs to.
- Session state must expire predictably and support safe refresh or rotation
  without storing sensitive tokens in browser local storage.
- All already implemented organization-scoped product records remain subject to
  tenant isolation under the authenticated organization context.
- Role enforcement must cover at least the currently implemented governance
  surfaces: admin connector and policy operations, browser-profile management,
  audit-log access, campaign and discovery editing, content review, and lead
  workflow actions.
- Unauthorized and cross-tenant access attempts must fail safely and be
  auditable.
- The auth boundary must preserve room for a later SSO provider without forcing
  the first MVP slice to depend on that provider decision.

## API Surface

- `POST /auth/login`: authenticate a human user and start a governed session.
- `POST /auth/refresh` or equivalent session-rotation endpoint: refresh an
  expiring session safely.
- `POST /auth/logout`: end the current session and revoke its refresh path.
- `GET /auth/me` or equivalent session read: return current actor, active
  organization, role, and session-expiry summary.
- Existing product endpoints must consume authenticated tenant context instead
  of development headers once this slice lands.

## UI Surface

The first identity surface should stay focused on safe access, not broad account
administration:

- Sign-in page or modal for email and password.
- Session bootstrap on app load so the frontend can decide whether to render
  authenticated routes, redirect to sign-in, or show an expired-session state.
- Minimal current-user or current-workspace indicator sufficient to explain
  which role and organization the user is acting within.
- Clear unauthorized and session-expired states for protected routes such as
  admin governance pages and reviewer-only actions.
- No full member-management console in this slice.

## Validation Implications

- Unit proof should cover password-verification rules, role-matrix checks,
  generic-failure responses, and session-expiry or refresh behavior.
- Integration proof should cover login, logout, authenticated identity loading,
  cross-tenant blocking, and representative protected endpoints.
- E2E proof should cover sign-in, protected-route access, role-based denial, and
  session-expired recovery in the web UI.
- Logs and audit proof should confirm login success, login failure, logout, and
  denied-access events are recorded without leaking secrets.
- Platform proof should replace the current dev-header dependency in the
  verification path before future member-management, notification, or SSO
  stories build on it.
