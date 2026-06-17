# Calendar Export Runbook

Operational entry for the `US-045` event calendar
export (ICS) baseline. This runbook documents
what an operator does when a calendar export
token leak is reported, when a calendar export
token expires, and when a user asks to
bulk-revoke a watchlist calendar feed.

The runbook reuses the existing operator workflow
from the observability, alert, audit, and
notification runbooks. It is intentionally
narrow: the calendar export surface is
read-only, current-user-scoped, and bounded by
the `EnvironmentMode` from `US-040`.

## What this runbook covers

- Calendar export token lifecycle:
  mint, resolve, revoke, and expiry.
- Calendar export audit entry shape and the
  matching admin audit log filter from
  `US-026`.
- Calendar export token leak response.
- Calendar export token expiry handling.
- Bulk calendar export feed revocation.

## What this runbook does NOT cover

- Calendar auth (OAuth with Google Calendar,
  Apple Calendar, Microsoft 365, or any other
  external calendar provider). The first slice
  ships a tokenized ICS URL, not a calendar auth
  flow.
- Shared-team watchlists, team calendar feeds,
  or aggregate watcher analytics. The first
  slice is current-user-scoped.
- Bulk watchlist add or remove actions, bulk
  token issuance, or bulk token revocation
  beyond the per-user `DELETE
  /calendar-export-tokens/{id}` endpoint.
- Bulk calendar import (a user importing a third
  party ICS feed into LiveLead).
- Subscription refresh semantics for calendar
  clients that re-fetch the ICS URL.
- Per-tenant calendar `STATUS` mapping or custom
  event categories.
- Re-sending calendar invitations or storing
  attendee lists.

## Calendar export token lifecycle

The `CalendarExportToken` row carries a
`token_hash` (argon2id), a `scope`, an
`expires_at`, a `revoked_at`, a `last_used_at`,
and a `use_count`. The plaintext is never
persisted. The lifecycle is:

1. `POST /calendar-export-tokens` mints a
   bounded export token, returns the plaintext
   token once in the response body, and writes
   a `CalendarExportToken` row with a
   `token_hash` (argon2id) and an
   `audit_correlation_id` linking the token row
   to the matching `CalendarExportAudit` row.
   The `expires_at` is bounded by the current
   `EnvironmentMode` from `US-040` (max 90 days
   in `pilot_live`, max 30 days in `test_like`).
2. `GET /calendar-export/{token}.ics` resolves
   the token by `token_hash`, asserts the row
   is not revoked or expired, increments
   `use_count`, updates `last_used_at`, and
   dispatches to the matching `build_*_ics`
   operation. Cross-user, revoked, or expired
   tokens return `TOKEN_NOT_FOUND`,
   `TOKEN_REVOKED`, or `TOKEN_EXPIRED` and emit
   a `calendar.token.used` audit entry with
   `result=forbidden|expired|revoked`.
3. `DELETE /calendar-export-tokens/{id}` revokes
   the token and emits a
   `calendar.token.revoked` audit entry.
4. The `EnvironmentMode` bound is enforced by
   the `CalendarExportService.mint_token`
   operation; a user asking for a longer
   expiry is rejected with
   `TOKEN_EXPIRY_TOO_LONG`.

## Calendar export audit entry shape

The audit entry shape reuses the existing
`AuditService` from `US-026`:

- `calendar.event.exported` — single event ICS
  export.
- `calendar.watchlist.exported` — current user
  watchlist ICS export.
- `calendar.filter.exported` — current event
  filter set ICS export.
- `calendar.token.minted` — export token mint.
- `calendar.token.revoked` — export token
  revocation.
- `calendar.token.used` — export token
  resolution.

Every audit payload runs through the existing
`SanitizeAlertPayload` helper from `US-041`.
The `calendar_export_tokens` table stores
the `token_hash` (argon2id) and the
`audit_correlation_id`; the
`calendar_export_audits` table stores the
redacted IP, the bounded user agent, and
the request id.

## Responding to a token leak

When a calendar export token leak is reported
(usually through the support inbox or a security
incident), the operator should:

1. Identify the affected user through the
   in-app inbox from `US-029` or the admin
   audit log filter from `US-026` (filter by
   `calendar.token.minted` and the user id).
2. Open the calendar exports panel and identify
   the affected `CalendarExportToken` row by
   its `id`.
3. Click `Revoke` on the affected row. The
   revocation transitions the row to
   `revoked_at`, emits a
   `calendar.token.revoked` audit entry, and
   returns `TOKEN_REVOKED` for any subsequent
   `GET /calendar-export/{token}.ics` request.
4. If the leak is severe, also call
   `DELETE /calendar-export-tokens/{id}` for
   every other active token owned by the same
   user.
5. If the leak is cross-tenant, also open a
   security incident and notify the security
   team; the calendar export token TTL bound
   from `US-040` limits the blast radius to 90
   days in `pilot_live` and 30 days in
   `test_like`.

## Responding to a token expiry

When a calendar export token expires (the
`expires_at` is reached), the operator should:

1. The `GET /calendar-export/{token}.ics`
   request returns `TOKEN_EXPIRED` and emits a
   `calendar.token.used` audit entry with
   `result=expired`.
2. The user must mint a new token through
   `POST /calendar-export-tokens` if they want
   to keep the calendar feed.
3. The expired token row stays in the table
   for audit history; the operator does not
   need to delete it.

## Responding to a bulk revocation request

When a user asks to bulk-revoke a watchlist
calendar feed (usually when they leave the
organization or when the calendar feed is no
longer needed), the operator should:

1. Identify the affected user through the
   in-app inbox from `US-029` or the admin
   audit log filter from `US-026`.
2. List the user's active calendar export
   tokens through `GET
   /calendar-export-tokens` (the
   `CalendarExportToken` row is sanitized and
   does not include the plaintext).
3. Call `DELETE /calendar-export-tokens/{id}`
   for every active token owned by the user.
4. Verify the revocation by checking the
   `calendar.token.revoked` audit entries in
   the admin audit log filter from `US-026`.

## Calendar export alert rules

The `US-041` alert evaluator does not currently
ship a calendar export-specific rule. Operators
who want to be notified when a calendar export
token is minted, revoked, or used can build a
custom rule through the existing alert rule
surface from `US-041` (for example,
`calendar.token.used.rate` over a 5-minute
window). The custom rule must respect the
existing `SanitizeAlertPayload` contract and the
existing audit retention guarantee from
`NFR-SEC-008`.

## Calendar export health probe

The new endpoints are covered by the health
probe contract from `US-040`: a missing or
failing `GET /events/{id}.ics` must not fail
`GET /health/ready`, only surface as a degraded
warning. The health probe is intentionally
shallow; the calendar export surface is
read-only, current-user-scoped, and bounded by
the `EnvironmentMode` from `US-040`.

## References

- `docs/product/event-calendar-export.md`
  (living product contract for the calendar
  export domain).
- `docs/decisions/0023-event-calendar-export-ics-baseline.md`
  (durable decision record for the calendar
  export baseline).
- `docs/stories/epics/E01-discovery-mvp/US-045-event-calendar-export-ics-baseline/`
  (this story packet).
- `docs/ops/observability-runbook.md`
  (operator workflow for the alert evaluator).
- `docs/ops/audit-runbook.md` (operator
  workflow for the admin audit log filter).
- `docs/product/audit-log-and-governance.md`
  (`US-026` contract).
- `docs/product/observability-and-alerting.md`
  (`US-041` contract).
- `docs/product/real-environment-cutover-and-live-operations.md`
  (`US-040` contract).
