# Design

## Domain Model

The story should formalize the first identity-boundary objects:

- `User`: human account with normalized email, display name, status, and
  password or external-auth credential reference.
- `OrganizationMembership`: actor-to-organization link with one baseline role
  and lifecycle state such as active, disabled, or invited-later.
- `AuthenticatedSession`: time-bounded session record with issued time, expiry,
  revocation state, refresh lineage or rotation metadata, and active
  organization context.
- `RolePolicy`: bounded permission matrix that maps the MVP roles Owner, Admin,
  Analyst, Sales/BD, Reviewer, and Viewer onto already implemented actions.
- `AuthAttempt`: normalized success or failure outcome used for rate limiting,
  lockout, and audit-safe diagnostics.

Business rules:

- A request may execute product behavior only when one authenticated actor and
  one active organization membership are resolved successfully.
- Password material must never be stored or logged in plaintext.
- Authentication failures must return generic user-facing errors even when the
  backend records more specific internal diagnostics.
- Sessions must expire predictably, support safe refresh or rotation, and be
  revocable on logout.
- Authorization decisions must be evaluated in backend commands, queries, or
  route boundaries, not only in the frontend.
- Cross-tenant reads and writes must fail safely even when record identifiers
  are otherwise valid.
- Temporary development headers must be removable or strictly dev-only once this
  story lands.

## Application Flow

- `LoginWithPassword` validates credentials, checks rate-limit or lockout state,
  resolves the active organization membership, starts a governed session, and
  records success or failure audit events.
- `RefreshAuthenticatedSession` rotates or refreshes an expiring session without
  reintroducing leaked browser-stored secrets.
- `LogoutAuthenticatedSession` revokes the active session and records logout in
  audit.
- `GetCurrentActorContext` resolves the current user, active organization, and
  baseline role for API and UI consumption.
- `AuthorizeAction` or equivalent shared policy boundary maps protected product
  actions to the baseline role matrix so routes stop inventing one-off header
  checks.
- Existing implemented surfaces should migrate onto the authenticated context in
  a bounded rollout rather than leaving some routes on dev headers and others on
  sessions.

## Interface Contract

Backend contract should minimally support:

- `POST /auth/login` for email-and-password sign-in.
- `POST /auth/refresh` or an equivalent safe session-rotation path.
- `POST /auth/logout` for current-session termination.
- `GET /auth/me` or equivalent current-session identity read.
- Consistent `401` vs `403` behavior so clients can distinguish unauthenticated,
  expired-session, and authenticated-but-unauthorized cases.

Expected payload concerns:

- Login responses should expose only the user, organization, role, and expiry
  information needed by the UI.
- Session secrets should stay in secure transport and storage boundaries; avoid
  frontend persistence in local storage.
- Protected routes should stop accepting `X-Actor-Role` and `X-Organization-Id`
  as the normal product contract, except possibly behind an explicit dev-only
  test harness switch if the repo still needs transitional fixtures.

## Data Model

- Add durable identity tables for users, organization memberships, and
  authenticated sessions, plus the minimum indexes needed for email lookup,
  membership lookup, and active-session validation.
- Keep current organization-scoped domain tables intact; the story should wire
  them to authenticated membership context rather than repartitioning every
  domain aggregate.
- Seed deterministic local development users and memberships so verification can
  prove role and tenant behavior without manual setup.
- Reuse the existing audit store for login and authorization events rather than
  creating a second auth-history source.
- Preserve room for a later external-identity provider link table without
  forcing SSO into the first baseline slice.

## UI / Platform Impact

- Add a minimal sign-in entry surface and protected-route bootstrap flow for the
  existing React app.
- Replace hard-coded admin header assumptions in E2E and frontend API access
  with story-owned auth helpers or fixtures.
- Show clear unauthorized and expired-session states on admin, reviewer, and
  other protected routes without degrading currently implemented user flows.
- Keep the first UX intentionally narrow: no full user directory, invite flow,
  or role editor in this story.

## Observability

- Record audit entries for login success, login failure, logout, and denied
  access on representative protected routes.
- Emit structured diagnostics for rate limiting, lockout state, invalid-session
  rejection, and cross-tenant access denial.
- Preserve request or correlation IDs so auth and audit events connect cleanly
  with existing route and worker traces.

## Alternatives Considered

1. Keep the header-based tenant context as the main contract and defer real auth
   until production hardening. Rejected because too many existing MVP stories
   already rely on role and tenant behavior for that boundary to remain
   non-product.
2. Make enterprise SSO the first and only login path. Rejected because the spec
   still allows configured providers later and the repo needs a bounded MVP
   login baseline before federation choices are finalized.
3. Store bearer tokens in local storage for simplicity. Rejected because it
   weakens the security boundary and conflicts with the repo's secret-handling
   direction.
