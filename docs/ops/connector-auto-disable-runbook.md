# Connector Auto-Disable And Policy Recovery Runbook

Source: `docs/product/connector-auto-disable-and-recovery.md`,
`docs/decisions/0026-connector-auto-disable-and-policy-recovery-baseline.md`,
and the runtime contracts established by
`US-003` (source registry), `US-026` (audit
log), `US-040` (real-environment cutover),
`US-041` (operational observability and
alerting), and `US-046` (connector health
surface).

This runbook entry documents what an
operator on call for the pilot-live
environment does when:

- A source flips to `auto_disabled`.
- A `captcha_rate_breach` fires.
- A `failure_rate_breach` fires.
- A `needs_user_action_storm` fires.
- A `manual_kill_switch` is issued.
- A recovery action is denied because the
  cooldown has not elapsed.
- The bounded evaluation rejects a signal
  (sanitization rejection, window
  rejection, invalid enum value).

## 1. When A Source Flips To `auto_disabled`

### Symptoms

- A `connector.auto_disable.triggered`
  audit entry is recorded with
  `trigger` set to one of
  `health_unhealthy`, `captcha_rate_breach`,
  `failure_rate_breach`,
  `needs_user_action_storm`, `error_spike`,
  or `manual_kill_switch`.
- The `Source.enabled` flag for the affected
  source is set to `false`; the
  `Source.auto_disabled_at` timestamp is
  populated; the
  `Source.auto_disabled_reason` is populated.
- The bounded source-side helper
  `evaluate_source_for_discovery` returns
  `RUN_AUTO_DISABLED` for the affected
  source.
- The orchestrator from `US-004` /
  `US-032` / `US-033` / `US-034` reads the
  bounded rejection code
  `SOURCE_AUTO_DISABLED` and refuses to
  dispatch a discovery job against the
  affected source.
- The in-app inbox from `US-029` shows the
  auto-disable event with a dedicated
  trigger icon and a deep link to the
  event detail in the operator panel.

### Steps

1. **Open the operator panel.** Navigate
   to `AdminConnectors` and locate the
   affected source in the
   `Auto-disable rules` and
   `Auto-disable events` widgets.
2. **Read the trigger.** The trigger badge
   on the event row tells you which
   signal fired. The `health_snapshot_id`
   and `alert_event_id` columns link to
   the matching `ConnectorHealthSnapshot`
   row from `US-046` and the matching
   `AlertEvent` row from `US-041`.
3. **Read the breach count and window.**
   The `breach_count`, `window_start`, and
   `window_end` columns tell you how many
   consecutive breaches fired in the
   bounded window.
4. **Diagnose the root cause.** Use the
   `ConnectorHealthSurface` runbook entry
   to diagnose the underlying connector
   health issue. Use the
   `ObservabilityAndAlerting` runbook
   entry to diagnose the underlying alert
   issue.
5. **Decide whether to recover.** If the
   underlying issue is fixed and the
   bounded `cooldown_seconds` window has
   elapsed, issue the bounded recovery
   action. If the underlying issue is
   not fixed, leave the source in
   `auto_disabled` state and continue
   diagnosis.
6. **Issue the bounded recovery action.**
   Click the `Recover` button on the
   event row. The button opens a
   confirmation dialog that captures the
   recovery reason. The bounded
   `AutoDisableService` transitions the
   event to `recovering` and emits the
   `connector.auto_disable.recovered`
   audit entry.
7. **Wait for the next evaluation cycle.**
   The bounded `AutoDisableOrchestrator`
   actor runs from a periodic worker tick
   (the existing scheduler from
   `US-035`). The next evaluation cycle
   confirms the source is `healthy` or
   `degraded` and the
   `cooldown_seconds` window has elapsed.
   The bounded `AutoDisableService`
   transitions the event to `resolved`,
   sets `Source.enabled = true`, and
   clears `Source.auto_disabled_at`,
   `Source.auto_disabled_reason`, and
   `Source.auto_disabled_by_event_id`.
8. **Confirm the recovery.** The
   `connector.auto_disable.recovery.resolved`
   audit entry is recorded. The
   `Source.enabled` flag is `true`. The
   `Source.auto_disabled_at`,
   `Source.auto_disabled_reason`, and
   `Source.auto_disabled_by_event_id`
   fields are `null`. The bounded
   source-side helper
   `evaluate_source_for_discovery`
   returns `RUN_ALLOWED` for the
   affected source.

## 2. When A `captcha_rate_breach` Fires

### Symptoms

- A `connector.auto_disable.triggered`
  audit entry is recorded with
  `trigger = captcha_rate_breach`.
- The `ConnectorHealthSnapshot.captcha_rate`
  from `US-046` exceeds the rule's
  `threshold_value` for at least
  `consecutive_breaches` evaluation cycles
  in the `window_seconds` window.

