# Exec Plan

## Goal

Add the first bounded event calendar export
(ICS) slice to LiveLead. The slice turns
`FR-EVT-005` into a documented contract, a
per-user ICS export endpoint, a tokenized
calendar feed, and a reusable export-token
surface that a later calendar auth or
shared-watchlist story can extend without
re-opening the contract.

## Scope

In scope:

- New durable `calendar_export_tokens` table
  with the minimum fields required to mint,
  resolve, revoke, and audit a tokenized ICS
  feed: `token_hash` (argon2id), `scope`,
  `target_id`, `filter_json`, `expires_at`,
  `revoked_at`, `last_used_at`, `use_count`,
  and `audit_correlation_id`. Forward-only
  Alembic migration with a documented
  rollback note in the migration header.
- New durable `calendar_export_audits` table
  with the minimum fields required to audit
  every export attempt: `token_id`, `scope`,
  `event_id`, `event_count`, `result`,
  `ip_address` (redacted to /24 for IPv4 and
  /48 for IPv6), `user_agent` (bounded to 256
  characters), and `request_id`. Forward-only
  Alembic migration with a documented
  rollback note in the migration header.
- New `CalendarScope` enum with three closed
  values: `event`, `watchlist`, and
  `event_filter`.
- New `CalendarExportService` that exposes
  the bounded operations:
  - `build_event_ics(event_id, requester_id)`
  - `build_watchlist_ics(user_id)`
  - `build_filter_ics(filter_json,
    requester_id)`
  - `mint_token(scope, target_id, filter_json,
    expires_at)`
  - `revoke_token(token_id)`
  - `resolve_token(plaintext_token)`
  - `record_export_audit(...)`
- New `CalendarExportFormatter` that owns the
  ICS line set, the calendar `STATUS`
  mapping, and the `X-LIVELEAD-EVENT-ID`
  extension.
- New current-user-only REST surface:
  - `GET /events/{id}.ics`
  - `GET /watchlist/events.ics`
  - `GET /events.ics?campaign_id=&industry=...`
  - `POST /calendar-export-tokens`
  - `GET /calendar-export-tokens`
  - `DELETE /calendar-export-tokens/{id}`
- New tokenized REST surface:
  - `GET /calendar-export/{token}.ics`
- New operator panel widget that lists the
  current user's active calendar export
  tokens, shows the most recent export audit
  entries, and exposes a `Revoke` button for
  each token.
- New audit entry types:
  `calendar.event.exported`,
  `calendar.watchlist.exported`,
  `calendar.filter.exported`,
  `calendar.token.minted`,
  `calendar.token.revoked`, and
  `calendar.token.used`.
- New bounded token TTL bound by the
  `EnvironmentMode` from `US-040` (max 90
  days in `pilot_live`, max 30 days in
  `test_like`).
- A new product doc
  (`docs/product/event-calendar-export.md`).
- A new runbook
  (`docs/ops/calendar-export-runbook.md`).
- A new decision record
  (`docs/decisions/0023-event-calendar-export-ics-baseline.md`).
- Reuse of the `SanitizeAlertPayload` helper
  from `US-041` for every audit payload
  before it is persisted on
  `calendar_export_audits`.
- Reuse of the `AuditService` from `US-026`
  for every `calendar.*` audit entry.
- Reuse of the `EnvironmentMode` from
  `US-040` for the calendar export token
  TTL bound.
- Reuse of the watchlist semantics from
  `US-030` for the
  `build_watchlist_ics` operation.
- Reuse of the canonical event model from
  `US-005` for the
  `CalendarExportFormatter.format_event`
  operation.
- Reuse of the existing modal and settings
  surfaces from `US-030` and `US-029` for
  the calendar export modal and the calendar
  exports panel.
- Unit, integration, E2E, security,
  operational, and platform checks wired
  into a `scripts/verify-us-045.sh` command
  that `harness-cli story verify` can run.

Out of scope:

- Calendar auth (OAuth with Google Calendar,
  Apple Calendar, Microsoft 365, or any
  other external calendar provider). The
  first slice ships a tokenized ICS URL, not
  a calendar auth flow.
- Shared-team watchlists, team calendar
  feeds, or aggregate watcher analytics.
  The first slice is current-user-scoped;
  shared watchlists are a follow-on story.
- Bulk watchlist add or remove actions,
  bulk token issuance, or bulk token
  revocation beyond the per-user `DELETE
  /calendar-export-tokens/{id}` endpoint.
- Bulk calendar import (a user importing a
  third party ICS feed into LiveLead). The
  first slice is export-only.
- Subscription refresh semantics for
  calendar clients that re-fetch the ICS
  URL. The current-user ICS endpoints are
  stateless; a later story can add an
  `ETag` and a `Last-Modified` response
  header.
- Per-tenant calendar `STATUS` mapping or
  custom event categories. The first slice
  ships the fixed
  `TENTATIVE`/`CONFIRMED`/`CANCELLED`
  mapping from `UPCOMING`/`LIVE`/`ENDED`.
- Re-sending calendar invitations or
  storing attendee lists. LiveLead is a
  discovery and engagement tool, not a
  calendar server; the ICS payload stays
  read-only.
- Replacing the existing report export from
  `US-019`. This story reuses the
  export-token pattern; it does not redefine
  the report export surface.
- Replacing the existing content handoff
  from `US-011`. This story reuses the audit
  entry shape; it does not redefine the
  content handoff surface.
