# 0027 Webhook Delivery And Event Fan-Out Baseline

Date: 2026-06-16

## Status

Proposed (companion decision to `US-049`).

## Context

`SPEC.md` section 7.4 commits the product to
a bounded outbound webhook surface:

> Giai đoạn sau có thể phát webhook:
>
> - Event được xếp hạng rất cao.
> - Lead chuyển trạng thái.
> - Meeting/opportunity được ghi nhận.
> - Job thất bại.
>
> Webhook phải có chữ ký HMAC, timestamp và
> retry policy.

LiveLead has shipped forty-eight stories that
all rely on the manual `Source.enabled` flag
from `US-003`, the read-only
`AlertEvaluator` from `US-041`, the closed
`ConnectorHealthStatus` enum from `US-046`,
the closed `AutoDisableTrigger` enum from
`US-048`, the `SanitizeAlertPayload` helper
from `US-041`, and the `EnvironmentMode` from
`US-040`. The product still has no bounded
webhook surface:

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
  webhook delivery to the bounded window
  the `EnvironmentMode` enforces.
- The `SanitizeAlertPayload` helper from
  `US-041` is the only place the product
  redacts secret material, but no path
  applies the redaction contract to a
  webhook payload before the bounded HTTP
  POST.

`docs/decisions/0019-observability-and-alerting-baseline.md`
explicitly carves the webhook surface out of
`US-041` as a follow-up:

> The evaluator is read-only with respect
> to product state. It persists `AlertEvent`
> rows and dispatches alerts through the
> existing in-app inbox and email channels;
> it does not pause jobs, disable
> connectors, flip live toggles, or roll
> back the environment.

`docs/decisions/0026-connector-auto-disable-and-policy-recovery-baseline.md`
explicitly carves the webhook surface out of
`US-048` as a follow-up:

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

The next step is therefore a bounded governed
webhook delivery slice that turns `SPEC.md`
section 7.4 into a documented contract, a
durable `webhook_subscriptions` and
`webhook_deliveries` pair, a closed
`WebhookEventType` enum, a closed
`WebhookDeliveryStatus` enum, a bounded
`WebhookDeliveryService`, a bounded
`WebhookSigner` HMAC helper, a bounded
`WebhookRetryPolicy`, a bounded
`WebhookDispatcher` actor, a bounded secret
rotation helper, and a reusable verification
command.

## Decision

`US-049` introduces the first bounded
governed webhook delivery surface for
LiveLead.

### Domain objects

- **`WebhookEventType`** — closed enum
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
- **`WebhookDeliveryStatus`** — closed
  enum (`pending`, `in_flight`,
  `succeeded`, `failed`, `dead_letter`,
  `cancelled`) that the bounded service
  uses to track the lifecycle of a
  webhook delivery.
- **`WebhookSubscription`** — durable
  table that records a per-workspace
  webhook subscription with `name`,
  `target_url`, `secret_id` (links to the
  encrypted secret in the `US-003` secret
  manager), `event_types` (closed enum
  set, JSON-encoded), `enabled`,
  `created_by`, `created_at`,
  `updated_at`, `last_rotated_at`,
  `last_success_at`, and
  `last_failure_at`.
- **`WebhookDelivery`** — durable table
  that records a per-delivery history
  with `subscription_id`, `event_id`,
  `event_type` (closed enum),
  `target_url`, `payload_hash`,
  `request_body` (sanitized, JSON-
  encoded), `signature`, `status` (closed
  enum), `attempt_count`,
  `next_attempt_at`, `last_attempt_at`,
  `last_response_code`,
  `last_response_message` (bounded to 500
  characters; the secret-safe payload
  contract from `US-041` is enforced
  before persistence), `delivered_at`, and
  `created_at`.
- **`WebhookDeliveryThresholds`** —
  bounded dataclass that exposes the
  closed default thresholds and the
  `max_attempts` /
  `initial_backoff_seconds` /
  `backoff_multiplier` /
  `max_backoff_seconds` /
  `jitter_seconds` /
  `max_window_seconds` bounds.
- **`WebhookDeliveryService`** — bounded
  service that exposes `emit_event`,
  `retry_delivery`, `cancel_subscription`,
  `list_subscriptions`, `list_deliveries`,
  and `rotate_secret`.
- **`WebhookSigner`** — bounded helper
  that owns the HMAC-SHA256 signing, the
  timestamp header, the `X-Webhook-Id`
  header, the `X-Webhook-Timestamp`
  header, and the `X-Webhook-Signature`
  header.
- **`WebhookRetryPolicy`** — bounded
  helper that owns the bounded retry
  algorithm with exponential backoff and
  bounded jitter.
