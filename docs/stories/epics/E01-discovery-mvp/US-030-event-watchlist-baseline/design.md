# Design

## Domain Model

The story should formalize the first watched-event objects:

- `EventWatchlistEntry`: tenant-scoped and user-scoped record linking one user
  to one canonical event with created/updated timestamps.
- `WatchlistReminder`: optional reminder metadata owned by the watch entry,
  including a resolved reminder timestamp and last-updated context.
- `WatchlistState`: at least `watched` and `not_watched` at the current-user
  projection layer, with reminder summary derived from the watch entry.

Business rules:

- A user may watch the same event at most once in the same organization.
- Watching or updating the same event repeatedly is idempotent and must update
  the existing entry rather than create duplicates.
- Reminder data belongs to the watch entry, so two users can track the same
  event independently.
- Removing a watch entry stops future reminder eligibility for that user but
  must not delete the canonical event, source observations, or related leads.
- Event projections must expose only the current user's watch state and reminder
  summary in this baseline.

## Application Flow

- `UpsertEventWatchlistEntry` creates or updates the current user's watched
  entry and optional reminder.
- `RemoveEventWatchlistEntry` clears the current user's watched entry.
- `ListWatchedEvents` returns the current user's tracked events with lightweight
  event timing and reminder fields.
- `ProjectWatchStateIntoEventList` enriches event list rows with current-user
  watch metadata.
- `ProjectWatchStateIntoEventDetail` enriches event detail responses with
  current-user watch metadata.
- `EvaluateWatchlistReminderEligibility` prepares durable reminder or
  notification eligibility signals without sending notifications directly from
  the event routes.

## Interface Contract

Backend contract should minimally support:

- `PUT /events/{id}/watchlist` for current-user watch or reminder upsert.
- `DELETE /events/{id}/watchlist` for current-user removal.
- `GET /watchlist/events` for current-user watched events.
- Extended `GET /campaigns/{id}/events` and `GET /events/{id}` payloads that
  expose current-user watched-state and reminder summary.

Expected payload concerns:

- Watchlist mutation payloads should accept bounded reminder data without
  requiring the caller to send another user's identity or raw notification
  payloads.
- Event list/detail responses should expose a stable watched-state shape so the
  UI can render toggles and filters consistently.
- Cross-user access must remain denied or invisible; one user must not fetch or
  mutate another user's watch entry in this baseline.

## Data Model

- Add a durable watchlist table or equivalent structure keyed by organization,
  user, and canonical event.
- Keep reminder fields alongside the watch entry or in a tightly related table
  so reminder lifecycle stays tied to current-user watch ownership.
- Add uniqueness on organization + user + event and indexes for current-user
  watchlist queries and reminder-time lookups.
- Reuse existing canonical event identifiers and auth scope rather than copying
  event snapshots into separate watchlist storage.
- Preserve room for future calendar-export tokens, shared-watchlist ownership,
  or richer reminder state without redefining baseline ownership rules.

## UI / Platform Impact

- Extend event results and event detail surfaces with watch or unwatch controls.
- Add reminder create/update/clear controls in the watched-event flow.
- Add a watched-state filter to event results.
- Add a simple watched-events list or equivalent revisit surface for the
  current user.
- Keep the first UX intentionally narrow: no bulk actions, no team assignment,
  and no calendar-auth management screens.

## Observability

- Record audit entries for watch, unwatch, and reminder changes that matter to
  governance and future support.
- Emit structured diagnostics for watchlist mutation, current-user projection,
  reminder validation failure, and any notification-eligibility evaluation.
- Preserve correlation between watch-entry changes, event ids, user ids, and
  later notification outcomes when future stories build on this contract.

## Alternatives Considered

1. Add shared watchlists first. Rejected because `SPEC.md` only requires that a
   user can watch an event and set a reminder; team ownership rules would add
   new governance semantics too early.
2. Store watched-state directly on the canonical event row. Rejected because
   the same event may be tracked differently by different users.
3. Require watchlist entries before reminders can exist but skip a dedicated
   watched-events list. Rejected because the feature would remain hard to revisit
   and would not satisfy the saved-event workflow implied by the watchlist
   requirement.
