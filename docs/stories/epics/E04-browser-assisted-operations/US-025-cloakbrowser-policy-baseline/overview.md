# Overview

## Current Behavior

LiveLead now has governed browser sessions, read-only actions, confirmation
flows, debug artifacts, and browser-profile lifecycle controls, but the product
still lacks a bounded contract for the optional CloakBrowser adapter. There is
no first-class approval model yet for when a source may use CloakBrowser, no
explicit kill-switch contract, and no policy surface that ties runtime
provenance checks to source-scoped enablement.

## Target Behavior

This story should establish the first CloakBrowser policy slice:

- Keep CloakBrowser disabled by default and source-scoped when enabled.
- Require explicit Owner/Admin and compliance approval before a source may use
  CloakBrowser.
- Record runtime-policy checks such as version pinning and checksum or
  signature verification when available.
- Allow rapid revoke or kill-switch disablement without changing business logic.
- Expose clear approved, pending, revoked, blocked, and runtime-failed states in
  admin governance surfaces.

## Affected Users

- Owners and admins who govern which sources may use optional browser engines.
- Compliance or security-minded operators who need durable approval and revoke
  visibility.
- Analysts or Sales/BD users who need understandable blocked or approved
  browser-engine behavior without assuming CloakBrowser is always available.

## Affected Product Docs

- `docs/product/cloakbrowser-policy-and-approvals.md`
- `docs/product/platform-and-automation-policy.md`
- `docs/product/source-registry-and-policy.md`
- `docs/product/browser-profile-lifecycle-and-consent.md`

## Non-Goals

- Any behavior that bypasses CAPTCHA, MFA, source terms, or access controls.
- Making CloakBrowser the default browser engine.
- Broad compliance workflow automation beyond this source-scoped approval slice.
- Packaging redesign outside bounded runtime provenance and kill-switch rules.
- New browser action permissions or outbound automation behavior.
