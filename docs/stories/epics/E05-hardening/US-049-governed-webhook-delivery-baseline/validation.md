# Validation

## Required Proof

| Layer | Expectation |
| --- | --- |
| Unit | `WebhookSigner.sign` returns the bounded `X-Webhook-Id`, `X-Webhook-Timestamp`, and `X-Webhook-Signature` headers with the bounded HMAC-SHA256 signature. `WebhookSigner.verify` uses the bounded constant-time comparison helper and rejects signatures whose timestamp is more than `300` seconds in the past or in the future. `WebhookRetryPolicy.next_attempt` returns the bounded `next_attempt_at` for the closed `max_attempts`, `initial_backoff_seconds`, `backoff_multiplier`, `max_backoff_seconds`, and `jitter_seconds` bounds; returns `None` when `attempt_count >= max_attempts`. `SanitizeAlertPayload` strips keys, cookies, raw PII, browser storage state, and full connection strings from every payload, delivery, and audit entry before persistence. The `WebhookEventType` and `WebhookDeliveryStatus` enums are closed; unknown values return `WEBHOOK_EVENT_TYPE_INVALID`. |
| Integration | `POST /admin/webhooks/subscriptions` creates a subscription after validation against the closed `WebhookEventType` enum and the `EnvironmentMode` bound; a `target_url` that fails the URL allowlist returns `WEBHOOK_TARGET_URL_INVALID`. `GET /admin/webhooks/subscriptions` returns the paginated subscription list with sanitized payloads. `PATCH /admin/webhooks/subscriptions/{id}` updates name, target URL, event types, and enabled state. `DELETE /admin/webhooks/subscriptions/{id}` soft-deletes the subscription. `POST /admin/webhooks/subscriptions/{id}/rotate-secret` rotates the signing secret and emits the `webhook.subscription.secret_rotated` audit entry. `POST /admin/webhooks/subscriptions/{id}/test` sends a bounded `webhook.test` event to the subscription and returns the delivery result inline. `GET /admin/webhooks/deliveries` returns the paginated delivery history with sanitized payloads. `POST /admin/webhooks/deliveries/{id}/retry` retries a `failed` or `dead_letter` delivery and emits the `webhook.delivery.retried` audit entry. The bounded window is enforced by the `EnvironmentMode` from `US-040` (max 24 hours in `pilot_live`, max 1 hour in `test_like`); a `next_attempt_at` that exceeds the bound is recorded in the audit log with the `webhook.delivery.dead_letter` action. Every subscription create / update / delete, every secret rotation, every test send, every successful and failed delivery, and every rejected delivery emits a durable audit entry with the same secret-safe payload contract as `US-026` and `US-041`. |
| E2E | An authenticated owner can open the new operator panel, see the per-subscription list, see the per-subscription delivery list, run a `Test send`, see the result inline, and acknowledge the result. The bounded verification harness runs a deterministic delivery cycle for a seeded subscription against a local HTTP receiver, asserts the HMAC-SHA256 signature matches, asserts the `X-Webhook-Id`, `X-Webhook-Timestamp`, and `X-Webhook-Signature` headers are present, asserts the bounded retry policy transitions the delivery to `succeeded` on first attempt, and asserts the audit entry was written. The bounded retry policy is exercised end-to-end by a delivery that fails on the first attempt; the bounded dispatcher retries with the bounded exponential backoff and bounded jitter, succeeds on the second attempt, and the `webhook.delivery.succeeded` audit entry is written. The bounded window is exercised end-to-end by a delivery whose `next_attempt_at` exceeds the `EnvironmentMode` bound; the delivery is transitioned to `dead_letter` and the `webhook.delivery.dead_letter` audit entry is written. The migration is exercised end-to-end by the verify script so a missing `webhook_subscriptions` table or a missing `webhook_deliveries` table fails the E2E check, not just the data check. |
| Security | Direct API calls to the new endpoints with viewer, analyst, sales, and reviewer sessions are rejected with the same error envelope as the existing admin surfaces. Sanitizer tests prove that subscriptions, deliveries, and audit entries carrying API keys, cookies, raw PII, browser storage state, and full connection strings are rejected or redacted before persistence. The bounded target URL validation refuses `target_url` values that resolve to private IP addresses (RFC 1918 ranges, loopback, link-local, multicast, or reserved) per `NFR-SEC-006`. The bounded `WebhookSigner.verify` uses the bounded constant-time comparison helper. The bounded window refuses zero or negative values. The bounded `max_attempts` refuses zero or negative values. The new `WebhookEventType` and `WebhookDeliveryStatus` enums do not weaken the existing `AlertAction` enum from `US-026`, the existing `AutoDisableTrigger` enum from `US-048`, or the existing `EnvironmentMode` from `US-040`. The migration does not weaken the existing audit retention guarantee from `NFR-SEC-008`. The bounded `WebhookSubscription.secret_id` does not leak the signing secret in any response payload. |
| Operational | A runbook entry for the webhook delivery domain documents what an operator does when a subscription flips to `dead_letter`, when a `signature_invalid` failure fires, when a `target_unreachable` failure fires, and when a secret rotation is denied because the `EnvironmentMode` bound is in `paused` state. The verification script proves that the bounded verification harness can run a deterministic delivery cycle for a seeded subscription against a local HTTP receiver and assert the recorded delivery stays within the contract. The new endpoints are covered by the health probe contract from `US-040`: a missing or failing endpoint must not fail `GET /health/ready`, only surface as a degraded warning. The bounded `WebhookDispatcher` actor is wired into the existing scheduler tick from `US-035`; the actor emits a `webhook.delivery.rejected` audit entry on a sanitization rejection. |
| Platform | The `scripts/verify-us-049.sh` command wires the unit, integration, E2E, security, and operational checks together and is the same command run by `harness-cli story verify` and `harness-cli story verify-all`. The `webhook_subscriptions` and `webhook_deliveries` migrations are exercised by the verify script so a missing table fails the platform check, not just the data check. The new `WebhookEventType` and `WebhookDeliveryStatus` enums and the new audit entry types are exercised by the verify script so a missing enum value fails the platform check, not just the data check. |

