# Connector Auto-Disable And Policy Recovery

Source: `SPEC.md` sections 5.3 (`FR-SRC-001..007`),
11 (browser automation and responsible use),
14.1, 14.2, and 20; the durable decisions
`0019-observability-and-alerting-baseline`,
`0024-connector-health-surface-baseline`, and
the runtime contracts established by `US-003`,
`US-026`, `US-040`, `US-041`, and `US-046`.

## Product Goal

Owners, admins, operators on call, analysts,
and sales/BD users need a bounded
connector auto-disable and policy recovery
surface that closes the operational gap
between "alert fires" and "source actually
stops running" without weakening the
`FR-SRC-004` source policy enforcement, the
`US-041` alerting contract, the `US-046`
connector health contract, the `US-040`
real-environment cutover contract, the
`US-026` audit log contract, or the `US-003`
source registry contract.

The MVP already depends on a manual
`Source.enabled` flag from `US-003`, an
`AlertEvaluator` that is read-only with
respect to product state from `US-041`, a
`ConnectorHealthService` that reports a
closed `ConnectorHealthStatus` enum from
`US-046`, a `SanitizeAlertPayload` helper
shared with the audit log from `US-041`, and
an `EnvironmentMode` from `US-040` that
bounds the evaluation window.

This product slice is the first step toward
turning the implicit `FR-SRC-004` and
`SPEC.md` 11.1 kill-switch requirements into
a documented contract, a durable
`connector_auto_disable_rules` and
`connector_auto_disable_events` pair, a
closed `AutoDisableTrigger` enum, a closed
`AutoDisableEventStatus` enum, a bounded
`AutoDisableService`, a bounded
`AutoDisableEvaluator`, a bounded
`AutoDisableOrchestrator`, a bounded
source-side helper, and a human-confirmed
recovery flow.

The slice is local-first by design. It does
not commit to a specific external runbook
service (PagerDuty, Opsgenie, a managed
Slack channel) in this step; it preserves a
stable seam for a later hardening story to
wire one.

## MVP Scope

This product slice covers:

- A durable `connector_auto_disable_rules`
  table with `id`, `organization_id`,
  `source_id`, `trigger` (closed enum),
  `threshold_value`, `window_seconds`,
  `consecutive_breaches`,
  `cooldown_seconds`, `enabled`,
  `created_by`, `created_at`, and
  `updated_at`.
- A durable `connector_auto_disable_events`
  table with `id`, `organization_id`,
  `source_id`, `trigger`, `reason`,
  `breach_count`, `window_start`,
  `window_end`, `status` (closed enum),
  `alert_event_id`,
  `health_snapshot_id`,
  `recovery_actor_id`, `recovery_reason`,
  `recovered_at`, `audit_correlation_id`,
  and `created_at`. The table is bounded
  to the most recent N events per source
  so a flapping connector cannot fill the
  table.
- A `Source` extension with
  `auto_disabled_at` (nullable timestamp),
  `auto_disabled_reason` (nullable string,
  bounded to 500 characters), and
  `auto_disabled_by_event_id` (nullable
  foreign key to
  `connector_auto_disable_events.id`).
  These fields are read-only from the
  domain side and only updated by the
  bounded `AutoDisableService`.
- A closed `AutoDisableTrigger` enum
  (`health_unhealthy`, `captcha_rate_breach`,
  `failure_rate_breach`,
  `needs_user_action_storm`, `error_spike`,
  `manual_kill_switch`) that the bounded
  `AutoDisableService` reads from the
  closed `ConnectorHealthStatus` enum from
  `US-046` and the closed `AlertMetric`
  enum from `US-041`.
- A closed `AutoDisableEventStatus` enum
  (`active`, `recovering`, `resolved`,
  `superseded`) that the bounded
  `AutoDisableService` uses to track the
  lifecycle of an auto-disable event.
- A bounded `AutoDisableThresholds`
  dataclass that exposes the closed default
  thresholds and the
  `default_window_seconds` bound. The
  defaults are read-only and locked in
  the decision record.
- A bounded `AutoDisableService` with
  `evaluate_source`, `list_rules`,
  `create_rule`, `update_rule`,
  `delete_rule`, `list_events`, and
  `recover_source`.
- A bounded `AutoDisableEvaluator` that
  owns the trigger rule evaluation, the
  `consecutive_breaches` counter, the
  `cooldown_seconds` window, and the
  bounded window helper.
