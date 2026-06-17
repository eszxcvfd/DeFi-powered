# Event Calendar Export (ICS)

Source: `SPEC.md` sections 5.6 (`FR-EVT-005`) and
5.7 (`FR-NOR-003`), `UI-003`, `UI-004`, and `UC-02`.

## Product Goal

Analysts and sales/BD users need a bounded way to
bring a watched event into Google Calendar, Apple
Calendar, or Outlook without copy-pasting the
event URL, the start time, and the title by hand.
The product contract must define how LiveLead
exports a canonical event, a current-user
watchlist, or a current event filter set as a
stable ICS feed, mints a bounded export token for
calendar clients that cannot share a session, and
audits every export attempt behind the existing
secret-safe payload contract from `US-026` and
`US-041`.

## MVP Scope

This product slice covers:

- Exporting a single canonical event as a
  `text/calendar` payload with the closed ICS
  line set (`UID`, `SUMMARY`, `DESCRIPTION`,
  `URL`, `LOCATION`, `DTSTART`, `DTEND`,
  `DTSTAMP`, `STATUS`,
  `X-LIVELEAD-EVENT-ID`).
- Exporting the current user's watchlist as a
  `text/calendar` payload in `start_at` order.
- Exporting the current event filter set as a
  `text/calendar` payload.
- Minting a bounded export token that a desktop
  or mobile calendar client can use to subscribe
  to a calendar feed without sharing a session.
- Revoking an active export token from the
  calendar exports panel.
- Auditing every successful and failed export
  attempt with the same secret-safe payload
  contract as `US-026` and `US-041`.
- Mapping the canonical event state to the
  calendar `STATUS` field:
  `UPCOMING` → `TENTATIVE`,
  `LIVE` → `CONFIRMED`,
  `ENDED` → `CANCELLED`.

This product slice does not yet cover:

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
  party ICS feed into LiveLead). The first
  slice is export-only.
- Subscription refresh semantics for calendar
  clients that re-fetch the ICS URL. The
  current-user ICS endpoints are stateless; a
  later story can add an `ETag` and a
  `Last-Modified` response header.
- Per-tenant calendar `STATUS` mapping or custom
  event categories. The first slice ships the
  fixed `TENTATIVE`/`CONFIRMED`/`CANCELLED`
  mapping from `FR-NOR-003`.
- Re-sending calendar invitations or storing
  attendee lists. LiveLead is a discovery and
  engagement tool, not a calendar server; the
  ICS payload stays read-only.

## Contract Rules

- The export surface is current-user-scoped.
  Anonymous requests, cross-user requests, and
  revoked or expired tokens are denied with
  `EVENT_FORBIDDEN`, `EVENT_NOT_FOUND`,
  `TOKEN_REVOKED`, `TOKEN_EXPIRED`, or
  `TOKEN_NOT_FOUND`.
- The export token plaintext is shown to the
  user exactly once: at mint time, in the
  response body of `POST
  /calendar-export-tokens`. Subsequent
  reads of the same `token_id` return the
  row without the plaintext. The
  `token_hash` is the only durable artifact;
  the plaintext is never persisted.
- The `expires_at` is bounded by the current
  `EnvironmentMode` from `US-040` (max 90 days
  in `pilot_live`, max 30 days in
  `test_like`). A user asking for a longer
  expiry is rejected with
  `TOKEN_EXPIRY_TOO_LONG`.
- The calendar `STATUS` mapping is fixed:
  `UPCOMING` → `TENTATIVE`,
  `LIVE` → `CONFIRMED`,
  `ENDED` → `CANCELLED`. A later
  story can extend the enum with explicit
  acceptance criteria; the first slice
  follows `SPEC.md` `FR-NOR-003`.
- The tokenized endpoint never returns a
  payload that includes another user's
  watched events or another user's event
  filter set. The token row is the
  authorization artifact; the
  `CalendarExportService.resolve_token` call
  resolves the user from the row, not from
  the session.
- The `SanitizeAlertPayload` helper from
  `US-041` runs on every audit payload
  before it is persisted on
  `calendar_export_audits`. The
  `calendar_export_tokens` table never
  stores the plaintext token, the IP
  address, the user agent, or any session
  identifier; the audit table stores the
  redacted IP and the bounded user agent.
- The `X-LIVELEAD-EVENT-ID` extension is
  the only LiveLead-specific extension. A
  later calendar auth story can add
  additional extensions behind the same
  `CalendarExportFormatter` seam.
- The ICS payload is a `text/calendar`
  response with `charset=utf-8` and a
  `Content-Disposition: inline; filename=...`
  header. The filename includes the
  organization id, the scope, and the
  current `start_at` so a desktop calendar
  client can identify the feed.
- The `calendar_export_tokens` and
  `calendar_export_audits` tables never
  store secret material, raw PII, browser
  storage state, or full connection
  strings. The operator panel widget is
  covered by the existing RBAC contract from
  `US-027`: a viewer, analyst, sales, or
  reviewer session gets no access to the
  token list, the audit list, or the
  revocation flow.
