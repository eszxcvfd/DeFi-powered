# Overview

## Current Behavior

LiveLead can now report overall metrics, funnel conversion, and source
performance, while the product also stores used-content history and optional
lead-outcome content links. However, users still do not have a first-class
reporting surface that compares how different content strategies perform. There
is no grouped comparison by content type, tone, or template metadata, and no
clear treatment of linked outcomes that cannot be attributed cleanly to one
content cohort.

## Target Behavior

This story should establish the first content-effectiveness reporting slice:

- Show grouped content-effectiveness reporting by content type, tone, and
  template metadata.
- Use used-content history and linked lead outcomes as the attribution source.
- Surface freshness and unattributed-record caveats clearly.
- Support one selected time range across the grouped report.
- Prepare a clean handoff for later report-export stories.

## Affected Users

- Owners and analysts who need to compare which content strategies correlate
  with better downstream outcomes.
- Sales/BD users who want visibility into which approved or used content styles
  are performing best.
- Viewers who consume read-only reporting surfaces.

## Affected Product Docs

- `docs/product/content-effectiveness-and-attribution.md`
- `docs/product/lead-outcomes-and-conversion-tracking.md`
- `docs/product/source-performance-and-reporting.md`

## Non-Goals

- CSV, PDF, HTML printable, or external export behavior.
- Multi-touch attribution or causal inference claims.
- Revenue or ROI estimation.
- Automatic content-optimization recommendations.
- External-channel analytics not already captured by the product.
