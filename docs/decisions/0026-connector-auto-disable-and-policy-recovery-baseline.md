# 0026 Connector Auto-Disable And Policy Recovery Baseline

Date: 2026-06-16

## Status

Proposed (companion decision to `US-048`).

## Context

`SPEC.md` commits the product to a source
policy enforcement contract and to a
three-level kill switch:

- `FR-SRC-004` — Orchestrator phải từ chối
  chạy job nếu source bị vô hiệu hóa, vượt
  quota, ngoài time window hoặc không có
  policy hợp lệ.
- `SPEC.md` 11.1 — Có kill switch cấp
  connector, workspace và toàn hệ thống.

LiveLead has shipped forty-seven stories that
all rely on the manual `Source.enabled` flag
from `US-003`, the read-only
`AlertEvaluator` from `US-041`, the closed
`ConnectorHealthStatus` enum from `US-046`,
and the `EnvironmentMode` from `US-040`. The
product still has no bounded auto-disable
loop:

- The source registry from `US-003` exposes
  a manual `enabled` flag and a
  `disabled_reason`, but nothing flips a
  source from `enabled` to `disabled`
  automatically when a health breach fires
  from `US-046` or an alert from `US-041`
  reaches a critical severity.
- The `ConnectorHealthStatus` enum from
  `US-046` reports `unhealthy`, but the
  bounded `ConnectorHealthService` does not
  know how to translate the status into a
  source policy change.
- The `connector.failure_rate` and
  `discovery.needs_user_action_rate` seed
  rules from `US-041` fire alerts, but the
  bounded `AlertEvaluator` is read-only
  and does not flip a `Source.enabled`
  flag.
- The orchestrator from `US-004` /
  `US-032` / `US-033` / `US-034` honours
  the manual `enabled` flag from `US-003`,
  but it has no path for a governed
  auto-disable event and no path for a
  bounded recovery.

`docs/decisions/0019-observability-and-alerting-baseline.md`
explicitly carves the auto-disable loop out
of `US-041` as a follow-up:

> The evaluator is read-only with respect
> to product state. It persists `AlertEvent`
> rows and dispatches alerts through the
> existing in-app inbox and email channels;
> it does not pause jobs, disable
> connectors, flip live toggles, or roll
> back the environment.

`docs/decisions/0024-connector-health-surface-baseline.md`
explicitly carves the auto-disable loop out
of `US-046` as a follow-up:

> Auto-remediation or self-healing actions
> driven by a connector health breach. The
> health surface is advisory, not
> authoritative.

The next step is therefore a bounded
connector auto-disable and policy recovery
slice that turns the implicit `FR-SRC-004`
+ `SPEC.md` 11.1 kill-switch requirements
into a documented contract, a durable
`connector_auto_disable_rules` and
`connector_auto_disable_events` pair, a
closed `AutoDisableTrigger` enum, a closed
`AutoDisableEventStatus` enum, a bounded
`AutoDisableService`, a bounded
`AutoDisableEvaluator`, a bounded
`AutoDisableOrchestrator`, a bounded
source-side helper, and a human-confirmed
recovery flow.

## Decision

`US-048` introduces the first bounded
connector auto-disable and policy recovery
surface for LiveLead.

### Domain objects

- **`AutoDisableTrigger`** — closed enum
  (`health_unhealthy`, `captcha_rate_breach`,
  `failure_rate_breach`,
  `needs_user_action_storm`, `error_spike`,
  `manual_kill_switch`) that the bounded
  `AutoDisableService` reads from the
  closed `ConnectorHealthStatus` enum from
  `US-046` and the closed `AlertMetric`
  enum from `US-041`.
- **`AutoDisableEventStatus`** — closed
  enum (`active`, `recovering`, `resolved`,
  `superseded`) that the bounded
  `AutoDisableService` uses to track the
  lifecycle of an auto-disable event.
- **`ConnectorAutoDisableRule`** — durable
  table that records a per-source
  auto-disable policy with `source_id`,
  `trigger`, `threshold_value`,
  `window_seconds`,
  `consecutive_breaches`,
  `cooldown_seconds`, `enabled`,
  `created_by`, `created_at`, and
  `updated_at`.
- **`ConnectorAutoDisableEvent`** — durable
  table that records a per-event
  auto-disable history with `source_id`,
  `trigger`, `reason`, `breach_count`,
  `window_start`, `window_end`, `status`,
  `alert_event_id`,
  `health_snapshot_id`,
  `recovery_actor_id`, `recovery_reason`,
  `recovered_at`,
  `audit_correlation_id`, and `created_at`.
