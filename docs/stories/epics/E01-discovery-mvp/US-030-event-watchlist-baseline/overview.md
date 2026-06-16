# Overview

## Current Behavior

LiveLead already lets users discover canonical events, score them, inspect
audience evidence, draft engagement content, and receive bounded notifications.
However, once an event has been reviewed there is still no durable user-scoped
way to save it for later follow-up. `SPEC.md` requires users to add or remove
events from a watchlist and set reminders, while current product docs only
mention watchlist behavior as deferred future work.

## Target Behavior

This story should establish the first watched-events workflow for LiveLead:

- Let the current user watch or unwatch an event from event list and detail
  surfaces.
- Persist one current-user watch entry per event with an optional reminder.
- Show watched-state and reminder summary in existing event review payloads.
- Provide a dedicated watched-events list or equivalent revisit surface.
- Supply durable watched-event truth that later calendar-export or watchlist
  notification stories can extend without parallel heuristics.

This story should help users keep high-priority events actionable without
turning watchlists into a team CRM, a bulk-ops surface, or a notification
designer.

## Affected Users

- Analysts who triage many discovered events and need a shortlist worth
  revisiting.
- Sales/BD users who want to track promising events before creating a lead or
  taking outreach action.
- Future implementation agents extending watchlist alerts, calendar export, or
  shared watchlist governance on top of a stable watched-event contract.

## Affected Product Docs

- `docs/product/event-results-and-review.md`
- `docs/product/event-watchlist-and-reminders.md`
- `docs/product/notification-delivery-and-preferences.md`

## Non-Goals

- ICS or calendar export.
- Bulk add or bulk remove watchlist actions.
- Shared team watchlists or watcher analytics.
- Automatic lead creation from watched events.
- New notification channels, digests, or marketing workflows.
