# Webhook Delivery And Event Fan-Out

Source: `SPEC.md` sections 5.13 (FR-NOT-001..003),
5.14 (FR-ADM-001..005), 7.4 (Webhook), 10.3
(NFR-SEC-001..010), 10.4 (NFR-PRIV-001..006),
12 (business rules), and the durable decisions
`0019-observability-and-alerting-baseline` and
`0026-connector-auto-disable-and-policy-recovery-baseline`.

## Product Goal

Owners, admins, operators on call, analysts,
and Sales/BD users need a bounded governed
webhook delivery surface that closes the
implicit `SPEC.md` section 7.4 contract
without weakening the `US-003` source
policy, the `US-026` audit log contract,
the `US-029` notification surface, the
`US-040` real-environment cutover contract,
the `US-041` alerting contract, the
`US-048` auto-disable contract, or the
`US-027` identity and access contract.

The MVP already depends on a per-workspace
secret manager from `US-003`, a read-only
`AlertEvaluator` from `US-041`, a
`ConnectorAutoDisableEvent` history from
`US-048`, a `LeadActivity` history from
`US-012`, a `DiscoveryJob` lifecycle from
`US-004`, a `SanitizeAlertPayload` helper
shared with the audit log from `US-041`, and
an `EnvironmentMode` from `US-040` that
bounds the runtime profile.

This product slice is the first step toward
turning `SPEC.md` section 7.4 into a
documented contract, a durable
`webhook_subscriptions` and
`webhook_deliveries` pair, a closed
`WebhookEventType` enum, a closed
`WebhookDeliveryStatus` enum, a bounded
`WebhookDeliveryService`, a bounded
`WebhookSigner` HMAC helper, a bounded
`WebhookRetryPolicy`, a bounded
`WebhookDispatcher` actor, a bounded
secret rotation helper, and a reusable
verification command.

The slice is local-first by design. It does
not commit to a specific external transport
(CloudEvents, Slack, Microsoft Teams,
PagerDuty, Opsgenie) in this step; it
preserves a stable seam for a later
hardening story to wire one.

## MVP Scope

This product slice covers:

- A durable `webhook_subscriptions` table
  with `id`, `organization_id`, `name`,
  `target_url`, `secret_id` (links to the
  encrypted secret from `US-003`),
  `event_types_json`, `enabled`,
  `created_by`, `created_at`, `updated_at`,
  `last_rotated_at`, `last_success_at`, and
  `last_failure_at`. The table is the single
  source of truth for outbound webhook
  subscriptions; the bounded
  `WebhookDeliveryService` reads from it.
- A durable `webhook_deliveries` table with
  `id`, `organization_id`,
  `subscription_id`, `event_id`,
  `event_type` (closed enum),
  `target_url`, `payload_hash`,
  `request_body` (sanitized, JSON-encoded),
  `signature`, `status` (closed enum),
  `attempt_count`, `next_attempt_at`,
  `last_attempt_at`, `last_response_code`,
  `last_response_message` (bounded to 500
  characters; the secret-safe payload
  contract from `US-041` is enforced before
  persistence), `delivered_at`, and
  `created_at`. The table is bounded to the
  most recent N deliveries per subscription
  so a flapping subscription cannot fill
  the table.
- A `WebhookSecret` row in the existing
  `secrets` table from `US-003` keyed by
  `webhook_subscription:{id}` so the secret
  manager owns the per-subscription signing
  secret. The bounded rotation helper
  reuses the existing `US-003` secret
  storage.
- A closed `WebhookEventType` enum
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
- A closed `WebhookDeliveryStatus` enum
  (`pending`, `in_flight`, `succeeded`,
  `failed`, `dead_letter`, `cancelled`)
  that the bounded service uses to track
  the lifecycle of a webhook delivery.
- A bounded `WebhookDeliveryThresholds`
  dataclass that exposes the closed default
  thresholds and the `max_attempts` /
  `initial_backoff_seconds` /
  `backoff_multiplier` /
  `max_backoff_seconds` /
  `jitter_seconds` /
  `max_window_seconds` bounds. The
  defaults are read-only and locked in the
  decision record.
- A bounded `WebhookDeliveryService` with
  `emit_event`, `retry_delivery`,
  `cancel_subscription`, `list_subscriptions`,
  `list_deliveries`, and `rotate_secret`.
- A bounded `WebhookSigner` that owns the
  HMAC-SHA256 signing, the timestamp
  header, the `X-Webhook-Id` header, the
  `X-Webhook-Timestamp` header, and the
  `X-Webhook-Signature` header.
- A bounded `WebhookRetryPolicy` that owns
  the bounded retry algorithm with
  exponential backoff and bounded jitter.
- A bounded `WebhookDispatcher` actor that
  runs from a periodic worker tick (the
  existing scheduler from `US-035`) and
  from the `emit_event` path.
- A bounded secret rotation helper that
  reuses the `US-003` secret manager to
  generate a new per-subscription signing
  secret. The helper is owner/admin only
  and emits the
  `webhook.subscription.secret_rotated`
  audit entry.
