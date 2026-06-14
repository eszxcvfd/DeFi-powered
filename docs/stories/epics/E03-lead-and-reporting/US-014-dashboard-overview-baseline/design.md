# Design

## Domain Model

The story should formalize the first reporting read-model objects:

- `DashboardOverview`: aggregate response for one requested time window.
- `DashboardTimeWindow`: normalized date-range selection used by every widget in
  the response.
- `DashboardMetricCard`: one summary widget with metric key, label, value, and
  availability status.
- `WidgetFreshness`: last-updated metadata or equivalent staleness context for a
  single metric card.
- `MetricAvailability`: baseline state model that distinguishes available,
  empty, and unavailable metrics.

Business rules:

- Dashboard widgets are read models only and must not create new operational
  workflows.
- Metrics must derive from durable stored event, content, lead, or reminder
  data already owned by the product.
- A widget may report zero only when the selected window truly contains no
  matching records; it must report unavailable when the product lacks durable
  source data for that metric.
- All widgets in one overview response must use the same normalized time window.
- Freshness should describe underlying data recency rather than only the moment
  the API query ran.

## Application Flow

- `GetDashboardOverview` validates the requested time window and gathers widget
  results from existing discovery, scoring, content, and lead domains.
- Widget builders classify each metric as available, empty, or unavailable
  before the response is rendered.
- Freshness derivation should use the newest relevant durable record timestamp
  or equivalent source-backed update time for each widget.
- Frontend queries should render the dashboard without requiring users to open
  separate event, content, or lead screens first.

## Interface Contract

Backend contract should minimally support:

- Dashboard overview query or equivalent reporting endpoint.
- Time-range input with predictable defaults and validation behavior.
- Response fields for widget key, label, availability state, numeric value when
  available, and freshness metadata.

Expected payload concerns:

- Errors should distinguish invalid date ranges from unsupported filters.
- Unavailable metrics must be explicit in the payload so the UI does not guess.
- Widget identifiers should stay stable enough for future funnel, source, or
  export stories to extend rather than replace the contract.

## Data Model

- Prefer a read-model or query-layer composition over new canonical transactional
  tables for this first slice.
- Reuse durable timestamps and workflow states already recorded in event,
  content, lead, and reminder storage.
- Add lightweight reporting-specific structures only when needed to express
  freshness or availability without duplicating operational truth.
- Preserve compatibility with later funnel, source-performance, and export
  reporting without locking the system into one aggregation strategy.

## UI / Platform Impact

- Add a dashboard overview surface with date-range control and responsive
  summary widgets.
- Show freshness text or equivalent update metadata on every widget.
- Render clear empty and unavailable states instead of hiding missing metrics.
- Keep funnel charts, export controls, and comparison reporting visibly
  deferred.

## Observability

- Record diagnostic context for dashboard queries, including time window,
  widget keys returned, availability status, and freshness fields.
- Keep enough structured evidence to explain why a widget rendered unavailable
  instead of silently returning zero.

## Alternatives Considered

1. Start reporting with funnel visualization first. Rejected because a simpler
   overview surface gives users value sooner and establishes shared freshness and
   availability rules for later report slices.
2. Compute dashboard cards only in the frontend from whatever pages already
   loaded. Rejected because reporting truth must come from one backend read
   model, not accidental client state.
3. Wait until every desired metric has a perfect source of truth. Rejected
   because a clearly scoped baseline with explicit unavailable states is better
   than no dashboard at all.