- The `GET /calendar-export/{token}.ics`
  endpoint is the only endpoint that accepts
  a token instead of a session. The
  endpoint is the only place that resolves
  the user from the token row, and the
  resolution is bounded to the tokenized
  `scope` and `target_id`; the endpoint
  cannot be repurposed to access another
  user's data.

## API Surface

- `GET /events/{id}.ics` — current user only.
  Returns a `text/calendar` payload for one
  event. Anonymous and cross-user requests
  return `EVENT_FORBIDDEN` or
  `EVENT_NOT_FOUND`.
- `GET /watchlist/events.ics` — current user
  only. Returns a `text/calendar` payload for
  the current user's watched events.
- `GET /events.ics?campaign_id=&industry=...`
  — current user only. Returns a
  `text/calendar` payload for the current
  event filter set.
- `POST /calendar-export-tokens` — current
  user only. Body shape:
  `{ scope, target_id?, filter_json?,
  expires_at? }`. Mints a bounded export
  token, returns the plaintext token once in
  the response body, and returns the
  `CalendarExportToken` row without the
  plaintext on subsequent reads.
- `GET /calendar-export-tokens` — current
  user only. Lists the user's active and
  revoked tokens with sanitized payloads
  (no plaintext).
- `DELETE /calendar-export-tokens/{id}` —
  current user only. Revokes the token and
  emits a `calendar.token.revoked` audit
  entry.
- `GET /calendar-export/{token}.ics` —
  tokenized. Resolves the token, increments
  `use_count`, updates `last_used_at`, and
  returns the matching ICS payload. Cross-
  user, revoked, or expired tokens return
  `TOKEN_NOT_FOUND`, `TOKEN_REVOKED`, or
  `TOKEN_EXPIRED`.

## ICS Payload Contract

The ICS payload follows the stable line set
documented in `docs/decisions/0023-event-calendar-export-ics-baseline.md`:

- `BEGIN:VCALENDAR` and `END:VCALENDAR` wrap
  the entire feed.
- `VERSION:2.0`, `PRODID:-//LiveLead//EN`, and
  `CALSCALE:GREGORIAN` set the calendar
  metadata.
- `METHOD:PUBLISH` declares the feed as
  read-only.
- `X-WR-CALNAME` and `X-WR-TIMEZONE` declare
  the calendar name and the timezone.
- `BEGIN:VEVENT` and `END:VEVENT` wrap each
  event.
- `UID` is a stable identifier that includes
  the organization id and the event id.
- `DTSTAMP` is the export time in UTC.
- `DTSTART` and `DTEND` are the event timing
  in UTC.
- `SUMMARY` is the event title.
- `DESCRIPTION` is the event description
  followed by a `\n\nSource: {source_url}`
  line and a `\nEvent id: {event_id}` line.
- `URL` is the canonical event URL.
- `LOCATION` is the event location when
  known.
- `STATUS` follows the closed
  `TENTATIVE`/`CONFIRMED`/`CANCELLED`
  mapping from `FR-NOR-003`.
- `X-LIVELEAD-EVENT-ID` is the round-trip
  identifier for the canonical event.

## Audit Entry Contract

The audit entry shape reuses the existing
`AuditService` from `US-026`:

- `calendar.event.exported` — single event
  ICS export.
- `calendar.watchlist.exported` — current user
  watchlist ICS export.
- `calendar.filter.exported` — current event
  filter set ICS export.
- `calendar.token.minted` — export token
  mint.
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

## UI Surface

The first calendar export slice should extend
existing event-review surfaces:

- `Export to calendar` action on the event
  list and event detail.
- `Subscribe in calendar` action on the
  watched-events list.
- `Calendar exports` panel on the settings
  surface for the current user.
- Calendar export modal that shows the
  `text/calendar` URL, the
  `Mint tokenized feed` button, and the
  `Copy URL` button.
- In-app inbox entry from `US-029` for every
  `calendar.*` audit entry with a dedicated
  severity icon and a deep link to the
  calendar exports panel.

## Validation Implications

- Unit proof should cover the
  `CalendarExportService` operations, the
  `CalendarExportFormatter` line set, the
  `CalendarScope` enum closure, the
  `EnvironmentMode` bound for the calendar
  export token TTL, and the
  `SanitizeAlertPayload` reuse for every
  audit entry.
- Integration proof should cover the REST
  surface, the audit entry shape, the token
  mint, resolve, revoke, and cross-user
  denial paths.
- E2E proof should cover the calendar export
  modal, the watched-events list, the
  calendar exports panel, and the
  deterministic ICS export for each
  `CalendarScope` value.
- Logs or audit proof should confirm who
  exported, minted, revoked, or resolved a
  calendar export token and when.
- Platform proof should keep the calendar
  export verification path wired into the
  Harness matrix before calendar auth,
  shared watchlists, or external calendar
  sync stories build on it.