- New bounded owner/admin-only REST
  surface:
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
- A new operator panel widget that renders
  the per-subscription list, the
  per-subscription delivery list, the
  `Rotate secret` button, the
  `Test send` button, and the `Retry`
  button.

This product slice does not yet cover:

- Distributed webhook fan-out across
  multiple worker nodes.
- Provider-specific HTTP transports
  (CloudEvents, Slack, Microsoft Teams,
  PagerDuty, Opsgenie).
- Per-tenant secret KMS integration. The
  slice reuses the existing `US-003`
  secret manager; per-tenant KMS is a
  follow-on story.
- Webhook signature verification on the
  inbound side. The slice is outbound
  only.
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

## Contract Rules

- All new admin endpoints require an
  authenticated session with `owner` or
  `admin` role. Viewer, analyst, sales,
  and reviewer roles get no webhook
  surface and cannot manage
  subscriptions.
- Every subscription create / update /
  delete, every secret rotation, every
  test send, every successful and failed
  delivery, and every rejected delivery
  must pass `SanitizeAlertPayload` from
  `US-041` before persistence. The helper
  rejects or redacts API keys, cookies,
  raw PII, browser storage state, and full
  connection strings.
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
- The bounded window is enforced by the
  `EnvironmentMode` from `US-040`
  (`pilot_live`: max 24h, `test_like`:
  max 1h). A `next_attempt_at` that
  exceeds the bound is recorded in the
  audit log with the
  `webhook.delivery.dead_letter` action
  and the delivery is transitioned to
  `dead_letter`.
- The bounded `WebhookEventType` and
  `WebhookDeliveryStatus` enums are
  closed. Adding a new value is an
  explicit follow-up story; the first
  slice ships only the values listed
  above.
- The bounded `target_url` is validated
  against the closed URL allowlist:
  `https://` or `http://localhost`; the
  bounded path refuses private IP
  addresses (RFC 1918 ranges, loopback,
  link-local, multicast, or reserved)
  per `NFR-SEC-006`.
- The bounded `WebhookSigner` uses
  HMAC-SHA256 with a constant-time
  comparison helper for the verifier
  side. The bounded path rejects
  signatures whose timestamp is more than
  `300` seconds in the past or in the
  future to defend against replay
  attacks.
- The bounded per-subscription signing
  secret is stored in the `US-003`
  secret manager. The bounded path never
  returns the signing secret in any
  response payload.
- The bounded
  `/admin/webhooks/*` endpoints are
  covered by the health probe contract:
  a missing or failing endpoint must not
  fail `GET /health/ready`, only surface
  as a degraded warning.

## Closed Enumerations

### `WebhookEventType`

| Value | Source | Default |
| --- | --- | --- |
| `event.high_priority` | `AuditAction.EVENT_SCORING_PRIORITY_VERY_HIGH` from `US-026` | n/a (audit action) |
| `lead.stage_changed` | `AuditAction.LEAD_STAGE_CHANGED` from `US-026` | n/a (audit action) |
| `lead.outcome_changed` | `AuditAction.LEAD_OUTCOME_RECORDED` from `US-026` | n/a (audit action) |
| `discovery.job_failed` | `AuditAction.DISCOVERY_RUN_FAILED` from `US-026` | n/a (audit action) |
| `connector.auto_disable_triggered` | `AuditAction.CONNECTOR_AUTO_DISABLE_TRIGGERED` from `US-048` | n/a (audit action) |
| `connector.auto_disable_recovered` | `AuditAction.CONNECTOR_AUTO_DISABLE_RECOVERED` from `US-048` | n/a (audit action) |
| `alert.fired` | `AlertEvent` from `US-041` with `severity in (warning, critical)` | n/a (alert event) |

### `WebhookDeliveryStatus`

| Value | Meaning |
| --- | --- |
| `pending` | The delivery is queued and waiting for the next worker tick. |
| `in_flight` | The dispatcher has picked up the delivery and is performing the bounded HTTP POST. |
| `succeeded` | The bounded HTTP POST returned a 2xx status code. |
| `failed` | The bounded HTTP POST returned a non-2xx status code or raised a network exception; the delivery is queued for the next retry attempt. |
| `dead_letter` | The bounded retry policy has exhausted `max_attempts` or the bounded window has elapsed; the delivery is no longer retried. |
| `cancelled` | The subscription was cancelled or deleted; the delivery is no longer retried. |

## Bounded HMAC Signing Contract

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
more than `300` seconds in the past or in
the future to defend against replay
attacks.

## Bounded Retry Policy

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
is `3600`; the bounded `jitter_seconds` is
`30`.

## Bounded Window Bound

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

## Sanitization Contract

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

## Audit Entry Shape

The bounded `WebhookDeliveryService` and
`WebhookDispatcher` emit the following
audit entries, all using the existing
`AuditEntry` contract from `US-026`:

- `webhook.subscription.created` —
  action, actor, `subscription_id`,
  `name`, `target_url`, `event_types`,
  `enabled`.
- `webhook.subscription.updated` —
  action, actor, `subscription_id`,
  before/after diff.
- `webhook.subscription.deleted` —
  action, actor, `subscription_id`.