- A bounded `AutoDisableOrchestrator` that
  runs from a periodic worker tick (the
  existing scheduler from `US-035`) and
  from the `POST /discovery-jobs`
  boundary.
- A bounded source-side helper
  `evaluate_source_for_discovery` that
  the orchestrator from `US-004` /
  `US-032` / `US-033` / `US-034` calls
  before a job is dispatched. The helper
  returns `RUN_ALLOWED`, `RUN_AUTO_DISABLED`,
  or `RUN_MANUAL_DISABLED` and the
  matching reason.
- A bounded `AutoDisableRecoveryFlow` that
  is human-confirmed: an owner/admin
  issues
  `POST
  /admin/connectors/auto-disable/events/{id}/recover`
  with a `reason` body, the bounded
  `AutoDisableService` transitions the
  event to `recovering`, and the next
  evaluation cycle transitions the event
  to `resolved` and clears
  `Source.auto_disabled_at`,
  `Source.auto_disabled_reason`, and
  `Source.auto_disabled_by_event_id`.
- New bounded owner/admin-only REST
  surface:
  - `GET
    /admin/connectors/auto-disable/rules`
  - `POST
    /admin/connectors/auto-disable/rules`
  - `GET
    /admin/connectors/auto-disable/rules/{id}`
  - `PATCH
    /admin/connectors/auto-disable/rules/{id}`
  - `DELETE
    /admin/connectors/auto-disable/rules/{id}`
  - `GET
    /admin/connectors/auto-disable/events`
  - `POST
    /admin/connectors/auto-disable/events/{id}/recover`
  - `POST
    /admin/connectors/{source_id}/auto-disable/evaluate`
- New bounded operator panel widget that
  lists the latest auto-disable rules and
  events per source, shows the trigger
  badge and the status badge, and exposes
  a `Recover` button for each `active`
  event.
- New audit entry types:
  `connector.auto_disable.rule.created`,
  `connector.auto_disable.rule.updated`,
  `connector.auto_disable.rule.deleted`,
  `connector.auto_disable.triggered`,
  `connector.auto_disable.recovered`,
  `connector.auto_disable.recovery.resolved`,
  `connector.auto_disable.recovery.rejected`,
  and
  `connector.auto_disable.evaluation.rejected`.

This product slice does not yet cover:

- Distributed auto-disable coordination.
- External runbook automation (PagerDuty,
  Opsgenie, Slack auto-recovery).
- Auto-recovery. The bounded recovery
  flow is human-confirmed; the slice does
  not auto-flip a source back to `enabled`.
- Per-tenant rule templates.
- Customer-facing status pages or external
  incident communication.
- Replacing the existing source registry
  from `US-003`. This story extends the
  `Source` row with auto-disable metadata;
  it does not redefine the source
  registry, the policy evaluation, or the
  manual `enabled` / `disabled` flow.
- Replacing the existing observability and
  alerting surface from `US-041`. This
  story consumes the `AlertEvent` rows
  and the `SanitizeAlertPayload` helper;
  it does not redefine the `AlertRule` or
  `AlertEvent` contract; the bounded
  `AutoDisableOrchestrator` is read-only
  with respect to alert state.
- Replacing the existing connector health
  surface from `US-046`. This story
  consumes the `ConnectorHealthSnapshot`
  rows and the closed
  `ConnectorHealthStatus` enum; it does
  not redefine the snapshot shape or the
  bounded computation algorithm.
- Replacing the existing audit log from
  `US-026`. This story extends the audit
  entry shape with
  `connector.auto_disable.*`; it does not
  redefine the `AuditEntryRow` or the
  audit retention guarantee.
- Replacing the existing real-environment
  cutover from `US-040`. This story
  consumes the `EnvironmentMode` from
  `US-040`; it does not redefine the
  launch-gate seam.
- Replacing the existing discovery job
  lifecycle from `US-004`. This story
  extends the orchestrator seam with the
  bounded source-side helper; it does not
  redefine the job state machine.

## Contract Rules

- All new admin endpoints require an
  authenticated session with `owner` or
  `admin` role. Viewer, analyst, sales,
  and reviewer roles get no auto-disable
  surface and cannot manage rules or
  trigger a recovery.
- Every rule create / update / delete,
  every trigger, every recovery, and every
  rejected evaluation must pass
  `SanitizeAlertPayload` from `US-041`
  before persistence. The helper rejects
  or redacts API keys, cookies, raw PII,
  browser storage state, and full
  connection strings.
