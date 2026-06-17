# Exec Plan

## Goal

Add the first bounded governed webhook
delivery surface to LiveLead. The slice turns
`SPEC.md` section 7.4 into a documented
contract, a durable `webhook_subscriptions`
and `webhook_deliveries` pair, a closed
`WebhookEventType` enum, a closed
`WebhookDeliveryStatus` enum, a bounded
`WebhookDeliveryService`, a bounded
`WebhookSigner` HMAC helper, a bounded
`WebhookRetryPolicy`, a bounded
`WebhookDispatcher` actor, a bounded secret
rotation helper, and a reusable verification
command.

## Scope

In scope:

- New durable `webhook_subscriptions` table
  with the minimum fields required to record
  a per-workspace webhook subscription:
  `organization_id`, `name`, `target_url`,
  `secret_id` (links to the encrypted
  secret from `US-003`),
  `event_types_json`,
  `enabled`, `created_by`, `created_at`,
  `updated_at`, `last_rotated_at`,
  `last_success_at`, and `last_failure_at`.
  Forward-only Alembic migration with a
  documented rollback note in the migration
  header.
- New durable `webhook_deliveries` table
  with the minimum fields required to
  record a bounded per-delivery history:
  `organization_id`, `subscription_id`,
  `event_id`, `event_type` (closed enum),
  `target_url`, `payload_hash`,
  `request_body` (sanitized, JSON-encoded),
  `signature`, `status` (closed enum),
  `attempt_count`, `next_attempt_at`,
  `last_attempt_at`, `last_response_code`,
  `last_response_message` (bounded to 500
  characters; the secret-safe payload
  contract from `US-041` is enforced before
  persistence), `delivered_at`, and
  `created_at`. Forward-only Alembic
  migration with a documented rollback
  note in the migration header.
- New `WebhookSecret` row in the existing
  `secrets` table from `US-003` keyed by
  `webhook_subscription:{id}` so the
  secret manager owns the per-subscription
  signing secret. The bounded rotation
  helper reuses the existing
  `US-003` secret storage.
- New closed `WebhookEventType` enum
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
- New closed `WebhookDeliveryStatus` enum
  (`pending`, `in_flight`, `succeeded`,
  `failed`, `dead_letter`, `cancelled`)
  that the bounded service uses to track
  the lifecycle of a webhook delivery.
- New `WebhookDeliveryThresholds` dataclass
  that exposes the closed default
  thresholds and the `max_attempts` /
  `initial_backoff_seconds` /
  `backoff_multiplier` /
  `max_backoff_seconds` /
  `jitter_seconds` /
  `max_window_seconds` bounds.
- New `WebhookDeliveryService` that
  exposes the bounded operations:
  - `emit_event(*, organization_id,
    event_type, payload)`
  - `retry_delivery(*, delivery_id)`
  - `cancel_subscription(*,
    subscription_id)`
  - `list_subscriptions(*,
    organization_id, enabled, limit,
    offset)`
  - `list_deliveries(*, subscription_id,
    status, limit, offset)`
  - `rotate_secret(*, subscription_id)`
- New `WebhookSigner` bounded helper that
  owns the HMAC-SHA256 signing, the
  timestamp header, the `X-Webhook-Id`
  header, the `X-Webhook-Timestamp` header,
  and the `X-Webhook-Signature` header.
- New `WebhookRetryPolicy` bounded helper
  that owns the bounded retry algorithm
  with exponential backoff and bounded
  jitter.
- New `WebhookDispatcher` bounded actor
  that runs from a periodic worker tick
  (the existing scheduler from `US-035`)
  and from the `emit_event` path.
- New owner/admin-only REST surface:
  - `GET /admin/webhooks/subscriptions`
  - `POST /admin/webhooks/subscriptions`
  - `GET
    /admin/webhooks/subscriptions/{id}`
  - `PATCH
    /admin/webhooks/subscriptions/{id}`
  - `DELETE
    /admin/webhooks/subscriptions/{id}`
  - `POST
    /admin/webhooks/subscriptions/{id}/rotate-secret`
  - `POST
    /admin/webhooks/subscriptions/{id}/test`
  - `GET /admin/webhooks/deliveries`
  - `POST
    /admin/webhooks/deliveries/{id}/retry`
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
- A new bounded window bound by the
  `EnvironmentMode` from `US-040`
  (`pilot_live`: max 24h retry window,
  `test_like`: max 1h retry window).
- A new product doc
  (`docs/product/webhook-delivery-and-event-fanout.md`).
- A new runbook
  (`docs/ops/webhook-delivery-runbook.md`).
- A new decision record
  (`docs/decisions/0027-webhook-delivery-and-fanout-baseline.md`).
- Reuse of the `SanitizeAlertPayload`
  helper from `US-041` for every payload,
  delivery, and audit entry before
  persistence.
- Reuse of the `AuditService` from
  `US-026` for every `webhook.*` audit
  entry.
- Reuse of the `EnvironmentMode` from
  `US-040` for the bounded window.
