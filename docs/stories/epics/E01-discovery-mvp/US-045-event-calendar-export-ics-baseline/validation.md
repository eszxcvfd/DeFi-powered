# Validation

## Required Proof

| Layer | Expectation |
| --- | --- |
| Unit | `CalendarExportService.build_event_ics` returns a single `text/calendar` payload for one event with the closed ICS line set (`UID`, `SUMMARY`, `DESCRIPTION`, `URL`, `LOCATION`, `DTSTART`, `DTEND`, `DTSTAMP`, `STATUS`, `X-LIVELEAD-EVENT-ID`) and emits a `calendar.event.exported` audit entry. `CalendarExportService.build_watchlist_ics` returns a `text/calendar` payload for the current user's watched events in `start_at` order and emits a `calendar.watchlist.exported` audit entry with `event_count`. `CalendarExportService.build_filter_ics` returns a `text/calendar` payload for the current event filter set and emits a `calendar.filter.exported` audit entry with `event_count` and `filter_label`. `CalendarExportService.mint_token` validates the scope, the target id, and the expiry against the closed `CalendarScope` enum and the current `EnvironmentMode` from `US-040`, mints the token row, and emits a `calendar.token.minted` audit entry. `CalendarExportService.revoke_token` transitions the row to `revoked_at` and emits a `calendar.token.revoked` audit entry. `CalendarExportService.resolve_token` returns the token row, increments `use_count`, updates `last_used_at`, and emits a `calendar.token.used` audit entry. `CalendarExportFormatter.format_event` maps `UPCOMING` to `TENTATIVE`, `LIVE` to `CONFIRMED`, and `ENDED` to `CANCELLED`. `SanitizeAlertPayload` strips keys, cookies, raw PII, browser storage state, and full connection strings from every audit entry before persistence. The `CalendarScope` enum is closed; unknown scopes return `CALENDAR_INVALID_SCOPE`. |
| Integration | `GET /events/{id}.ics` returns a `text/calendar` payload for one event; anonymous and cross-user requests return `EVENT_FORBIDDEN` or `EVENT_NOT_FOUND`. `GET /watchlist/events.ics` returns a `text/calendar` payload for the current user's watched events. `GET /events.ics?campaign_id=&industry=...` returns a `text/calendar` payload for the current event filter set. `POST /calendar-export-tokens` mints a bounded export token, returns the plaintext token once in the response body, and returns the `CalendarExportToken` row without the plaintext on subsequent reads. `GET /calendar-export-tokens` lists the user's active and revoked tokens with sanitized payloads (no plaintext). `DELETE /calendar-export-tokens/{id}` revokes the token and emits a `calendar.token.revoked` audit entry. `GET /calendar-export/{token}.ics` resolves the token, increments `use_count`, updates `last_used_at`, and returns the matching ICS payload; cross-user, revoked, or expired tokens return `TOKEN_NOT_FOUND`, `TOKEN_REVOKED`, or `TOKEN_EXPIRED`. The export token TTL is bounded by the current `EnvironmentMode` from `US-040` (max 90 days in `pilot_live`, max 30 days in `test_like`); an expiry that exceeds the bound returns `TOKEN_EXPIRY_TOO_LONG`. Every successful and failed export attempt emits a durable audit entry with the same secret-safe payload contract as `US-026` and `US-041`. |
| E2E | An authenticated current user can open the event detail surface, click `Export to calendar`, see the `text/calendar` URL, copy the URL, mint a tokenized feed, and see the plaintext token exactly once. The same user can open the watched-events list, click `Subscribe in calendar`, and copy the `GET /watchlist/events.ics` URL. The same user can open the settings surface, see the `Calendar exports` panel, see the active and revoked tokens, see the most recent export audit entries, and revoke a token. The bounded verification harness runs a deterministic ICS export for each `CalendarScope` value and asserts the recorded `calendar_export_audits` row stays within the contract. The migration is exercised end-to-end by the verify script so a missing `calendar_export_tokens` table or a missing `calendar_export_audits` table fails the E2E check, not just the data check. |
| Security | Direct API calls to the new endpoints with anonymous, cross-user, revoked, or expired tokens are rejected with the same error envelope as the existing event and watchlist surfaces. Sanitizer tests prove that audit entries carrying API keys, cookies, raw PII, browser storage state, and full connection strings are rejected or redacted before persistence. The export token plaintext is never persisted on `calendar_export_tokens`; subsequent reads of the same `token_id` return the row without the plaintext. The tokenized endpoint refuses to resolve a token whose scope does not match the requested `text/calendar` response. The calendar exports panel is covered by the existing RBAC contract from `US-027`: a viewer, analyst, sales, or reviewer session gets no access to the token list, the audit list, or the revocation flow. The migration does not weaken the existing audit retention guarantee from `NFR-SEC-008`. The new `CalendarScope` enum does not weaken the existing audit entry shape from `US-026` or the existing sanitization contract from `US-041`. |
| Operational | A runbook entry for the calendar export domain documents what an operator does when a token leak is reported, when a token expires, and when a user asks to bulk-revoke a watchlist calendar feed. The verification script proves that the bounded verification harness can run a deterministic ICS export for each `CalendarScope` value and assert the recorded `calendar_export_audits` row stays within the contract. The new endpoints are covered by the health probe contract from `US-040`: a missing or failing `GET /events/{id}.ics` must not fail `GET /health/ready`, only surface as a degraded warning. |
| Platform | The `scripts/verify-us-045.sh` command wires the unit, integration, E2E, security, and operational checks together and is the same command run by `harness-cli story verify` and `harness-cli story verify-all`. The `calendar_export_tokens` and `calendar_export_audits` migrations are exercised by the verify script so a missing table fails the platform check, not just the data check. The new `CalendarScope` enum and the new audit entry types are exercised by the verify script so a missing enum value fails the platform check, not just the data check. |