- The bounded `AutoDisableOrchestrator` is
  read-only with respect to alert state.
  It persists `AutoDisableEvent` rows and
  flips `Source.enabled` when a trigger
  fires; it does not modify `AlertRule` or
  `AlertEvent` rows.
- The bounded `cooldown_seconds` window
  prevents flapping: once a rule fires,
  the rule is suppressed for
  `cooldown_seconds` seconds before it
  can fire again. The
  `consecutive_breaches` counter requires
  multiple breaches in a row before the
  rule fires; a single transient breach
  does not disable a source.
- The bounded window is enforced by the
  `EnvironmentMode` from `US-040`
  (max 24 hours in `pilot_live`, max 1
  hour in `test_like`); a
  `window_seconds` value that exceeds the
  bound is clipped to the bound and
  recorded in the audit log with the
  `connector.auto_disable.evaluation.rejected`
  action.
- The bounded `AutoDisableTrigger` and
  `AutoDisableEventStatus` enums are
  closed. Adding a new value is an
  explicit follow-up story; the first
  slice ships only the values listed
  above.
- The bounded recovery flow is
  human-confirmed. The slice does not
  auto-flip a source back to `enabled`.
  An owner/admin must issue
  `POST
  /admin/connectors/auto-disable/events/{id}/recover`
  with a `reason` body.
- The source-side helper
  `evaluate_source_for_discovery` is
  called from the orchestrator seam
  before a job is dispatched. The helper
  returns `RUN_ALLOWED`,
  `RUN_AUTO_DISABLED`, or
  `RUN_MANUAL_DISABLED` and the matching
  reason. The helper refuses to run a
  discovery job against an
  `auto_disabled` source even when the
  manual `enabled` flag is `true`; the
  manual `enabled` flag is preserved as a
  separate signal.
- The bounded `/admin/connectors/auto-disable/*`
  endpoints are covered by the health
  probe contract: a missing or failing
  endpoint must not fail
  `GET /health/ready`, only surface as a
  degraded warning.

## Closed Enumerations

### `AutoDisableTrigger`

| Value | Source | Default Threshold |
| --- | --- | --- |
| `health_unhealthy` | `ConnectorHealthStatus.unhealthy` from `US-046` | n/a (status match) |
| `captcha_rate_breach` | `ConnectorHealthSnapshot.captcha_rate` from `US-046` | `0.2` |
| `failure_rate_breach` | `1.0 - ConnectorHealthSnapshot.success_rate` from `US-046` | `0.5` |
| `needs_user_action_storm` | `AlertEvent` from `US-041` with `metric = discovery.needs_user_action_rate` and `severity >= warning` | `3` breaches |
| `error_spike` | `AlertEvent` from `US-041` with `metric = connector.failure_rate` and `severity >= warning` | `3` breaches |
| `manual_kill_switch` | owner/admin explicit trigger | n/a (manual) |

### `AutoDisableEventStatus`

| Value | Meaning |
| --- | --- |
| `active` | The event is the most recent active disable for the source; the source is currently `auto_disabled`. |
| `recovering` | An owner/admin has issued the bounded `recover_source` action; the source remains `auto_disabled` until the next evaluation cycle returns `healthy` or `degraded` and the `cooldown_seconds` window has elapsed. |
| `resolved` | The next evaluation cycle confirmed the source is `healthy` or `degraded`; the source is `enabled`. |
| `superseded` | A new event replaced the current active event for the same source; the older event is preserved for audit. |

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
prevents flapping. The
`consecutive_breaches` counter requires
multiple breaches in a row.

## Bounded Recovery Flow

The bounded recovery flow is
human-confirmed:

1. An owner/admin issues
   `POST
   /admin/connectors/auto-disable/events/{id}/recover`
   with a `reason` body.
2. The bounded `AutoDisableService`
   validates the session, the role, the
   tenant scope, and the event id.
3. The bounded `AutoDisableService`
   transitions the
   `ConnectorAutoDisableEvent` row from
   `active` to `recovering` and emits the
   `connector.auto_disable.recovered` audit
   entry.
4. The next evaluation cycle confirms the
   source is `healthy` or `degraded` and
   the `cooldown_seconds` window has
   elapsed.
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

- `pilot_live` —
  `max_window_seconds = 24 * 3600` (24
  hours).
