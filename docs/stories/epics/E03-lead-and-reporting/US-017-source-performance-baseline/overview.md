# Overview

## Current Behavior

LiveLead can now summarize overall dashboard metrics, show funnel conversion
steps, and preserve durable lead outcomes. However, users still do not have a
grouped reporting surface that explains which source dimensions are producing
valuable pipeline activity. There is no first-class way to compare platform,
connector, campaign, or industry performance using one durable reporting model,
and no clear treatment of records that cannot be attributed to a source group.

## Target Behavior

This story should establish the first source-performance reporting slice:

- Show grouped source-performance reporting by platform, connector, campaign,
  and industry.
- Use durable source-linked discovery, event, lead, and outcome data for
  attributable metrics.
- Surface freshness and unattributed-record caveats clearly.
- Support one selected time range across the grouped report.
- Prepare a clean handoff for later content-effectiveness and export stories.

## Affected Users

- Owners and analysts who need to compare which sources and campaigns are
  producing qualified pipeline movement.
- Admins who need product-level source effectiveness visibility separate from
  connector operational health.
- Viewers who consume read-only reporting surfaces.

## Affected Product Docs

- `docs/product/source-performance-and-reporting.md`
- `docs/product/dashboard-overview-and-freshness.md`
- `docs/product/funnel-reporting-and-conversion-steps.md`

## Non-Goals

- Content-effectiveness comparisons by template, tone, or content type.
- CSV, PDF, HTML printable, or external export behavior.
- Revenue or ROI estimation.
- Connector-health administration such as latency or CAPTCHA-rate dashboards.
- Multi-touch attribution or CRM-synced revenue analysis.
