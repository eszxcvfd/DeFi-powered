# Funnel Reporting And Conversion Steps

Source: `SPEC.md` sections 4.4, 5.11, 5.12, 7.2, 8, and `AC-BIZ-09`.

## Product Goal

Owners, analysts, and sales users need a reporting surface that turns event,
lead, and outcome records into an explainable conversion funnel. The product
contract must define how LiveLead reports the baseline steps from event to lead
to contact to response to meeting to opportunity, how the selected cohort or
time window is applied, how funnel freshness is exposed, and how manual leads or
missing source linkage are handled before source-performance, content-
effectiveness, or export stories arrive.

## MVP Scope

This product slice covers:

- Showing a baseline funnel report for a selected cohort or time range.
- Reporting the first conversion steps required by the spec: event, lead,
  contact, response, meeting, and opportunity.
- Defining how event-linked and manual leads participate in the funnel.
- Showing freshness or last-updated metadata for the funnel read model.
- Showing explicit empty states when the selected cohort has no matching data.

This product slice does not yet cover:

- Source-performance breakdowns by platform, connector, campaign, or domain.
  Those grouped reporting behaviors are defined in
  `docs/product/source-performance-and-reporting.md`.
- Content-effectiveness comparisons by template, tone, or content type.
- CSV, PDF, HTML printable, or external export workflows. The first report-export
  slice is defined in `docs/product/report-export-and-printing.md`.
- CRM synchronization or automatic external outcome ingestion.
- Revenue forecasting, weighted pipeline, or closed-won modeling.

## Contract Rules

- Funnel counts must derive from durable event, lead, and outcome records rather
  than inferred client-side state.
- The first funnel slice must document a stable cohort rule so users can
  understand why a record appears in the report.
- Contact, response, meeting, and opportunity steps must come from explicit
  recorded outcome facts, not only from current lead stage.
- Event and lead steps may use different entity types, so the first event-to-
  lead conversion edge does not need to be numerically monotonic; later steps
  based on lead outcomes should remain comparable within the selected cohort.
- Manual leads that do not have an event link must be either excluded from the
  event step or surfaced as unattributed lead context rather than silently
  inflating event-origin funnel metrics.
- Funnel responses must expose freshness metadata so users can judge reporting
  recency.

## API Surface

- `GET /reports/funnel` or equivalent reporting endpoint with cohort or
  time-range input.
- Response payload that returns ordered funnel steps, counts, cohort metadata,
  and freshness information.
- Optional metadata for unattributed or manual-entry lead counts when those
  records participate from the lead step onward.

## UI Surface

The MVP funnel slice should deepen the reporting area after dashboard overview:

- Funnel visualization or equivalent ordered step list.
- Shared date-range or cohort selection.
- Step labels and counts for event, lead, contact, response, meeting, and
  opportunity.
- Freshness text and clear empty-state behavior.
- Optional unattributed-lead note when manual leads are not counted at the event
  step.

## Validation Implications

- Unit proof should cover cohort membership rules, step-count derivation, manual
  lead handling, and freshness behavior.
- Integration proof should cover funnel endpoint responses across event-linked
  leads, manual leads, and recorded outcome data.
- E2E proof should cover loading the funnel, changing the selected window, and
  understanding empty or unattributed states when they appear.
- Logs or diagnostics should keep funnel queries explainable by cohort rule,
  step counts, freshness, and unattributed counts when present.
- Platform proof should keep the future funnel verification command wired into
  the Harness matrix before source-performance, content-effectiveness, or export
  stories build on it.
