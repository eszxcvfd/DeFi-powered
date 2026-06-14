# Overview

## Current Behavior

LiveLead can now create leads, move them through default stages, schedule
follow-up reminders, and define the first dashboard overview. However, the
product still lacks a first-class way to record the manual conversion facts that
matter after follow-up work happens. Users can move a lead to another stage, but
there is no explicit outcome entry for contact, response, meeting, or
opportunity milestones, no optional link from those outcomes back to content
that was used, and no durable outcome history for later funnel or
content-effectiveness reporting.

## Target Behavior

This story should establish the first lead-outcome slice:

- Let users record manual contact, response, meeting, and opportunity outcomes.
- Preserve those outcomes as append-only timeline history on the lead.
- Allow optional linkage between an outcome and previously used content.
- Surface latest-outcome context in lead views.
- Prepare a clean handoff for later funnel, content-effectiveness, and CRM-sync
  stories.

## Affected Users

- Sales/BD users who need to record what happened after outreach or follow-up.
- Analysts who monitor whether event and content work turns into real pipeline
  movement.
- Owners or viewers who depend on accurate conversion facts for later reports.

## Affected Product Docs

- `docs/product/lead-pipeline-and-activities.md`
- `docs/product/lead-outcomes-and-conversion-tracking.md`
- `docs/product/dashboard-overview-and-freshness.md`

## Non-Goals

- Funnel charts or aggregate reporting visuals.
- CRM synchronization or automatic import of external outcomes.
- Automatic browser-send or autonomous outreach detection.
- Revenue forecasting, closed-won modeling, or advanced deal management.
- Full content-effectiveness analysis beyond storing linkable outcome evidence.
