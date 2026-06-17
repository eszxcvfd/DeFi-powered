# Design

## Domain Model

The first event calendar export slice formalizes
the durable objects and bounded services that turn
`FR-EVT-005` into a documented contract, a
per-user ICS export endpoint, a tokenized calendar
feed, and a reusable export-token surface.

### `CalendarExportToken`

A durable record of a bounded calendar export
token. The row carries enough information to mint,
resolve, revoke, and audit a tokenized ICS feed
without leaking the plaintext token or any
session-bound material.

- `id`
- `organization_id`
- `user_id` (the token owner)
- `token_hash` (argon2id hash of the plaintext
  token; the plaintext is never stored)
- `scope` (`event`, `watchlist`, `event_filter`)
- `target_id` (nullable; the event id for
  `event`, `null` for `watchlist` and
  `event_filter`)
- `filter_json` (nullable; the event filter for
  `event_filter`)
- `expires_at` (bounded by the current
  `EnvironmentMode` from `US-040`: max 90 days
  in `pilot_live`, max 30 days in `test_like`)
- `revoked_at` (nullable)
- `last_used_at` (nullable)
- `use_count` (defaults to 0)
- `audit_correlation_id` (links the token row
  to the matching `calendar_export_audits`
  row)
- `created_at`, `updated_at`

### `CalendarExportAudit`

A durable record of every export attempt. The
row is the audit-of-record for the calendar
export surface and is consumed by the
operator panel widget and the existing
admin audit log filter from `US-026`.

- `id`
- `organization_id`
- `user_id` (nullable for tokenized requests
  where the user is resolved from the token)
- `token_id` (nullable for session-based
  requests)
- `scope`
- `event_id` (nullable for `watchlist` and
  `event_filter` exports)
- `event_count`
- `result` (`success`, `forbidden`, `expired`,
  `revoked`, `invalid_scope`)
- `ip_address` (redacted to /24 for IPv4 and
  /48 for IPv6 by the existing redaction
  helper from `US-041`)
- `user_agent` (bounded to a 256-character
  truncated string)
- `request_id`
- `created_at`

### `CalendarScope` (closed enum)

A closed enumeration of export scopes. New
scopes cannot be added without first extending
the `CalendarExportService` and the audit entry
shape:

- `event` — single event ICS
- `watchlist` — current user watched events ICS
- `event_filter` — current event filter set ICS

### `CalendarExportService`

The application service that owns the bounded
operations. The service is the only place that
mutates `calendar_export_tokens` and
`calendar_export_audits` and emits the
`calendar.*` audit entries; the REST layer
calls it from the request handlers.

- `build_event_ics(event_id, requester_id)` —
  returns a single `text/calendar` payload for
  one event, with `UID`,
  `SUMMARY`, `DESCRIPTION`,
  `URL`, `LOCATION` (when known),
  `DTSTART`, `DTEND`, `DTSTAMP`,
  and `STATUS`
  (`TENTATIVE` for `UPCOMING`,
  `CONFIRMED` for `LIVE`,
  `CANCELLED` for `ENDED`), and an
  `X-LIVELEAD-EVENT-ID`
  extension for round-trip
  identification.
- `build_watchlist_ics(user_id)` — returns a
  `text/calendar` payload for the current
  user's watched events, in `start_at` order,
  with the same per-event shape and a calendar
  `NAME` and `X-WR-CALNAME` set to
  `LiveLead watchlist`.
- `build_filter_ics(filter_json, requester_id)`
  — returns a `text/calendar` payload for the
  current event-filter set, with the same
  per-event shape and the calendar `NAME` set
  to `LiveLead events ({filter_label})`.
- `mint_token(scope, target_id, filter_json,
  expires_at)` — creates a row in
  `calendar_export_tokens` with a
  `token_hash` (argon2id), an
  `expires_at` bounded by the current
  `EnvironmentMode` from `US-040`, and a
  matching `calendar_export_audits` row.
- `revoke_token(token_id)` — transitions the
  row to `revoked_at` and emits a
  `calendar.token.revoked` audit entry.
- `resolve_token(plaintext_token)` — returns
  the token row, increments `use_count`,
  updates `last_used_at`, and emits a
  `calendar.token.used` audit entry.
- `record_export_audit(...)` — appends a row
  to `calendar_export_audits` with the
  secret-safe payload helper from `US-041`.

### `CalendarExportFormatter`

A small helper that converts a canonical event
into a stable ICS line set. The formatter is
the only place that owns the `STATUS` mapping
and the `X-LIVELEAD-EVENT-ID` extension; the
service and the test fixtures call it from a
single seam.

- `format_event(event, status)` — returns the
  ICS line set for one event.
- `format_calendar_name(scope, filter_label)`
  — returns the `NAME` and `X-WR-CALNAME`
  for the calendar feed.
