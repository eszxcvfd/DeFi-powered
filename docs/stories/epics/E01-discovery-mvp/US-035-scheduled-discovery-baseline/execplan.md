# Exec Plan

## Goal

Define and implement the first governed scheduled-discovery slice so LiveLead
can dispatch recurring discovery runs through the existing job pipeline with
bounded recurrence, overlap protection, and clear pause/resume control.

## Scope

In scope:

- Discovery schedule creation for valid campaigns and approved sources.
- Daily, weekly, and restricted-cron recurrence with timezone-aware next-run
  preview.
- Scheduler-driven dispatch into standard discovery jobs.
- Overlap protection plus execution-time policy/quota re-checks.
- Schedule status, latest run, and pause/resume/disable controls.

Out of scope:

- AI query expansion or discovery copilot.
- Complex calendars, blackout windows, or holiday rules.
- Scheduled report/email digest delivery.
- Full incremental sync cursor management.
- Autonomous rescheduling based on connector-health signals.

## Risk Classification

Risk flags:

- External systems.
- Data model.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- External provider behavior.
- Removing or weakening validation requirements.

## Work Phases

1. Discovery: confirm schedule requirements from `SPEC.md`, discovery lifecycle,
   runtime architecture, and scheduler boundaries.
2. Design: define recurrence model, next-run calculation, overlap policy, and
   dispatch-to-job linkage.
3. Validation planning: design proof for schedule validation, scheduler tick
   dispatch, policy re-checks, and pause/resume behavior.
4. Implementation: add schedule storage, scheduler dispatch logic, discovery
   API/UI surfaces, and latest-run projections.
5. Verification: prove scheduled runs create standard discovery jobs safely and
   avoid overlap or runaway frequency.
6. Harness update: keep product docs current, update durable story status, and
   leave a clean handoff for query expansion or discovery copilot stories.

## Stop Conditions

Pause for human confirmation if:

- Product behavior is ambiguous.
- Data migration or deletion risk appears.
- Validation requirements need to be weakened.
- Architecture direction changes.
- The first scheduling slice would require arbitrary cron/calendar complexity
  instead of bounded recurrence.
- The team wants AI query expansion or scheduled report delivery folded into
  this baseline.
