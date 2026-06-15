# 0015 Notification Delivery Baseline

Date: 2026-06-15

## Status

Accepted

## Context

LiveLead has reminder, discovery-job, and event-timing workflow truth, and
`US-013` already surfaces due or overdue reminders in-app, but `SPEC.md`
still requires per-user email notifications for upcoming events, failed
discovery jobs, and overdue follow-up reminders, plus per-user notification
preferences and a governed read/dismiss lifecycle. There is no first-class
notification product contract, no email provider boundary, and no user
preference store. The change touches an external provider behavior
boundary, audit/security, public API contract, the existing reminder
behavior, and spans multiple product domains (reminders, discovery,
events, identity, audit), so the slice is high-risk.

## Decision

`US-029` introduces the first notification delivery baseline:

- A new `UserNotification` durable record holds per-user in-app alerts
  with `notification_type`, `state`, `source_record_type`,
  `source_record_id`, `organization_id`, `user_id`, `title`, `summary`,
  and `deep_link` metadata. The cleartext email body and provider
  payloads are never stored in the inbox row.
- A new `NotificationPreference` record holds per-user, per-type, and
  per-channel enable/disable settings. The first slice ships two
  channels (`in_app`, `email`) and a bounded set of `notification_type`
  values: `job_completed`, `job_needs_user_action`, `job_failed`,
  `reminder_due`, `reminder_overdue`, and `event_upcoming`.
- A new `NotificationDeliveryAttempt` record holds per-attempt email
  delivery outcomes with provider correlation IDs and a redacted
  `diagnostics` payload. Provider tokens, SMTP secrets, and raw
  recipient lists are never persisted in this table.
- A new `NotificationService` is the only writer of in-app rows and
  the only caller of the email provider adapter. The service is
  invoked from three trigger points: the reminder
  `list_in_app_alerts` path (US-013 surface), discovery-job
  state-transition hooks, and an upcoming-event timing scan. The
  service is invoked from REST only by admin or test paths; user
  routes are read/dismiss/preference updates, not generation.
- A `NotificationProviderAdapter` Protocol defines the email provider
  boundary. The first implementation is an in-memory dev adapter
  (`InMemoryEmailProvider`) that records every attempt and returns
  deterministic success or failure. The interface is shaped so a
  future SMTP, SES, or transactional-email provider can be wired
  without changing the service.
- The new `AuditAction` values are
  `notification.preference_changed`, `notification.delivered`,
  `notification.suppressed`, and `notification.delivery_failed`. The
  audit log redaction pipeline keeps the email subject, recipient
  email, and provider token out of audit metadata.
- The REST surface is `GET /notifications`,
  `POST /notifications/{id}/read`, `POST /notifications/{id}/dismiss`,
  `GET /notification-preferences`, and `PATCH /notification-preferences`.
  A bounded `POST /admin/notifications/scan` admin endpoint lets the
  operator run the upcoming-event and reminder scans on demand for
  tests and for the first MVP rollout.
- A new `alembic` revision creates `user_notifications`,
  `notification_preferences`, and `notification_delivery_attempts`
  tables with organization/user, unread state, notification type, and
  created-at indexes. Default rows are seeded for every existing user
  on first read so the preferences endpoint always returns a complete
  matrix.
- A new React `NotificationInbox` and `NotificationPreferencesPage`
  surface the inbox and the preference matrix. The existing
  in-app reminder banner is kept as the lightweight top-bar cue.

## Alternatives Considered

1. Keep notifications in-app only and defer email. Rejected because
   `SPEC.md` requires per-user email alerts for upcoming events,
   failed jobs, and overdue reminders and the product doc is explicit
   about it.
2. Generate notifications directly inside each feature route. Rejected
   because reminders, discovery-job transitions, and event timing
   need a single preference and delivery boundary to avoid
   duplicated per-route logic.
3. Add a generic multi-channel framework (Slack, webhook, push) in
   the first slice. Rejected because the MVP needs user-facing
   product value and a clear adapter boundary before multi-channel
   integration complexity.
4. Use the same audit row for every preference change and delivery
   attempt. Rejected because the audit log is a product fact, not a
   delivery pipeline; collapsing both would muddle redaction
   semantics and dilute the action family.

## Consequences

Positive:

- Operators and sales/BD users can configure their own notification
  contract without forcing every organization into one default.
- Email delivery is bounded by the adapter boundary, so a real
  provider can be wired without rewriting the application layer.
- Existing reminder, discovery, and event sources keep their
  contracts; the new service is an observer, not a mutator.
- Audit evidence is consistent with US-026 redaction rules and adds
  a clear `notification` action family for governance review.

Tradeoffs:

- The first slice ships without a real SMTP or transactional
  provider; production email delivery remains a follow-on story.
- A scan-based cadence is sufficient for MVP; push, real-time
  streams, and digest scheduling remain out of scope.
- The default preference matrix is permissive (everything on,
  email on). Future privacy controls may need a stricter default
  per organization.

## Follow-Up

- A real SMTP or transactional-email provider should implement
  `NotificationProviderAdapter` and be wired in
  `apps/api/main.py` without changing the service.
- A digest-frequency story should add a `digest_window` field to
  the preference record and a delayed-delivery path.
- A watchlist-driven alert story should reuse
  `UserNotification.source_record_type` and `source_record_id` to
  link notifications back to watchlist targets.
- A push/Slack/webhook story should add a new `NotificationChannel`
  value and a new adapter without redefining the existing contract.