- `format_uid(event_id, organization_id)` —
  returns a stable `UID` that includes the
  organization id and the event id so a later
  shared-watchlist story can extend the
  payload without a UID collision.

Business rules:

- All new endpoints require an authenticated
  session for the current-user ICS endpoints
  and a valid export token for the tokenized
  endpoints. Anonymous requests, cross-user
  requests, and revoked or expired tokens are
  denied with `EVENT_FORBIDDEN`,
  `EVENT_NOT_FOUND`, `TOKEN_REVOKED`,
  `TOKEN_EXPIRED`, or `TOKEN_NOT_FOUND`.
- The export token plaintext is shown to the
  user exactly once: at mint time, in the
  response body of `POST
  /calendar-export-tokens`. Subsequent
  reads of the same `token_id` return the
  row without the plaintext. The `token_hash`
  is the only durable artifact; the plaintext
  is never persisted.
- The `expires_at` is bounded by the current
  `EnvironmentMode` from `US-040` (max 90 days
  in `pilot_live`, max 30 days in
  `test_like`). A user asking for a longer
  expiry is rejected with
  `TOKEN_EXPIRY_TOO_LONG` and the audit
  entry shape stays the same.
- The calendar `STATUS` mapping is fixed:
  `UPCOMING` → `TENTATIVE`, `LIVE` →
  `CONFIRMED`, `ENDED` → `CANCELLED`. A later
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

## Application Flow

- `BuildEventIcs` (current user) — loads the
  canonical event by id, asserts the
  requester is in the same organization, calls
  `CalendarExportFormatter.format_event`, and
  emits a `calendar.event.exported` audit
  entry with `result=success`.
- `BuildWatchlistIcs` (current user) — loads
  the current user's watched events, calls
  `CalendarExportFormatter.format_event` for
  each, and emits a `calendar.watchlist.exported`
  audit entry with `event_count`.
- `BuildFilterIcs` (current user) — loads the
  event filter set, calls
  `CalendarExportFormatter.format_event` for
  each, and emits a `calendar.filter.exported`
  audit entry with `event_count` and
  `filter_label`.
- `MintCalendarExportToken` (current user) —
  validates the scope, the target id, and the
  expiry against the closed `CalendarScope`
  enum and the current `EnvironmentMode`,
  mints the token row, and emits a
  `calendar.token.minted` audit entry. The
  response body includes the plaintext token
  exactly once.
- `RevokeCalendarExportToken` (current user)
  — asserts the requester owns the token row,
  transitions the row to `revoked_at`, and
  emits a `calendar.token.revoked` audit
  entry.
- `ResolveCalendarExportToken` (tokenized) —
  looks up the token row by `token_hash`,
  asserts the row is not revoked or expired,
  increments `use_count`, updates
  `last_used_at`, and dispatches to the
  matching `build_*_ics` operation. Cross-
  user, revoked, or expired tokens return
  `TOKEN_NOT_FOUND`, `TOKEN_REVOKED`, or
  `TOKEN_EXPIRED` and emit a
  `calendar.token.used` audit entry with
  `result=forbidden|expired|revoked`.
- `SanitizeExportPayload` (shared helper) —
  runs every audit payload through the
  existing helper from `US-041` so the
  contract is defined once and reused.

## Interface Contract

This slice adds the minimum REST surface that
current users need to export events to a
desktop or mobile calendar client, mint a
bounded export token, and revoke a token.

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

Expected payload concerns:

- All new error responses follow the existing
  error envelope (`code`, `message`,
  `request_id`, `details`).
- Unknown scopes, unknown targets, missing
  acceptance metadata, and expiry that
  exceeds the `EnvironmentMode` bound return
  `CALENDAR_INVALID_SCOPE`,
  `CALENDAR_TARGET_NOT_FOUND`,
  `CALENDAR_ACCEPTANCE_REQUIRED`, and
  `TOKEN_EXPIRY_TOO_LONG` respectively.
- Every successful and failed export attempt
  emits a durable audit entry with the same
  secret-safe payload contract as `US-026`
  and `US-041`.
- The ICS payload is a `text/calendar`
  response with `charset=utf-8` and a
  `Content-Disposition: inline; filename=...`
  header.

## Data Model

New durable objects, each with a forward-only
migration and an index strategy sized for the
current SQLite baseline:

- `calendar_export_tokens` (organization-scoped,
  index on `(organization_id, user_id)` for the
  per-user token list, index on `token_hash`
  for the resolve path, index on
  `(organization_id, expires_at)` for the
  retention prune).
- `calendar_export_audits` (organization-scoped,
  index on `(organization_id, user_id,
  created_at)` for the per-user audit list,
  index on `(organization_id, result,
  created_at)` for the admin audit filter from
  `US-026`, index on `token_id` for the
  per-token audit history).