- Reuse of the secret manager from
  `US-003` for the per-subscription
  signing secret.
- Reuse of the `AlertEvaluator` from
  `US-041` for the `alert.fired` event
  type.
- Reuse of the `AutoDisableService` from
  `US-048` for the
  `connector.auto_disable_*` event
  types.
- Reuse of the existing settings and
  inbox surfaces from `US-026` and
  `US-029` for the operator panel widget.
- Unit, integration, E2E, security,
  operational, and platform checks wired
  into a `scripts/verify-us-049.sh`
  command that `harness-cli story verify`
  can run.

Out of scope:

- Distributed webhook fan-out across
  multiple worker nodes. This story ships
  the contract, not a UI for multi-host
  coordination.
- Provider-specific HTTP transports
  (CloudEvents, Slack, Microsoft Teams,
  PagerDuty, Opsgenie). The slice delivers
  a single HTTP POST transport with
  HMAC-SHA256 signing; a future story can
  add provider-specific transports behind
  the same `WebhookDispatcher` seam.
- Per-tenant secret KMS integration. The
  slice reuses the existing `US-003`
  secret manager; per-tenant KMS is a
  follow-on story.
- Webhook signature verification on the
  inbound side. The slice is outbound
  only; inbound webhook verification is
  a follow-on story.
- Customer-facing status pages or
  external incident communication.
- Replacing the existing notification
  surface from `US-029`. This story
  extends the notification surface with a
  bounded webhook channel; it does not
  redefine the in-app inbox, the email
  channel, or the per-user notification
  preferences.
- Replacing the existing audit log from
  `US-026`. This story extends the audit
  entry shape with `webhook.*`; it does
  not redefine the `AuditEntryRow` or the
  audit retention guarantee.
- Replacing the existing source registry
  from `US-003`. This story reuses the
  secret manager; it does not redefine
  the source registry, the policy
  evaluation, or the manual `enabled` /
  `disabled` flow.
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
  read-only with respect to alert state.
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

## Risk Classification

Risk flags:

- Authorization — owner/admin role gate
  for every new endpoint; tenant scope
  for the webhook subscription surface;
  per-subscription ownership.
- Data model — new `webhook_subscriptions`
  and `webhook_deliveries` tables; new
  indexes; forward-only migrations; new
  `WebhookEventType` enum; new
  `WebhookDeliveryStatus` enum.
- Audit/security — every subscription
  create / update / delete, every
  secret rotation, every test send,
  every successful and failed delivery,
  and every rejected delivery must carry
  a secret-safe payload and a
  `webhook.*` audit entry; the bounded
  window is enforced by the
  `EnvironmentMode` from `US-040`; the
  HMAC-SHA256 signing reuses the secret
  manager from `US-003`.
- Public contracts — new REST endpoints,
  new error codes, new operator panel
  widget, new audit entry types; the
  outbound webhook contract includes a
  `X-Webhook-Id` header, a
  `X-Webhook-Timestamp` header, a
  `X-Webhook-Signature` header, and a
  bounded retry policy.
- External systems — the bounded
  `WebhookDispatcher` performs HTTP
  POST against a customer-controlled
  URL; the bounded `WebhookRetryPolicy`
  enforces the closed `max_attempts`,
  `initial_backoff_seconds`,
  `backoff_multiplier`,
  `max_backoff_seconds`, and
  `jitter_seconds` bounds.
- Existing behavior — the
  `WebhookDispatcher` writes to
  `webhook_deliveries`; the bounded
  `WebhookDeliveryService` does not
  modify `AuditEntry`, `AlertEvent`,
  `ConnectorAutoDisableEvent`, or
  `LeadActivity` rows.
- Weak proof — there is currently no
  bounded verification command for the
  webhook surface; the new
  `scripts/verify-us-049.sh` command
  must wire the unit, integration, E2E,
  security, operational, and platform
  checks together.
- Multi-domain — the slice touches
  notifications (`US-029`), audit
  (`US-026`), secrets (`US-003`),
  observability (`US-041`), connector
  auto-disable (`US-048`), and the
  real-environment cutover (`US-040`).

Hard gates:

- Any subscription create / update /
  delete, any secret rotation, any test
  send, any successful and failed
  delivery, and any rejected delivery
  that mutates product state without an
  authenticated session with `owner` or
  `admin` role.
- Any subscription create / update /
  delete, any secret rotation, any test
  send, any successful and failed
  delivery, and any rejected delivery
  that leaks a secret, a cookie,
  browser storage state, raw PII, or a
  full connection string.
- Any change that weakens the
  `SanitizeAlertPayload` contract from
  `US-041` or the audit retention
  guarantee from `NFR-SEC-008`.
- Any change that bypasses the existing
  `AuditService` from `US-026` or the
  existing `SanitizeAlertPayload` helper
  from `US-041`.
- Any change that adds a new value to
  the `WebhookEventType` or
  `WebhookDeliveryStatus` enum without
  first extending the
  `WebhookDeliveryService` and the audit
  entry shape.
