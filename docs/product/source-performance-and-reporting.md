# Source Performance And Reporting

Source: `SPEC.md` sections 5.4, 5.5, 5.11, 5.12, 10, and `AC-BIZ-09`.

## Product Goal

Owners, admins, and analysts need to understand which acquisition sources are
producing useful pipeline movement rather than only raw discovery volume. The
product contract must define how LiveLead reports baseline performance by
platform, connector, campaign, and industry using durable discovery, event,
lead, and outcome data, while keeping reporting explainable and distinguishable
from connector-health administration or content-effectiveness analysis.

## MVP Scope

This product slice covers:

- Showing source-performance reporting for a selected time range.
- Grouping performance by platform, connector, campaign, and industry when those
  dimensions are available on durable records.
- Reporting baseline counts such as discovered events, prioritized events,
  created leads, and downstream conversion outcomes attributed to source-linked
  records.
- Showing freshness or last-updated metadata for the source-performance read
  model.
- Showing explicit empty or unavailable states when a requested grouping or
  metric lacks supporting data in the selected window.

This product slice does not yet cover:

- Content-effectiveness comparisons by template, tone, or content type. Those
  attribution behaviors are defined in
  `docs/product/content-effectiveness-and-attribution.md`.
- Export workflows in CSV, PDF, HTML, or external systems. The first report-
  export slice is defined in `docs/product/report-export-and-printing.md`.
- Weighted revenue modeling or ROI estimation.
- Live connector operational health dashboards such as CAPTCHA rate or latency
  administration beyond what already exists in admin surfaces.
- CRM-synced revenue attribution or multi-touch attribution models.

## Contract Rules

- Source-performance counts must derive from durable source-linked event, lead,
  and outcome records rather than guessed client-side joins.
- Reporting dimensions must clearly distinguish operational connector identity
  from product-level grouping keys such as platform, campaign, or industry.
- Records without the required source linkage for a grouping must be excluded or
  surfaced as unattributed, not silently blended into source metrics.
- The same selected time window must apply consistently across all groupings in
  one response.
- Source-performance reporting must expose freshness metadata and explicit empty
  or unavailable states when data is incomplete.

## API Surface

- Source-performance query or equivalent reporting endpoint with time-range and
  grouping input.
- Response payload that returns grouping dimension, grouped metric values,
  freshness metadata, and optional unattributed summaries.
- Validation errors that distinguish unsupported grouping keys from invalid date
  ranges without exposing storage internals.

## UI Surface

The MVP source-performance slice should deepen the reporting area after funnel:

- Source-performance table or equivalent grouped reporting surface.
- Grouping controls for platform, connector, campaign, and industry.
- Metrics for source-linked event volume, scored priority volume, lead creation,
  and downstream outcome milestones when attributable.
- Freshness text and clear empty or unattributed states.

## Validation Implications

- Unit proof should cover grouping normalization, source-attribution rules,
  unattributed handling, and freshness behavior.
- Integration proof should cover grouped reporting across connector, platform,
  campaign, and industry dimensions plus invalid-group handling.
- E2E proof should cover loading source-performance reporting, switching group
  dimensions, and understanding empty or unattributed states.
- Logs or diagnostics should keep source-performance queries explainable by time
  range, grouping key, metric set, freshness, and unattributed counts when
  present.
- Platform proof should keep the future source-performance verification command
  wired into the Harness matrix before content-effectiveness or export stories
  build on it.
