# Overview

## Current Behavior

`US-001` through `US-048` delivered a broad MVP
and the first bounded hardening slices for
LiveLead. The product now has:

- A modular monolith with a Python API, a
  worker, a scheduler, a browser worker, a
  SQLite store, a Redis broker, and a
  React/TypeScript UI.
- A first source registry and policy baseline
  (`US-003`) with manual `enabled` /
  `disabled` state, owner/admin approval,
  rate limits, authentication metadata, and
  an encrypted secret manager for API keys,
  cookies, and credentials.
- A first operational observability and
  alerting baseline (`US-041`) with
  `AlertRule`, `AlertEvent`, the
  `SanitizeAlertPayload` helper, the in-app
  inbox + email channels, and seed rules for
  `connector.failure_rate`,
  `discovery.needs_user_action_rate`,
  `browser.crash_loop`, stale backup, missing
  worker heartbeat, and audit retention
  risk.
- A first external metrics pipeline baseline
  (`US-042`) with `MetricsExportPolicy`,
  `MetricRegistry`, and the
  `PrometheusExposition` / `OtelCollector` /
  `SentryIngest` transports.
- A first backup and restore operations
  baseline (`US-043`), a first bounded
  performance baseline (`US-044`), a first
  calendar export slice (`US-045`), a first
  connector health surface slice (`US-046`),
  a first internationalization and timezone
  baseline (`US-047`), and a first connector
  auto-disable and policy recovery baseline
  (`US-048`).
- A first real-environment cutover baseline
  (`US-040`) with `EnvironmentMode`,
  `LaunchGateReport`, `LiveIntegrationToggle`,
  and `BackupSnapshot`.
- A first audit log baseline (`US-026`) with
  the `AuditService`, the `AuditEntryRow`,
  and the secret-safe payload contract that
  the bounded services reuse.

`SPEC.md` section 7.4 (Webhook) commits the
product to a bounded outbound webhook
surface:

> Giai đoạn sau có thể phát webhook:
>
> - Event được xếp hạng rất cao.
> - Lead chuyển trạng thái.
> - Meeting/opportunity được ghi nhận.
> - Job thất bại.
>
> Webhook phải có chữ ký HMAC, timestamp và
> retry policy.

`docs/decisions/0019-observability-and-alerting-baseline.md`
explicitly carves the webhook surface out of
`US-041` as a follow-up. The relevant extract
from the durable record is:

> The evaluator is read-only with respect to
> product state. It persists `AlertEvent`
> rows and dispatches alerts through the
> existing in-app inbox and email channels; it
> does not pause jobs, disable connectors,
> flip live toggles, or roll back the
> environment.

`docs/decisions/0026-connector-auto-disable-and-policy-recovery-baseline.md`
explicitly carves the webhook surface out of
`US-048` as a follow-up. The relevant
extract is:

> External runbook automation (PagerDuty,
> Opsgenie, Slack auto-recovery). The slice
> reuses the `AlertEvent` from `US-041` and
> the `AlertEvaluator` from `US-041`; a later
> story can wire an external runbook consumer
> behind the same `AutoDisableService` seam.

`docs/product/notification-delivery-and-preferences.md`
explicitly defers the webhook surface to a
follow-on story:

> No marketing-campaign composer, no bulk
> recipient management, and no webhook
> fan-out.

`docs/product/audit-log-and-governance.md`
flags the webhook surface as a planned seam:

> SIEM export, webhook fan-out, or external
> compliance integrations.

The product still has no bounded webhook
surface:

- The product has no
  `webhook_subscriptions` table, no
  `webhook_deliveries` table, and no
  bounded delivery record. Operators and
  external integrations cannot subscribe to
  any of the documented webhook events.
- The `connector.auto_disable.triggered`
  audit entry from `US-048`, the
  `alert.fired` entry from `US-041`, the
  `lead.stage.changed` entry from `US-012`,
  and the `discovery.run.failed` entry from
  `US-004` are all persisted in the audit
  log, but no path fires an outbound HTTP
  POST against a customer-controlled URL.
- The secret manager from `US-003` is the
  only place the product stores webhook
  signing secrets today. No bounded
  `WebhookSubscription` row references it,
  and no path rotates the secret on the
  bounded cadence the secret manager
  supports.
- The `EnvironmentMode` from `US-040` is
  the only place the product bounds the
  runtime profile, but no path clips a
  webhook delivery to the bounded window the
  `EnvironmentMode` enforces.
- The `SanitizeAlertPayload` helper from
  `US-041` is the only place the product
  redacts secret material, but no path
  applies the redaction contract to a
  webhook payload before the bounded HTTP
  POST.