- **`WebhookDispatcher`** — bounded
  actor that runs from a periodic worker
  tick (the existing scheduler from
  `US-035`) and from the `emit_event`
  path.

### Bounded HMAC signing contract

The bounded `WebhookSigner` returns:

- `X-Webhook-Id: {delivery_id}`
- `X-Webhook-Timestamp: {timestamp}`
- `X-Webhook-Signature: v1,{hex_signature}`

The bounded `hex_signature` is
`HMAC-SHA256(secret, "{timestamp}.{body}")`
hex-encoded. The bounded path uses a
constant-time comparison helper for the
verifier side. The bounded timestamp is
the Unix epoch seconds at the time the
signature is generated. The bounded path
rejects signatures whose timestamp is
more than `300` seconds in the past or
in the future to defend against replay
attacks.

### Bounded retry policy

The bounded `WebhookRetryPolicy` returns
`None` when `attempt_count >=
max_attempts`. Otherwise, the bounded
algorithm is:

```text
backoff = min(
    initial_backoff_seconds
    * (backoff_multiplier ** (attempt_count - 1)),
    max_backoff_seconds,
)
jitter = random.uniform(0, jitter_seconds)
return now + timedelta(seconds=backoff + jitter)
```

The bounded `max_attempts` is `6`; the
bounded `initial_backoff_seconds` is
`30`; the bounded `backoff_multiplier` is
`2.0`; the bounded `max_backoff_seconds`
is `3600`; the bounded `jitter_seconds`
is `30`.

### Bounded window bound

The bounded window is enforced by the
`EnvironmentMode` from `US-040`:

- `pilot_live` —
  `max_window_seconds = 24 * 3600` (24
  hours).
- `test_like` —
  `max_window_seconds = 3600` (1 hour).

The `WebhookDeliveryService.emit_event`
and `WebhookDispatcher.dispatch_pending`
operations clip the
`next_attempt_at` to the bound. A
`next_attempt_at` that exceeds the bound
is recorded in the audit log with the
`webhook.delivery.dead_letter` action
and the delivery is transitioned to
`dead_letter`.

### Bounded target URL validation

The bounded `WebhookDeliveryService` and
`WebhookDispatcher` validate the
`target_url` against the closed URL
allowlist:

- The `target_url` must start with
  `https://` or `http://localhost`.
- The `target_url` must not resolve to a
  private IP address (RFC 1918 ranges,
  loopback, link-local, multicast, or
  reserved) per `NFR-SEC-006`.
- The `target_url` must not be a
  metadata service endpoint
  (`169.254.169.254`).
- The `target_url` must not be longer than
  `2048` characters.

A `target_url` that fails the validation
is rejected with
`WEBHOOK_TARGET_URL_INVALID` and the
rejection is recorded in the audit log
with the `webhook.delivery.rejected`
action.

### Sanitization contract

The bounded `WebhookDeliveryService` and
`WebhookDispatcher` reuse the
`SanitizeAlertPayload` helper from
`US-041` for every payload, delivery, and
audit entry before persistence. A payload,
delivery, or audit entry that fails the
sanitization is rejected with
`WEBHOOK_PAYLOAD_INVALID` and the
rejection is recorded in the audit log
with the `webhook.delivery.rejected`
action.

### API contract

- `GET /admin/webhooks/subscriptions` —
  paginated subscription list with
  sanitized payloads.
- `POST /admin/webhooks/subscriptions` —
  creates a subscription after validation
  against the closed `WebhookEventType`
  enum and the `EnvironmentMode` bound.
- `GET
  /admin/webhooks/subscriptions/{id}` —
  returns a single subscription with the
  sanitized payload.
- `PATCH
  /admin/webhooks/subscriptions/{id}` —
  updates name, target URL, event types,
  and enabled state.
- `DELETE
  /admin/webhooks/subscriptions/{id}` —
  soft-deletes the subscription.
- `POST
  /admin/webhooks/subscriptions/{id}/rotate-secret`
  — rotates the signing secret and emits
  the
  `webhook.subscription.secret_rotated`
  audit entry.
- `POST
  /admin/webhooks/subscriptions/{id}/test`
  — sends a bounded `webhook.test` event
  to the subscription and returns the
  delivery result inline.
- `GET /admin/webhooks/deliveries` —
  paginated delivery history with
  sanitized payloads.
- `POST
  /admin/webhooks/deliveries/{id}/retry`
  — retries a `failed` or `dead_letter`
  delivery and emits the
  `webhook.delivery.retried` audit
  entry.

### Audit entry shape

The bounded `WebhookDeliveryService` and
`WebhookDispatcher` emit the following
audit entries, all using the existing
`AuditEntry` contract from `US-026`:

