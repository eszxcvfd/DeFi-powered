# Design

## Domain Model

The story should formalize the first notification-governance objects:

- `UserNotification`: in-app alert with actor scope, tenant scope, source
  record reference, notification type, state, timestamps, and deep-link
  metadata.
- `NotificationPreference`: per-user configuration for whether a notification
  type is enabled for in-app or email delivery and what bounded cadence applies.
- `NotificationType`: bounded types such as `job_completed`,
  `job_needs_user_action`, `job_failed`, `reminder_due`, `reminder_overdue`,
  and `event_upcoming`.
- `NotificationDeliveryAttempt`: email or channel-delivery attempt record with
  result, provider correlation, suppression reason, and redacted diagnostics.
- `NotificationState`: at least `unread`, `read`, `dismissed`, and
  delivery-oriented suppressed or failed states where needed.

Business rules:

- Notifications are always scoped to one authenticated user inside one
  organization.
- A user must not receive an in-app or email notification for a record they
  are not authorized to access.
- Preference evaluation happens before email delivery is attempted.
- In-app notification state changes must not erase delivery history or the
  underlying source event.
- Reminder and job notifications must derive from existing durable workflow
  truth, not duplicated heuristics.
- Upcoming-event notifications require a trustworthy event time and a bounded
  lead time window.

## Application Flow

- `GenerateNotificationCandidates` listens to reminder, discovery-job, and
  event-timing transitions and produces candidate notifications.
- `ApplyNotificationPreferences` filters candidates by user-scoped preference
  rules and returns in-app deliveries, email deliveries, or suppressions.
- `CreateInAppNotification` persists unread notifications with related-record
  references and UI link metadata.
- `DeliverEmailNotification` hands an email-safe payload to the provider
  adapter and records the outcome in durable delivery-attempt storage.
- `ListUserNotifications` returns the authenticated user's notification inbox.
- `MarkNotificationRead` and `DismissNotification` update in-app state without
  mutating the underlying workflow source.
- `GetNotificationPreferences` and `UpdateNotificationPreferences` manage the
  current user's settings.

## Interface Contract

Backend contract should minimally support:

- `GET /notifications` for the current-user inbox.
- `POST /notifications/{id}/read` and `POST /notifications/{id}/dismiss` or
  equivalent state-transition actions.
- `GET /notification-preferences` for the current-user preference matrix.
- `PATCH /notification-preferences` for bounded preference updates.

Expected payload concerns:

- Inbox payloads should expose notification type, created time, state, summary
  text, and deep-link context without dumping large source payloads.
- Preference payloads should expose only the current user's settings and should
  not let one user edit another user's notification policy in this baseline.
- Delivery diagnostics must stay redacted; provider tokens, SMTP secrets, or
  raw recipient lists must not leak in API responses.

## Data Model

- Add durable notification, notification-preference, and delivery-attempt
  tables or equivalent structures with organization scope, user scope, type,
  state, source references, and timestamps.
- Index by user, unread state, notification type, and created time for a stable
  inbox experience.
- Keep delivery-attempt data separate from inbox state so email failures do not
  corrupt in-app notification truth.
- Reuse existing user, membership, reminder, job, and event records instead of
  copying large source objects into the notification store.
- Preserve room for later digest frequency, additional channels, or watchlist
  rules without redefining the baseline notification objects.

## UI / Platform Impact

- Add a first notification inbox or equivalent global alert surface in the
  React app.
- Add a current-user preferences surface for notification types and channels.
- Show clear unread state, read/dismiss actions, and preference-disabled states.
- Keep the first UX intentionally narrow: no bulk notification admin console,
  no scheduled digest designer, and no external channel management screens.

## Observability

- Record audit entries for preference updates and notification state changes
  that matter to governance.
- Emit structured diagnostics for notification generation, suppression,
  delivery attempt, and provider failure.
- Preserve correlation IDs between the source workflow event, notification row,
  and email-delivery attempt for support/debugging.

## Alternatives Considered

1. Keep notifications in-app only and defer email completely. Rejected because
   `SPEC.md` explicitly calls for user-configurable email alerts for key cases.
2. Add a generic webhook or Slack framework first. Rejected because the MVP
   needs user-facing product value before multi-channel integration complexity.
3. Generate notifications directly inside each feature route. Rejected because
   reminders, discovery jobs, and event timing need one reusable preference and
   delivery boundary rather than duplicated per-route logic.