The next step in the hardening epic is
therefore a bounded governed webhook delivery
slice that turns `SPEC.md` section 7.4 into a
documented contract, a durable
`webhook_subscriptions` and
`webhook_deliveries` pair, a closed
`WebhookEventType` enum, a closed
`WebhookDeliveryStatus` enum, a bounded
`WebhookDeliveryService` that consumes the
`AlertEvent` rows from `US-041`, the
`ConnectorAutoDisableEvent` rows from
`US-048`, the `LeadActivity` rows from
`US-012`, and the `DiscoveryJob` rows from
`US-004`, an HMAC-signed delivery contract
with a timestamp anti-replay header, a
bounded retry policy with exponential
backoff and a bounded dedup key, and a
reusable verification command that a future
story can extend without re-opening the
audit log, the source policy, or the
metrics export contracts.

## Target Behavior

This story establishes the first bounded
governed webhook delivery surface for
LiveLead. After the story is complete:

- A new durable `webhook_subscriptions`
  table records the bounded per-workspace
  webhook subscription with `id`,
  `organization_id`, `name`, `target_url`,
  `secret_id` (links to the encrypted
  secret from `US-003`), `event_types`
  (closed enum set, JSON-encoded),
  `enabled`, `created_by`, `created_at`,
  `updated_at`, `last_rotated_at`,
  `last_success_at`, and
  `last_failure_at`. The table is the
  single source of truth for outbound
  webhook subscriptions; the
  `WebhookDeliveryService` reads from it.
- A new durable `webhook_deliveries` table
  records the bounded per-delivery history
  with `id`, `organization_id`,
  `subscription_id`, `event_id` (links to
  the matching `AuditEntry` row from
  `US-026`), `event_type` (closed enum),
  `target_url`, `payload_hash`,
  `request_body` (sanitized, JSON-encoded),
  `signature`, `status` (closed enum:
  `pending`, `in_flight`, `succeeded`,
  `failed`, `dead_letter`, `cancelled`),
  `attempt_count`, `next_attempt_at`,
  `last_attempt_at`, `last_response_code`,
  `last_response_message` (bounded to 500
  characters; the secret-safe payload
  contract from `US-041` is enforced before
  persistence), `delivered_at`, and
  `created_at`. The table is bounded to
  the most recent N deliveries per
  subscription so a flapping subscription
  cannot fill the table.
- A new closed `WebhookEventType` enum
  (`event.high_priority`,
  `lead.stage_changed`,
  `lead.outcome_changed`,
  `discovery.job_failed`,
  `connector.auto_disable_triggered`,
  `connector.auto_disable_recovered`,
  `alert.fired`) that the bounded
  `WebhookDeliveryService` reads from the
  closed `AuditAction` enum from `US-026`
  and the closed `AutoDisableTrigger` enum
  from `US-048`.
- A new closed `WebhookDeliveryStatus` enum
  (`pending`, `in_flight`, `succeeded`,
  `failed`, `dead_letter`, `cancelled`)
  that the bounded service uses to track
  the lifecycle of a webhook delivery.
- A new `WebhookDeliveryService` exposes
  the bounded operations:
  - `emit_event(*, organization_id,
    event_type, payload)` — reads the
    matching subscriptions, derives the
    bounded `webhook_deliveries` rows with
    status `pending`, and dispatches them
    through the bounded retry policy.
  - `retry_delivery(*, delivery_id)` —
    re-attempts a bounded delivery with the
    closed `max_attempts` and
    `backoff_seconds` bound from the
    `WebhookDeliveryThresholds` dataclass.
  - `cancel_subscription(*,
    subscription_id)` — owner/admin only.
    Transitions the subscription to
    `disabled` and cancels all pending
    deliveries.
  - `list_subscriptions(*,
    organization_id, enabled, limit,
    offset)` — paginated subscription list
    with sanitized payloads.
  - `list_deliveries(*, subscription_id,
    status, limit, offset)` — paginated
    delivery history with sanitized
    payloads.
  - `rotate_secret(*, subscription_id)` —
    owner/admin only. Generates a new
    per-subscription signing secret,
    persists the secret in the `US-003`
    secret manager, and emits the
    `webhook.subscription.secret_rotated`
    audit entry.
- A new `WebhookSigner` bounded helper that
  owns the HMAC-SHA256 signing, the
  timestamp header, the `X-Webhook-Id`
  header, the `X-Webhook-Timestamp` header,
  and the `X-Webhook-Signature` header. The
  helper is pure; it does not touch the
  database or the network.
- A new `WebhookRetryPolicy` bounded
  helper that owns the bounded
  `max_attempts` (default `6`),
  `initial_backoff_seconds` (default `30`),
  `backoff_multiplier` (default `2.0`),
  `max_backoff_seconds` (default `3600`),
  and `jitter_seconds` (default `30`)
  bounds. The helper returns the bounded
  next-attempt timestamp.
