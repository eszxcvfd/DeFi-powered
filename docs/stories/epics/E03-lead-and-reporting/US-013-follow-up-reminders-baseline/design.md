# Design

## Domain Model

The story should formalize the first reminder-workflow objects:

- `FollowUpReminder`: lead-linked reminder record with due timestamp, owner,
  current reminder state, and last action metadata.
- `ReminderState`: baseline states needed to distinguish scheduled, due,
  overdue, completed, and rescheduled work without implying full cadence
  automation.
- `ReminderNotificationView`: in-app visibility model for due reminder alerts.
- `ReminderHistoryEntry`: append-only history item for reminder completion,
  reschedule, and dismissal actions.

Business rules:

- A reminder must remain linked to one lead and inherit enough lead context for
  users to understand why follow-up is required.
- Due versus overdue classification must be deterministic from stored
  scheduling data.
- Completing or rescheduling a reminder must append history instead of hiding
  the original reminder event.
- Reminder actions must not imply outreach was sent; they only track follow-up
  work state.

## Application Flow

- `ScheduleLeadReminder` creates or refreshes reminder state when a lead gains
  or changes a follow-up date.
- `ListDueReminders` returns due or overdue reminder queues with lead context.
- `CompleteReminder` records the action and closes the current reminder item.
- `RescheduleReminder` updates due time and records why the work moved.
- Lead detail and pipeline queries should include reminder summaries so users do
  not need a separate reporting surface to see upcoming or overdue work.

## Interface Contract

Backend contract should minimally support:

- Reminder queue query or equivalent API surface.
- Reminder completion action.
- Reminder reschedule action.
- Lead payload reminder summaries for detail and pipeline views.

Expected payload concerns:

- Reminder items expose lead id, lead display context, due time, owner, current
  reminder state, and latest action metadata.
- Errors should distinguish missing reminder context, invalid state changes,
  and attempts to resolve reminders for leads without scheduled follow-up.

## Data Model

- Add durable reminder storage or equivalent lead-linked reminder fields that
  can represent current due state and next scheduled action.
- Add append-only reminder history storage or structured activity entries for
  completion, reschedule, and dismissal events.
- Preserve compatibility with later email notifications, preference settings,
  reporting, and outreach-outcome tracking without forcing those workflows into
  this first slice.

## UI / Platform Impact

- Add a reminder queue or equivalent follow-up worklist in the lead area.
- Add due or overdue indicators in lead table, Kanban, and detail views.
- Add complete or reschedule controls with immediate feedback.
- Keep email notifications, dashboard widgets, and cadence automation visibly
  deferred.

## Observability

- Record audit-friendly events for reminder creation or refresh, due
  classification, completion, and reschedule actions.
- Keep enough structured fields in logs to relate reminder changes back to the
  lead, owner, and original follow-up schedule.

## Alternatives Considered

1. Skip reminder records and infer due work only from raw lead follow-up dates.
   Rejected because users need an actionable queue and audit trail, not just a
   date field.
2. Start reporting before reminder resolution exists. Rejected because reminder
   metrics would rest on incomplete workflow truth.
3. Include email delivery and preference management immediately. Rejected
   because in-app reminder visibility is the safer first slice before external
   notification channels.
