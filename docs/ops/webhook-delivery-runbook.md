# Webhook Delivery And Event Fan-Out Runbook

Source: `docs/product/webhook-delivery-and-event-fanout.md`,
`docs/decisions/0027-webhook-delivery-and-fanout-baseline.md`,
and the runtime contracts established by
`US-003` (source registry and secret
manager), `US-026` (audit log),
`US-029` (notification delivery),
`US-040` (real-environment cutover),
`US-041` (operational observability and
alerting), `US-048` (connector
auto-disable and policy recovery), and
`US-027` (identity and access).

This runbook entry documents what an
operator on call for the pilot-live
environment does when:

- A webhook subscription flips to
  `dead_letter`.
- A `signature_invalid` failure fires.
- A `target_unreachable` failure fires.
- A secret rotation is denied because
  the `EnvironmentMode` bound is in
  `paused` state.
- A bounded `next_attempt_at` exceeds the
  `EnvironmentMode` bound.

## 1. When A Webhook Subscription Flips To `dead_letter`

### Symptoms

- A `webhook.delivery.dead_letter` audit
  entry is recorded with
  `subscription_id`, `event_type`, and
  `reason`.
- The bounded `WebhookDispatcher` has
  exhausted the `max_attempts` retries
  on a delivery, or the bounded window
  has elapsed.

### Steps

1. **Open the operator panel.** Navigate
   to `AdminSettings` and locate the
   affected subscription in the
   `Webhooks` widget.
2. **Read the `dead_letter` reason.** The
   `last_response_code`,
   `last_response_message`, and
   `attempt_count` columns tell you
   whether the failure was an HTTP error
   (4xx, 5xx), a network exception, a
   window rejection, or a sanitization
   rejection.
3. **Diagnose the root cause.** Use the
   `webhook.delivery.failed` audit
   entries to understand the failure
   history. Common root causes include:
   - `4xx` — the target URL rejected the
     request (signature invalid,
     target URL changed, or the
     downstream consumer rejected the
     payload).
   - `5xx` — the downstream consumer
     returned a transient error.
   - Network exception — DNS
     resolution failed, the target URL
     is unreachable, or the connection
     timed out.
   - Window rejection — the bounded
     `next_attempt_at` exceeded the
     `EnvironmentMode` bound.
   - Sanitization rejection — the payload
     failed the
     `SanitizeAlertPayload` contract.
4. **Decide whether to recover.** If the
   underlying issue is fixed, retry the
   delivery via the operator panel or
   the `POST
   /admin/webhooks/deliveries/{id}/retry`
   endpoint. If the underlying issue is
   not fixed, leave the delivery in
   `dead_letter` state and continue
   diagnosis.

## 2. When A `signature_invalid` Failure Fires

### Symptoms

- A `webhook.delivery.failed` audit entry
  is recorded with `last_response_code
  = 401` or `last_response_code = 403`
  and `last_response_message` containing
  the substring `signature` or `invalid`.
- The downstream consumer rejected the
  request because the
  `X-Webhook-Signature` header did not
  match the expected HMAC-SHA256
  signature.

### Steps

1. **Open the operator panel.** Navigate
   to `AdminSettings` and locate the
   affected subscription in the
   `Webhooks` widget.
2. **Verify the signing secret.** Check
   the `last_rotated_at` timestamp. If
   the secret was rotated recently, the
   downstream consumer may still be
   using the old secret.
3. **Coordinate secret rotation.** If
   the downstream consumer is using the
   old secret, coordinate a secret
   rotation with the consumer team.
   Use the `POST
   /admin/webhooks/subscriptions/{id}/rotate-secret`
   endpoint to rotate the secret and
   share the new secret with the
   consumer team through a secure
   channel.
4. **Test the subscription.** Use the
   `POST
   /admin/webhooks/subscriptions/{id}/test`
   endpoint to send a bounded
   `webhook.test` event and verify the
   new signature is accepted by the
   downstream consumer.
5. **Retry the delivery.** Once the
   downstream consumer is using the new
   secret, retry the failed delivery via
   the `POST
   /admin/webhooks/deliveries/{id}/retry`
   endpoint.

## 3. When A `target_unreachable` Failure Fires

### Symptoms

- A `webhook.delivery.failed` audit entry
  is recorded with `last_response_code
  = 0` (network exception) and
  `last_response_message` containing
  the substring `connection refused`,
  `dns`, or `timeout`.
- The downstream consumer's URL is
  unreachable.

### Steps

1. **Open the operator panel.** Navigate
   to `AdminSettings` and locate the
   affected subscription in the
   `Webhooks` widget.
