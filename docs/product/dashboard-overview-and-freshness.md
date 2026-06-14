# Dashboard Overview And Freshness

Source: `SPEC.md` sections 4.4, 5.12, 5.13, and `AC-BIZ-09`.

## Product Goal

Owners, analysts, sales users, and viewers need the first reporting surface that
summarizes whether discovery, prioritization, content work, and lead follow-up
are producing usable pipeline movement. The product contract must define how
LiveLead exposes a trustworthy dashboard overview, applies a shared time window,
shows widget freshness, and distinguishes real zero values from metrics that are
not yet backed by durable workflow data.

## MVP Scope

This product slice covers:

- Showing a dashboard overview for a selected time range.
- Returning summary widgets for workflow signals already backed by durable
  product data, such as discovered events, prioritized events, new leads,
  content created or reviewed or used, and stage-based pipeline outcomes when
  those states exist in current records.
- Showing freshness or last-updated metadata for every dashboard widget.
- Rendering empty states when the selected time range has no matching records.
- Rendering explicit unavailable states when a requested metric still lacks a
  durable source of truth in the current MVP data model.

This product slice does not yet cover:

- Funnel visualization or conversion-step reporting.
- Performance-by-source or campaign-comparison reporting.
- Content-effectiveness comparison by template, tone, or variant.
- CSV, PDF, or printable report export.
- Email digests, notification preferences, or scheduled report delivery.
- New watchlist, outcome-entry, or CRM-sync workflows created only to satisfy a
  dashboard card.

## Contract Rules

- Dashboard widgets must derive from durable stored product data rather than
  guessed client-side approximations.
- All widgets in one dashboard response must respect the same requested time
  window.
- A widget must expose freshness metadata that helps the user understand how
  recent the underlying data is.
- Zero values are valid only when matching records truly count to zero for the
  selected window; metrics without durable backing data must be marked
  unavailable instead of silently returning misleading zeroes.
- The first dashboard slice is read-only and must not introduce new mutation
  workflows.

## API Surface

- Dashboard overview query or equivalent endpoint with date-range input.
- Response payload that returns widget identity, label, value or availability
  state, and freshness metadata.
- Validation errors that distinguish invalid date ranges from unsupported
  filters without exposing storage internals.

## UI Surface

The MVP reporting slice should introduce the first dashboard overview before
funnel or export stories:

- Date-range selection for the dashboard overview.
- Summary cards or equivalent widgets for available metrics.
- Freshness or last-updated text on each widget.
- Clear empty and unavailable states so deferred metrics are visible without
  pretending the data already exists.

## Validation Implications

- Unit proof should cover time-window normalization, metric availability
  classification, and freshness derivation rules.
- Integration proof should cover dashboard aggregation across existing event,
  content, and lead data plus empty or unavailable-state behavior.
- E2E proof should cover choosing a time range, loading the dashboard, and
  seeing both populated and empty or unavailable widget states.
- Logs or diagnostics should keep dashboard queries explainable by time range,
  widget key, freshness, and availability status.
- Platform proof should keep the future dashboard verification command wired
  into the Harness matrix before funnel, source-performance, or export stories
  build on it.