- `webhook.subscription.secret_rotated` —
  action, actor, `subscription_id`,
  `rotated_at`.
- `webhook.subscription.test_sent` —
  action, actor, `subscription_id`,
  `delivery_id`, `status`,
  `last_response_code`.
- `webhook.delivery.succeeded` — action,
  actor (system), `delivery_id`,
  `subscription_id`, `event_type`,
  `attempt_count`, `last_response_code`.
- `webhook.delivery.failed` — action,
  actor (system), `delivery_id`,
  `subscription_id`, `event_type`,
  `attempt_count`, `last_response_code`,
  `last_response_message`.
- `webhook.delivery.dead_letter` —
  action, actor (system), `delivery_id`,
  `subscription_id`, `event_type`,
  `attempt_count`, `reason`.
- `webhook.delivery.rejected` — action,
  actor, `delivery_id`,
  `subscription_id`, `event_type`,
  `reason` (sanitization rejection,
  target URL rejection, or window
  rejection).
- `webhook.delivery.retried` — action,
  actor, `delivery_id`,
  `subscription_id`, `event_type`,
  `attempt_count`.

## API Surface

The new owner/admin-only REST surface:

- `GET /admin/webhooks/subscriptions?organization_id=&enabled=&limit=&offset=`
  — paginated subscription list with
  sanitized payloads.
- `POST /admin/webhooks/subscriptions` —
  body shape:
  ```json
  {
    "name": "SIEM",
    "target_url": "https://siem.example.com/webhook",
    "event_types": ["event.high_priority", "alert.fired"],
    "enabled": true
  }
  ```
- `GET
  /admin/webhooks/subscriptions/{id}` —
  returns a single subscription with the
  sanitized payload.
- `PATCH
  /admin/webhooks/subscriptions/{id}` —
  body shape: same as create. Updates
  name, target URL, event types, and
  enabled state.
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
- `GET /admin/webhooks/deliveries?subscription_id=&status=&limit=&offset=`
  — paginated delivery history with
  sanitized payloads.
- `POST
  /admin/webhooks/deliveries/{id}/retry`
  — retries a `failed` or `dead_letter`
  delivery and emits the
  `webhook.delivery.retried` audit
  entry.

All new error responses follow the
existing error envelope (`code`,
`message`, `request_id`, `details`):

- `WEBHOOK_SUBSCRIPTION_NOT_FOUND` —
  subscription id not found in the tenant
  scope.
- `WEBHOOK_DELIVERY_NOT_FOUND` — delivery
  id not found in the tenant scope.
- `WEBHOOK_TARGET_URL_INVALID` — target
  URL validation rejection.
- `WEBHOOK_PAYLOAD_INVALID` — sanitization
  rejection.
- `WEBHOOK_EVENT_TYPE_INVALID` — unknown
  event type.
- `WEBHOOK_DELIVERY_REJECTED` — bounded
  window rejection.
- `WEBHOOK_RETRY_EXHAUSTED` — bounded
  `max_attempts` exhausted.

## UI / Ops Surface

- A new operator panel widget on the
  `AdminSettings` page that lists the
  per-subscription list, the
  per-subscription delivery list, the
  `WebhookEventType` badges, the
  `WebhookDeliveryStatus` badges, the
  `Rotate secret` button, the
  `Test send` button, and the `Retry`
  button.
- The in-app inbox from `US-029` shows
  webhook events with a dedicated trigger
  icon and a deep link to the event
  detail in the operator panel.
- A new runbook
  (`docs/ops/webhook-delivery-runbook.md`)
  documents what an operator does when
  a subscription flips to `dead_letter`,
  when a `signature_invalid` failure
  fires, when a `target_unreachable`
  failure fires, and when a secret
  rotation is denied because the
  `EnvironmentMode` bound is in `paused`
  state.

## Validation Implications

- Unit tests must prove that the
  `WebhookSigner` and the
  `WebhookRetryPolicy` reject or
  correctly process the documented input
  space, that the `cooldown_seconds`
  window is enforced, that the bounded
  window helper returns the bounded
  `(start, end)` pair, and that the
  bounded target URL validation refuses
  private IP addresses.
- Integration tests must exercise every
  new endpoint against an in-memory
  SQLite plus a stubbed HTTP receiver
  and prove that role gates, sanitization,
  HMAC signing, retry policy, and window
  enforcement are enforced.
- E2E tests must cover the operator
  panel render, the simulated seed event
  fire, the test send, the recovery
  flow, the secret rotation, and the
  bounded window enforcement.
- Security tests must prove that viewer,
  analyst, sales, and reviewer sessions
  are rejected on every new endpoint,
  that SSRF / private IP refusal is
  enforced, and that the bounded
  constant-time comparison helper is
  used for HMAC verification.
- Operational tests must prove the
  seed defaults match the documented
  table, the runbook entry exists, the
  verify script exercises each event
  type, and the bounded
  `WebhookDispatcher` actor is wired
  into the existing scheduler tick from
  `US-035`.
- Platform proof is the
  `scripts/verify-us-049.sh` command
  wired into `story verify` and
  `story verify-all`.