- Any change that bypasses the existing
  `EnvironmentMode` bound from `US-040`
  for the bounded window.
- Any change that bypasses the existing
  `US-003` secret manager for the
  per-subscription signing secret.
- Any change that bypasses the existing
  `AuditService` from `US-026` for the
  `webhook.*` audit entry.
- Any change that bypasses the existing
  `SanitizeAlertPayload` helper from
  `US-041` for every payload, delivery,
  and audit entry.
- Any outbound HTTP POST that carries
  raw PII, an API key, a cookie, a
  password, browser storage state, or a
  full connection string in the request
  body.

## Work Phases

1. Discovery — read `SPEC.md` §7.4
   (Webhook), the `US-003` source
   registry contract, the `US-026` audit
   log contract, the `US-029` notification
   contract, the `US-040` environment
   mode contract, the `US-041` alerting
   contract, the `US-048` auto-disable
   contract, the `US-012` lead activity
   contract, the `US-004` discovery job
   lifecycle, and the
   `pilot-live-rollback-runbook.md`
   entry. Confirm the seams that the
   slice consumes are stable and
   reusable.
2. Design — define
   `WebhookSubscription`,
   `WebhookDelivery`,
   `WebhookEventType`,
   `WebhookDeliveryStatus`,
   `WebhookDeliveryThresholds`,
   `WebhookDeliveryService`,
   `WebhookSigner`, `WebhookRetryPolicy`,
   and `WebhookDispatcher`. Lock the
   sanitization contract to the existing
   `SanitizeAlertPayload` helper from
   `US-041` and refuse any payload,
   delivery, or audit entry that fails
   the filter. Lock the bounded window
   to the existing `EnvironmentMode`
   from `US-040`. Lock the bounded retry
   algorithm to the closed
   `max_attempts` /
   `initial_backoff_seconds` /
   `backoff_multiplier` /
   `max_backoff_seconds` /
   `jitter_seconds` bounds.
3. Validation planning — design a
   per-subscription test harness that
   spins up a local HTTP receiver, runs
   a bounded delivery cycle, asserts the
   HMAC-SHA256 signature matches, asserts
   the `X-Webhook-Id`,
   `X-Webhook-Timestamp`, and
   `X-Webhook-Signature` headers are
   present, asserts the bounded retry
   policy transitions the delivery to
   `succeeded` on first attempt, and
   asserts the audit entry was written.
4. Implementation — add the migrations,
   the domain models, the
   `WebhookEventType` and
   `WebhookDeliveryStatus` enums, the
   `WebhookDeliveryService`, the
   `WebhookSigner`, the
   `WebhookRetryPolicy`, the
   `WebhookDispatcher`, the admin
   endpoints, the operator panel widget,
   the runbook entry, and the
   `scripts/verify-us-049.sh` harness.
   Reuse the existing
   `SanitizeAlertPayload` helper; do not
   introduce a parallel redaction helper.
5. Verification — run unit, integration,
   E2E, security, operational, and
   platform checks defined in
   `validation.md`. Run a deterministic
   delivery cycle for a seeded
   subscription and assert the recorded
   delivery stays within the contract.
   Assert the bounded retry policy
   transitions a `failed` delivery to
   `dead_letter` after
   `max_attempts` attempts. Assert the
   secret rotation emits the
   `webhook.subscription.secret_rotated`
   audit entry.
6. Harness update — add the new product
   doc, the decision record, the durable
   story status, the
   `scripts/verify-us-049.sh` command,
   and a final trace. Capture any
   friction in the `harness_friction`
   field.

## Stop Conditions

Pause for human confirmation if:

- The story starts requiring a specific
  external transport (CloudEvents,
  Slack, Microsoft Teams, PagerDuty,
  Opsgenie) to meet the acceptance
  criteria. This slice is local-first
  and transport-agnostic by design.
- Product direction becomes ambiguous
  between "HMAC-SHA256 only" and "per-
  provider signing variant".
- Validation would need to weaken the
  `SanitizeAlertPayload` contract, the
  audit retention guarantee, or the
  existing `EnvironmentMode` bound from
  `US-040` to fit schedule.
- A new `WebhookEventType` value is
  needed that cannot be justified from
  `SPEC.md` §7.4; the value must be
  deferred or added to the spec in the
  same story with explicit acceptance
  criteria.
- A later story wants to ship a
  per-tenant secret KMS or a
  provider-specific HTTP transport
  before this slice is implemented; in
  that case, the integration must wait
  until the local-first baseline is in
  place.
- The bounded window needs to weaken
  the existing `EnvironmentMode` bound
  from `US-040`; the slice must extend
  the bound, not redefine it.
- The per-subscription signing secret
  needs to weaken the existing
  `US-003` secret manager; the slice
  must extend the secret manager, not
  redefine it.
- The audit entry needs to weaken the
  existing `AuditService` from
  `US-026`; the slice must extend the
  audit service, not redefine it.
- The payload sanitization needs to
  weaken the existing
  `SanitizeAlertPayload` helper from
  `US-041`; the slice must extend the
  helper, not redefine it.
