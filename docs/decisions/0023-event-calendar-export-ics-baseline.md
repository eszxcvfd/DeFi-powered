# 0023 Event Calendar Export (ICS) Baseline

Date: 2026-06-16

## Status

Planned (companion decision to `US-045`).

## Context

`US-030` shipped the first user-scoped event
watchlist and reminder surface for LiveLead and
explicitly carved the calendar export out as a
follow-up. The relevant extracts from the
durable record are:

- `docs/product/event-watchlist-and-reminders.md`,
  "This product slice does not yet cover"
  section: "Calendar export or ICS generation."
- `docs/stories/epics/E01-discovery-mvp/US-030-event-watchlist-baseline/design.md`,
  "Data Model" section: "Preserve room for
  future calendar-export tokens, shared-watchlist
  ownership, or richer reminder state without
  redefining baseline ownership rules."

`SPEC.md` section 5.6 (`FR-EVT-005`) commits the
product to a calendar export surface:

> **FR-EVT-005 — Calendar export**
> **Ưu tiên:** Should
> Hệ thống cho phép export sự kiện sang ICS.

`SPEC.md` section 5.7 (`FR-NOR-003`) commits the
product to a stable event state classification
that the calendar export must honor:

> **FR-NOR-003 — Phân loại trạng thái thời gian**
> Hệ thống phải gán trạng thái `UPCOMING`, `LIVE`,
> `ENDED` cho mỗi sự kiện để phục vụ playbook
> state-aware và báo cáo.

`US-005` shipped the canonical event model with
`UPCOMING`, `LIVE`, and `ENDED` states and a
canonical event URL. `US-019` shipped the first
report export surface with CSV plus printable
output and the export-token pattern that the
calendar export reuses. `US-026` shipped the
admin audit log with the secret-safe payload
contract that the calendar export audit entries
inherit. `US-027` shipped the RBAC contract that
the calendar exports panel inherits. `US-040`
shipped the `EnvironmentMode` bound that the
calendar export token TTL inherits. `US-041`
shipped the `SanitizeAlertPayload` helper that
the calendar export audit payloads reuse.

The product still has no bounded calendar export
slice. An operator who wants to bring a watched
event into Google Calendar, Apple Calendar, or
Outlook has to copy the event URL, the start
time, and the title by hand. The existing report
export from `US-019` is owner/admin-scoped and
does not support a tokenized calendar feed. The
content handoff from `US-011` does not emit an
ICS file. The product needs a third export
surface that is read-only, current-user-scoped,
and reuses the existing audit and sanitization
contracts.

The next step in the discovery MVP is therefore
a bounded event calendar export slice that turns
`FR-EVT-005` into a documented contract, a
per-user ICS export endpoint, a tokenized
calendar feed, and a reusable export-token
surface that a later calendar auth or
shared-watchlist story can extend without
re-opening the contract.

## Decision

`US-045` introduces the first event calendar
export (ICS) baseline for LiveLead.

### Domain objects

- **`CalendarExportToken`** — durable record of
  a bounded calendar export token. The row
  carries enough information to mint, resolve,
  revoke, and audit a tokenized ICS feed without
  leaking the plaintext token or any
  session-bound material. The row stores a
  `token_hash` (argon2id) and an
  `audit_correlation_id`; the plaintext is never
  stored.
- **`CalendarExportAudit`** — durable record of
  every export attempt. The row is the
  audit-of-record for the calendar export
  surface and is consumed by the operator panel
  widget and the existing admin audit log filter
  from `US-026`. The row stores a redacted IP
  address, a bounded user agent, and a request
  id.
- **`CalendarScope`** — closed enum of export
  scopes: `event`, `watchlist`, `event_filter`.
  New scopes cannot be added without first
  extending the `CalendarExportService` and the
  audit entry shape.

### Bounded operations

- **`CalendarExportService`** — application
  service that owns the bounded operations. The
  service is the only place that mutates
  `calendar_export_tokens` and
  `calendar_export_audits` and emits the
  `calendar.*` audit entries; the REST layer
  calls it from the request handlers.
- **`CalendarExportFormatter`** — small helper
  that converts a canonical event into a stable
  ICS line set. The formatter is the only place
  that owns the `STATUS` mapping and the
  `X-LIVELEAD-EVENT-ID` extension; the service
  and the test fixtures call it from a single
  seam.

### REST surface

- `GET /events/{id}.ics` — current user only.
- `GET /watchlist/events.ics` — current user
  only.
- `GET /events.ics?campaign_id=&industry=...`
  — current user only.
