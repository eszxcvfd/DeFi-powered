# Exec Plan

## Goal

Define and implement the first user-scoped event watchlist workflow so LiveLead
can persist watched events, optional reminders, and watched-state projections in
event review surfaces without changing canonical event truth or widening the
product into bulk event management.

## Scope

In scope:

- Current-user watch or unwatch behavior for canonical events.
- Optional reminder creation, update, and clear behavior on a watched event.
- Watched-state projection into event list and event detail payloads.
- Dedicated watched-events list or equivalent current-user revisit surface.
- Durable data model and audit evidence for watchlist changes.
- Notification-eligibility handoff for future watched-event reminder alerts.

Out of scope:

- Calendar export or ICS feeds.
- Bulk watchlist table actions.
- Shared watchlists, assignee routing, or team-level watcher counts.
- Automatic lead creation or CRM sync from watched events.
- New notification delivery channels or digest configuration.

## Risk Classification

Risk flags:

- Data model.
- Public contracts.
- Existing behavior.
- Multi-domain.

Hard gates:

- Data migration or deletion risk appears.
- Validation requirements need to weaken because watched-state semantics become
  ambiguous across users.

## Work Phases

1. Discovery: confirm watchlist and reminder requirements from `SPEC.md`, event
   review surfaces, and current notification assumptions.
2. Design: define watch-entry ownership, reminder semantics, event-list/detail
   projections, and future notification hooks.
3. Validation planning: design proof for idempotent watch updates,
   current-user isolation, reminder persistence, and watched-state filters.
4. Implementation: add durable watchlist storage, API contract changes, and
   minimal React surfaces for watch or unwatch plus reminder controls.
5. Verification: prove watched events can be saved, revisited, filtered, and
   updated safely without leaking another user's watch choices.
6. Harness update: keep product docs current, record durable story status, and
   leave a clean handoff for calendar export or shared watchlist stories.

## Stop Conditions

Pause for human confirmation if:

- Product behavior is ambiguous.
- Data migration or deletion risk appears.
- Validation requirements need to be weakened.
- Architecture direction changes.
- The team wants shared watchlists, bulk table actions, or calendar sync folded
  into the baseline.
- Reminder timing semantics require a product rule that is not yet defined in
  the event contract.
