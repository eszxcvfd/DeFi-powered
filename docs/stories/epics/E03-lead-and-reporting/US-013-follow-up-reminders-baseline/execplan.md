# Exec Plan

## Goal

Define and implement the minimum follow-up reminder slice that turns lead
follow-up dates into actionable due or overdue work, lets users complete or
reschedule reminders, and provides baseline in-app visibility before reporting
or email notification stories arrive.

## Scope

In scope:

- Lead-linked reminder scheduling from follow-up dates.
- Due and overdue reminder queue behavior.
- Reminder completion and reschedule actions.
- Reminder cues in lead detail and pipeline views.
- Baseline in-app visibility for due reminders.

Out of scope:

- Email delivery and notification preferences.
- Dashboard, funnel, or performance reporting.
- CRM sync, CSV export, or bulk outreach automation.
- Recurring cadence logic or multi-step follow-up sequences.

## Risk Classification

Risk flags:

- Data model.
- Public contracts.
- Existing behavior.
- Weak proof.
- Multi-domain.

Hard gates:

- None triggered directly, but the lane stays high-risk because this story adds
  new durable reminder workflow, user-visible notification behavior, and
  cross-domain lead-to-notification state.

## Work Phases

1. Discovery: confirm reminder, due or overdue, and in-app visibility rules
   from `SPEC.md`, `FR-LEAD-006`, and `FR-NOT-001`.
2. Design: define reminder entities, queue behavior, resolution actions, and
   lead-surface cues without dragging in reporting or email delivery.
3. Validation planning: design proof for due classification, queue queries,
   completion or reschedule behavior, and visible in-app reminder alerts.
4. Implementation: add reminder persistence, queue contracts, lead-surface
   summaries, and baseline in-app visibility.
5. Verification: prove reminder creation, due or overdue listing, completion,
   and reschedule behavior end to end.
6. Harness update: record the new reminder contract and leave a clean handoff
   for reporting, notification preferences, and export stories.

## Stop Conditions

Pause for human confirmation if:

- Reminder behavior needs recurrence or cadence policy beyond one follow-up
  step.
- Email delivery or notification preferences are pulled into this story.
- Reminder completion needs to imply outreach outcomes or CRM synchronization.
- Validation requirements need to be weakened because queue and lead surfaces
  expand beyond one slice.