## Suggested Checks

- Backend unit tests for:
  - `CalendarExportService.build_event_ics`
  - `CalendarExportService.build_watchlist_ics`
  - `CalendarExportService.build_filter_ics`
  - `CalendarExportService.mint_token`
  - `CalendarExportService.revoke_token`
  - `CalendarExportService.resolve_token`
  - `CalendarExportService.record_export_audit`
  - `CalendarExportFormatter.format_event`
  - `CalendarExportFormatter.format_calendar_name`
  - `CalendarExportFormatter.format_uid`
  - `SanitizeAlertPayload` reuse for every
    audit entry
  - `CalendarScope` enum closure
  - `EnvironmentMode` bound for the
    calendar export token TTL
  - `calendar.STATUS` mapping
    (`UPCOMING` → `TENTATIVE`,
    `LIVE` → `CONFIRMED`,
    `ENDED` → `CANCELLED`)
- Backend integration tests for:
  - `GET /events/{id}.ics`
  - `GET /watchlist/events.ics`
  - `GET /events.ics?campaign_id=&industry=...`
  - `POST /calendar-export-tokens`
  - `GET /calendar-export-tokens`
  - `DELETE /calendar-export-tokens/{id}`
  - `GET /calendar-export/{token}.ics`
  - Cross-user denial for every new endpoint
  - Revoked token denial for
    `GET /calendar-export/{token}.ics`
  - Expired token denial for
    `GET /calendar-export/{token}.ics`
  - Audit entries for every successful and
    failed export attempt
- E2E tests for:
  - Calendar export modal renders the
    `text/calendar` URL and the
    `Mint tokenized feed` button.
  - Watched-events list renders the
    `Subscribe in calendar` action.
  - Calendar exports panel renders the
    active and revoked tokens, the most
    recent export audit entries, and the
    `Revoke` button.
  - The bounded verification harness runs a
    deterministic ICS export for each
    `CalendarScope` value and asserts the
    recorded `calendar_export_audits` row
    stays within the contract.
  - The migrations are exercised by the
    verify script.
