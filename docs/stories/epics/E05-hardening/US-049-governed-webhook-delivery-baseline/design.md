# Design

## Domain Model

The first governed webhook delivery slice
formalizes the durable objects, bounded
enums, and bounded services that turn
`SPEC.md` section 7.4 into a documented
contract.

### `WebhookSubscription`

A single record of a per-workspace webhook
subscription. The row carries enough
information for the bounded
`WebhookDeliveryService` to dispatch a
delivery against the closed retry policy
without reading raw tables.

- `id`
- `organization_id`
- `name` (bounded to 200 characters)
- `target_url` (validated against
  `https://` or `http://localhost`; the
  bounded path refuses private IP
  addresses per `NFR-SEC-006`)
- `secret_id` (links to the encrypted
  secret in the `US-003` secret manager)
- `event_types` (closed enum set,
  JSON-encoded)
- `enabled`
- `created_by` (foreign key to `users.id`)
- `created_at`
- `updated_at`
- `last_rotated_at` (nullable)
- `last_success_at` (nullable)
- `last_failure_at` (nullable)

### `WebhookDelivery`

A single record of a per-delivery history.
The table is bounded to the most recent N
deliveries per subscription so a flapping
subscription cannot fill the table.

- `id`
- `organization_id`
- `subscription_id` (foreign key to
  `webhook_subscriptions.id`)
- `event_id` (nullable; links to the
  matching `AuditEntry` row from
  `US-026`)
- `event_type` (closed enum)
- `target_url`
- `payload_hash` (SHA-256 of the sanitized
  payload, hex-encoded)
- `request_body` (sanitized, JSON-encoded)
- `signature` (HMAC-SHA256 signature, hex-
  encoded)
- `status` (closed enum)
- `attempt_count` (closed non-negative
  integer)
- `next_attempt_at` (nullable)
- `last_attempt_at` (nullable)
- `last_response_code` (nullable HTTP
  status code)
- `last_response_message` (bounded to 500
  characters; the secret-safe payload
  contract from `US-041` is enforced
  before persistence)
- `delivered_at` (nullable)
- `created_at`

### `WebhookEventType`

Closed enum that the bounded
`WebhookDeliveryService` reads from the
closed `AuditAction` enum from `US-026`
and the closed `AutoDisableTrigger` enum
from `US-048`:

- `event.high_priority` — fires when the
  `event.scoring.priority.very_high` audit
  entry is written.
- `lead.stage_changed` — fires when the
  `lead.stage.changed` audit entry is
  written.
- `lead.outcome_changed` — fires when the
  `lead.outcome.recorded` audit entry is
  written.
- `discovery.job_failed` — fires when the
  `discovery.run.failed` audit entry is
  written.
- `connector.auto_disable_triggered` —
  fires when the
  `connector.auto_disable.triggered`
  audit entry is written.
- `connector.auto_disable_recovered` —
  fires when the
  `connector.auto_disable.recovered`
  audit entry is written.
- `alert.fired` — fires when an
  `AlertEvent` is created with `severity
  in (warning, critical)`.

### `WebhookDeliveryStatus`

Closed enum that the bounded
`WebhookDeliveryService` uses to track
the lifecycle of a webhook delivery:

- `pending` — the delivery is queued and
  waiting for the next worker tick.
- `in_flight` — the dispatcher has picked
  up the delivery and is performing the
  bounded HTTP POST.
- `succeeded` — the bounded HTTP POST
  returned a 2xx status code.
- `failed` — the bounded HTTP POST
  returned a non-2xx status code or
  raised a network exception; the
  delivery is queued for the next retry
  attempt.
- `dead_letter` — the bounded retry
  policy has exhausted `max_attempts` or
  the bounded window has elapsed; the
  delivery is no longer retried.
- `cancelled` — the subscription was
  cancelled or deleted; the delivery is
  no longer retried.

### `WebhookDeliveryThresholds`

