# Overview

## Current Behavior

`US-001` through `US-044` delivered a broad MVP and the
first bounded hardening slices for LiveLead. The
product now has:

- A modular monolith with a Python API, a worker, a
  scheduler, a browser worker, a SQLite store, a
  Redis broker, and a React/TypeScript UI.
- A canonical event model with provenance-aware
  deduplication and confidence scoring
  (`US-005`).
- A user-scoped event watchlist and reminder
  surface (`US-030`) that exposes
  `PUT/DELETE /events/{id}/watchlist`,
  `GET /watchlist/events`, and current-user
  watched-state in the event list and detail
  payloads.
- A governed report export surface (`US-019`) that
  ships CSV plus printable output for dashboard,
  funnel, source-performance, and
  content-effectiveness reports, with the existing
  audit entry shape from `US-026` and the
  sanitization contract from `US-041`.
- A governed content handoff surface (`US-011`)
  that emits an `content.handoff.used` audit entry
  when an operator copies or exports an approved
  content variant.

`SPEC.md` section 5.6 (`FR-EVT-005`) commits the
product to a calendar export surface:

> **FR-EVT-005 — Calendar export**
> **Ưu tiên:** Should
> Hệ thống cho phép export sự kiện sang ICS.

`docs/product/event-watchlist-and-reminders.md`
explicitly defers the surface in its "This product
slice does not yet cover" list:

> Calendar export or ICS generation.

`docs/stories/epics/E01-discovery-mvp/US-030-event-watchlist-baseline/design.md`
explicitly preserves the seam:

> Preserve room for future calendar-export tokens,
> shared-watchlist ownership, or richer reminder
> state without redefining baseline ownership
> rules.

The product still has no bounded calendar export
slice:

- There is no `GET /events/{id}.ics` endpoint and
  no `GET /watchlist/events.ics` endpoint. An
  operator who wants to bring a watched event
  into Google Calendar, Apple Calendar, or
  Outlook has to copy the event URL, the start
  time, and the title by hand.
- There is no export token. The existing report
  export from `US-019` is owner/admin-scoped and
  uses query parameters; the calendar export must
  support a tokenized URL so a user can subscribe
  to a calendar feed from a desktop or mobile
  client without leaking a session cookie.
- There is no shared watchlist, no per-user
  calendar auth flow, and no team calendar feed.
  The first slice must stay current-user-scoped
  and explainable; calendar auth and shared
  watchlists are explicitly deferred.
- The event timing payload today is a UTC
  `start_at` and `end_at`. ICS requires a stable
  timezone-aware formatting path that handles
  `UPCOMING`, `LIVE`, and `ENDED` event states
  with explicit `DTSTART`, `DTEND`, `DTSTAMP`,
  `UID`, `SUMMARY`, `DESCRIPTION`, `URL`, and
  `STATUS` fields.
- The reporting export from `US-019` does not
  include calendar events, and the content
  handoff from `US-011` does not emit an ICS
  file. The product needs a third export surface
  that is read-only, current-user-scoped, and
  reuses the existing audit and sanitization
  contracts.

The next step in the discovery MVP is therefore a
bounded event calendar export slice that turns
`FR-EVT-005` into a documented contract, a
per-user ICS export endpoint, a tokenized calendar
feed, and a reusable export-token surface that a
later shared-watchlist or calendar-auth story can
extend without re-opening the contract.

## Target Behavior

This story establishes the first bounded event
calendar export slice for LiveLead. After the
story is complete:

- A new durable `calendar_export_tokens` table
  records the bounded export token shape:
  `id`, `organization_id`, `user_id`,
  `token_hash` (argon2id), `scope` (`event`,
  `watchlist`, `event_filter`),
  `target_id` (nullable for `event_filter`),
  `filter_json` (nullable), `expires_at`,
  `revoked_at` (nullable), `last_used_at`
  (nullable), `use_count`,
  `audit_correlation_id`, `created_at`, and
  `updated_at`.
- A new durable `calendar_export_audits` table
  records every export attempt with
  `id`, `organization_id`, `user_id`, `token_id`
  (nullable for session-based exports),
  `scope`, `event_id` (nullable),
  `event_count`, `result` (`success`,
  `forbidden`, `expired`, `revoked`,
  `invalid_scope`), `ip_address`,
  `user_agent`, `request_id`, `created_at`.
