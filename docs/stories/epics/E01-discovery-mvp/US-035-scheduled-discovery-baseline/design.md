# Design

## Domain Model

The story should formalize the first governed scheduled-discovery objects:

- `DiscoverySchedule`: campaign-scoped recurring discovery definition with
  recurrence rule, timezone, enabled state, overlap policy, and selected source
  scope.
- `ScheduledDiscoveryTemplate`: immutable or versioned template context that
  records how future jobs should derive criteria/source snapshots.
- `ScheduledDispatchRecord`: durable link between one schedule trigger and the
  discovery job it launched, including dispatch outcome and failure reason when
  no job is created.

Business rules:

- A schedule exists only for a valid campaign and approved sources.
- Schedule recurrence stays bounded to daily, weekly, or restricted-cron shapes.
- Execution-time policy checks still apply even when the saved schedule itself
  is valid.
- Overlap prevention is part of product behavior; one schedule cannot flood the
  system with concurrent duplicate runs.
- Historical runs remain immutable even when a schedule is edited, paused, or
  disabled later.

## Application Flow

- `CreateDiscoverySchedule` validates campaign/source eligibility, recurrence,
  timezone, and overlap policy before storing a schedule.
- `ListDiscoverySchedules` returns active/inactive schedule summaries with next
  run and latest run projection.
- `UpdateDiscoverySchedule` handles recurrence changes and pause/resume or
  disable transitions for future runs only.
- `DispatchScheduledDiscoveryRuns` is driven by the scheduler process and turns
  eligible schedules into standard discovery jobs through the existing
  orchestration path.
- `RecordScheduledDispatchOutcome` preserves whether a schedule produced a job,
  was skipped for overlap, or was blocked by live policy/quota checks.

## Interface Contract

This baseline should extend discovery administration and existing job surfaces:

- `POST /campaigns/{id}/discovery-schedules` creates a schedule for a campaign.
- `GET /campaigns/{id}/discovery-schedules` returns bounded schedule summaries.
- `PATCH /discovery-schedules/{id}` or equivalent actions update recurrence or
  pause/resume/disable status.
- Existing discovery job routes remain the source of truth for actual run
  outcomes after dispatch.

Expected payload concerns:

- Schedule responses should include recurrence summary, timezone, enabled state,
  next run, selected sources, and latest run summary.
- Validation errors should reject unsupported cron shapes or unsafe frequency
  clearly.
- Dispatch/block reasons should stay action-oriented without exposing secret or
  low-level scheduler internals.

## Data Model

- Add durable schedule storage keyed by organization/campaign with recurrence,
  timezone, enabled state, overlap policy, and selected source scope.
- Preserve dispatch history or latest-dispatch metadata needed for status,
  observability, and audit.
- Reuse existing discovery-job storage for actual run execution records rather
  than creating a separate scheduled-result silo.
- Add query support needed for next-run ordering and schedule status reads.

## UI / Platform Impact

- Campaign discovery UI should offer bounded schedule creation from the same
  campaign context used for manual runs.
- Schedule list/detail UI should show recurrence summary, next run, latest run,
  and pause/resume or disable controls.
- Scheduler process becomes a first-class runtime path for discovery dispatch,
  but users still review actual results through the existing job/event flows.
- Platform work should stay inside the existing `scheduler` process boundary and
  shared discovery orchestration path.

## Observability

- Record structured diagnostics for schedule validation, dispatch attempt,
  overlap skip, policy block, and created job linkage.
- Keep audit outputs explainable with actor, campaign id, schedule id,
  recurrence summary, and dispatched job id where applicable.
- Preserve enough scheduler counters/metrics to support later health analytics
  without requiring that dashboard in this baseline.

## Alternatives Considered

1. Jump directly to AI-assisted query expansion before schedules exist.
   Rejected because repeated runs need a governed scheduling contract first.
2. Let scheduled runs bypass manual discovery orchestration. Rejected because
   the same policy, job-state, and event-review rules should still apply.
3. Support arbitrary cron or calendar logic in the first slice. Rejected
   because bounded recurrence is safer and easier to validate.
