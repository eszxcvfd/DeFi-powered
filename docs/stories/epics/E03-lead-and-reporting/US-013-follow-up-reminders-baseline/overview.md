# Overview

## Current Behavior

LiveLead now has a first lead pipeline slice with owner, follow-up date, and
activity history, but follow-up work is still passive. Users can store a date
on a lead, yet the product does not define how that date becomes a due or
overdue reminder, where reminder work is reviewed, or how reminder completion
and rescheduling should appear in the UI and audit trail.

## Target Behavior

This story should establish the first reminder workflow slice:

- Turn lead follow-up scheduling data into actionable reminders.
- Show due and overdue reminders in the product.
- Surface reminder cues in lead detail and pipeline views.
- Allow completion or rescheduling of reminder work.
- Provide baseline in-app visibility when reminders become due.

## Affected Users

- Sales/BD users who own lead follow-up work.
- Analysts who hand off qualified leads and need visibility into next steps.
- Admins or reviewers who need audit context for reminder actions.

## Affected Product Docs

- `docs/product/lead-pipeline-and-activities.md`
- `docs/product/follow-up-reminders-and-notifications.md`

## Non-Goals

- Email reminder delivery or notification-preference settings.
- Dashboard, funnel, or performance reporting.
- CRM sync, CSV export, or bulk outreach automation.
- Multi-step cadence or recurrence engines.