- `webhook.subscription.created`
- `webhook.subscription.updated`
- `webhook.subscription.deleted`
- `webhook.subscription.secret_rotated`
- `webhook.subscription.test_sent`
- `webhook.delivery.succeeded`
- `webhook.delivery.failed`
- `webhook.delivery.dead_letter`
- `webhook.delivery.rejected`
- `webhook.delivery.retried`

## Consequences

- The bounded `WebhookDispatcher` is
  read-only with respect to alert state,
  auto-disable state, lead state, and
  discovery job state. It persists
  `webhook_deliveries` rows and dispatches
  outbound HTTP POSTs; it does not modify
  `AuditEntry`, `AlertEvent`,
  `ConnectorAutoDisableEvent`, or
  `LeadActivity` rows.
- The bounded `WebhookRetryPolicy`
  prevents flapping: once a delivery
  fails, the bounded `next_attempt_at`
  is computed from the closed
  `max_attempts`,
  `initial_backoff_seconds`,
  `backoff_multiplier`,
  `max_backoff_seconds`, and
  `jitter_seconds` bounds. The delivery is
  transitioned to `dead_letter` when
  `attempt_count >= max_attempts`.
- The bounded `WebhookEventType` and
  `WebhookDeliveryStatus` enums are
  closed. Adding a new value is an
  explicit follow-up story; the first
  slice ships only the values listed in
  the design doc.
- The bounded per-subscription signing
  secret is stored in the `US-003` secret
  manager. The bounded path never returns
  the signing secret in any response
  payload.
- The slice is local-first by design. It
  does not commit to a specific external
  transport (CloudEvents, Slack,
  Microsoft Teams, PagerDuty, Opsgenie)
  in this step; it preserves a stable
  seam for a later hardening story to
  wire one.
- The slice touches the secret manager
  from `US-003`, the audit log from
  `US-026`, the notification surface from
  `US-029`, the real-environment cutover
  from `US-040`, the alerting surface from
  `US-041`, the auto-disable surface from
  `US-048`, and the identity and access
  baseline from `US-027`. The
  `WebhookDispatcher` does not modify any
  of the existing surfaces; it only reads
  the audit log entries and persists the
  bounded `webhook_deliveries` rows.

## Alternatives Considered

- **Make the webhook surface part of
  `US-029` notification delivery.**
  Rejected: `US-029` is read-only with
  respect to product state by design.
  Adding an outbound HTTP POST would
  weaken that contract and would couple
  notification delivery to outbound
  network I/O.
- **Make the webhook surface part of
  `US-041` alerting.** Rejected:
  `US-041` is read-only with respect to
  product state by design (decision
  `0019`). Adding an outbound HTTP POST
  would weaken that contract and would
  couple alert evaluation to outbound
  network I/O.
- **Use the existing `US-003` source
  registry as the subscription
  catalog.** Rejected: the source
  registry is a governance surface for
  inbound data collection. Mixing the
  outbound webhook subscriptions with the
  source registry would conflate two
  distinct governance signals.
- **Provider-specific HTTP transports
  (CloudEvents, Slack, Microsoft Teams,
  PagerDuty, Opsgenie) in the first
  slice.** Rejected: out of scope for
  the local-first baseline. A follow-on
  story can add provider-specific
  transports behind the same
  `WebhookDispatcher` seam.
- **Per-tenant secret KMS integration.**
  Rejected: out of scope for the
  local-first baseline. The slice reuses
  the existing `US-003` secret manager;
  per-tenant KMS is a follow-on story.
- **Inbound webhook signature
  verification.** Rejected: the slice
  is outbound only. Inbound webhook
  verification is a follow-on story if
  the product ever needs to accept
  webhooks.

## Compliance

This decision preserves the existing
contracts from `US-003`, `US-004`,
`US-012`, `US-026`, `US-029`, `US-040`,
`US-041`, `US-048`, and the audit retention
guarantee from `NFR-SEC-008`. The slice does
not redefine the source registry, the
secret manager, the audit log, the
notification surface, the real-environment
cutover, the alerting surface, or the
connector auto-disable surface.

The slice introduces the first bounded
outbound webhook surface that fans out
high-priority events, lead stage changes,
auto-disable events, and alert events to
customer-controlled URLs with HMAC-SHA256
signing, a bounded retry policy, a bounded
window bound, and a secret manager that
owns the per-subscription signing secret.

## Follow-Up

- Provider-specific HTTP transports
  (CloudEvents, Slack, Microsoft Teams,
  PagerDuty, Opsgenie).
- Per-tenant secret KMS integration.
- Inbound webhook signature verification.
- Distributed webhook fan-out across
  multiple worker nodes.
- Per-tenant thresholds for the bounded
  window, the bounded `max_attempts`, and
  the bounded `cooldown_seconds`.
- Bulk rotate action on the operator panel
  widget.