Bounded dataclass that exposes the closed
default thresholds and the
`max_attempts` / `initial_backoff_seconds`
/ `backoff_multiplier` /
`max_backoff_seconds` / `jitter_seconds` /
`max_window_seconds` bounds:

- `max_attempts` = `6`
- `initial_backoff_seconds` = `30`
- `backoff_multiplier` = `2.0`
- `max_backoff_seconds` = `3600`
- `jitter_seconds` = `30`
- `max_window_seconds` = bounded by
  `EnvironmentMode` from `US-040` (24h in
  `pilot_live`, 1h in `test_like`)
- `request_timeout_seconds` = `30`
- `recent_deliveries_per_subscription` =
  `100`
- `max_response_message_length` = `500`

### `WebhookSigner`

Bounded helper that owns the HMAC-SHA256
signing, the timestamp header, the
`X-Webhook-Id` header, the
`X-Webhook-Timestamp` header, and the
`X-Webhook-Signature` header. The helper
is pure; it does not touch the database
or the network.

```python
from typing import Protocol


class WebhookSigner(Protocol):
    def sign(
        self,
        *,
        body: bytes,
        secret: str,
        timestamp: int,
        delivery_id: str,
    ) -> dict[str, str]: ...
```

The bounded signature returns:

- `X-Webhook-Id: {delivery_id}`
- `X-Webhook-Timestamp: {timestamp}`
- `X-Webhook-Signature: v1,{hex_signature}`

The bounded `hex_signature` is
`HMAC-SHA256(secret, "{timestamp}.{body}")`
hex-encoded. The bounded path uses a
constant-time comparison helper for the
verifier side.

### `WebhookRetryPolicy`

Bounded helper that owns the bounded retry
algorithm with exponential backoff and
bounded jitter. The helper is pure; it
does not touch the database or the
network.

```python
from typing import Protocol
from datetime import datetime


class WebhookRetryPolicy(Protocol):
    def next_attempt(
        self,
        *,
        attempt_count: int,
        thresholds: WebhookDeliveryThresholds,
        now: datetime,
    ) -> datetime | None: ...
```

The bounded algorithm is:

```text
if attempt_count >= max_attempts:
    return None
backoff = min(
    initial_backoff_seconds
    * (backoff_multiplier ** (attempt_count - 1)),
    max_backoff_seconds,
)
jitter = random.uniform(0, jitter_seconds)
return now + timedelta(seconds=backoff + jitter)
```

The bounded `max_attempts` is
`6`; the bounded `initial_backoff_seconds`
is `30`; the bounded `backoff_multiplier`
is `2.0`; the bounded `max_backoff_seconds`
is `3600`; the bounded `jitter_seconds` is
`30`.

### `WebhookDeliveryService`

Bounded service that exposes the bounded
operations:

- `emit_event(*, organization_id,
  event_type, payload)` — reads the
  matching subscriptions, derives the
  bounded `webhook_deliveries` rows with
  status `pending`, and dispatches them
  through the bounded retry policy. The
  bounded path applies the
  `SanitizeAlertPayload` helper from
  `US-041` to the payload before
  persistence.
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

### `WebhookDispatcher`

Bounded actor that runs from a periodic
worker tick (the existing scheduler from
`US-035`) and from the `emit_event` path.
The actor reads the `pending` and `failed`
deliveries whose `next_attempt_at` has
elapsed, marks them `in_flight`, performs
the bounded HTTP POST, and transitions
them to `succeeded` / `failed` /
`dead_letter`.

The bounded dispatcher enforces:

- The `EnvironmentMode` bound from
  `US-040` for the bounded window.
- The closed `max_attempts` /
  `initial_backoff_seconds` /
  `backoff_multiplier` /
  `max_backoff_seconds` /
  `jitter_seconds` bounds.
- The closed `request_timeout_seconds`
  bound.
- The closed `recent_deliveries_per_subscription`
  bound.
