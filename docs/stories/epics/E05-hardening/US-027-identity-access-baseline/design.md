# Design

## Domain Model

The first identity-and-access boundary needs four new domain objects:

- `User`: durable human record with a server-issued identifier, email,
  display name, PBKDF2 password hash, per-user salt, disabled flag, and
  timestamps. Email is normalized to lowercase and treated as a unique handle.
- `PasswordMaterial`: PBKDF2-HMAC-SHA256 hash with a fixed iteration count
  and a per-user salt. The material is opaque to the rest of the system and
  is only verified through `verify_password`.
- `OrganizationMembership`: link row tying one user to one organization with
  one role. The combination `(user_id, organization_id)` is unique. The role
  is a small enum that maps to the existing `X-Actor-Role` vocabulary
  (`owner`, `admin`, `compliance`, `analyst`, `sales_bd`, `reviewer`,
  `viewer`).
- `Session`: opaque, server-issued record holding a salted token hash, the
  owning user and organization, a role snapshot, issued-at, expires-at, and
  revoked-at timestamps. The cleartext token is never stored and is only
  returned once at login and refresh.

Business rules:

- Login is constant-time and always returns the same generic failure body for
  unknown email, wrong password, and disabled account. Audit records the
  precise reason without surfacing it in the HTTP response.
- Passwords must be at least 12 characters and must not be the same as the
  email. Verification uses `hmac.compare_digest`.
- Sessions are time-bounded (default 8 hours, refresh extends the expires-at
  by another window but never reuses the original token).
- `Session.revoked_at` blocks reuse even if the cookie is replayed.
- A user without an active membership cannot authenticate; login fails the
  same way it fails for unknown email.
- Lockout state is tracked per `client_ip + email_hash` and unlocks after a
  configurable cooldown window.
- Login audit records the request id, client ip, user agent, and a redacted
  reason. The cleartext email is never persisted, only its hash.

## Application Flow

- `AuthService` owns the bounded login, refresh, logout, and `me` use cases
  and is the only place that touches the password verifier and the session
  repository.
- `RateLimiter` keeps a small in-process window of failed login attempts and
  short-circuits the login flow with a `LOCKED` outcome once the configured
  threshold is reached. The limiter is keyed by the SHA-256 of the email
  concatenated with the client IP so it cannot be used to enumerate emails.
- `IssueSession` writes a new `Session` row, returns the cleartext cookie
  value once, and records an `auth.login.succeeded` audit entry.
- `RotateSession` issues a new session row, marks the previous session
  `rotated_at`, and records `auth.session.rotated`.
- `RevokeSession` marks the session `revoked_at` and records
  `auth.session.revoked`. A revoked session blocks all future reads and
  rotates, even if the cookie is replayed.
- `RecordDeniedAccess` is a shared application helper that any RBAC check can
  call to record `auth.access.denied` audit entries without leaking the
  decision back to the caller.
- `BootstrapOwnerUseCase` is a one-shot startup check: if there is no
  `User` and no `OrganizationMembership` for the dev organization, it creates
  the seeded owner with the documented default password, hashed with PBKDF2.

## Interface Contract

Backend contract:

- `POST /auth/login`: body `{ email, password }`. Returns `200` with a
  `Set-Cookie` session token and a JSON body that summarizes the current
  actor, organization, role, and session expiry. Returns `401` with the same
  generic body for any credential or lockout failure.
- `POST /auth/refresh`: rotates the active session. Returns the same body
  shape as login plus a refreshed `Set-Cookie`.
- `POST /auth/logout`: revokes the active session. Returns `204` and clears
  the cookie.
- `GET /auth/me`: returns the current actor, organization, role, and session
  expiry. Returns `401` when no valid session is present.
- Existing endpoints continue to accept the development headers only when no
  valid session is present (controlled by the
  `LIVELEAD_AUTH_ALLOW_DEV_HEADERS` setting, default `true` in tests and
  `false` outside tests), so unit and integration tests can still drive the
  routes while production callers must use the cookie.

Expected payload concerns:

- The login response never reveals whether the email exists, whether the
  password was close, or which organizations a user belongs to.
- `Set-Cookie` attributes are `HttpOnly`, `SameSite=Lax`, `Path=/`, and
  `Secure` when the request is TLS-terminated.
- The session cookie name is `livelead_session` and the value is a 256-bit
  URL-safe random token.
- The auth router writes audit entries through the existing `AuditService`,
  reusing the redaction rules and the generic error envelope.

## Data Model

Three new tables in the project-local SQLite store:

- `users` (`id`, `email` unique, `email_hash`, `display_name`, `password_hash`,
  `password_salt`, `password_iterations`, `disabled`, `last_login_at`,
  `failed_attempts`, `locked_until`, `created_at`, `updated_at`).
- `organization_memberships` (`id`, `user_id`, `organization_id`, `role`,
  `state`, `created_at`, `updated_at`; unique on
  `(user_id, organization_id)`).
- `sessions` (`id`, `user_id`, `organization_id`, `role`, `token_hash`,
  `issued_at`, `expires_at`, `last_seen_at`, `rotated_at`, `revoked_at`,
  `client_ip`, `user_agent`, `created_at`).

The migration also adds a unique index on `users.email_hash` and a composite
index on `sessions(organization_id, expires_at)` for tenant-isolated
lookups. A `LIVELEAD_AUTH_DEFAULT_OWNER_EMAIL`,
`LIVELEAD_AUTH_DEFAULT_OWNER_PASSWORD`, and
`LIVELEAD_AUTH_ALLOW_DEV_HEADERS` setting are added to the runtime settings
and used by the bootstrap and the dependency layer.

## UI / Platform Impact

- A new `SignInPage` renders the email and password form, surfaces generic
  errors, and on success redirects to the originally requested route.
- An `AuthBootstrap` wrapper around the existing `AppLayout` loads the
  current session on first paint, redirects to `/sign-in` when the session
  is missing, and shows an expired-session banner when the session is no
  longer valid.
- The sidebar shows a small "Signed in as <email> · <role>" indicator and a
  sign-out button that posts to `/auth/logout` and clears the in-memory
  session.
- Admin-only routes continue to use the existing role checks; the
  difference is that the role now comes from the session, not the header.
- No new platform components are introduced beyond the cookie, the
  bootstrap, and the page.

## Observability

- The request logging middleware records the resolved actor id, role, and
  organization for every protected request so future traces can correlate
  HTTP -> audit entry.
- Login success, login failure, lockout, refresh, and logout emit audit
  entries with a redacted `reason` field.
- Passwords, cleartext session tokens, full cookies, and bearer tokens are
  never logged or persisted.
- The `last_seen_at` column on `sessions` is updated on every authenticated
  request so operators can later reason about session age.

## Alternatives Considered

1. Keep the header-based dev boundary and only add an audit log for it.
   Rejected because the SPEC requires real authentication, RBAC, and tenant
   isolation, and because the existing header path is not a safe production
   boundary.
2. Use a third-party identity provider for the first slice. Rejected because
   the SPEC allows the first slice to keep an internal identity model and
   because introducing a third-party provider would force a decision the
   repo has not yet made.
3. Use JWT for the session token. Rejected for the first slice because the
   baseline needs an authoritative server-side revoke, and JWTs without a
   persistent server-side index make that harder to enforce and audit.
4. Add role enforcement only on the admin routes and leave the other
   endpoints header-driven. Rejected because the SPEC requires backend
   enforcement across the implemented governance surfaces and because
   leaving headers authoritative would create a hidden second trust path.
