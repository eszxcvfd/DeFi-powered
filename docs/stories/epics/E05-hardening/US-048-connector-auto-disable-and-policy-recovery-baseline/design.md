# Design

## Domain Model

The first connector auto-disable and policy
recovery slice formalizes the durable objects,
bounded enums, and bounded services that turn
the implicit `FR-SRC-004` + `SPEC.md` 11.1
kill-switch requirements into a documented
contract.

### `ConnectorAutoDisableRule`

A single record of a per-source auto-disable
policy. The row carries enough information for
the bounded `AutoDisableService` to evaluate a
source against the closed trigger rules without
reading raw tables.

- `id`
- `organization_id`
- `source_id` (foreign key to
  `sources.id` from `US-003`)
- `trigger` (closed enum:
  `health_unhealthy`, `captcha_rate_breach`,
  `failure_rate_breach`,
  `needs_user_action_storm`, `error_spike`,
  `manual_kill_switch`)
- `threshold_value` (closed numeric, depends
  on the `trigger`; for
  `health_unhealthy` it is the closed
  `ConnectorHealthStatus` threshold; for
  `captcha_rate_breach` and
  `failure_rate_breach` it is a closed
  `[0.0, 1.0]` ratio; for
  `needs_user_action_storm` and `error_spike`
  it is a closed positive integer)
- `window_seconds` (closed positive integer,
  bounded by the `EnvironmentMode` from
  `US-040`: max 24 hours in `pilot_live`,
  max 1 hour in `test_like`)
- `consecutive_breaches` (closed positive
  integer, default `3`)
- `cooldown_seconds` (closed non-negative
  integer, default `900`)
- `enabled` (boolean, default `true`)
- `created_by` (foreign key to `users.id`)
- `created_at`
- `updated_at`

### `ConnectorAutoDisableEvent`

A single record of a per-event auto-disable
history. The table is bounded to the most
recent N events per source so a flapping
connector cannot fill the table.

- `id`
- `organization_id`
- `source_id` (foreign key to
  `sources.id` from `US-003`)
- `trigger` (closed enum, see above)
- `reason` (bounded to 500 characters; the
  secret-safe payload contract from `US-041`
  is enforced before persistence)
- `breach_count` (closed positive integer)
- `window_start`
- `window_end`
- `status` (closed enum: `active`,
  `recovering`, `resolved`, `superseded`)
- `alert_event_id` (nullable foreign key to
  `alert_events.id` from `US-041`)
- `health_snapshot_id` (nullable foreign key
  to `connector_health_snapshots.id` from
  `US-046`)
- `recovery_actor_id` (nullable foreign key
  to `users.id`)
- `recovery_reason` (nullable string, bounded
  to 500 characters; the secret-safe payload
  contract is enforced before persistence)
- `recovered_at` (nullable timestamp)
- `audit_correlation_id` (links the event row
  to the matching `AuditEntry` row)
- `created_at`

### `Source` extension

The existing `Source` row from `US-003` gains
three read-only fields. The bounded
`AutoDisableService` is the only writer.

- `auto_disabled_at` (nullable timestamp)
- `auto_disabled_reason` (nullable string,
  bounded to 500 characters; the secret-safe
  payload contract is enforced before
  persistence)
- `auto_disabled_by_event_id` (nullable
  foreign key to
  `connector_auto_disable_events.id`)

### `AutoDisableTrigger`

Closed enum that the bounded
`AutoDisableService` reads from the closed
`ConnectorHealthStatus` enum from `US-046` and
the closed `AlertMetric` enum from `US-041`:

- `health_unhealthy` — fires when the most
  recent `ConnectorHealthSnapshot.status` is
  `unhealthy`.
- `captcha_rate_breach` — fires when the most
  recent `ConnectorHealthSnapshot.captcha_rate`
  exceeds the rule's `threshold_value`.
- `failure_rate_breach` — fires when the most
  recent `ConnectorHealthSnapshot.success_rate`
  drops below `1.0 - threshold_value`.