- A new `CalendarExportService` exposes the
  bounded operations:
  - `build_event_ics(event_id, requester_id)` —
    returns a single `text/calendar` payload for
    one event, with `UID`, `SUMMARY`,
    `DESCRIPTION`, `URL`, `LOCATION` (when
    known), `DTSTART`, `DTEND`, `DTSTAMP`, and
    `STATUS` (`TENTATIVE` for `UPCOMING`,
    `CONFIRMED` for `LIVE`, `CANCELLED` for
    `ENDED`), and an `X-LIVELEAD-EVENT-ID`
    extension for round-trip identification.
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
    `token_hash` (argon2id), an `expires_at`
    bounded to the current `EnvironmentMode`
    from `US-040` (max 90 days in
    `pilot_live`, max 30 days in `test_like`),
    and a `audit_correlation_id` linking the
    token row to the `calendar_export_audits`
    row.
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
- A new owner/admin-or-self REST surface:
  - `GET /events/{id}.ics` — current user. Returns
    a `text/calendar` payload for one event.
    Anonymous and cross-user requests are denied
    with `EVENT_FORBIDDEN` or `EVENT_NOT_FOUND`.
  - `GET /watchlist/events.ics` — current user.
    Returns a `text/calendar` payload for the
    current user's watched events.
  - `GET /events.ics?campaign_id=&industry=...` —
    current user. Returns a `text/calendar`
    payload for the current event filter set.
  - `POST /calendar-export-tokens` — current
    user. Mints a bounded export token, returns
    the plaintext token once in the response
    body, and returns `404` on subsequent reads
    of the same `token_id`.
  - `GET /calendar-export-tokens` — current
    user. Lists the user's active and revoked
    tokens with sanitized payloads (no
    plaintext).
  - `DELETE /calendar-export-tokens/{id}` —
    current user. Revokes the token and emits a
    `calendar.token.revoked` audit entry.
  - `GET /calendar-export/{token}.ics` —
    tokenized. Resolves the token, increments
    `use_count`, updates `last_used_at`, and
    returns the matching ICS payload. Cross-user
    or revoked tokens return `TOKEN_REVOKED`,
    `TOKEN_EXPIRED`, or `TOKEN_NOT_FOUND`.
- A new operator panel widget that lists the
  current user's active calendar export tokens,
  shows the most recent export audit entries,
  and exposes a `Revoke` button for each token.
- A new product doc
  (`docs/product/event-calendar-export.md`) that
  documents the ICS payload contract, the
  export-token lifecycle, the calendar `STATUS`
  mapping for `UPCOMING`/`LIVE`/`ENDED`, and the
  audit entry shape.
- A new runbook
  (`docs/ops/calendar-export-runbook.md`) that
  documents what an operator does when a token
  leak is reported, when a token expires, and
  when a user asks to bulk-revoke a watchlist
  calendar feed.
- A new decision record
  (`docs/decisions/0023-event-calendar-export-ics-baseline.md`)
  that locks the export-token contract, the
  per-event ICS payload, the calendar `STATUS`
  mapping, and the audit entry shape.
- A new bounded verification command
  (`scripts/verify-us-045.sh`) that runs the unit,
  integration, E2E, security, and operational
  checks defined in `validation.md` and is wired
  into `harness-cli story verify` and
  `harness-cli story verify-all`.

The slice stops at the current-user, single-host
baseline. Calendar auth (OAuth with Google
Calendar, Apple Calendar, Microsoft 365),
shared-team watchlists, and external calendar
sync remain in the follow-up backlog.

## Affected Users

- Analysts and sales/BD users who want to bring a
  watched event into Google Calendar, Apple
  Calendar, or Outlook without copy-pasting the
  event URL and the start time by hand. They need
  a current-user-scoped ICS URL and a bounded
  export token that they can paste into a desktop
  or mobile calendar client.
- Owners and admins responsible for the
  calendar-export governance. They need the
  operator panel widget, the token revocation
  flow, and the runbook entry that explains what
  to do when a token leak is reported.
- Future implementation agents and engineers
  extending calendar auth, shared watchlists, or
  team calendar feeds that need a stable
  export-token contract.

## Affected Product Docs

- `docs/product/event-watchlist-and-reminders.md`
  (US-030 contract; this story extends the
  watchlist with a calendar export surface, it
  does not redefine watchlist ownership or
  reminder semantics).
- `docs/product/event-results-and-review.md`
  (US-005 contract; this story adds a calendar
  export of canonical events, it does not
  redefine the canonical event model).
- `docs/product/overview.md` (product summary;
  this story adds the calendar export surface
  to the supporting capabilities list).
- `docs/product/report-export-and-printing.md`
  (US-019 contract; this story reuses the
  export-token pattern and the audit entry
  shape from `US-019`; it does not redefine
  report export).
- `docs/product/audit-log-and-governance.md`
  (US-026 contract; the export audit entry
  shape and the sanitization contract come from
  `US-026` and `US-041`; the new
  `calendar.*` audit entries use the same
  secret-safe payload contract).
- `docs/product/real-environment-cutover-and-live-operations.md`
  (US-040 contract; the export token TTL is
  bounded by the `EnvironmentMode` from
  `US-040`).
- `docs/product/event-calendar-export.md` (new
  product doc that this story seeds as the
  living contract for the calendar export
  domain).

## Non-Goals

- Calendar auth (OAuth with Google Calendar,
  Apple Calendar, Microsoft 365, or any other
  external calendar provider). The first slice
  ships a tokenized ICS URL, not a calendar auth
  flow.
- Shared-team watchlists, team calendar feeds,
  or aggregate watcher analytics. The first
  slice is current-user-scoped; shared
  watchlists are a follow-on story.
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
  mapping from `UPCOMING`/`LIVE`/`ENDED`.
- Re-sending calendar invitations or storing
  attendee lists. LiveLead is a discovery and
  engagement tool, not a calendar server; the
  ICS payload stays read-only.
- Replacing the existing report export from
  `US-019`. This story reuses the
  export-token pattern; it does not redefine
  the report export surface.
- Replacing the existing content handoff from
  `US-011`. This story reuses the audit entry
  shape; it does not redefine the content
  handoff surface.
- Replacing the existing watchlist from
  `US-030`. This story extends the watchlist
  with a calendar export; it does not redefine
  the watchlist ownership or reminder
  semantics.