- `test_like` —
  `max_window_seconds = 3600` (1 hour).

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
before persistence. A rule, event, or audit
entry that fails the sanitization is
rejected with
`AUTO_DISABLE_RULE_INVALID_PAYLOAD`,
`AUTO_DISABLE_EVENT_INVALID_PAYLOAD`, or
`AUTO_DISABLE_AUDIT_INVALID_PAYLOAD`. The
rejection is recorded in the audit log with
the
`connector.auto_disable.evaluation.rejected`
action.

## Audit Entry Shape

The bounded `AutoDisableService` and
`AutoDisableOrchestrator` emit the
following audit entries, all using the
existing `AuditEntry` contract from
`US-026`:

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
  action, actor (system or owner/admin
  for manual kill switch), `event_id`,
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
  `reason` (sanitization rejection,
  window rejection, or invalid enum
  value).

## API Surface

The new owner/admin-only REST surface:

- `GET
  /admin/connectors/auto-disable/rules?source_id=&enabled=&limit=&offset=`
  — paginated rule list with sanitized
  payloads.
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
- `GET
  /admin/connectors/auto-disable/rules/{id}`
  — single rule with sanitized payload.
- `PATCH
  /admin/connectors/auto-disable/rules/{id}`
  — body shape: same as create.
- `DELETE
  /admin/connectors/auto-disable/rules/{id}`
  — soft-deletes the rule.
- `GET
  /admin/connectors/auto-disable/events?source_id=&status=&limit=&offset=`
  — paginated event history with
  sanitized payloads.
- `POST
  /admin/connectors/auto-disable/events/{id}/recover`
  — body shape:
  ```json
  {
    "reason": "Operator confirmed the source is healthy and ready to re-enable."
  }
  ```
- `POST
  /admin/connectors/{source_id}/auto-disable/evaluate`
  — triggers a single bounded evaluation
  cycle for the source and returns the
  result inline.

All new error responses follow the existing
error envelope (`code`, `message`,
`request_id`, `details`):

- `AUTO_DISABLE_RULE_INVALID` — invalid
  rule payload.
- `AUTO_DISABLE_RULE_INVALID_WINDOW` —
  `window_seconds` exceeds the
  `EnvironmentMode` bound.
- `AUTO_DISABLE_RULE_INVALID_PAYLOAD` —
  sanitization rejection.
- `AUTO_DISABLE_EVENT_NOT_FOUND` — event
  id not found in the tenant scope.
- `AUTO_DISABLE_RECOVERY_REJECTED` —
  recovery action denied.
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

## UI / Ops Surface

- A new operator panel widget on the
  `AdminConnectors` page that lists the
  latest auto-disable rules and events
  per source, shows the trigger badge
  and the status badge, and exposes a
  `Recover` button for each `active`
  event, a `Compute evaluation` button
  per source, and a `Create rule` button
  that opens a modal with the rule form.
- The in-app inbox from `US-029` shows
  auto-disable events with a dedicated
  trigger icon and a deep link to the
  event detail in the operator panel.
- A new runbook
  (`docs/ops/connector-auto-disable-runbook.md`)
  documents what an operator does when a
  source flips to `auto_disabled`, when
  a `captcha_rate_breach` fires, when a
  `failure_rate_breach` fires, when a
  `needs_user_action_storm` fires, and
  when a recovery action is denied
  because the cooldown has not elapsed.

## Validation Implications

- Unit tests must prove that the
  `AutoDisableEvaluator` and the
  `AutoDisableService` reject or correctly
  process the documented input space, that
  the `cooldown_seconds` window is enforced,
  that the `consecutive_breaches` counter
  is enforced, and that the bounded window
  helper returns the bounded
  `(window_start, window_end)` pair.
- Integration tests must exercise every
  new endpoint against an in-memory
  SQLite plus a stubbed notification
  dispatcher and prove that role gates
  and sanitization are enforced.
- E2E tests must cover the operator
  panel render, the simulated seed
  signal fire, the recovery flow, and
  the bounded window enforcement.
- Security tests must prove that viewer,
  analyst, sales, and reviewer sessions
  are rejected on every new endpoint.
- Operational tests must prove the
  seed defaults match the documented
  table, the runbook entry exists, and
  the verify script exercises each
  trigger type.
- Platform proof is the
  `scripts/verify-us-048.sh` command
  wired into `story verify` and
  `story verify-all`.
