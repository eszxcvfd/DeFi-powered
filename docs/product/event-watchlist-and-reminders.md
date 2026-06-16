# Event Watchlist And Reminders

Source: `SPEC.md` sections 5.6, 7.2, 12, `UI-003`, `UI-004`, and `UC-02`.

## Product Goal

Analysts and sales users need a lightweight way to keep high-potential events
visible after review instead of rediscovering them manually. The product
contract must define how LiveLead lets a user watch or unwatch an event, attach
an optional reminder, surface watched-state in event views, and provide a
durable source of truth that later notification and calendar workflows can
build on safely.

## MVP Scope

This product slice covers:

- Adding or removing an event from the current user's watchlist.
- Persisting watched-state per user and per organization without mutating the
  canonical event itself.
- Setting, changing, or clearing one optional reminder for a watched event.
- Showing watched-state in event list and detail surfaces.
- Filtering or listing watched events so users can revisit tracked
  opportunities quickly.
- Preserving enough reminder metadata for existing notification workflows to
  determine whether a watched event is eligible for future alerting.

This product slice does not yet cover:

- Calendar export or ICS generation.
- Bulk watchlist add or remove actions from the event table.
- Shared team watchlists, assignee routing, or aggregate watcher analytics.
- Automatic lead creation from a watched event.
- New outbound notification channels or digest scheduling.

## Contract Rules

- Watchlist records are tenant-scoped and current-user-scoped. One user must
  not silently add or remove another user's watched events in this baseline.
- The same user may watch the same event at most once; repeated watch requests
  must be idempotent updates rather than duplicate rows.
- Removing an event from the watchlist must stop future reminder eligibility
  for that watch entry without deleting the canonical event, existing leads, or
  historical audit evidence.
- Reminder data belongs to the watch entry, not to the canonical event model,
  so different users may track the same event differently.
- A watched event must remain reviewable through existing event detail and
  source-evidence surfaces; watchlist state is additional workflow context, not
  a replacement for canonical event provenance.
- Event list and detail payloads must expose current-user watched-state and
  reminder summary without leaking another user's private watch choices.
- Any upcoming-event or watchlist reminder notifications must derive from this
  durable watchlist truth rather than broad heuristics about campaign
  ownership, lead ownership, or event score alone.
- Calendar export, bulk watchlist management, and shared watchlist semantics are
  intentionally deferred so the baseline can stay user-scoped and explainable.

## API Surface

- `GET /campaigns/{id}/events`: include current-user watched-state and reminder
  summary in event list rows.
- `GET /events/{id}`: include current-user watch entry or equivalent watched
  summary in event detail responses.
- `PUT /events/{id}/watchlist`: create or update the current user's watch entry,
  including optional reminder data.
- `DELETE /events/{id}/watchlist`: remove the current user's watch entry.
- `GET /watchlist/events`: list the current user's watched events with reminder
  state, event timing context, and lightweight filters.

## UI Surface

The first watchlist slice should extend existing event-review surfaces:

- Watch or unwatch toggle from event list and event detail.
- Reminder controls attached to the watched-event workflow.
- Watched-state filter in event discovery results.
- Dedicated watched-events list or equivalent saved-events view for the current
  user.
- Clear empty states when no events are being tracked.

## Validation Implications

- Unit proof should cover watch or unwatch idempotency, reminder validation,
  current-user scoping, and notification-eligibility projection rules.
- Integration proof should cover watchlist persistence, event list or detail
  projection, watched-events queries, and unauthorized cross-user access
  denial.
- E2E proof should cover watching an event, setting or clearing a reminder,
  filtering by watched-state, and reopening the event later from the watchlist
  view.
- Logs or audit proof should confirm who watched, unwatched, or changed a
  reminder and when.
- Platform proof should keep the watchlist verification path wired into the
  Harness matrix before calendar export, bulk actions, or shared-team tracking
  stories build on it.