- Security tests for:
  - Role enforcement on every new endpoint.
  - Audit entry sanitization for every new
    write path.
  - Plaintext token never persisted on
    `calendar_export_tokens`.
  - Tokenized endpoint refuses to resolve a
    token whose scope does not match the
    requested `text/calendar` response.
  - Calendar exports panel is covered by
    the existing RBAC contract from
    `US-027`.
- Operational checks for:
  - The bounded verification harness can
    run a deterministic ICS export for
    each `CalendarScope` value and assert
    the recorded `calendar_export_audits`
    row stays within the contract.
  - The new endpoints are covered by the
    health probe contract from `US-040`.
  - The runbook entry exists and
    references the right surfaces.
- Platform proof is the
  `scripts/verify-us-045.sh` command wired
  into `harness-cli story verify` and
  `harness-cli story verify-all`.

## Evidence Hooks

- `tests/unit/test_calendar_export_service.py`
  — service unit tests
- `tests/unit/test_calendar_export_formatter.py`
  — formatter unit tests
- `tests/unit/test_calendar_scope_enum.py`
  — `CalendarScope` enum closure
- `tests/unit/test_calendar_export_token_ttl.py`
  — `EnvironmentMode` bound for the
  calendar export token TTL
- `tests/unit/test_calendar_audit_sanitizer.py`
  — `SanitizeAlertPayload` reuse for every
  audit entry
- `tests/integration/test_calendar_export_api.py`
  — REST surface integration tests
- `tests/integration/test_calendar_export_audit.py`
  — audit entry integration tests
- `tests/integration/test_calendar_export_token_lifecycle.py`
  — token mint, resolve, revoke, and
  cross-user denial
- `tests/security/test_calendar_export_role_gates.py`
  — RBAC contract from `US-027`
- `tests/security/test_calendar_export_sanitizer.py`
  — secret-safe payload contract
- `tests/e2e/calendar_export.py`
  — calendar export modal, watched-events
  list, and calendar exports panel
- `frontend/e2e/calendar-export.spec.ts`
  — frontend e2e
- `scripts/verify-us-045.sh`
  — bounded verification harness
- `docs/ops/calendar-export-runbook.md`
  (operational entry)
- `docs/product/event-calendar-export.md`
  (living product contract)
- `docs/decisions/0023-event-calendar-export-ics-baseline.md`
  (durable decision record)

## Open Questions

- Should the calendar export token TTL be
  configurable per workspace, or should it
  always follow the closed
  `EnvironmentMode` bound from `US-040`?
  The first implementation follows the
  closed bound; per-workspace tuning is a
  follow-on story.
- Should the tokenized endpoint support a
  custom calendar `NAME`, or should it
  always return the closed
  `LiveLead watchlist` or
  `LiveLead events ({filter_label})`
  label? The first implementation follows
  the closed label; a follow-on story can
  add a per-token `name` field with
  explicit acceptance criteria.
- Should the `X-LIVELEAD-EVENT-ID`
  extension be reused by a later calendar
  auth story, or should the auth story
  introduce a new extension? The first
  implementation reuses the extension; a
  later story can introduce a new
  extension behind the same
  `CalendarExportFormatter` seam.
- Should the `GET /calendar-export/{token}.ics`
  endpoint return an `ETag` and a
  `Last-Modified` response header for
  calendar client refresh semantics, or
  should the endpoint stay stateless? The
  first implementation stays stateless; a
  follow-on story can add the response
  headers with explicit acceptance
  criteria.
- Should the calendar exports panel expose
  a bulk revoke action, or should the
  panel only expose the per-token `Revoke`
  button? The first implementation exposes
  the per-token button; a follow-on story
  can add the bulk action behind the same
  RBAC contract.
