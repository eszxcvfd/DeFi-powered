# Audit Log And Governance

Source: `SPEC.md` sections 5.1, 5.14, 6.2, 6.3, 7.2, 8.1, 10.3, 10.4, 10.6, and 14.3.

## Product Goal

Owners, admins, and compliance-minded operators need a governed audit surface
that explains who did what, when, against which tenant-scoped record, and with
what result. LiveLead already depends on auditability across login, source
policy, discovery control, content approval, browser confirmation, and lead
updates, but the MVP still needs one bounded contract for how audit records are
written, queried, redacted, and reviewed.
This is a supporting governance slice for the core MVP jobs in
`docs/product/mvp-scope-and-priorities.md`, not a new primary value track by
itself.

## MVP Scope

This product slice covers:

- Tenant-scoped audit entries for sensitive or contract-relevant actions across
  the implemented MVP flows.
- A standard audit shape with actor, actor type, action, target type or id,
  result, occurred time, request or session context, and secret-safe metadata.
- Audit capture for representative high-value actions such as login success or
  failure, source-policy decisions, discovery cancel or failure, content review
  decisions, confirmation-gated browser actions, lead stage changes, and
  governed browser-profile or CloakBrowser policy changes.
- A read-only admin-facing audit surface under Settings that supports filtered
  search and detail inspection without exposing raw secrets.
- Service-account or system-generated audit entries for background jobs and
  automated policy enforcement where no interactive user is present.
- Minimum immutability and retention-ready rules so later retention-policy and
  deletion stories build on a stable audit contract.

This product slice does not yet cover:

- A workspace retention-policy editor or retention cleanup jobs.
- Data deletion, anonymization, or privacy-request workflows.
- Connector-health dashboards or alerting surfaces.
- SIEM export, webhook fan-out, or external compliance integrations.
- Broad member invitation and role-management UX beyond audit visibility into
  those future actions.

## Contract Rules

- Every audit entry must remain organization-scoped and append-only from the
  application point of view.
- Success, failure, denied, cancelled, and expired outcomes are all auditable;
  the product must not record only successful actions.
- Audit metadata must never contain plaintext passwords, raw access tokens, full
  cookies, secret values, or other credential material.
- Login failure records must stay generic enough that the audit path does not
  weaken the product rule against revealing whether an email exists.
- Audit reads are owner/admin governance surfaces unless a later story adds a
  narrower read model for other roles.
- Audit queries should support actor, action family, target type, result, time
  range, and request or correlation identifiers so operators can reconstruct a
  workflow.
- System-triggered or service-account-triggered audit entries must remain
  distinguishable from human actions.
- Audit records should link to source policy, campaign, discovery job, content,
  lead, browser session, or profile identifiers without embedding large raw
  payloads when a reference is enough.
- The audit contract should preserve the later requirement for minimum retention
  windows without forcing retention configuration into this first slice.

## API Surface

- `GET /admin/audit-logs`: list audit entries with filterable fields such as
  actor, action family, target type, result, and time range.
- `GET /admin/audit-logs/{id}` or equivalent detail read: return the full
  governed record for one audit event.
- Existing product commands should be able to emit normalized audit events
  through an internal application boundary rather than custom route-level
  logging.

## Admin UI Surface

The initial governance surface should stay operator-focused:

- Settings -> Audit Log list with timestamp, actor, action, target, result, and
  quick filters.
- Detail panel or page that shows redacted metadata, request or correlation
  context, and linked record references when present.
- Clear empty, unauthorized, and redacted-metadata states.
- No inline editing or deletion of audit entries from the UI.

## Validation Implications

- Unit proof should cover event normalization, redaction, immutable write rules,
  and result-state mapping.
- Integration proof should cover persistence, tenant scoping, role-gated reads,
  representative event capture, and blocked unauthorized access.
- E2E proof should cover an owner/admin filtering the audit log and opening an
  entry created by an implemented workflow.
- Logs and audit proof should confirm that representative sensitive actions emit
  audit entries without leaking secrets.
- Platform proof should keep the audit APIs and admin audit UI wired into the
  Harness matrix before retention, deletion, connector-health, or auth stories
  build on them.