- **`Source` extension** — three
  read-only fields on the existing `Source`
  row: `auto_disabled_at` (nullable
  timestamp), `auto_disabled_reason`
  (nullable string, bounded to 500
  characters), and
  `auto_disabled_by_event_id` (nullable
  foreign key).
- **`AutoDisableThresholds`** — bounded
  dataclass that exposes the closed default
  thresholds and the
  `default_window_seconds` bound.
- **`AutoDisableService`** — bounded
  service that exposes `evaluate_source`,
  `list_rules`, `create_rule`,
  `update_rule`, `delete_rule`,
  `list_events`, and `recover_source`.
- **`AutoDisableEvaluator`** — bounded
  helper that owns the trigger rule
  evaluation, the `consecutive_breaches`
  counter, the `cooldown_seconds` window,
  and the bounded window helper.
- **`AutoDisableOrchestrator`** — bounded
  actor that runs from a periodic worker
  tick (the existing scheduler from
  `US-035`) and from the
  `POST /discovery-jobs` boundary.
- **`evaluate_source_for_discovery`** —
  bounded source-side helper that the
  orchestrator from `US-004` / `US-032` /
  `US-033` / `US-034` calls before a job
  is dispatched.

### Bounded evaluation algorithm

The bounded evaluation algorithm is
deterministic and is locked in this
decision. The algorithm reads the most
recent `ConnectorHealthSnapshot` row and
the most recent matching `AlertEvent`
rows, applies the closed trigger rules,
and returns a deterministic result. The
`consecutive_breaches` counter requires
multiple breaches in a row; the
`cooldown_seconds` window prevents
flapping. See the design doc for the full
algorithm.

### Bounded recovery flow

The bounded recovery flow is
human-confirmed:

1. An owner/admin issues
   `POST
   /admin/connectors/auto-disable/events/{id}/recover`
   with a `reason` body.
2. The bounded `AutoDisableService`
   transitions the
   `ConnectorAutoDisableEvent` row from
   `active` to `recovering` and emits the
   `connector.auto_disable.recovered` audit
   entry.
3. The next evaluation cycle confirms the
   source is `healthy` or `degraded` and
   the `cooldown_seconds` window has
   elapsed.
4. The bounded `AutoDisableService`
   transitions the event to `resolved`,
   sets `Source.enabled = true`, and
   clears `Source.auto_disabled_at`,
   `Source.auto_disabled_reason`, and
   `Source.auto_disabled_by_event_id`.
5. The bounded `AutoDisableService` emits
   the
   `connector.auto_disable.recovery.resolved`
   audit entry.

The slice does not auto-flip a source back
to `enabled`. An owner/admin must issue the
bounded recovery action.

### Bounded window bound

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

### Sanitization contract

The bounded `AutoDisableService` and
`AutoDisableOrchestrator` reuse the
`SanitizeAlertPayload` helper from `US-041`
for every rule, event, and audit entry
before persistence. A rule, event, or
audit entry that fails the sanitization is
rejected with
`AUTO_DISABLE_RULE_INVALID_PAYLOAD`,
`AUTO_DISABLE_EVENT_INVALID_PAYLOAD`, or
`AUTO_DISABLE_AUDIT_INVALID_PAYLOAD`. The
rejection is recorded in the audit log with
the
`connector.auto_disable.evaluation.rejected`
action.

### API contract

- `GET
  /admin/connectors/auto-disable/rules?source_id=&enabled=&limit=&offset=`
  — paginated rule list with sanitized
  payloads.
- `POST
  /admin/connectors/auto-disable/rules` —
  creates a rule after validation against
  the closed enums and the
  `EnvironmentMode` bound.
- `GET
  /admin/connectors/auto-disable/rules/{id}`
  — single rule with sanitized payload.
- `PATCH
  /admin/connectors/auto-disable/rules/{id}`
  — updates threshold, window,
  `consecutive_breaches`,
  `cooldown_seconds`, and `enabled`
  state.
- `DELETE
  /admin/connectors/auto-disable/rules/{id}`
  — soft-deletes the rule.
- `GET
  /admin/connectors/auto-disable/events?source_id=&status=&limit=&offset=`
  — paginated event history with
  sanitized payloads.
- `POST
  /admin/connectors/auto-disable/events/{id}/recover`
  — transitions the event to `recovering`
  and writes the audit entry.
- `POST
  /admin/connectors/{source_id}/auto-disable/evaluate`
  — triggers a single bounded evaluation
  cycle for the source and returns the
  result inline.

### Audit entry shape

The bounded `AutoDisableService` and
`AutoDisableOrchestrator` emit the
following audit entries, all using the
existing `AuditEntry` contract from
`US-026`:

- `connector.auto_disable.rule.created`
- `connector.auto_disable.rule.updated`
- `connector.auto_disable.rule.deleted`
- `connector.auto_disable.triggered`
- `connector.auto_disable.recovered`
- `connector.auto_disable.recovery.resolved`
- `connector.auto_disable.recovery.rejected`
- `connector.auto_disable.evaluation.rejected`

### Source-side helper contract

The bounded
`evaluate_source_for_discovery` helper
returns `RUN_ALLOWED`, `RUN_AUTO_DISABLED`,
or `RUN_MANUAL_DISABLED` and the matching
reason. The helper refuses to run a
discovery job against an `auto_disabled`
source even when the manual `enabled` flag
is `true`; the manual `enabled` flag is
preserved as a separate signal. The
orchestrator from `US-004` / `US-032` /
`US-033` / `US-034` reads the bounded
rejection code `SOURCE_AUTO_DISABLED` and
refuses to dispatch a discovery job.

## Consequences

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
- The bounded `AutoDisableTrigger` and
  `AutoDisableEventStatus` enums are
  closed. Adding a new value is an
  explicit follow-up story; the first
  slice ships only the values listed in
  the design doc.
- The bounded recovery flow is
  human-confirmed. The slice does not
  auto-flip a source back to `enabled`.
  An owner/admin must issue
  `POST
  /admin/connectors/auto-disable/events/{id}/recover`
  with a `reason` body.
- The slice is local-first by design. It
  does not commit to a specific external
  runbook service (PagerDuty, Opsgenie, a
  managed Slack channel) in this step;
  it preserves a stable seam for a later
  hardening story to wire one.
- The slice touches the orchestrator seam
  from `US-004` / `US-032` / `US-033` /
  `US-034`. The orchestrator must call
  the bounded
  `evaluate_source_for_discovery` helper
  before dispatching a job. A future
  story that wants to bypass the helper
  must reopen this decision.

## Alternatives Considered

- **Make the auto-disable loop part of
  `US-041` observability and alerting.**
  Rejected: `US-041` is read-only with
  respect to product state by design
  (decision `0019`). Adding a
  `Source.enabled` flip would weaken
  that contract and would couple alert
  evaluation to source policy mutation.
- **Make the auto-disable loop part of
  `US-046` connector health surface.**
  Rejected: `US-046` is advisory by
  design (decision `0024`). Adding a
  `Source.enabled` flip would weaken
  that contract and would couple
  connector health computation to source
  policy mutation.
- **Use the existing `Source.disabled_reason`
  field instead of a new
  `auto_disabled_reason` field.**
  Rejected: `Source.disabled_reason` is
  owned by the manual flow from `US-003`.
  Mixing the manual and auto-disable
  reasons would conflate two distinct
  governance signals.
- **Auto-recover after a clean
  `cooldown_seconds` window.** Rejected:
  the slice is human-confirmed by design
  to keep the `FR-SRC-004` rejection
  contract intact and to preserve the
  audit trail. A follow-on story can add
  auto-recovery behind the same
  `AutoDisableService` seam.
- **Distributed auto-disable coordination.**
  Rejected: out of scope for the local-
  first baseline. A follow-on story can
  add multi-host coordination behind the
  same `AutoDisableService` seam.
- **External runbook automation (PagerDuty,
  Opsgenie, Slack auto-recovery).**
  Rejected: out of scope for the
  local-first baseline. A follow-on
  story can wire an external runbook
  consumer behind the same `AutoDisableService`
  seam.

## Compliance

This decision preserves the existing
contracts from `US-003`, `US-004`,
`US-026`, `US-032`, `US-033`, `US-034`,
`US-035`, `US-040`, `US-041`, and
`US-046`. The slice does not redefine the
source registry, the source policy
evaluation, the manual `enabled` /
`disabled` flow, the alert rule contract,
the alert event contract, the connector
health snapshot contract, the connector
health status enum, the audit log
contract, the audit retention guarantee
from `NFR-SEC-008`, the launch-gate seam
from `US-040`, or the discovery job
lifecycle from `US-004`.

The slice introduces the first bounded
auto-disable loop that flips
`Source.enabled` automatically when a
health breach fires or when an alert
reaches a critical severity, and the
first bounded human-confirmed recovery
flow that re-enables a source after a
clean evaluation cycle.

## Follow-Up

- Per-tenant rule templates.
- Auto-recovery after a clean
  `cooldown_seconds` window.
- External runbook automation (PagerDuty,
  Opsgenie, Slack auto-recovery).
- Distributed auto-disable coordination.
- Per-tenant thresholds.
- Bulk recovery action on the operator
  panel widget.