- `needs_user_action_storm` — fires when the
  rolling `discovery.needs_user_action_rate`
  alert from `US-041` fires more than
  `consecutive_breaches` times in the
  `window_seconds` window.
- `error_spike` — fires when the rolling
  `connector.failure_rate` alert from `US-041`
  fires more than `consecutive_breaches` times
  in the `window_seconds` window.
- `manual_kill_switch` — owner/admin explicit
  trigger; the bounded
  `AutoDisableService` records the manual
  kill switch as an `active` event with
  `trigger = manual_kill_switch` and
  `reason = owner_or_admin_manual_action`.

### `AutoDisableEventStatus`

Closed enum that the bounded
`AutoDisableService` uses to track the
lifecycle of an auto-disable event:

- `active` — the event is the most recent
  active disable for the source; the source is
  currently `auto_disabled`.
- `recovering` — an owner/admin has issued
  the bounded `recover_source` action; the
  source remains `auto_disabled` until the
  next evaluation cycle returns `healthy` or
  `degraded` and the `cooldown_seconds` window
  has elapsed.
- `resolved` — the next evaluation cycle
  confirmed the source is `healthy` or
  `degraded`; the source is `enabled`.
- `superseded` — a new event replaced the
  current active event for the same source;
  the older event is preserved for audit.

### `AutoDisableThresholds`

Bounded dataclass that exposes the closed
default thresholds and the
`default_window_seconds` bound. The defaults
are read-only and locked in the decision
record:

- `default_health_unhealthy_threshold` =
  `ConnectorHealthStatus.unhealthy`
- `default_captcha_rate_breach_threshold` =
  `0.2`
- `default_failure_rate_breach_threshold` =
  `0.5`
- `default_needs_user_action_storm_threshold`
  = `3`
- `default_error_spike_threshold` = `3`
- `default_window_seconds` = `1800`
- `default_consecutive_breaches` = `3`
- `default_cooldown_seconds` = `900`
- `min_window_seconds` = `60`
- `max_window_seconds` = bounded by
  `EnvironmentMode` from `US-040` (24 hours
  in `pilot_live`, 1 hour in `test_like`)

### `AutoDisableService`

Bounded service that exposes the closed
operations:

- `evaluate_source(source_id, *, now=None)` —
  reads the most recent
  `ConnectorHealthSnapshot` row from `US-046`
  and the most recent matching `AlertEvent`
  rows from `US-041`, applies the closed
  trigger rules with the
  `consecutive_breaches` and
  `cooldown_seconds` bounds, returns the
  bounded `AutoDisableEvaluationResult`
  dataclass with `should_disable`,
  `trigger`, `reason`, `breach_count`,
  `window_start`, `window_end`,
  `alert_event_id`, and
  `health_snapshot_id`.
- `list_rules(*, source_id, enabled, limit,
  offset)` — paginated rule list with
  sanitized payloads.
- `create_rule(*, source_id, trigger,
  threshold_value, window_seconds,
  consecutive_breaches, cooldown_seconds,
  enabled)` — owner/admin only. Validates
  against the closed enums and the
  `EnvironmentMode` bound.
- `update_rule(*, rule_id, ...)` —
  owner/admin only. Validates against the
  closed enums.
- `delete_rule(*, rule_id)` — owner/admin
  only. Soft-deletes the rule.
- `list_events(*, source_id, status, limit,
  offset)` — paginated event history with
  sanitized payloads.
- `recover_source(*, source_id, *,
  event_id, reason)` — owner/admin only.
  Transitions the matching
  `ConnectorAutoDisableEvent` row from
  `active` to `recovering`, then to
  `resolved` after the next evaluation cycle
  returns `healthy` or `degraded` and the
  `cooldown_seconds` window has elapsed.
  Emits the
  `connector.auto_disable.recovered` audit
  entry.

### `AutoDisableEvaluator`

