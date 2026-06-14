# Design

## Domain Model

The story should formalize the first governed browser-profile objects:

- `BrowserProfile`: tenant-scoped profile aggregate with lifecycle state,
  ownership metadata, expiry, and allowed session-usage metadata.
- `BrowserProfileState`: bounded states such as active, locked, expired,
  pending-renewal, deleting, and deleted.
- `BrowserProfileConsent`: consent and policy record that explains whether
  cookie or storage-state retention is allowed for the profile.
- `BrowserProfileStateMaterial`: encrypted browser-state payload reference such
  as cookies or storage state, stored behind secret-safe boundaries rather than
  inline query responses.
- `BrowserProfileUsage`: last-used and current-session linkage metadata needed
  to explain why a profile may or may not be reusable.

Business rules:

- Browser profiles must remain tenant-scoped governance assets.
- Only authorized admin roles may create, lock, renew, expire, or delete
  profiles.
- A profile can back a new supervised session only while active, unexpired, and
  policy-eligible.
- Saving cookie or storage-state material requires explicit user consent and a
  source-policy allowance.
- Secret-bearing browser-state material must be encrypted at rest and hidden
  from normal read surfaces and logs.
- Deleting or expiring a profile must revoke future reuse and preserve audit
  explainability.

## Application Flow

- `CreateBrowserProfile` creates a governed profile record with initial policy,
  expiry, and consent requirements.
- `RecordBrowserProfileConsent` records whether a user approved storage-state
  retention for the profile in the relevant supervised session context.
- `StoreBrowserProfileStateMaterial` persists encrypted cookie or storage-state
  material when consent and policy are both satisfied.
- `ListBrowserProfiles` and `GetBrowserProfile` return lifecycle metadata,
  allowed usage status, and secret-safe summaries.
- `LockBrowserProfile`, `RenewBrowserProfile`, `ExpireBrowserProfile`, and
  `DeleteBrowserProfile` enforce bounded state transitions and safe terminal
  behavior.
- Session-launch flows should resolve whether a selected profile is reusable or
  blocked because of lock, expiry, deletion, consent, or policy state.

## Interface Contract

Backend contract should minimally support:

- Admin profile create, list, detail, lock, renew, expire, and delete routes.
- Session-creation payloads or responses that indicate when a governed profile
  is selected or when a selected profile is blocked.
- Error states for unauthorized profile actions, missing consent, expired
  profile, active-in-use delete attempts, and policy-denied state retention.
- Secret-safe profile summaries that expose presence or status of stored state
  material without returning raw payloads.

Expected payload concerns:

- Raw cookie or storage-state material must not be returned from standard
  profile APIs.
- API responses should make expiry, lock, and consent status explainable enough
  for admin and session-launch UI decisions.
- The contract should leave room for later CloakBrowser policy metadata without
  redefining the profile core.

## Data Model

- Store browser-profile metadata in SQLite with tenant, creator, lifecycle
  state, expiry timestamps, last-used timestamps, consent status, and usage
  references.
- Store secret-bearing browser-state material as encrypted data or an encrypted
  external reference, not as plaintext in logs or UI-facing fields.
- Keep enough metadata to support safe expiry sweeps, delete workflows, and
  session launch checks.
- Preserve audit evidence that state material existed or was revoked without
  leaking the material itself.

## UI / Platform Impact

- Extend admin-facing browser or connector management surfaces with a browser
  profile list and detail flow.
- Show lifecycle status, consent status, last used, and expiry feedback clearly.
- Make lock, renew, expire, and delete flows visible and reversible only where
  policy allows.
- Keep session-launch surfaces able to explain when a selected profile is
  blocked or unavailable.

## Observability

- Record audit and diagnostics for profile create, consent record, state
  storage, lock, renew, expire, delete, and session launch with profile use.
- Keep structured signals for blocked reuse reasons, expiry sweeps, and
  unauthorized access attempts.
- Preserve enough correlation to link source-policy decision, supervised
  session, browser profile, and profile-state lifecycle changes.

## Alternatives Considered

1. Keep all supervised sessions ephemeral with no governed reusable profiles.
   Rejected because the SPEC explicitly requires browser profile lifecycle and
   consent-aware saved state handling.
2. Return raw cookie or storage-state payloads to admins for easier debugging.
   Rejected because it violates secret-safe and privacy-safe handling rules.
3. Fold profile lifecycle directly into the later CloakBrowser policy story.
   Rejected because profile governance is engine-agnostic and should exist
   before optional CloakBrowser controls widen the browser surface.
