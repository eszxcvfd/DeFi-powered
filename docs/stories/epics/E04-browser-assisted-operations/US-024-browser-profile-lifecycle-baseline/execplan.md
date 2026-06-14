# Exec Plan

## Goal

Define the first governed browser-profile lifecycle slice so LiveLead can
manage reusable profile-backed browser isolation with explicit consent,
tenant-scoped access, and expiry controls before optional CloakBrowser policy
work extends the browser stack.

## Scope

In scope:

- Admin create, list, detail, lock, renew, expire, and delete flows for
  governed browser profiles.
- Consent-aware storage-state or cookie retention when current policy allows
  it.
- Session launch rules for active, locked, expired, or deleted profiles.
- Audit visibility and secret-safe query behavior for profile lifecycle events.
- Expiry handling for inactive or time-limited profiles.

Out of scope:

- CloakBrowser approval workflow or engine selection beyond the current default
  adapter rules.
- CAPTCHA bypass, MFA bypass, or identity-evasion workflows.
- Broad end-user self-service profile management.
- New browser action permissions beyond the current session, read-only,
  confirmation, and debug-artifact slices.
- Cross-tenant shared profiles or unmanaged personal browser-state import.

## Risk Classification

Risk flags:

- Authorization.
- Data model.
- Audit/security.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- Authorization and audit/security because profile lifecycle governs who may
  reuse stored browser state and how secrets or consented cookies are handled.

## Work Phases

1. Discovery: confirm profile, consent, expiry, and session-usage requirements
   from `SPEC.md`, source-policy rules, and browser-session contracts.
2. Design: define profile states, consent model, encrypted state handling, and
   admin lifecycle boundaries.
3. Validation planning: design proof for state transitions, blocked profile
   launches, secret-safe reads, and expiry or delete effects.
4. Implementation: add the bounded profile lifecycle backend and admin UI
   surfaces.
5. Verification: prove governed profile creation, blocked states, session use,
   and lifecycle changes safely.
6. Harness update: leave a clean handoff for CloakBrowser policy work.

## Stop Conditions

Pause for human confirmation if:

- The story requires exposing raw cookie, storage-state, or secret payloads.
- Profile sharing or lifecycle needs to cross tenant boundaries.
- The slice requires a new secret-management or KMS architecture beyond the
  current bounded baseline.
- Compliance requirements imply broader policy governance than current product
  docs define.