### Steps

1. **Open the operator panel.** Navigate
   to `AdminConnectors` and locate the
   affected source in the
   `Auto-disable events` widget.
2. **Read the breach count and window.**
   The `breach_count`, `window_start`, and
   `window_end` columns tell you how many
   consecutive breaches fired in the
   bounded window.
3. **Diagnose the CAPTCHA rate.** Use the
   `ConnectorHealthSurface` runbook entry
   to diagnose the underlying CAPTCHA
   rate issue. The CAPTCHA rate is
   derived from the
   `connector_health_snapshots.captcha_rate`
   column from `US-046`.
4. **Decide whether to recover.** If the
   CAPTCHA rate is back below the rule's
   `threshold_value` and the bounded
   `cooldown_seconds` window has elapsed,
   issue the bounded recovery action. If
   the CAPTCHA rate is still above the
   threshold, leave the source in
   `auto_disabled` state and continue
   diagnosis.

## 3. When A `failure_rate_breach` Fires

### Symptoms

- A `connector.auto_disable.triggered`
  audit entry is recorded with
  `trigger = failure_rate_breach`.
- The `ConnectorHealthSnapshot.success_rate`
  from `US-046` drops below
  `1.0 - threshold_value` for at least
  `consecutive_breaches` evaluation cycles
  in the `window_seconds` window.

### Steps

1. **Open the operator panel.** Navigate
   to `AdminConnectors` and locate the
   affected source in the
   `Auto-disable events` widget.
2. **Read the breach count and window.**
   The `breach_count`, `window_start`, and
   `window_end` columns tell you how many
   consecutive breaches fired in the
   bounded window.
3. **Diagnose the failure rate.** Use the
   `ConnectorHealthSurface` runbook entry
   to diagnose the underlying failure
   rate issue. The failure rate is
   derived from the
   `connector_health_snapshots.success_rate`
   column from `US-046`.
4. **Decide whether to recover.** If the
   failure rate is back below the rule's
   `threshold_value` and the bounded
   `cooldown_seconds` window has elapsed,
   issue the bounded recovery action. If
   the failure rate is still above the
   threshold, leave the source in
   `auto_disabled` state and continue
   diagnosis.

## 4. When A `needs_user_action_storm` Fires

### Symptoms

- A `connector.auto_disable.triggered`
  audit entry is recorded with
  `trigger = needs_user_action_storm`.
- The `discovery.needs_user_action_rate`
  alert from `US-041` fires more than
  `consecutive_breaches` times in the
  `window_seconds` window.

### Steps

1. **Open the operator panel.** Navigate
   to `AdminConnectors` and locate the
   affected source in the
   `Auto-disable events` widget.
2. **Read the breach count and window.**
   The `breach_count`, `window_start`, and
   `window_end` columns tell you how many
   consecutive breaches fired in the
   bounded window.
3. **Diagnose the
   `NEEDS_USER_ACTION` storm.** Use the
   `ObservabilityAndAlerting` runbook
   entry to diagnose the underlying
   `NEEDS_USER_ACTION` issue. The
   `NEEDS_USER_ACTION` rate is derived
   from the `discovery_jobs.status`
   transitions.
4. **Decide whether to recover.** If the
   `NEEDS_USER_ACTION` rate is back below
   the rule's `threshold_value` and the
   bounded `cooldown_seconds` window has
   elapsed, issue the bounded recovery
   action. If the `NEEDS_USER_ACTION`
   rate is still above the threshold,
   leave the source in `auto_disabled`
   state and continue diagnosis.

## 5. When A `manual_kill_switch` Is Issued

### Symptoms

- A `connector.auto_disable.triggered`
  audit entry is recorded with
  `trigger = manual_kill_switch` and
  `reason = owner_or_admin_manual_action`.
- The `Source.enabled` flag for the
  affected source is set to `false`; the
  `Source.auto_disabled_at` timestamp is
  populated; the
  `Source.auto_disabled_reason` is
  populated with the
  `owner_or_admin_manual_action` reason.

### Steps

1. **Open the operator panel.** Navigate
   to `AdminConnectors` and locate the
   affected source in the
   `Auto-disable events` widget.
2. **Read the actor and the reason.** The
   `recovery_actor_id` (nullable at this
   point) and the `recovery_reason`
   (nullable at this point) tell you who
   issued the manual kill switch and why.
3. **Decide whether to recover.** If the
   manual kill switch is no longer
   needed, issue the bounded recovery
   action. If the manual kill switch is
   still needed, leave the source in
   `auto_disabled` state and continue
   diagnosis.

## 6. When A Recovery Action Is Denied

### Symptoms

- A `POST
  /admin/connectors/auto-disable/events/{id}/recover`
  call returns
  `AUTO_DISABLE_RECOVERY_REJECTED` with a
  reason.
