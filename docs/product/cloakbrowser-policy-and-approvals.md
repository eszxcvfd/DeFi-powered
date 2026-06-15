# CloakBrowser Policy And Approvals

Source: `SPEC.md` sections 3.4, 5.3, 5.10, 10.3, 10.4, 11.3, and 14.2.

## Product Goal

Owners, admins, and compliance-minded operators need a governed way to enable
the optional CloakBrowser adapter only for narrowly approved sources. LiveLead
must define how CloakBrowser enablement is requested, approved, constrained,
audited, and disabled so the optional engine can exist behind explicit policy
gates without being treated as permission to evade source terms, bypass
challenges, or access unauthorized data.
This is an optional governance layer that supports the core MVP jobs in
`docs/product/mvp-scope-and-priorities.md`; it must not become the main product
direction or overshadow the seven core user jobs.

## MVP Scope

This product slice covers:

- Source-scoped CloakBrowser enablement behind explicit Owner/Admin and
  compliance approval.
- Approval metadata that records why CloakBrowser is allowed, for which source,
  under which legal or operational scope, and with which kill-switch controls.
- Runtime policy requirements for version pinning, checksum or signature
  verification when available, and no silent production auto-upgrade behavior.
- Kill-switch and revoke behavior so CloakBrowser can be disabled quickly for a
  source, tenant, or broader environment scope.
- Admin visibility into approval, runtime policy, and blocked-state status for
  CloakBrowser-capable connectors.

This product slice does not yet cover:

- A generalized compliance workflow engine for every product policy.
- Automatic justification generation or legal-policy drafting.
- Bypass behavior for CAPTCHA, MFA, rate limits, access controls, or source
  restrictions.
- Making CloakBrowser the default engine for browser sessions.
- Broad runtime packaging changes beyond the bounded policy and enablement
  contract.

## Contract Rules

- CloakBrowser is an optional adapter and must remain disabled by default.
- A source may use CloakBrowser only when both Owner/Admin approval and
  compliance approval are present and still valid.
- Approval must stay source-scoped and purpose-scoped; approval for one source
  or workflow must not implicitly authorize others.
- CloakBrowser enablement must not be interpreted as permission to bypass terms
  of service, bot challenges, login challenges, or unauthorized access rules.
- Runtime policy must pin the approved CloakBrowser version and verify
  checksum or signature when that evidence is available.
- Production environments must not auto-upgrade CloakBrowser without a fresh
  approval path or equivalent governed review.
- A kill switch must be able to disable CloakBrowser use quickly without
  requiring business-logic code changes.
- Audit and admin query surfaces must expose approval state, kill-switch state,
  and blocked reasons without leaking secrets or sensitive binary material.

## API Surface

- Admin-facing connector or source policy routes should expose whether
  CloakBrowser is requested, approved, blocked, or revoked for that source.
- Approval metadata reads should expose approver roles, decision timestamps,
  scope notes, runtime-policy status, and kill-switch state.
- Session or connector runtime selection should distinguish policy-denied,
  unapproved, revoked, checksum-failed, and disabled-engine outcomes.
- Kill-switch actions should return clear blocked or revoked results when a
  source that previously used CloakBrowser can no longer do so.

## Admin UI Surface

The first CloakBrowser policy slice should extend connector governance surfaces:

- Source or connector detail that shows whether CloakBrowser is requested,
  pending approval, approved, revoked, or blocked.
- Approval and revoke controls reserved for allowed roles, with clear scope and
  rationale fields.
- Runtime-policy indicators for version pinning, checksum or signature status,
  and kill-switch state.
- Clear blocked states explaining why CloakBrowser cannot be used for a source.

## Validation Implications

- Unit proof should cover approval-scope rules, kill-switch precedence, version-
  pin policy checks, and blocked-reason mapping.
- Integration proof should cover persistence of approval metadata, runtime
  policy enforcement, revoked or disabled states, and source-scoped engine
  selection behavior.
- E2E proof should cover admin approval or revoke flows and visible blocked or
  approved engine status for a source without widening session permissions.
- Logs or audit proof should confirm who approved, revoked, disabled, or tried
  to use CloakBrowser and why a request was allowed or blocked.
- Platform proof should keep the future CloakBrowser verification command wired
  into the Harness matrix without weakening existing browser-session safety
  proofs.
