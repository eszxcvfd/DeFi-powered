# Browser Profile Lifecycle And Consent

Source: `SPEC.md` sections 5.3, 5.10, 7.2, 10.3, 10.4, 11, 14.2, and `UC-04`.

## Product Goal

Admins and supervised browser users need governed browser profiles that can
persist allowed session state without turning temporary automation context into
an uncontrolled credential store. LiveLead must define how browser profiles are
created, locked, expired, renewed, and deleted, how consented cookie or storage
state may be attached to them, and how the system keeps profile access tenant-
scoped, auditable, and secret-safe.
This profile lifecycle exists to support governed access for the core MVP jobs
in `docs/product/mvp-scope-and-priorities.md`; it should not become a product
goal separate from discovery, analysis, engagement, and pipeline tracking.

## MVP Scope

This product slice covers:

- Admin-managed browser profiles that may be created, locked, expired, renewed,
  and deleted.
- Clear linkage between a governed browser profile and a supervised browser
  session when profile-backed isolation is used.
- Consent-aware storage of cookies or storage state only when the user
  explicitly approves and source or workspace policy allows it.
- Expiry and inactive-profile handling so dormant profiles stop being silently
  reusable.
- Audit and access controls for profile lifecycle and profile-backed session
  usage.

This product slice does not yet cover:

- CloakBrowser approval workflow or engine enablement policy.
- Automatic login bypass, CAPTCHA bypass, MFA bypass, or identity-evasion
  behavior.
- Broad secret-management redesign outside the bounded profile and storage-state
  contract.
- Cross-tenant shared browser profiles.
- Full self-service end-user profile administration outside the admin-governed
  lifecycle.

## Contract Rules

- Browser profiles are governed tenant-scoped assets, not personal unmanaged
  browser state.
- A profile may be used only when it is active, not expired, not locked, and
  allowed by current workspace and source policy.
- Cookies or storage state may be saved only after explicit user consent and
  only when the current source policy permits that retention.
- Saved browser-state material must be encrypted at rest, must not be written
  to logs in plaintext, and must not be returned in raw form from normal admin
  or session query surfaces.
- Profile lifecycle actions such as create, lock, renew, expire, and delete
  must remain role-gated and auditable.
- Expired profiles must no longer back new supervised sessions until they are
  renewed or replaced through an allowed admin workflow.
- Deleting a profile must revoke future use of the profile and should remove or
  disable associated stored browser-state material according to retention rules.
- Profile lifecycle must support supervised browser work without widening which
  browser actions are allowed in a session.

## API Surface

- Admin-facing profile management routes should support create, list, detail,
  lock, renew, expire, and delete flows.
- Session creation should expose whether the session uses an ephemeral isolated
  context or a governed stored profile.
- Profile query responses should expose lifecycle status, last-used metadata,
  expiry state, and secret-presence or consent status without returning raw
  cookie or storage-state payloads.
- Profile deletion, lock, and expiry errors should distinguish unauthorized,
  active-in-use, already-expired, and policy-blocked outcomes.

## Admin UI Surface

The first profile-lifecycle slice should extend the browser-admin surfaces:

- Browser profile list with status, last used, expiry, and consent-state cues.
- Create or renew profile flow that makes consent and policy prerequisites
  visible.
- Lock, expire, delete, and reactivate or renew controls with safe feedback.
- Clear blocked states when a profile cannot be used because of policy, expiry,
  or missing consent.

## Validation Implications

- Unit proof should cover profile-state transitions, consent gating, expiry
  calculation, and secret-safe serialization rules.
- Integration proof should cover persistence, encrypted browser-state handling,
  session launch with active or blocked profiles, and delete or expiry effects.
- E2E proof should cover admin profile lifecycle actions and a supervised
  session using an eligible profile without exposing raw stored browser state.
- Logs or audit proof should confirm who created, changed, used, expired, or
  deleted a profile and whether stored browser-state retention was consented.
- Platform proof should keep the future browser-profile verification command
  wired into the Harness matrix before CloakBrowser policy work builds on it.