- A
  `connector.auto_disable.recovery.rejected`
  audit entry is recorded with
  `trigger`, `reason`, and
  `rejection_reason`.

### Steps

1. **Read the rejection reason.** The
   `rejection_reason` tells you why the
   recovery action was denied. The
   bounded reasons are:
   - `event_not_active` — the event is
     not in `active` state. The event
     must be in `active` state for the
     recovery action to succeed.
   - `cooldown_not_elapsed` — the
     bounded `cooldown_seconds` window
     has not elapsed. Wait for the
     `cooldown_seconds` window to
     elapse and try again.
   - `source_unhealthy` — the next
     evaluation cycle returned
     `unhealthy`. Investigate the
     underlying connector health issue
     before retrying the recovery
     action.
2. **Take the corrective action.** Follow
   the corrective action for the specific
   rejection reason. For
   `event_not_active`, find the active
   event for the source and issue the
   recovery action on the active event.
   For `cooldown_not_elapsed`, wait for
   the `cooldown_seconds` window to
   elapse and try again. For
   `source_unhealthy`, investigate the
   underlying connector health issue
   before retrying the recovery action.
3. **Retry the recovery action.** Once
   the corrective action is taken,
   retry the bounded recovery action.

## 7. When The Bounded Evaluation Rejects A Signal

### Symptoms

- A `POST
  /admin/connectors/{source_id}/auto-disable/evaluate`
  call returns
  `AUTO_DISABLE_RULE_INVALID_PAYLOAD`,
  `AUTO_DISABLE_EVENT_INVALID_PAYLOAD`, or
  `AUTO_DISABLE_AUDIT_INVALID_PAYLOAD`
  with a reason.
- A
  `connector.auto_disable.evaluation.rejected`
  audit entry is recorded with
  `trigger`, `reason`, and
  `rejection_reason`.

### Steps

1. **Read the rejection reason.** The
   `rejection_reason` tells you why the
   evaluation was rejected. The bounded
   reasons are:
   - `sanitization_rejection` — the
     rule, event, or audit entry
     carries an API key, a cookie, raw
     PII, browser storage state, or a
     full connection string. The
     `SanitizeAlertPayload` helper from
     `US-041` rejected the payload.
   - `window_rejection` — the
     `window_seconds` value exceeds
     the `EnvironmentMode` bound from
     `US-040`. The bounded
     `AutoDisableService` clipped the
     window to the bound and recorded
     the rejection.
   - `invalid_enum_value` — the
     `trigger` value is not in the
     closed `AutoDisableTrigger` enum.
     The bounded `AutoDisableService`
     rejected the rule.
2. **Take the corrective action.** Follow
   the corrective action for the specific
   rejection reason. For
   `sanitization_rejection`, fix the
   payload and retry the evaluation. For
   `window_rejection`, lower the
   `window_seconds` value to fit the
   `EnvironmentMode` bound and retry the
   evaluation. For `invalid_enum_value`,
   fix the `trigger` value to a closed
   enum value and retry the evaluation.
3. **Retry the evaluation.** Once the
   corrective action is taken, retry
   the bounded evaluation.

## 8. Health Probe Contract

The bounded `/admin/connectors/auto-disable/*`
endpoints are covered by the health probe
contract from `US-040`: a missing or failing
endpoint must not fail `GET /health/ready`,
only surface as a degraded warning. If a
health probe returns a degraded warning,
follow the `PilotLiveCutover` runbook entry
to diagnose the underlying health probe
issue.

## 9. Escalation

If the underlying connector health issue,
the underlying alert issue, or the underlying
`NEEDS_USER_ACTION` issue cannot be resolved
within the bounded `cooldown_seconds`
window, escalate to the next-level on-call
rotation. Provide the following context:

- The affected source id.
- The trigger type
  (`health_unhealthy`,
  `captcha_rate_breach`,
  `failure_rate_breach`,
  `needs_user_action_storm`,
  `error_spike`, or
  `manual_kill_switch`).
- The breach count and the bounded
  window.
- The `health_snapshot_id` and
  `alert_event_id` (if applicable).
- The bounded recovery action history
  (if any).
- The bounded evaluation rejection
  history (if any).

## 10. Related Runbooks

- `docs/ops/connector-health-runbook.md`
  — what an operator does when a
  connector flips to `degraded` or
  `unhealthy`, when a CAPTCHA rate
  breaches the threshold, and when a
  user reports a missing connector.
- `docs/ops/observability-runbook.md`
  — what an operator does when a
  `critical` alert fires.
- `docs/ops/pilot-live-cutover-runbook.md`
  — what an operator does during the
  real-environment cutover.
- `docs/ops/pilot-live-rollback-runbook.md`
  — what an operator does during the
  real-environment rollback.
