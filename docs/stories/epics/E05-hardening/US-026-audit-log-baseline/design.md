# Design

## Domain Model

The story should formalize the first audit-governance objects:

- `AuditEntry`: durable event record with tenant scope, actor, action, target,
  result, timestamps, and redacted metadata.
- `AuditActor`: human user, service account, or system actor descriptor with the
  minimum identity needed for review.
- `AuditTarget`: normalized target reference for campaign, source, job, content,
  lead, browser session, profile, or policy objects.
- `AuditOutcome`: bounded result such as succeeded, failed, denied, cancelled,
  expired, or system-recorded.
- `AuditContext`: request, correlation, session, IP, and workflow reference
  fields that help reconstruct a cross-surface action safely.

Business rules:

- Audit entries must remain append-only from the application point of view.
- Audit capture must include denied and failed actions, not only successful
  actions.
- Audit metadata must be redacted before persistence when values contain secret
  or credential material.
- Audit reads must remain tenant-scoped and role-gated to owner/admin surfaces.
- Login success and failure should both be auditable without exposing account-
  existence details in user-visible responses.
- System or service-generated entries must remain distinguishable from interactive
  user actions.

## Application Flow

- `RecordAuditEntry` should be the shared application boundary for writing a
  normalized audit event from implemented workflows.
- Existing high-value workflows should emit audit entries through that boundary
  rather than each route inventing a different shape.
- `ListAuditEntries` should support filtered admin reads by actor, action family,
  target type, result, and time range.
- `GetAuditEntryDetail` should return one governed record with redacted metadata
  and linked references.
- Unauthorized or cross-tenant audit reads must fail safely and leave audit-
  friendly denial evidence where appropriate.

## Interface Contract

Backend contract should minimally support:

- `GET /admin/audit-logs` with pagination, stable filters, and tenant-scoped
  results.
- `GET /admin/audit-logs/{id}` or equivalent detail read for one audit event.
- Stable response fields for actor summary, action, target summary, result,
  occurred time, and request or correlation context.

Expected payload concerns:

- Metadata must stay useful for investigation without returning raw credential
  material, full cookies, access tokens, or oversized raw payloads.
- Audit responses should distinguish human, service, and system actors clearly.
- The contract should preserve room for later retention or export metadata
  without forcing those follow-on features into the initial read model.

## Data Model

- Store audit entries in SQLite with organization scope, actor identifiers,
  action, target type/id, result, redacted metadata, occurred time, and request
  or session context.
- Preserve enough linkage to reconstruct representative workflows across login,
  discovery, content, browser, and lead surfaces.
- Keep the persistence shape compatible with later retention markers, deletion
  status, or export references without redefining existing audit rows.
- Avoid reusing ad hoc per-feature history tables as the sole audit source for
  governance reads.

## UI / Platform Impact

- Add an admin audit-log surface under Settings that shows the most important
  filters first: actor, action family, target, result, and time range.
- Make redacted fields visually obvious so operators understand why metadata is
  partial instead of assuming data loss.
- Keep the surface read-only in this slice; no inline mutation of audit entries.
- Preserve room for future links into connector health, retention, or deletion
  surfaces without turning audit into a generic admin dumping ground.

## Observability

- Record structured audit diagnostics for write failures, redaction outcomes, and
  unauthorized read attempts.
- Preserve request or correlation identifiers so future traces can connect API
  request -> job -> browser action -> audit entry.
- Keep audit payloads and logs aligned so observability does not reintroduce the
  secrets that the audit surface redacts.

## Alternatives Considered

1. Keep feature-specific history in each domain and skip a central audit
   contract. Rejected because the SPEC requires an admin audit surface and
   consistent governance visibility.
2. Use raw application logs as the audit log. Rejected because logs are not a
   stable tenant-scoped product contract and may not satisfy redaction or query
   requirements.
3. Combine audit, retention, deletion, and connector health into one hardening
   story. Rejected because the blast radius would be too large and would blur the
   boundary between action history and later governance workflows.