- Replacing the existing watchlist from
  `US-030`. This story extends the watchlist
  with a calendar export; it does not
  redefine the watchlist ownership or
  reminder semantics.

## Risk Classification

Risk flags:

- Data model — new
  `calendar_export_tokens` and
  `calendar_export_audits` tables, new
  indexes, forward-only migrations; new
  `CalendarScope` enum.
- Audit/security — every export attempt,
  token mint, token revocation, and token
  resolution must carry a secret-safe
  payload and a `calendar.*` audit entry;
  the export token TTL is bounded by the
  `EnvironmentMode` from `US-040`.
- Public contracts — new REST endpoints
  (`text/calendar` responses), new error
  codes, new operator panel widget, new
  audit entry types; consumed by the same
  event and watchlist surfaces that already
  speak to the canonical event model from
  `US-005` and the watchlist from `US-030`.
- Multi-domain — touches events
  (`US-005`), watchlist (`US-030`), audit
  (`US-026`), notification (`US-029`),
  environment mode (`US-040`), and the
  existing report export pattern
  (`US-019`).

Hard gates:

- Any export attempt, token mint, token
  revocation, or token resolution that
  mutates product state without an
  authenticated session or a valid export
  token.
- Any export attempt, token mint, token
  revocation, or token resolution that
  leaks the plaintext token, a secret, a
  cookie, browser storage state, raw PII,
  or a full connection string.
- Any change that weakens the
  `SanitizeAlertPayload` contract from
  `US-041` or the audit retention guarantee
  from `NFR-SEC-008`.
- Any change that bypasses the existing
  `AuditService` from `US-026` or the
  existing `SanitizeAlertPayload` helper
  from `US-041`.
- Any change that adds a new scope to the
  `CalendarScope` enum without first
  extending the `CalendarExportService`
  and the audit entry shape.
- Any change that weakens the existing
  watchlist ownership or reminder semantics
  from `US-030`.
- Any change that bypasses the existing
  `EnvironmentMode` bound from `US-040` for
  the calendar export token TTL.

## Work Phases

1. Discovery — read `SPEC.md` §5.6 and §5.7
   (`FR-EVT-005`, `FR-NOR-003`), the
   `US-030` story packet, the `US-005`
   canonical event contract, the `US-019`
   report export contract, the `US-026`
   audit log contract, the `US-027` RBAC
   contract, the `US-040` environment mode
   contract, and the `US-041` sanitization
   helper. Confirm the seams that the slice
   consumes are stable and reusable.
2. Design — define `CalendarExportToken`,
   `CalendarExportAudit`, `CalendarScope`,
   `CalendarExportService`, and
   `CalendarExportFormatter`. Lock the
   sanitization contract to the existing
   `SanitizeAlertPayload` helper from
   `US-041` and refuse any audit entry that
   fails the filter. Lock the export token
   TTL bound to the existing
   `EnvironmentMode` from `US-040`.
3. Validation planning — design a per-scope
   test harness that runs a deterministic
   ICS export for each `CalendarScope` value,
   asserts the audit entry was written, and
   asserts the `text/calendar` response
   shape. Add a `POST
   /calendar-export-tokens` smoke test that
   a current user can run from the calendar
   exports panel.
4. Implementation — add the migrations, the
   domain models, the `CalendarScope` enum,
   the `CalendarExportService`, the
   `CalendarExportFormatter`, the current-
   user endpoints, the tokenized endpoint,
   the operator panel widget, the calendar
   export modal, the runbook entry, and the
   `scripts/verify-us-045.sh` harness.
   Reuse the existing
   `SanitizeAlertPayload` helper; do not
   introduce a parallel redaction helper.
5. Verification — run unit, integration,
   E2E, security, operational, and platform
   checks defined in `validation.md`. Run a
   deterministic ICS export for each
   `CalendarScope` value and assert the
   audit entry was written.
6. Harness update — add the new product
   doc, the decision record, the durable
   story status, the
   `scripts/verify-us-045.sh` command, and
   a final trace. Capture any friction in
   the `harness_friction` field.

## Stop Conditions

Pause for human confirmation if:

- The story starts requiring a specific
  calendar provider (Google Calendar, Apple
  Calendar, Microsoft 365, or any other
  external provider) to meet the acceptance
  criteria. This slice is local-first and
  token-based by design.
- Product direction becomes ambiguous
  between "current-user-scoped ICS URL" and
  "ship a full calendar auth stack this
  cycle".
- Validation would need to weaken the
  `SanitizeAlertPayload` contract, the
  audit retention guarantee, or the
  existing `EnvironmentMode` bound from
  `US-040` to fit schedule.
- A new calendar `STATUS` value is needed
  that cannot be justified from
  `FR-NOR-003`; the value must be deferred
  or added to the spec in the same story
  with explicit acceptance criteria.
- A later story wants to ship a shared-team
  watchlist or a shared-team calendar feed
  before this slice is implemented; in
  that case, the integration must wait
  until the current-user baseline is in
  place.
- The calendar export token TTL needs to
  weaken the existing `EnvironmentMode`
  bound from `US-040`; the slice must
  extend the bound, not redefine it.
- The watchlist calendar export needs to
  weaken the existing watchlist ownership
  or reminder semantics from `US-030`;
  the slice must extend the watchlist, not
  redefine it.
