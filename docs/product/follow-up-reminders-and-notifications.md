# Follow-Up Reminders And Notifications

Source: `SPEC.md` sections 4.4, 5.11, 5.13, `UI-006`, and `AC-BIZ-08`.

## Product Goal

Sales and analyst users need follow-up work to become actionable after a lead
has an owner and follow-up date. The product contract must define how LiveLead
turns lead follow-up dates into due or overdue reminders, surfaces those
reminders in the product, lets users resolve or reschedule them, and provides
baseline in-app visibility before reporting, email delivery, or broader
notification preferences arrive.

## MVP Scope

This product slice covers:

- Creating or refreshing a lead-linked reminder from follow-up scheduling data.
- Showing due and overdue follow-up reminders in a dedicated list or equivalent
  queue.
- Surfacing reminder state in lead detail and lead pipeline views.
- Allowing users to mark a reminder completed or reschedule it after follow-up
  work happens.
- Showing baseline in-app notification or alert visibility when reminders
  become due.
- Preserving reminder history or audit context sufficient to explain who
  completed, rescheduled, or dismissed a reminder.

This product slice does not yet cover:

- Email reminder delivery.
- User-configurable notification preferences or digest frequency.
- Funnel, dashboard, or performance reporting. The first reporting slice is
  defined in `docs/product/dashboard-overview-and-freshness.md`.
- CRM sync, CSV export, or downstream outreach automation.
- Advanced reminder recurrence or multi-step cadence automation.

## Contract Rules

- A reminder must stay linked to its lead and preserve owner context so due
  work is attributable.
- Due and overdue reminders must be distinguishable in both API and UI.
- Completing or rescheduling a reminder must not erase the underlying lead
  history; reminder actions should append audit-friendly history.
- Reminder visibility should derive from explicit follow-up scheduling data
  rather than hidden heuristics.
- In-app reminder notifications may be minimal in this slice, but due reminders
  must become visible without requiring a reporting surface.
- Email delivery and notification preferences are deferred; this slice must not
  imply those channels already exist.

## API Surface

- Lead detail and list payloads must expose reminder state summary when a
  follow-up is scheduled.
- Reminder queue query or equivalent endpoint should return due and overdue
  reminder items with lead context and due timestamps.
- Reminder actions should support completion and rescheduling behavior with
  actor and timestamp context.

## UI Surface

The MVP reminder slice should deepen `UI-006` before reporting:

- Due or overdue reminder queue.
- Reminder badges or equivalent cues in lead table, Kanban, or detail views.
- Complete or reschedule reminder controls.
- Basic in-app alert visibility when reminders are due.

## Validation Implications

- Unit proof should cover due-date classification, reminder-state transitions,
  completion or reschedule rules, and audit-entry creation.
- Integration proof should cover reminder queue behavior, lead-linked reminder
  persistence, and in-app notification read models when present.
- E2E proof should cover creating or updating a follow-up date, seeing a due
  reminder, and completing or rescheduling it from the UI.
- Logs or audit proof should confirm who resolved or moved a reminder and when.
- Platform proof should keep future reminder verification wired into the
  Harness matrix before email notification or reporting stories build on it.