Bounded helper that owns the trigger rule
evaluation, the `consecutive_breaches`
counter, the `cooldown_seconds` window, and
the bounded window helper. The helper is
pure; it does not touch the database or the
audit log.

### `AutoDisableOrchestrator`

Bounded actor that runs from a periodic
worker tick and from the
`POST /discovery-jobs` boundary. The actor
calls `AutoDisableService.evaluate_source`
for every source with at least one enabled
rule, transitions `Source.enabled` to
`false` when the trigger fires, and emits
the `connector.auto_disable.triggered`
audit entry.

### `evaluate_source_for_discovery`

Source-side helper that the orchestrator
from `US-004` / `US-032` / `US-033` /
`US-034` calls before a job is dispatched.
The helper returns `RUN_ALLOWED`,
`RUN_AUTO_DISABLED`, or `RUN_MANUAL_DISABLED`
and the matching reason. The helper refuses
to run a discovery job against an
`auto_disabled` source even when the manual
`enabled` flag is `true`; the manual
`enabled` flag is preserved as a separate
signal.

## Bounded Evaluation Algorithm

The bounded evaluation algorithm reads the
most recent `ConnectorHealthSnapshot` row
and the most recent matching `AlertEvent`
rows, applies the closed trigger rules, and
returns a deterministic result. The
algorithm is:

```text
for each enabled rule in source.rules:
  signals = read_signals(rule, source, now)
  breach_count = count_consecutive_breaches(
    rule, signals, window_seconds)
  if breach_count < consecutive_breaches:
    continue
  if in_cooldown(rule, source, now):
    continue
  return AutoDisableEvaluationResult(
    should_disable=True,
    trigger=rule.trigger,
    reason=format_reason(rule, signals),
    breach_count=breach_count,
    window_start=...,
    window_end=...,
    alert_event_id=...,
    health_snapshot_id=...)

return AutoDisableEvaluationResult(
  should_disable=False,
  trigger=None,
  reason=None,
  breach_count=0,
  window_start=None,
  window_end=None,
  alert_event_id=None,
  health_snapshot_id=None)
```

The bounded `cooldown_seconds` window
prevents flapping: once a rule fires, the
rule is suppressed for `cooldown_seconds`
seconds before it can fire again. The
`consecutive_breaches` counter requires
multiple breaches in a row before the rule
fires; a single transient breach does not
disable a source.

## Bounded Recovery Flow

The bounded recovery flow is
human-confirmed:

1. An owner/admin issues
   `POST
   /admin/connectors/auto-disable/events/{id}/recover`
   with a `reason` body.
2. The bounded `AutoDisableService` validates
   the session, the role, the tenant scope,
   and the event id.
3. The bounded `AutoDisableService`
   transitions the `ConnectorAutoDisableEvent`
   row from `active` to `recovering` and
   emits the
   `connector.auto_disable.recovered` audit
   entry.
4. The next evaluation cycle confirms the
   source is `healthy` or `degraded` and the
   `cooldown_seconds` window has elapsed.
5. The bounded `AutoDisableService`
   transitions the event to `resolved`,
   sets `Source.enabled = true`, and
   clears `Source.auto_disabled_at`,
   `Source.auto_disabled_reason`, and
   `Source.auto_disabled_by_event_id`.
6. The bounded `AutoDisableService` emits
   the
   `connector.auto_disable.recovery.resolved`
   audit entry.

If the next evaluation cycle returns
`unhealthy`, the bounded
`AutoDisableService` re-disables the source
and emits the
`connector.auto_disable.recovery.rejected`
audit entry.

## Bounded Window Bound

The bounded window is enforced by the
`EnvironmentMode` from `US-040`:

- `pilot_live` — `max_window_seconds = 24 *
  3600` (24 hours).
- `test_like` — `max_window_seconds = 3600`
  (1 hour).

The `AutoDisableService.create_rule` and
`update_rule` operations clip the
`window_seconds` value to the bound. A
`window_seconds` value that exceeds the
bound is rejected with
`AUTO_DISABLE_RULE_INVALID_WINDOW`.

