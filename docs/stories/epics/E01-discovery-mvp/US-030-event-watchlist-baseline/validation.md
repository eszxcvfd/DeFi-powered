# Validation

## Proof Strategy

This story is done only when LiveLead can persist current-user watched events,
set or clear optional reminders, project watched-state into event-review
surfaces, and keep all watchlist changes explainable without leaking another
user's private tracking choices.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | Watch or unwatch idempotency, reminder validation, current-user ownership rules, and reminder-eligibility projection. |
| Integration | Watchlist persistence, uniqueness enforcement, event list/detail watched-state projection, watched-events query behavior, and unauthorized cross-user mutation denial. |
| E2E | User watches an event from results or detail, sets or clears a reminder, filters by watched-state, and reopens the event later from the watched-events surface. |
| Platform | Story verification command proves backend, frontend, and auth-aware watchlist fixtures succeed without weakening event-review or notification proof paths. |
| Performance | Current-user watchlist queries and watched-state projections remain bounded for normal campaign result volumes. |
| Logs/Audit | Watch, unwatch, and reminder-change actions create explainable audit or diagnostic evidence with actor, event, and timestamp context. |

## Fixtures

- At least one authenticated user with access to a campaign and canonical event.
- One second user in the same organization to prove private watch ownership is
  not leaked across accounts.
- One canonical event with a trustworthy upcoming time and one event with
  limited timing data for reminder validation edge cases.
- Event result fixtures that can be filtered by watched and not watched state.

## Commands

```text
TBD
```

Planned proof should eventually include:

- unit tests for watchlist ownership and reminder rules
- integration tests for watchlist API and event projections
- one frontend e2e scenario for watched-event revisit flow
- `scripts/bin/harness-cli story verify US-030` after a verification command is
  added

## Acceptance Evidence

- `scripts/bin/harness-cli query matrix` reports `US-030` once implemented with
  the expected proof columns populated.
- A representative e2e run covers watch, reminder change, watched-state filter,
  and revisit behavior from the current user's perspective.
- Integration proof confirms another authenticated user cannot mutate or view
  the first user's watch entry through event list, event detail, or watched-list
  routes.
