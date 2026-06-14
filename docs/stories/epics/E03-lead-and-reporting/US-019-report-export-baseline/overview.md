# Overview

## Current Behavior

LiveLead now has multiple reporting surfaces: dashboard overview, funnel,
source-performance, and content-effectiveness. Users can review those reports in
the product, but they still cannot take the current report view out into
spreadsheets, printable review packets, or meeting follow-up. Reporting export
is also still conflated with content handoff in some product expectations, even
though content export and report export are different user workflows.

## Target Behavior

This story should establish the first reporting-export slice:

- Export dashboard, funnel, source-performance, and content-effectiveness views.
- Support CSV export for stable tabular report output.
- Support PDF or HTML-printable export for human-readable report sharing.
- Preserve the currently selected time range and grouping context in exported
  output.
- Surface freshness or generated-at context in the exported artifact.

## Affected Users

- Owners and analysts who need portable reporting for review and sharing.
- Sales/BD users who need to bring current reporting into follow-up workflows.
- Viewers who consume reporting in read-only form and may need printable output.

## Affected Product Docs

- `docs/product/report-export-and-printing.md`
- `docs/product/dashboard-overview-and-freshness.md`
- `docs/product/funnel-reporting-and-conversion-steps.md`
- `docs/product/source-performance-and-reporting.md`
- `docs/product/content-effectiveness-and-attribution.md`
- `docs/product/content-handoff-and-export.md`

## Non-Goals

- Scheduled report delivery, email digests, or subscriptions.
- External-system export or synchronization.
- Custom branded report templates or presentation editing.
- Revenue or ROI modeling beyond current report semantics.
- Changing how dashboard, funnel, source-performance, or content-effectiveness
  metrics themselves are calculated.