## Sanitization Contract

The bounded `AutoDisableService` and
`AutoDisableOrchestrator` reuse the
`SanitizeAlertPayload` helper from `US-041`
for every rule, event, and audit entry
before persistence. The helper rejects or
redacts API keys, cookies, raw PII, browser
storage state, and full connection strings.

A rule, event, or audit entry that fails the
sanitization is rejected with
`AUTO_DISABLE_RULE_INVALID_PAYLOAD`,
`AUTO_DISABLE_EVENT_INVALID_PAYLOAD`, or
`AUTO_DISABLE_AUDIT_INVALID_PAYLOAD`. The
rejection is recorded in the audit log with
the `connector.auto_disable.evaluation.rejected`
action.

## Audit Entry Shape

The bounded `AutoDisableService` and
`AutoDisableOrchestrator` emit the
following audit entries, all using the
existing `AuditEntry` contract from `US-026`:

- `connector.auto_disable.rule.created` —
  action, actor, `rule_id`, `source_id`,
  `trigger`, `threshold_value`,
  `window_seconds`,
  `consecutive_breaches`,
  `cooldown_seconds`, `enabled`.
- `connector.auto_disable.rule.updated` —
  action, actor, `rule_id`, `source_id`,
  before/after diff.
- `connector.auto_disable.rule.deleted` —
  action, actor, `rule_id`, `source_id`.
- `connector.auto_disable.triggered` —
  action, actor (system or owner/admin for
  manual kill switch), `event_id`,
  `source_id`, `trigger`, `reason`,
  `breach_count`, `window_start`,
  `window_end`, `alert_event_id`,
  `health_snapshot_id`.
- `connector.auto_disable.recovered` —
  action, actor, `event_id`, `source_id`,
  `recovery_reason`.
- `connector.auto_disable.recovery.resolved`
  — action, actor (system), `event_id`,
  `source_id`.
- `connector.auto_disable.recovery.rejected`
  — action, actor (system), `event_id`,
  `source_id`, `trigger`, `reason`.
- `connector.auto_disable.evaluation.rejected`
  — action, actor, `source_id`, `trigger`,
  `reason` (sanitization rejection, window
  rejection, or invalid enum value).

## API Contract

The new owner/admin-only REST surface:

- `GET
  /admin/connectors/auto-disable/rules?source_id=&enabled=&limit=&offset=`
  — returns paginated rule list with
  sanitized payloads.
- `POST
  /admin/connectors/auto-disable/rules` —
  body shape:
  ```json
  {
    "source_id": "src_01...",
    "trigger": "health_unhealthy",
    "threshold_value": 0.5,
    "window_seconds": 1800,
    "consecutive_breaches": 3,
    "cooldown_seconds": 900,
    "enabled": true
  }
  ```
  Returns the created rule with the
  sanitized payload.
- `GET
  /admin/connectors/auto-disable/rules/{id}`
  — returns a single rule with the
  sanitized payload.
- `PATCH
  /admin/connectors/auto-disable/rules/{id}`
  — body shape: same as create. Updates
  threshold, window,
  `consecutive_breaches`,
  `cooldown_seconds`, and `enabled` state.
- `DELETE
  /admin/connectors/auto-disable/rules/{id}`
  — soft-deletes the rule.
- `GET
  /admin/connectors/auto-disable/events?source_id=&status=&limit=&offset=`
  — returns paginated event history with
  sanitized payloads.
- `POST
  /admin/connectors/auto-disable/events/{id}/recover`
  — body shape:
  ```json
  {
    "reason": "Operator confirmed the source is healthy and ready to re-enable."
  }
  ```
  Transitions the event to `recovering` and
  writes the audit entry.
- `POST
  /admin/connectors/{source_id}/auto-disable/evaluate`
  — triggers a single bounded evaluation
  cycle for the source and returns the
  result inline.

