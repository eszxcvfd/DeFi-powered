# Overview

## Current Behavior

LiveLead now has a dashboard overview and durable lead outcomes, so the product
can summarize isolated metrics and store conversion facts. However, users still
do not have a first-class reporting surface that shows how records move through
the conversion path from event to lead to contact to response to meeting to
opportunity. There is no explicit cohort rule, no dedicated funnel read model,
and no clear handling for manual leads that do not start from an event link.

## Target Behavior

This story should establish the first funnel reporting slice:

- Show an ordered conversion funnel from event to lead to contact to response to
  meeting to opportunity.
- Apply a clear cohort or time-window rule so counts are explainable.
- Use recorded lead outcomes as the source of truth for downstream conversion
  steps.
- Surface freshness and any unattributed or manual-lead caveats clearly.
- Prepare a clean handoff for later source-performance, content-effectiveness,
  and export stories.

## Affected Users

- Owners and analysts who need to understand conversion flow across the product.
- Sales/BD users who need visibility into whether outreach and follow-up are
  moving leads forward.
- Viewers who consume read-only reporting surfaces.

## Affected Product Docs

- `docs/product/dashboard-overview-and-freshness.md`
- `docs/product/lead-outcomes-and-conversion-tracking.md`
- `docs/product/funnel-reporting-and-conversion-steps.md`

## Non-Goals

- Source-performance breakdowns by platform, connector, campaign, or domain.
- Content-effectiveness comparisons or attribution analysis.
- CSV, PDF, HTML printable, or external export behavior.
- CRM-sync ingestion or automatic external outcome import.
- Revenue forecasting or advanced deal analytics.