- A new bounded `WebhookDispatcher` that
  runs from a periodic worker tick (the
  existing scheduler from `US-035`) and
  from the `emit_event` path. The actor
  reads the `pending` and `failed`
  deliveries whose `next_attempt_at` has
  elapsed, marks them `in_flight`, performs
  the bounded HTTP POST, and transitions
  them to `succeeded` / `failed` /
  `dead_letter`.
- A new bounded secret rotation helper
  that reuses the `US-003` secret manager
  to generate a new per-subscription
  signing secret. The helper is owner/admin
  only and emits the
  `webhook.subscription.secret_rotated`
  audit entry.
- New bounded owner/admin-only REST
  surface:
  - `GET /admin/webhooks/subscriptions` —
    paginated subscription list with
    sanitized payloads.
  - `POST /admin/webhooks/subscriptions` —
    creates a subscription after
    validation against the closed
    `WebhookEventType` enum and the
    `EnvironmentMode` bound.
  - `GET
    /admin/webhooks/subscriptions/{id}` —
    returns a single subscription with the
    sanitized payload.
  - `PATCH
    /admin/webhooks/subscriptions/{id}` —
    updates name, target URL, event
    types, and enabled state. The signing
    secret is rotated through the
    dedicated `POST
    /admin/webhooks/subscriptions/{id}/rotate-secret`
    endpoint.
  - `DELETE
    /admin/webhooks/subscriptions/{id}` —
    soft-deletes the subscription.
  - `POST
    /admin/webhooks/subscriptions/{id}/rotate-secret` —
    rotates the signing secret and emits
    the `webhook.subscription.secret_rotated`
    audit entry.
  - `POST
    /admin/webhooks/subscriptions/{id}/test` —
    sends a bounded `webhook.test` event
    to the subscription and returns the
    delivery result inline.
  - `GET /admin/webhooks/deliveries` —
    paginated delivery history with
    sanitized payloads.
  - `POST
    /admin/webhooks/deliveries/{id}/retry` —
    retries a `failed` or `dead_letter`
    delivery and emits the
    `webhook.delivery.retried` audit
    entry.
- New audit entry types:
  `webhook.subscription.created`,
  `webhook.subscription.updated`,
  `webhook.subscription.deleted`,
  `webhook.subscription.secret_rotated`,
  `webhook.subscription.test_sent`,
  `webhook.delivery.succeeded`,
  `webhook.delivery.failed`,
  `webhook.delivery.dead_letter`,
  `webhook.delivery.rejected`, and
  `webhook.delivery.retried`.
- New bounded window bound by the
  `EnvironmentMode` from `US-040`
  (`pilot_live`: max 24h retry window,
  `test_like`: max 1h retry window). A
  delivery whose `next_attempt_at` falls
  outside the bound is transitioned to
  `dead_letter`.
- A new product doc
  (`docs/product/webhook-delivery-and-event-fanout.md`)
  that documents the closed
  `WebhookEventType` enum, the closed
  `WebhookDeliveryStatus` enum, the
  per-subscription shape, the
  per-delivery shape, the bounded retry
  policy, the HMAC signing contract, the
  timestamp anti-replay header, the
  audit entry shape, the secret rotation
  cadence, and the operator recovery
  flow.
- A new runbook
  (`docs/ops/webhook-delivery-runbook.md`)
  that documents what an operator does
  when a webhook subscription flips to
  `dead_letter`, when a
  `signature_invalid` failure fires, when
  a `target_unreachable` failure fires,
  and when a secret rotation is denied
  because the `EnvironmentMode` bound is
  in `paused` state.
- A new decision record
  (`docs/decisions/0027-webhook-delivery-and-fanout-baseline.md`)
  that locks the closed
  `WebhookEventType` enum, the closed
  `WebhookDeliveryStatus` enum, the
  bounded retry policy, the HMAC signing
  contract, the secret rotation cadence,
  the bounded window bound, and the audit
  entry shape.
- A new bounded verification command
  (`scripts/verify-us-049.sh`) that runs
  the unit, integration, E2E, security,
  operational, and platform checks
  defined in `validation.md` and is wired
  into `harness-cli story verify` and
  `harness-cli story verify-all`.

The slice stops at the local-first,
single-host baseline. Distributed webhook
fan-out across multiple worker nodes,
provider-specific HTTP transports
(CloudEvents, Slack, Microsoft Teams,
PagerDuty), and per-tenant secret KMS
integration remain in the follow-up
backlog.

## Affected Users

- Owners and Admins responsible for the
  real-environment pilot. They need a
  bounded webhook subscription surface
  that can fan out high-priority events
  to an external SIEM, an incident
  management system, or a custom
  downstream consumer.
- Operators on call for the pilot-live
  environment. They need a
  `webhook-delivery-runbook.md` entry
  that explains what to do when a
  subscription flips to `dead_letter`,
  when a `signature_invalid` failure
  fires, and when a secret rotation is
  denied because the `EnvironmentMode`
  bound is in `paused` state.