2. **Verify the target URL.** Check the
   `target_url` value and confirm the
   URL is correct. If the URL is
   incorrect, update the subscription
   via the `PATCH
   /admin/webhooks/subscriptions/{id}`
   endpoint.
3. **Verify network connectivity.** Use
   the bounded target URL validation to
   confirm the URL passes the
   `https://` / `http://localhost`
   allowlist and the SSRF / private IP
   refusal.
4. **Wait for the retry window.** The
   bounded `WebhookRetryPolicy` will
   retry the delivery on the bounded
   exponential backoff. The next
   attempt will be queued automatically.
5. **Escalate if the URL is correct.** If
   the URL is correct and the
   downstream consumer is still
   unreachable, escalate to the
   downstream consumer's on-call
   rotation.

## 4. When A Secret Rotation Is Denied

### Symptoms

- The `POST
  /admin/webhooks/subscriptions/{id}/rotate-secret`
  call returns `403` with the reason
  `environment_mode_paused`.
- The `webhook.subscription.secret_rotated`
  audit entry is recorded with
  `reason = environment_mode_paused`.
- The `EnvironmentMode` is in `paused`
  state.

### Steps

1. **Verify the `EnvironmentMode`
   state.** Navigate to
   `AdminSettings` and confirm the
   `EnvironmentMode` is in `paused`
   state.
2. **Promote the `EnvironmentMode`.** If
   the operator is authorized to promote
   the `EnvironmentMode`, use the
   bounded promotion endpoint to
   transition the `EnvironmentMode` to
   `pilot_live`.
3. **Wait for the cutover to settle.** The
   bounded `LaunchGateReport` from
   `US-040` must report `ready` before
   the secret rotation succeeds.
4. **Retry the secret rotation.** Once
   the `EnvironmentMode` is in
   `pilot_live`, retry the secret
   rotation via the `POST
   /admin/webhooks/subscriptions/{id}/rotate-secret`
   endpoint.

## 5. When A Bounded `next_attempt_at` Exceeds The `EnvironmentMode` Bound

### Symptoms

- A `webhook.delivery.dead_letter` audit
  entry is recorded with
  `reason = window_rejection`.
- The bounded `next_attempt_at` exceeded
  the `EnvironmentMode` bound.

### Steps

1. **Open the operator panel.** Navigate
   to `AdminSettings` and locate the
   affected subscription in the
   `Webhooks` widget.
2. **Read the `dead_letter` reason.** The
   `reason` column tells you the
   delivery was rejected because the
   `EnvironmentMode` bound was exceeded.
3. **Decide whether to retry.** The
   bounded `WebhookDispatcher` has
   already transitioned the delivery to
   `dead_letter`. To retry, the operator
   must use the `POST
   /admin/webhooks/deliveries/{id}/retry`
   endpoint. The retry will create a
   new `webhook_deliveries` row with
   `attempt_count = 1` and the bounded
   `next_attempt_at` reset to the
   current `now`.
4. **Verify the `EnvironmentMode` is
   correct.** If the bounded window is
   too short for the retry window,
   consider promoting the
   `EnvironmentMode` to `pilot_live` or
   extending the bounded window in a
   follow-on story.

## 6. Health Probe Contract

The bounded
`/admin/webhooks/*` endpoints are covered
by the health probe contract from
`US-040`: a missing or failing endpoint
must not fail `GET /health/ready`, only
surface as a degraded warning. If a health
probe returns a degraded warning, follow
the `PilotLiveCutover` runbook entry to
diagnose the underlying health probe
issue.

## 7. Escalation

If the underlying webhook delivery issue,
the underlying secret rotation issue, or
the underlying `EnvironmentMode` issue
cannot be resolved within the bounded
window, escalate to the next-level
on-call rotation. Provide the following
context:

- The affected `subscription_id`.
- The affected `delivery_id` (if
  applicable).
- The `event_type` and the bounded
  `attempt_count`.
- The `last_response_code` and
  `last_response_message`.
- The bounded `EnvironmentMode`.
- The `webhook.subscription.secret_rotated`
  audit entry (if applicable).
- The `webhook.delivery.dead_letter`
  audit entry (if applicable).

## 8. Related Runbooks

- `docs/ops/connector-auto-disable-runbook.md`
  — what an operator does when a
  connector flips to `auto_disabled`.
- `docs/ops/observability-runbook.md` —
  what an operator does when a
  `critical` alert fires.
- `docs/ops/pilot-live-cutover-runbook.md`
  — what an operator does during the
  real-environment cutover.
- `docs/ops/pilot-live-rollback-runbook.md`
  — what an operator does during the
  real-environment rollback.
