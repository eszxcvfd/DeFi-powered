# Live Feed And API Discovery

Source: `SPEC.md` sections 5.3, 5.4, 7.2, 11, 12, 14.1, 14.2, and `UC-01`.

## Product Goal

Analysts need the first real discovery path that can find actual events or
livestream candidates from approved public feeds or APIs. Before LiveLead adds
browser-driven platform connectors, the product contract should define how
manual discovery jobs use official `API`, `RSS`, `Atom`, `sitemap`, or `ICS`
sources, how those responses become canonical event review data, and how the
system fails safely when a source is blocked, misconfigured, or unexpectedly
interactive.

## MVP Scope

This product slice covers:

- Running approved live external `API`, `RSS`, `Atom`, `sitemap`, or `ICS`
  connectors from the existing manual discovery-job workflow.
- Supporting at least one real feed-style or API-style source family and the
  reusable connector contract needed to add more without changing business
  logic.
- Preserving per-source fetch outcome, fetched-at timestamp, source URL or
  endpoint context, and connector provenance needed for event review.
- Normalizing live connector output through the existing canonical event and
  source-observation pipeline instead of keeping live discovery as a raw dump.
- Surfacing partial success, per-source errors, and safe-stop reasons when one
  source fails but others still return usable results.
- Showing enough connector readiness state that admins can distinguish runnable,
  denied, misconfigured, and needs-user-action sources.

This product slice does not yet cover:

- Public website connectors that require `Playwright` or `Selenium`
  navigation. The first `Playwright` slice is defined in
  `docs/product/public-website-playwright-discovery.md`.
- Interactive login, headed browser assistance, or saved browser-state reuse.
- Private platform APIs that require a broader delegated-auth contract than the
  current source policy supports.
- Scheduled synchronization, incremental cursors, or always-on polling beyond
  manual discovery runs.
- Full connector-health dashboards or long-term latency analytics.

## Contract Rules

- Official `API`, `RSS`, `Atom`, `sitemap`, or `ICS` access remains the
  preferred discovery path when a suitable official source exists.
- A live feed or API connector must not run unless the source is enabled,
  approved, within policy window, and inside quota or budget limits.
- Source configuration for this slice must preserve enough execution metadata to
  run safely: endpoint or feed URL, parser family, authentication mode, request
  window or paging hints when needed, and stable identity hints for downstream
  deduplication.
- Connectors must enforce configured request budgets and rate limits and must
  never log secrets, tokens, cookies, or raw credential material.
- If a source returns an auth challenge, CAPTCHA, MFA, or other interactive
  barrier, the system must stop safely by marking the source denied or
  `NEEDS_USER_ACTION`; it must not silently fall back to hidden browser
  automation.
- Each fetched item must retain enough provenance for event review, including
  source id, source URL, observation or fetch time, and connector type.
- Partial failure of one selected source must not discard successful items from
  other selected sources in the same discovery job.
- Live external discovery is only complete when users can review the resulting
  canonical events through the existing event list and detail surfaces.

## API Surface

- `POST /campaigns/{id}/discovery-jobs`: existing manual launch flow should be
  able to execute approved live feed or API connectors for the selected sources.
- `GET /discovery-jobs/{id}`: existing job detail should expose per-source live
  fetch outcome, safe-stop reasons, and counts suitable for progress and
  partial-success UX.
- `GET /campaigns/{id}/events` and `GET /events/{id}`: existing review surfaces
  should expose live-source provenance through canonical events and linked
  source observations without leaking secrets.
- `GET /admin/connectors`: admin registry responses should surface live-source
  readiness or validation state without exposing raw secrets.

## UI Surface

- Analysts can launch a manual discovery run against approved live feed or API
  sources from the existing campaign workflow.
- Discovery job progress shows which live sources succeeded, failed, were
  denied, or require user action.
- Event review surfaces show usable canonical events from live sources without
  requiring a different review UI than the existing event list and detail flow.
- Admin connector surfaces show whether a feed or API source is runnable or
  blocked, plus a clear non-secret reason.

## Validation Implications

- Unit proof should cover source-readiness decisions, parser mapping, safe-stop
  rules, and provenance shaping for live feed or API items.
- Integration proof should cover stubbed or fixture-backed HTTP responses,
  policy enforcement before fetch, partial-success behavior, and canonical event
  persistence from live source output.
- E2E proof should cover launching a manual discovery run, observing per-source
  live progress, and reviewing canonical events created from live connector
  results.
- Logs and audit proof should confirm connector-denied, quota-blocked,
  needs-user-action, and secret-redaction paths remain explainable.
- Platform proof should keep worker, API, and frontend verification wired into
  the Harness matrix before browser-based connector stories begin.