## Suggested Checks

- Backend unit tests for:
  - `WebhookSigner.sign`
  - `WebhookSigner.verify`
  - `WebhookRetryPolicy.next_attempt`
  - `WebhookDeliveryService.emit_event`
  - `WebhookDeliveryService.retry_delivery`
  - `WebhookDeliveryService.cancel_subscription`
  - `WebhookDeliveryService.list_subscriptions`
  - `WebhookDeliveryService.list_deliveries`
  - `WebhookDeliveryService.rotate_secret`
  - `SanitizeAlertPayload` reuse for every
    payload, delivery, and audit entry
  - `WebhookEventType` enum closure
  - `WebhookDeliveryStatus` enum closure
  - `EnvironmentMode` bound for the bounded
    window
  - `AuditService` reuse for every
    `webhook.*` audit entry
- Backend integration tests for:
  - `POST /admin/webhooks/subscriptions`
  - `GET /admin/webhooks/subscriptions`
  - `PATCH /admin/webhooks/subscriptions/{id}`
  - `DELETE /admin/webhooks/subscriptions/{id}`
  - `POST /admin/webhooks/subscriptions/{id}/rotate-secret`
  - `POST /admin/webhooks/subscriptions/{id}/test`
  - `GET /admin/webhooks/deliveries`
  - `POST /admin/webhooks/deliveries/{id}/retry`
  - Cross-tenant denial for every new
    endpoint
  - Audit entries for every successful and
    failed subscription, secret rotation,
    test send, delivery, and retry
  - Bounded window enforcement
  - Bounded retry policy
- E2E tests for:
  - Operator panel renders the per-
    subscription list, the per-subscription
    delivery list, the `WebhookEventType`
    badge, the `WebhookDeliveryStatus`
    badge, the `Rotate secret` button, the
    `Test send` button, and the `Retry`
    button.
  - The bounded verification harness runs
    a deterministic delivery cycle for a
    seeded subscription against a local
    HTTP receiver and asserts the recorded
    delivery stays within the contract.
  - The bounded retry policy is exercised
    end-to-end by a delivery that fails on
    the first attempt.
  - The bounded window is exercised
    end-to-end.
  - The migrations are exercised by the
    verify script.
- Security tests for:
  - Role enforcement on every new
    endpoint.
  - Subscription, delivery, and audit
    entry sanitization for every new write
    path.
  - The bounded target URL validation
    refuses private IP addresses.
  - The bounded `WebhookSigner.verify` uses
    the bounded constant-time comparison
    helper.
  - The bounded window refuses zero or
    negative values.
  - The bounded `max_attempts` refuses
    zero or negative values.