No raw payload, secret, cookie, or browser
storage state is stored in the new tables. The
migration header documents that the change is
additive and that dropping the new tables is
the documented rollback path; no data outside
the new tables is affected.

The slice also extends:

- The audit entry shape from `US-026` with
  four new `calendar.*` event types:
  `calendar.event.exported`,
  `calendar.watchlist.exported`,
  `calendar.filter.exported`,
  `calendar.token.minted`,
  `calendar.token.revoked`, and
  `calendar.token.used`.
- The `EnvironmentMode` from `US-040` with
  the explicit `calendar_export_token_ttl`
  bound used by the
  `CalendarExportService.mint_token`
  operation.

## UI / Platform Impact

- The event list and event detail surfaces
  gain an `Export to calendar` action that
  opens a small modal. The modal explains
  the current-user scope, shows the
  `text/calendar` URL, and offers a
  `Copy URL` button plus a
  `Mint tokenized feed` button that calls
  `POST /calendar-export-tokens` and shows
  the plaintext token exactly once.
- The watched-events list gains a
  `Subscribe in calendar` action that opens
  the same modal with the
  `GET /watchlist/events.ics` URL pre-
  filled.
- The settings surface gains a
  `Calendar exports` panel for the current
  user. The panel lists the user's active
  and revoked tokens, the most recent
  export audit entries, and a `Revoke`
  button for each token.
- The in-app inbox from `US-029` shows
  `calendar.*` audit entries with a
  dedicated severity icon and a deep link
  to the calendar exports panel.
- The frontend does not need a parallel
  calendar client; it reuses the existing
  modal and settings surfaces already
  shipped by `US-030` and `US-029`.
- The `scripts/verify-us-045.sh` command
  wires the unit, integration, E2E,
  security, operational, and platform
  checks together and is the same command
  run by `harness-cli story verify` and
  `harness-cli story verify-all`.

## Observability

This story is the calendar export side of the
existing event surface, so it must set the
standard that the next story will be measured
against.

- Every request handled by the new endpoints
  keeps a correlation id that matches the
  existing request envelope and is forwarded
  to the audit entry and the
  `calendar_export_audits` row.
- Every export attempt, token mint, token
  revocation, and token resolution emits a
  structured log line and a matching audit
  entry.
- The bounded verification harness publishes
  a thin counter
  (`calendar.export.duration_ms`) so a
  future performance story can detect a slow
  export before it becomes a launch-gate
  blocker.
- The new endpoints are themselves covered
  by the health probe contract from
  `US-040`: a missing or failing
  `GET /events/{id}.ics` must not fail
  `GET /health/ready`, only surface as a
  degraded warning.

## Alternatives Considered

1. **Reuse the existing report export from
   `US-019` directly.** This would have
   collapsed two different user workflows
   into one surface and would have leaked
   the existing report export's owner/admin
   authorization to the calendar export
   surface. The slice ships a new
   `CalendarExportService` and a new
   `CalendarExportToken` table; it reuses
   the export-token pattern and the audit
   entry shape from `US-019`, it does not
   redefine them.
2. **Use a JWT instead of a dedicated
   `CalendarExportToken` table.** This
   would have forced the calendar export
   surface to depend on the existing JWT
   secret rotation contract from `US-027`
   and would have made per-user revocation
   impossible without a JWT deny list. The
   slice ships a dedicated table so a
   later calendar auth story can extend the
   contract without re-opening the JWT
   rotation contract.
3. **Skip the per-user scope and ship a
   tenant-wide calendar feed.** This would
   have forced the calendar export to
   depend on a shared team watchlist and
   would have leaked one user's reminder
   data to another user. The first slice is
   current-user-scoped; a later
   shared-watchlist story can extend the
   `CalendarScope` enum with explicit
   acceptance criteria.
4. **Push the calendar export through a
   new external channel instead of the
   existing in-app inbox and settings
   surfaces.** This would have added a new
   provider before the local-first baseline
   was proven and would have created a
   parallel channel that could drift away
   from the existing notification
   preferences from `US-029` and the
   sanitization helper from `US-041`.
   Reusing the same helper and the same
   audit entry shape keeps the contract
   aligned with the rest of the product.
5. **Skip the calendar `STATUS` mapping and
   emit every event as `CONFIRMED`.** This
   would have hidden the `UPCOMING`,
   `LIVE`, and `ENDED` state from desktop
   and mobile calendar clients and would
   have forced a later state-aware calendar
   story to re-open the payload. The
   slice ships the fixed
   `TENTATIVE`/`CONFIRMED`/`CANCELLED`
   mapping from `SPEC.md` `FR-NOR-003`.