- `POST /calendar-export-tokens` — current user
  only. Mints a bounded export token, returns
  the plaintext token once in the response
  body.
- `GET /calendar-export-tokens` — current user
  only. Lists the user's active and revoked
  tokens with sanitized payloads (no plaintext).
- `DELETE /calendar-export-tokens/{id}` —
  current user only. Revokes the token and
  emits a `calendar.token.revoked` audit entry.
- `GET /calendar-export/{token}.ics` —
  tokenized. Resolves the token, increments
  `use_count`, updates `last_used_at`, and
  returns the matching ICS payload.

### Audit entry types

- `calendar.event.exported`
- `calendar.watchlist.exported`
- `calendar.filter.exported`
- `calendar.token.minted`
- `calendar.token.revoked`
- `calendar.token.used`

### Calendar `STATUS` mapping

- `UPCOMING` → `TENTATIVE`
- `LIVE` → `CONFIRMED`
- `ENDED` → `CANCELLED`

The mapping is fixed and follows `SPEC.md`
`FR-NOR-003`. A later story can extend the
mapping with explicit acceptance criteria; the
first slice follows the spec.

### Export token TTL bound

- `pilot_live` — max 90 days
- `test_like` — max 30 days

The bound is derived from the `EnvironmentMode`
shipped by `US-040`. A user asking for a longer
expiry is rejected with `TOKEN_EXPIRY_TOO_LONG`.

### Follow-Up

A follow-on story can extend the calendar export
surface with:

- Calendar auth (OAuth with Google Calendar,
  Apple Calendar, Microsoft 365, or any other
  external calendar provider).
- Shared-team watchlists, team calendar feeds,
  or aggregate watcher analytics.
- Bulk watchlist add or remove actions, bulk
  token issuance, or bulk token revocation
  beyond the per-user `DELETE
  /calendar-export-tokens/{id}` endpoint.
- Bulk calendar import (a user importing a third
  party ICS feed into LiveLead).
- Subscription refresh semantics for calendar
  clients that re-fetch the ICS URL (an `ETag`
  and a `Last-Modified` response header).
- Per-tenant calendar `STATUS` mapping or custom
  event categories.
- Re-sending calendar invitations or storing
  attendee lists.

The follow-on stories must keep the export token
TTL bound, the `SanitizeAlertPayload` contract,
the audit entry shape, and the RBAC contract
from `US-027` stable.

## Consequences

- LiveLead now has a third export surface that
  is read-only, current-user-scoped, and reuses
  the existing audit and sanitization contracts.
- Operators can bring a watched event into
  Google Calendar, Apple Calendar, or Outlook
  without copy-pasting the event URL, the start
  time, and the title by hand.
- The calendar export token TTL is bounded by
  the `EnvironmentMode` from `US-040`, so the
  pilot-live environment ships a 90-day
  maximum and the test-like environment ships
  a 30-day maximum.
- The `X-LIVELEAD-EVENT-ID` extension is the
  only LiveLead-specific extension; a later
  calendar auth story can add additional
  extensions behind the same
  `CalendarExportFormatter` seam.
- The calendar exports panel is covered by the
  existing RBAC contract from `US-027`: a
  viewer, analyst, sales, or reviewer session
  gets no access to the token list, the audit
  list, or the revocation flow.

## References

- `SPEC.md` sections 5.6 (`FR-EVT-005`) and
  5.7 (`FR-NOR-003`).
- `docs/product/event-calendar-export.md`
  (living product contract seeded by `US-045`).
- `docs/product/event-watchlist-and-reminders.md`
  (`US-030` contract; this story extends the
  watchlist with a calendar export surface).
- `docs/product/event-results-and-review.md`
  (`US-005` contract; this story adds a
  calendar export of canonical events).
- `docs/product/report-export-and-printing.md`
  (`US-019` contract; this story reuses the
  export-token pattern and the audit entry
  shape from `US-019`).
- `docs/product/audit-log-and-governance.md`
  (`US-026` contract; the export audit entry
  shape and the sanitization contract come from
  `US-026` and `US-041`).
- `docs/product/real-environment-cutover-and-live-operations.md`
  (`US-040` contract; the export token TTL is
  bounded by the `EnvironmentMode` from
  `US-040`).
- `docs/stories/epics/E01-discovery-mvp/US-030-event-watchlist-baseline/`
  (predecessor story packet; the watchlist
  design preserves the calendar export seam).
- `docs/stories/epics/E01-discovery-mvp/US-045-event-calendar-export-ics-baseline/`
  (this story packet).
- `docs/ops/calendar-export-runbook.md`
  (operational entry seeded by this story).
