# Notification Delivery And Preferences

Source: `SPEC.md` sections 5.4, 5.5, 5.11, 5.13, `UI-006`, and `AC-BIZ-08`.

## Product Goal

Analysts, sales users, reviewers, and admins need important LiveLead events to
become actionable without polling every page manually. The product must define a
governed notification layer that can surface in-app alerts for discovery-job
outcomes and due reminders, deliver bounded email notifications for selected
high-value events, and let each user control which notifications they receive
and how often.

## MVP Scope

This product slice covers:

- In-app notifications for discovery job completion, needs-user-action,
  failure, and due or overdue reminders.
- Email notifications for upcoming events, failed jobs, and overdue follow-up
  reminders.
- Per-user notification preferences with at least notification-type and
  channel enable or disable controls.
- Basic delivery cadence or frequency controls at a bounded level such as
  immediate vs disabled where needed by the first implementation.
- Read, unread, dismissed, or resolved notification state for in-app alerts.
- Linking notifications back to the triggering record such as discovery job,
  reminder, lead, or event.
- Audit-safe delivery and preference-change evidence without leaking email
  secrets or recipient lists beyond what the actor is allowed to see.

This product slice does not yet cover:

- Bulk marketing or outreach email sending.
- Multi-step digest builders, scheduled reports, or complex recurrence engines.
- Watchlist-driven alert automation beyond the existing reminder and event
  surfaces.
- Push notifications, SMS, Slack, or webhook fan-out.
- CRM sync or external ticketing workflow automation.

## Contract Rules

- Notification generation must remain tenant-scoped and user-scoped. A user may
  only see or receive alerts for records they are allowed to know about.
- In-app notifications must distinguish unread vs dismissed or resolved state so
  the product does not repeatedly surface the same alert without context.
- Email notifications must honor the current preference settings before
  delivery is attempted.
- Failed or suppressed notification deliveries must be explainable in audit or
  diagnostic output without exposing provider secrets.
- Reminder notifications must build on the durable reminder truth from
  `docs/product/follow-up-reminders-and-notifications.md` rather than inventing
  parallel due-date heuristics.
- Discovery-job notifications must build on the durable job-state transitions
  from `docs/product/discovery-job-lifecycle.md`.
- Upcoming-event notifications must rely on canonical event time data and must
  not fabricate time windows when the source event lacks a trustworthy start
  time.
- Preference changes must take effect for future notifications without
  retroactively mutating already delivered or already dismissed records.
- The first implementation may keep cadence choices intentionally narrow, but
  the API must leave room for later digest frequency expansion.

## API Surface

- `GET /notifications`: list in-app notifications for the authenticated user
  with read or unread state and lightweight filter support.
- `POST /notifications/{id}/read`, `dismiss`, or equivalent actions: update
  in-app notification state safely.
- `GET /notification-preferences`: return the current user's notification
  preference matrix.
- `PATCH /notification-preferences`: update per-type and per-channel preference
  settings.
- Internal notification-generation flows must react to reminder, discovery-job,
  and event-timing signals without requiring callers to send raw email payloads
  from feature routes.

## UI Surface

The first notification slice should stay focused on trustworthy operator value:

- Global or contextual in-app notification inbox with unread count and clear
  deep links back to the related record.
- Read/dismiss controls for in-app notifications.
- User-facing notification preferences surface with bounded channel and event-
  type controls.
- Clear empty states when no notifications exist and clear explanatory states
  when email delivery is disabled by preference.
- No marketing-campaign composer, no bulk recipient management, and no webhook
  admin console in this slice.

## Validation Implications

- Unit proof should cover notification eligibility, preference application,
  state transitions, and suppression rules.
- Integration proof should cover in-app notification persistence, email-delivery
  request generation or provider adapter behavior, tenant scoping, and
  preference updates.
- E2E proof should cover a user receiving an in-app alert, marking it read or
  dismissed, changing preferences, and seeing future deliveries honor those
  settings.
- Logs and audit proof should confirm notification generation, suppression,
  delivery attempts, and preference changes remain explainable without leaking
  provider secrets.
- Platform proof should keep notification verification wired into the Harness
  matrix before watchlist, digest, or external integration stories build on it.
