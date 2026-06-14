# Overview

## Current Behavior

LiveLead can now run supervised browser sessions, allowlisted actions,
confirmation-gated side-effect actions, and governed debug artifacts, but it
still lacks a first-class admin lifecycle for reusable browser profiles. The
product has no bounded contract yet for creating, locking, expiring, renewing,
or deleting browser profiles, and no governed rule set for when consented
cookies or storage state may back later supervised sessions.

## Target Behavior

This story should establish the first browser profile-lifecycle slice:

- Let admins create and govern browser profiles used for supervised session
  isolation.
- Allow locking, expiring, renewing, and deleting profiles with clear status
  feedback.
- Persist consent-aware cookie or storage-state material only when policy and
  user approval allow it.
- Block new session launches from ineligible profiles and expose why they are
  blocked.
- Preserve audit-safe and secret-safe lifecycle handling without widening
  browser action permissions.

## Affected Users

- Admins who need to govern reusable browser profiles and their lifecycle.
- Analysts or Sales/BD users who may launch supervised sessions from approved
  governed profiles.
- Security or compliance-minded operators who need consent, expiry, and audit
  controls around stored browser state.

## Affected Product Docs

- `docs/product/browser-profile-lifecycle-and-consent.md`
- `docs/product/browser-session-console-and-isolation.md`
- `docs/product/source-registry-and-policy.md`
- `docs/product/platform-and-automation-policy.md`
- `docs/product/browser-debug-artifacts-and-retention.md`

## Non-Goals

- CloakBrowser approval workflow or feature gating.
- Broad secret-management redesign beyond this profile slice.
- Cross-tenant shared profiles.
- New outbound, destructive, or autonomous browser action permissions.
- Automatic challenge bypass or login bypass behavior.