- Analysts, Sales/BD users, and
  Reviewers who need an external
  consumer to react to high-priority
  events, lead stage changes, and
  connector auto-disable events without
  polling the LiveLead API.
- Performance and SRE engineers who need
  a documented webhook baseline and a
  bounded `WebhookDeliveryService` they
  can extend for future event types and
  external transports.
- Future implementation agents and
  engineers extending the webhook
  surface, the retry policy, the
  per-tenant transport, or the
  provider-specific HMAC variant that
  need a stable webhook contract.

## Affected Product Docs

- `docs/product/notification-delivery-and-preferences.md`
  (`US-029` contract; this story extends
  the notification surface with a
  bounded webhook channel; it does not
  redefine the in-app inbox, the email
  channel, or the per-user notification
  preferences).
- `docs/product/audit-log-and-governance.md`
  (`US-026` contract; the webhook
  subscription and delivery actions emit
  `webhook.*` audit entries with the
  same secret-safe payload contract).
- `docs/product/source-registry-and-policy.md`
  (`US-003` contract; this story reuses
  the `US-003` secret manager for the
  per-subscription signing secret; it
  does not redefine the source registry,
  the policy evaluation, or the manual
  `enabled` / `disabled` flow).
- `docs/product/real-environment-cutover-and-live-operations.md`
  (`US-040` contract; the webhook
  delivery window is bounded by the
  `EnvironmentMode` from `US-040`; the
  bounded runbook is covered by the
  same launch-gate seam).
- `docs/product/observability-and-alerting.md`
  (`US-041` contract; the
  `WebhookDeliveryService` consumes the
  `AlertEvent` rows and the
  `SanitizeAlertPayload` helper; it does
  not redefine the `AlertRule` or
  `AlertEvent` contract; the bounded
  `WebhookDispatcher` is read-only with
  respect to alert state).
- `docs/product/connector-auto-disable-and-recovery.md`
  (`US-048` contract; the
  `WebhookDeliveryService` consumes the
  `ConnectorAutoDisableEvent` rows; it
  does not redefine the auto-disable
  loop, the bounded recovery flow, or
  the audit entry shape).
- `docs/product/identity-and-access.md`
  (`US-027` contract; every webhook
  endpoint requires an authenticated
  session with `owner` or `admin` role).
- `docs/product/webhook-delivery-and-event-fanout.md`
  (new product doc that this story
  seeds as the living contract for the
  webhook delivery domain).

## Non-Goals

- Distributed webhook fan-out across
  multiple worker nodes. This story
  ships the contract, not a UI for
  multi-host coordination.
- Provider-specific HTTP transports
  (CloudEvents, Slack, Microsoft Teams,
  PagerDuty, Opsgenie). The slice
  delivers a single HTTP POST transport
  with HMAC-SHA256 signing; a future
  story can add provider-specific
  transports behind the same
  `WebhookDispatcher` seam.
- Per-tenant secret KMS integration. The
  slice reuses the existing
  `US-003` secret manager; per-tenant
  KMS is a follow-on story.
- Webhook signature verification on the
  inbound side. The slice is outbound
  only; inbound webhook verification is
  a follow-on story if the product ever
  needs to accept webhooks.
- Customer-facing status pages or
  external incident communication.
- Replacing the existing notification
  surface from `US-029`. This story
  extends the notification surface with
  a bounded webhook channel; it does
  not redefine the in-app inbox, the
  email channel, or the per-user
  notification preferences.
- Replacing the existing audit log from
  `US-026`. This story extends the
  audit entry shape with
  `webhook.*`; it does not redefine
  the `AuditEntryRow` or the audit
  retention guarantee.
- Replacing the existing source registry
  from `US-003`. This story reuses the
  secret manager; it does not redefine
  the source registry, the policy
  evaluation, or the manual `enabled`
  / `disabled` flow.
- Replacing the existing real-environment
  cutover from `US-040`. This story
  consumes the `EnvironmentMode` from
  `US-040`; it does not redefine the
  launch-gate seam.
- Replacing the existing observability
  and alerting surface from `US-041`.
  This story consumes the `AlertEvent`
  rows and the `SanitizeAlertPayload`
  helper; it does not redefine the
  `AlertRule` or `AlertEvent` contract;
  the bounded `WebhookDispatcher` is
  read-only with respect to alert
  state.
- Replacing the existing connector
  auto-disable surface from `US-048`.
  This story consumes the
  `ConnectorAutoDisableEvent` rows; it
  does not redefine the auto-disable
  loop, the bounded recovery flow, or
  the audit entry shape.
- Replacing the existing identity and
  access baseline from `US-027`. This
  story enforces the same RBAC contract
  on every new endpoint; it does not
  redefine the authentication boundary
  or the tenant isolation contract.