All new error responses follow the existing
error envelope (`code`, `message`,
`request_id`, `details`):

- `AUTO_DISABLE_RULE_INVALID` — invalid
  rule payload (unknown `trigger`, invalid
  `threshold_value`, invalid
  `window_seconds`, invalid
  `consecutive_breaches`, invalid
  `cooldown_seconds`).
- `AUTO_DISABLE_RULE_INVALID_WINDOW` —
  `window_seconds` exceeds the
  `EnvironmentMode` bound.
- `AUTO_DISABLE_RULE_INVALID_PAYLOAD` —
  sanitization rejection.
- `AUTO_DISABLE_EVENT_NOT_FOUND` — event
  id not found in the tenant scope.
- `AUTO_DISABLE_RECOVERY_REJECTED` —
  recovery action denied (event not
  `active`, `cooldown_seconds` not
  elapsed, source is `unhealthy`).
- `AUTO_DISABLE_SNAPSHOT_MISSING` — no
  `ConnectorHealthSnapshot` rows for the
  source.
- `AUTO_DISABLE_ALERT_MISSING` — no
  matching `AlertEvent` rows for the
  source.
- `SOURCE_AUTO_DISABLED` — the
  source-side helper returns this code
  when the source is `auto_disabled`; the
  orchestrator from `US-004` /
  `US-032` / `US-033` / `US-034` reads
  this code and refuses to dispatch a
  discovery job.

## UI Surface

The new operator panel widget renders:

- A per-source rule list with the
  `AutoDisableTrigger` badge, the
  threshold value, the window, the
  `consecutive_breaches`, the
  `cooldown_seconds`, and the `enabled`
  state.
- A per-source event list with the
  `AutoDisableEventStatus` badge, the
  trigger, the reason, the breach count,
  the window, the `alert_event_id`, the
  `health_snapshot_id`, the recovery
  actor, and the recovery reason.
- A `Recover` button for each `active`
  event. The button opens a confirmation
  dialog that captures the recovery
  reason and calls
  `POST
  /admin/connectors/auto-disable/events/{id}/recover`.
- A `Compute evaluation` button per source
  that calls
  `POST
  /admin/connectors/{source_id}/auto-disable/evaluate`
  and shows the result inline.
- A `Create rule` button that opens a
  modal with the rule form.

The widget reuses the existing settings and
inbox surfaces from `US-026` and `US-029`.

## Affected Existing Code Paths

The bounded slice touches the following
existing code paths. Each touch is
explicitly bounded:

- `src/livelead/domain/sources/`
  (`US-003` source registry) — extend the
  `Source` row with `auto_disabled_at`,
  `auto_disabled_reason`, and
  `auto_disabled_by_event_id`.
- `src/livelead/domain/observability/`
  (`US-041` alerting) — read the
  `AlertEvent` rows from the bounded
  `AutoDisableEvaluator`; reuse the
  `SanitizeAlertPayload` helper.
- `src/livelead/domain/connector_health/`
  (`US-046` connector health) — read the
  `ConnectorHealthSnapshot` rows from the
  bounded `AutoDisableEvaluator`; reuse
  the closed `ConnectorHealthStatus` enum.
- `src/livelead/runtime/environment/`
  (`US-040` environment mode) — read the
  `EnvironmentMode` from the bounded
  `AutoDisableService` for the bounded
  window.
- `src/livelead/domain/audit/`
  (`US-026` audit log) — emit the
  `connector.auto_disable.*` audit entries
  via the existing `AuditService`.
- `apps/api/orchestrator/` (`US-004` /
  `US-032` / `US-033` / `US-034` discovery
  orchestrator) — call the bounded
  `evaluate_source_for_discovery` helper
  before dispatching a job.
- `apps/api/main.py` — register the new
  admin endpoints.
- `frontend/src/pages/AdminConnectors.tsx`
  — render the new operator panel widget.
- `frontend/src/api/auto_disable.ts` — new
  API client for the new admin endpoints.
