# Overview

## Current Behavior

LiveLead now has event discovery, scoring, content workflow, lead pipeline, and
follow-up reminders, but there is still no shared reporting surface that helps
users understand whether that work is moving the business forward. Users can
inspect individual records, yet they do not have a date-range dashboard view,
per-widget freshness, or a clear distinction between empty metrics and metrics
that are not ready because the underlying workflow truth is still deferred.

## Target Behavior

This story should establish the first dashboard reporting slice:

- Add a dashboard overview driven by a selected time range.
- Show summary widgets for metrics already backed by durable workflow data.
- Show freshness or last-updated context on each widget.
- Distinguish real zero values from explicitly unavailable metrics.
- Prepare a clean handoff for later funnel, source-performance, and export
  stories.

## Affected Users

- Owners and admins who need high-level business visibility.
- Analysts who monitor discovery and qualification throughput.
- Sales/BD users who need a shared view of pipeline momentum.
- Viewers who consume read-only reporting surfaces.

## Affected Product Docs

- `docs/product/dashboard-overview-and-freshness.md`
- `docs/product/lead-pipeline-and-activities.md`
- `docs/product/follow-up-reminders-and-notifications.md`

## Non-Goals

- Funnel visualization or conversion-step reporting.
- Source-performance, campaign-comparison, or content-effectiveness reporting.
- CSV, PDF, printable, or CRM-oriented export behavior.
- Email digests, notification preferences, or scheduled reporting.
- New event-watchlist or outcome-entry workflows created only to satisfy one
  dashboard card.
