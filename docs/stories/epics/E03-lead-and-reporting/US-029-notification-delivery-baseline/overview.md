# Overview

## Current Behavior

LiveLead already has discovery-job state transitions, canonical events, lead
follow-up reminders, and member-scoped access control, but important changes
still require users to poll multiple pages manually. `US-013` introduced only
baseline in-app reminder visibility and explicitly deferred email delivery and
notification preferences. `SPEC.md` still requires in-app notifications, email
notifications, and user-configurable notification preferences, yet there is no
first-class product contract or story packet for them.

## Target Behavior

This story should establish the first notification-delivery slice for
LiveLead:

- Surface in-app notifications for job completion, needs-user-action, failure,
  and due or overdue reminder events.
- Deliver email notifications for selected high-value events: upcoming event,
  failed discovery job, and overdue follow-up reminder.
- Let each user configure bounded notification preferences by type and channel.
- Preserve read/dismiss lifecycle for in-app alerts.
- Keep delivery, suppression, and preference changes auditable and explainable.

This story should make LiveLead proactive without turning notifications into a
bulk outreach or marketing system.

## Affected Users

- Analysts who need discovery-job completion or failure visibility.
- Sales/BD users who need overdue follow-up prompts and event-timing alerts.
- Reviewers and admins who may need needs-user-action or failure visibility in
  governed workflows.
- Future implementation agents extending watchlist alerts, digest frequency, or
  external notification channels on top of a stable notification contract.

## Affected Product Docs

- `docs/product/follow-up-reminders-and-notifications.md`
- `docs/product/discovery-job-lifecycle.md`
- `docs/product/notification-delivery-and-preferences.md`

## Non-Goals

- Bulk marketing or outreach email.
- Scheduled report delivery or digest-builder workflows.
- Push, SMS, Slack, or webhook notification channels.
- Watchlist automation or calendar-export alerts.
- CRM-sync or ticketing automation.
