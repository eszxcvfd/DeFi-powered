# Overview

## Current Behavior

LiveLead currently stops the analyst-to-sales workflow at approved content
handoff. Users can review events, score them, generate and approve content, and
mark that content as used, but there is no first-class lead workspace for
turning a qualified event into a trackable pipeline record. The repo also lacks
an E03 product slice that defines lead creation, state tracking, duplicate
guardrails, or activity history.

## Target Behavior

This story should establish the first lead-pipeline slice:

- Allow users to create leads from event-linked context or manual entry.
- Persist the core lead fields needed for pipeline work.
- Expose default pipeline states in both detail and pipeline views.
- Record baseline activity history for create, note, and status-change events.
- Apply duplicate guardrails before a second lead record is created.

## Affected Users

- Sales/BD users who create and advance leads.
- Analysts who pass qualified events into the lead workflow.
- Admins or reviewers who need audit visibility into lead changes.

## Affected Product Docs

- `docs/product/overview.md`
- `docs/product/lead-pipeline-and-activities.md`

## Non-Goals

- Reminder queue UX or overdue follow-up management.
- CSV import/export, CRM sync, or dashboard metrics.
- Browser-assisted outreach or automatic send behavior.
- Complex merge-resolution workflow for ambiguous duplicates.
