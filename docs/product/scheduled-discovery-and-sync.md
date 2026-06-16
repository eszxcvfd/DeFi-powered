# Scheduled Discovery And Sync

Source: `SPEC.md` sections 5.4, 7.2, 7.3, 11, 12, 14.1, and `UC-01`.

## Product Goal

Analysts and admins need discovery to run on a governed schedule so LiveLead
can refresh event and livestream findings without requiring a person to trigger
every run manually. The product contract should define the first bounded
scheduled-discovery slice, including supported recurrence patterns, how a
schedule captures campaign and source context, how scheduled runs avoid unsafe
overlap, and how scheduled execution remains explainable through the same job
and event review surfaces as manual runs.

## MVP Scope

This product slice covers:

- Creating a bounded discovery schedule for a valid campaign with approved
  source scope.
- Supporting daily, weekly, and restricted-cron recurrence patterns.
- Storing the schedule timezone, next-run calculation, enabled/paused state,
  and the job template context needed to launch future runs safely.
- Launching scheduled discovery jobs through the existing discovery orchestration
  path rather than introducing a separate execution model.
- Preventing unsafe overlap, runaway retries, or unbounded run frequency for
  scheduled jobs.
- Showing schedule status, next run, latest run result, and pause/resume
  controls in the product.

This product slice does not yet cover:

- AI query expansion or discovery-copilot assistance before a scheduled run.
  The first query-expansion slice is defined in
  `docs/product/query-expansion-and-review.md`.
- Complex calendars, exclusions, blackout windows, or multi-step recurrence
  designers.
- Incremental sync cursors per source beyond the first schedule baseline.
- Scheduled report delivery, digest builders, or non-discovery outbound
  automation.
- Full connector-health analytics or autonomous rescheduling based on observed
  performance.

## Contract Rules

- A discovery schedule may exist only for a valid campaign and at least one
  currently approved source selection.
- The schedule must retain enough template context to explain why a future run
  executed, including campaign id, source scope, timezone, recurrence rule, and
  the criteria snapshot strategy.
- Scheduled runs must still pass source policy, quota, and connector readiness
  checks at execution time; a valid saved schedule does not bypass live policy.
- The first schedule baseline must keep recurrence bounded: daily, weekly, or a
  restricted cron shape validated by product rules.
- The scheduler must prevent unsafe overlap according to an explicit rule such
  as skip-while-running or queue-one, rather than launching unlimited concurrent
  copies for the same schedule.
- Pause, resume, disable, and delete actions must take effect for future runs
  without mutating historical job records.
- Scheduled job outcomes must remain explainable through the same job-state and
  event-review surfaces used for manual discovery.
- Failed or blocked scheduled runs may retry only within the controlled retry
  rules already defined for discovery jobs; schedules must not amplify infinite
  retry loops.

## API Surface

- `POST /campaigns/{id}/discovery-schedules`: create a bounded discovery
  schedule for the current campaign and selected source scope.
- `GET /campaigns/{id}/discovery-schedules` or equivalent list route: return
  current schedules with enabled state, recurrence summary, timezone, next run,
  and latest run status.
- `PATCH /discovery-schedules/{id}` or equivalent actions: update recurrence,
  pause/resume, or disable a schedule safely.
- Scheduled runs should produce standard discovery jobs visible through the
  existing job and event routes rather than a separate result API.

## UI Surface

- Analysts can create a bounded discovery schedule from a campaign that already
  works for manual discovery.
- Schedule forms show recurrence summary, timezone, selected sources, and next
  run preview before save.
- Users can view current schedules, latest run status, and next planned run.
- Pause/resume or disable controls give immediate status feedback.
- Scheduled results remain visible through the standard discovery job and event
  review surfaces instead of a separate reporting screen.

## Validation Implications

- Unit proof should cover recurrence validation, next-run calculation, overlap
  rules, and schedule state transitions.
- Integration proof should cover schedule persistence, scheduler tick/dispatch,
  execution-time policy re-checks, and scheduled-job creation through the
  shared discovery path.
- E2E proof should cover creating a schedule, seeing the next-run preview,
  observing a scheduled run appear, and pausing/resuming the schedule.
- Logs and audit proof should confirm schedule create/update/pause/resume plus
  dispatched-run provenance remain explainable with actor, campaign, schedule,
  and job context.
- Platform proof should keep scheduler-process verification wired into the
  Harness matrix before AI query expansion or discovery-copilot stories build on
  top.