- Operational checks for:
  - The bounded verification harness can
    run a deterministic delivery cycle for
    a seeded subscription against a local
    HTTP receiver and assert the recorded
    delivery stays within the contract.
  - The new endpoints are covered by the
    health probe contract from `US-040`.
  - The runbook entry exists and references
    the right surfaces.
  - The bounded `WebhookDispatcher` actor
    is wired into the existing scheduler
    tick from `US-035`.
- Platform proof is the
  `scripts/verify-us-049.sh` command wired
  into `harness-cli story verify` and
  `harness-cli story verify-all`.

## Evidence Hooks

- `tests/unit/test_webhook_signer.py` —
  signer unit tests
- `tests/unit/test_webhook_retry_policy.py`
  — retry policy unit tests
- `tests/unit/test_webhook_delivery_service.py`
  — service unit tests
- `tests/unit/test_webhook_event_type_enum.py`
  — `WebhookEventType` enum closure
- `tests/unit/test_webhook_delivery_status_enum.py`
  — `WebhookDeliveryStatus` enum closure
- `tests/unit/test_webhook_audit_sanitizer.py`
  — `SanitizeAlertPayload` reuse for every
  payload, delivery, and audit entry
- `tests/unit/test_webhook_window_bound.py`
  — `EnvironmentMode` bound for the
  bounded window
- `tests/unit/test_webhook_target_url_validation.py`
  — `target_url` validation
- `tests/integration/test_webhook_api.py`
  — REST surface integration tests
- `tests/integration/test_webhook_audit.py`
  — audit entry integration tests
- `tests/integration/test_webhook_window.py`
  — bounded window integration tests
- `tests/integration/test_webhook_retry.py`
  — bounded retry policy integration
  tests
- `tests/security/test_webhook_role_gates.py`
  — RBAC contract from `US-027`
- `tests/security/test_webhook_sanitizer.py`
  — secret-safe payload contract
- `tests/security/test_webhook_target_url.py`
  — SSRF / private IP refusal
- `tests/e2e/webhook.py` — operator panel,
  test send, and bounded retry
- `frontend/e2e/webhook.spec.ts` — frontend
  e2e
- `scripts/verify-us-049.sh` — bounded
  verification harness
- `docs/ops/webhook-delivery-runbook.md`
  (operational entry)
- `docs/product/webhook-delivery-and-event-fanout.md`
  (living product contract)
- `docs/decisions/0027-webhook-delivery-and-fanout-baseline.md`
  (durable decision record)

## Open Questions

- Should the bounded window be configurable
  per workspace, or should it always follow
  the closed `EnvironmentMode` bound from
  `US-040`? The first implementation follows
  the closed bound; per-workspace tuning is a
  follow-on story.
- Should the `WebhookEventType` enum
  include a `manual_test` value, or should
  the manual test send be a separate
  internal event type? The first
  implementation uses a separate internal
  `webhook.test` event; a follow-on story
  can add additional event types with
  explicit acceptance criteria.
- Should the bounded dispatcher read
  browser-session or browser-debug rows, or
  should it stay scoped to `AuditEntry`,
  `AlertEvent`, `ConnectorAutoDisableEvent`,
  and `LeadActivity`? The first
  implementation stays scoped; a follow-on
  story can extend the dispatcher to read
  those rows behind the same
  `WebhookDispatcher` seam.
- Should the bounded dispatcher run on a
  periodic worker tick, or should it stay
  bounded to explicit
  `POST /admin/webhooks/subscriptions/{id}/test`
  requests? The first implementation runs on
  a periodic worker tick (the bounded
  `WebhookDispatcher` actor is wired into the
  existing scheduler tick from `US-035`);
  a follow-on story can disable the periodic
  tick per workspace.
- Should the operator panel widget expose a
  bulk rotate action, or should the widget
  only expose the per-subscription
  `Rotate secret` button? The first
  implementation exposes the per-subscription
  button; a follow-on story can add the bulk
  action behind the same RBAC contract.
- Should the bounded `cooldown_seconds`
  window be configurable per subscription,
  or should it always follow the closed
  default? The first implementation allows
  per-subscription configuration; a follow-on
  story can lock the cooldown to the closed
  default per workspace.