- The closed `target_url` validation
  against `https://` or
  `http://localhost` (refuses private IP
  addresses per `NFR-SEC-006`).

## Bounded HMAC Signing Contract

The bounded `WebhookSigner` returns:

- `X-Webhook-Id: {delivery_id}`
- `X-Webhook-Timestamp: {timestamp}`
- `X-Webhook-Signature: v1,{hex_signature}`

The bounded `hex_signature` is
`HMAC-SHA256(secret, "{timestamp}.{body}")`
hex-encoded. The bounded path uses a
constant-time comparison helper for the
verifier side.

The bounded timestamp is the Unix epoch
seconds at the time the signature is
generated. The bounded path rejects
signatures whose timestamp is more than
`300` seconds in the past or in the
future to defend against replay attacks.

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

- `pilot_live` — `max_window_seconds = 24
  * 3600` (24 hours).
- `test_like` — `max_window_seconds = 3600`
  (1 hour).

The `WebhookDeliveryService.emit_event`
and `WebhookDispatcher.dispatch_pending`
operations clip the
`next_attempt_at` to the bound. A
`next_attempt_at` that exceeds the bound
is recorded in the audit log with the
`webhook.delivery.dead_letter` action and
the delivery is transitioned to
`dead_letter`.

## Bounded Target URL Validation

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

## API Contract

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
  Returns the created subscription with
  the sanitized payload.
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
  the `webhook.subscription.secret_rotated`
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

## UI Surface

The new operator panel widget renders:

- A per-subscription list with the
  `WebhookEventType` badges, the
  `target_url`, the `enabled` state, the
  `last_success_at` and `last_failure_at`
  timestamps.
- A per-subscription delivery list with
  the `WebhookDeliveryStatus` badge, the
  `event_type`, the `attempt_count`, the
  `last_response_code`, and the
  `delivered_at` timestamp.
- A `Create subscription` button that
  opens a modal with the subscription
  form.
- A `Rotate secret` button per
  subscription that opens a confirmation
  dialog and calls
  `POST
  /admin/webhooks/subscriptions/{id}/rotate-secret`.
- A `Test send` button per subscription
  that calls
  `POST
  /admin/webhooks/subscriptions/{id}/test`
  and shows the result inline.
- A `Retry` button per `failed` or
  `dead_letter` delivery that calls
  `POST
  /admin/webhooks/deliveries/{id}/retry`.

The widget reuses the existing settings
and inbox surfaces from `US-026` and
`US-029`.

## Affected Existing Code Paths

The bounded slice touches the following
existing code paths. Each touch is
explicitly bounded:

- `src/livelead/domain/sources/` (`US-003`
  source registry) — the bounded
  `WebhookSubscription.secret_id` reuses
  the `US-003` secret manager.
- `src/livelead/domain/audit/`
  (`US-026` audit log) — the webhook
  subscription and delivery actions emit
  `webhook.*` audit entries via the
  existing `AuditService`.
- `src/livelead/domain/observability/`
  (`US-041` alerting) — the bounded
  `WebhookDeliveryService` consumes the
  `AlertEvent` rows; reuse the
  `SanitizeAlertPayload` helper.
- `src/livelead/domain/auto_disable/`
  (`US-048` auto-disable) — the bounded
  `WebhookDeliveryService` consumes the
  `ConnectorAutoDisableEvent` rows.
- `src/livelead/runtime/environment/`
  (`US-040` environment mode) — the
  bounded window is enforced by the
  `EnvironmentMode` from `US-040`.
- `src/livelead/domain/identity/`
  (`US-027` identity and access) — every
  new endpoint requires an authenticated
  session with `owner` or `admin` role.
- `apps/api/main.py` — register the new
  admin endpoints.
- `frontend/src/pages/AdminSettings.tsx`
  — render the new operator panel widget.
- `frontend/src/api/webhooks.ts` — new
  API client for the new admin endpoints.
