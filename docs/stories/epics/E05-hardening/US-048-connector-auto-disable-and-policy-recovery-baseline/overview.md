# Overview

## Current Behavior

`US-001` through `US-047` delivered a broad MVP and
the first bounded hardening slices for LiveLead. The
product now has:

- A modular monolith with a Python API, a worker,
  a scheduler, a browser worker, a SQLite store,
  a Redis broker, and a React/TypeScript UI.
- A first source registry and policy baseline
  (`US-003`) with manual `enabled` / `disabled`
  state, owner/admin approval, rate limits,
  authentication metadata, and the
  `SOURCE_POLICY_DENIED` rejection code returned
  by the orchestrator.
- A first operational observability and alerting
  baseline (`US-041`) with `AlertRule`,
  `AlertEvent`, the `SanitizeAlertPayload` helper,
  the in-app inbox + email channels, and seed
  rules for `connector.failure_rate`,
  `discovery.needs_user_action_rate`,
  `browser.crash_loop`, stale backup, missing
  worker heartbeat, and audit retention risk.
- A first external metrics pipeline baseline
  (`US-042`) with `MetricsExportPolicy`,
  `MetricRegistry`, and the
  `PrometheusExposition` / `OtelCollector` /
  `SentryIngest` transports.
- A first connector health surface baseline
  (`US-046`) with `connector_health_snapshots`,
  `connector_health_errors`, a closed
  `ConnectorHealthStatus` enum (`healthy`,
  `degraded`, `unhealthy`, `unknown`), a
  `ConnectorHealthService` with
  `compute_snapshot`, `list_snapshots`,
  `build_summary`, and `list_recent_errors`, and
  a bounded `EnvironmentMode`-clipped window.
- A first real-environment cutover baseline
  (`US-040`) with `EnvironmentMode`,
  `LaunchGateReport`, `LiveIntegrationToggle`, and
  `BackupSnapshot`.
- A first internationalization and timezone
  baseline (`US-047`) with a closed `Locale` enum,
  a bounded `Timezone` validation, a reusable
  `I18nService`, and audit entries for
  `user.locale.updated` and
  `organization.locale.updated`.

`SPEC.md` section 5.3 (`FR-SRC-004`) commits the
product to source policy enforcement:

> **FR-SRC-004 — Source policy enforcement**
> **Ưu tiên:** Must
> Orchestrator phải từ chối chạy job nếu source
> bị vô hiệu hóa, vượt quota, ngoài time window
> hoặc không có policy hợp lệ.

`SPEC.md` section 11.1 commits the product to
three kill-switch levels:

> 8. Có kill switch cấp connector, workspace và
>    toàn hệ thống.

`docs/decisions/0019-observability-and-alerting-baseline.md`
explicitly carves the auto-disable loop out of
`US-041` as a follow-up. The relevant extract
from the durable record is:

> The evaluator is read-only with respect to
> product state. It persists `AlertEvent` rows
> and dispatches alerts through the existing
> in-app inbox and email channels; it does not
> pause jobs, disable connectors, flip live
> toggles, or roll back the environment.

`docs/decisions/0024-connector-health-surface-baseline.md`
explicitly carves the auto-disable loop out of
`US-046` as a follow-up. The relevant extract is:

> Auto-remediation or self-healing actions driven
> by a connector health breach. The health
> surface is advisory, not authoritative.

The product still has no bounded auto-disable
loop:

- The source registry from `US-003` exposes a
  manual `enabled` flag and a `disabled_reason`,
  but nothing flips a source from `enabled` to
  `disabled` automatically when a health breach
  fires from `US-046` or an alert from `US-041`
  reaches a critical severity.
- The `ConnectorHealthStatus` enum from `US-046`
  reports `unhealthy`, but the bounded
  `ConnectorHealthService` does not know how to
  translate the status into a source policy
  change.
- The `connector.failure_rate` and
  `discovery.needs_user_action_rate` seed rules
  from `US-041` fire alerts, but the bounded
  `AlertEvaluator` is read-only and does not
  flip a `Source.enabled` flag.
- The orchestrator from `US-004` /
  `US-032` / `US-033` / `US-034` honours the
  manual `enabled` flag from `US-003`, but it
  has no path for a governed auto-disable event
  and no path for a bounded recovery.
- Operators who want to answer "why is connector
  X currently disabled?" still have to read raw
  tables or run ad-hoc scripts. There is no
  bounded `auto_disable_reason` field, no bounded
  `auto_disabled_at` timestamp, and no bounded
  `auto_disabled_by` actor reference.
- The system kill switch from `SPEC.md` 11.1
  is a workspace-level toggle from `US-040`
  (`LiveIntegrationToggle`) and a per-source
  manual toggle from `US-003`. The connector
  kill switch (per-source) is partially
  satisfied by the manual toggle, but the
  auto-disable loop closes the operational
  gap between "alert fires" and "source actually
  stops running".

The next step in the hardening epic is therefore
a bounded connector auto-disable and policy
recovery slice that turns the implicit
`FR-SRC-004` + `SPEC.md` 11.1 kill-switch
requirements into a documented contract, a
durable `connector_auto_disable_rules` and
`connector_auto_disable_events` pair, a closed
`AutoDisableTrigger` enum, a bounded
`AutoDisableService` that consumes the
`US-046` health surface and the `US-041`
alerting channel, a bounded recovery flow with
owner/admin re-enable, and a reusable
verification command that a future story can
extend without re-opening the source policy,
the alerting, or the metrics contracts.

## Target Behavior

This story establishes the first bounded
connector auto-disable and policy recovery
surface for LiveLead. After the story is
complete:

- A new durable `connector_auto_disable_rules`
  table records the bounded per-source
  auto-disable policy with `id`,
  `organization_id`, `source_id`, `trigger`
  (closed enum), `threshold_value`,
  `window_seconds`, `consecutive_breaches`,
  `cooldown_seconds`, `enabled`, `created_by`,
  `created_at`, `updated_at`. The table is the
  single source of truth for the auto-disable
  policy; the orchestrator and the
  `AutoDisableService` read from it.
- A new durable `connector_auto_disable_events`
  table records the bounded per-event auto-
  disable history with `id`, `organization_id`,
  `source_id`, `trigger`, `reason`, `breach_count`,
  `window_start`, `window_end`, `status`
  (`active`, `recovering`, `resolved`,
  `superseded`), `alert_event_id` (links to the
  matching `AlertEvent` row from `US-041`),
  `health_snapshot_id` (links to the matching
  `ConnectorHealthSnapshot` row from `US-046`),
  `recovery_actor_id`, `recovery_reason`,
  `recovered_at`, `audit_correlation_id`, and
  `created_at`. The table is bounded to the
  most recent N events per source so a flapping
  connector cannot fill the table.
- A new closed `AutoDisableTrigger` enum
  (`health_unhealthy`, `captcha_rate_breach`,
  `failure_rate_breach`,
  `needs_user_action_storm`, `error_spike`,
  `manual_kill_switch`) that the bounded
  `AutoDisableService` reads from the closed
  `ConnectorHealthStatus` enum from `US-046`
  and the closed `AlertMetric` enum from
  `US-041`.
- A new closed `AutoDisableEventStatus` enum
  (`active`, `recovering`, `resolved`,
  `superseded`) that the bounded service
  uses to track the lifecycle of an
  auto-disable event.
- A new `AutoDisableService` exposes the
  bounded operations:
  - `evaluate_source(source_id, *,
    now=None)` — reads the most recent
    `ConnectorHealthSnapshot` row from `US-046`
    and the most recent matching
    `AlertEvent` rows from `US-041`,
    applies the closed trigger rules with
    the `consecutive_breaches` and
    `cooldown_seconds` bounds, returns the
    bounded evaluation result.
  - `list_rules(*, source_id, enabled,
    limit, offset)` — paginated rule list
    for the admin surface.
  - `create_rule(*, source_id, trigger,
    threshold_value, window_seconds,
    consecutive_breaches, cooldown_seconds,
    enabled)` — owner/admin only. Validates
    against the closed enums and the
    `EnvironmentMode` bound from `US-040`.
  - `update_rule(*, rule_id, ...)` —
    owner/admin only. Validates against the
    closed enums.
  - `delete_rule(*, rule_id)` — owner/admin
    only. Soft-deletes the rule.
  - `list_events(*, source_id, status,
    limit, offset)` — paginated event
    history with sanitized payloads.
  - `recover_source(*, source_id, *,
    event_id, reason)` — owner/admin only.
    Transitions the matching
    `AutoDisableEvent` row from `active` to
    `recovering`, then to `resolved` after
    the next evaluation cycle, and emits
    the `connector.auto_disable.recovered`
    audit entry. The recovery action also
    sets `Source.enabled = true` only after
    the bounded `cooldown_seconds` window
    has elapsed and the bounded evaluation
    returns `healthy` or `degraded`.
- A new bounded `AutoDisableEvaluator` that
  owns the trigger rule evaluation, the
  consecutive-breach counter, the
  cooldown, and the bounded window helper.
- A new source-side helper
  `evaluate_source_for_discovery` that
  the orchestrator from `US-004` /
  `US-032` / `US-033` / `US-034` calls
  before a job is dispatched. The helper
  returns `RUN_ALLOWED`, `RUN_AUTO_DISABLED`,
  or `RUN_MANUAL_DISABLED` and the matching
  reason. The helper refuses to run a
  discovery job against an auto-disabled
  source even when the manual `enabled`
  flag is `true`; the manual `enabled` flag
  is preserved as a separate signal.
- A new `Source` extension with
  `auto_disabled_at` (nullable timestamp),
  `auto_disabled_reason` (nullable string,
  bounded to 500 characters), and
  `auto_disabled_by_event_id` (nullable
  foreign key to
  `connector_auto_disable_events.id`).
  These fields are read-only from the
  domain side and only updated by the
  bounded `AutoDisableService`.
- A new bounded `AutoDisableOrchestrator`
  that runs from a periodic worker tick
  and from the `POST /discovery-jobs`
  boundary. The orchestrator calls
  `AutoDisableService.evaluate_source`
  for every source with at least one
  matching rule, transitions
  `Source.enabled` to `false` when the
  trigger fires, and emits the
  `connector.auto_disable.triggered`
  audit entry.
- A new owner/admin-only REST surface:
  - `GET /admin/connectors/auto-disable/rules`
    — paginated rule list.
  - `POST /admin/connectors/auto-disable/rules`
    — creates a rule after validation
    against the closed enums and the
    `EnvironmentMode` bound.
  - `GET /admin/connectors/auto-disable/rules/{id}`
    — returns a single rule with the
    sanitized payload.
  - `PATCH /admin/connectors/auto-disable/rules/{id}`
    — updates threshold, window,
    consecutive_breaches, cooldown_seconds,
    and enabled state.
  - `DELETE /admin/connectors/auto-disable/rules/{id}`
    — soft-deletes the rule.
  - `GET /admin/connectors/auto-disable/events`
    — paginated event history with
    sanitized payloads.
  - `POST /admin/connectors/auto-disable/events/{id}/recover`
    — owner/admin only. Body shape:
    `{ reason: string }`. Transitions the
    event to `recovering` and writes the
    audit entry.
  - `POST /admin/connectors/{source_id}/auto-disable/evaluate`
    — owner/admin only. Triggers a single
    bounded evaluation cycle for the source
    and returns the result inline.
- A new operator panel widget that lists
  the latest auto-disable rules and events
  per source, shows the trigger badge and
  the status badge, and exposes a
  `Recover` button for each `active` event.
- A new product doc
  (`docs/product/connector-auto-disable-and-recovery.md`)
  that documents the closed
  `AutoDisableTrigger` enum, the closed
  `AutoDisableEventStatus` enum, the
  per-source auto-disable rule shape, the
  per-event auto-disable history shape, the
  bounded evaluation algorithm, the bounded
  recovery flow, the bounded window bound,
  the orchestrator integration seam, and
  the audit entry shape.
- A new runbook
  (`docs/ops/connector-auto-disable-runbook.md`)
  that documents what an operator does when
  a source flips to `auto_disabled`, when a
  `captcha_rate_breach` fires, when a
  `failure_rate_breach` fires, and when a
  recovery action is denied because the
  cooldown has not elapsed.
- A new decision record
  (`docs/decisions/0026-connector-auto-disable-and-policy-recovery-baseline.md`)
  that locks the closed
  `AutoDisableTrigger` enum, the closed
  `AutoDisableEventStatus` enum, the
  bounded evaluation algorithm, the
  bounded recovery flow, the bounded
  window bound, the orchestrator
  integration seam, the source-side
  helper, and the audit entry shape.
- A new bounded verification command
  (`scripts/verify-us-048.sh`) that runs
  the unit, integration, E2E, security,
  operational, and platform checks
  defined in `validation.md` and is wired
  into `harness-cli story verify` and
  `harness-cli story verify-all`.

The slice stops at the local-first, single-host
baseline. Distributed auto-disable coordination,
external runbook automation (PagerDuty, Opsgenie),
and per-tenant rule templates remain in the
follow-up backlog.

## Affected Users

- Owners and Admins responsible for the
  real-environment pilot. They need a bounded
  auto-disable loop that consumes the
  `US-046` health surface and the `US-041`
  alert channel, plus a bounded recovery flow
  that flips a source back to `enabled` after
  a human-confirmed recovery.
- Operators on call for the pilot-live
  environment. They need a
  `connector-auto-disable-runbook.md` entry
  that explains what to do when a source flips
  to `auto_disabled`, when a
  `captcha_rate_breach` fires, when a
  `failure_rate_breach` fires, and when a
  recovery action is denied because the
  cooldown has not elapsed.
- Analysts and Sales/BD users. They need
  discovery jobs to stop dispatching against
  a source that is currently `auto_disabled`
  so the dashboard, the funnel, and the
  source-performance report do not get
  polluted with failed runs.
- Performance and SRE engineers who need a
  documented auto-disable baseline and a
  bounded `AutoDisableService` they can
  extend for future trigger types.
- Future implementation agents and engineers
  extending the auto-disable loop, the
  per-tenant thresholds, or the runbook
  automation that need a stable
  auto-disable contract.

## Affected Product Docs

- `docs/product/source-registry-and-policy.md`
  (`US-003` contract; this story extends the
  `Source` row with
  `auto_disabled_at`,
  `auto_disabled_reason`, and
  `auto_disabled_by_event_id`, it does not
  redefine the source registry, the policy
  evaluation, or the manual `enabled` /
  `disabled` flow).
- `docs/product/observability-and-alerting.md`
  (`US-041` contract; this story consumes the
  `AlertEvent` rows and the
  `SanitizeAlertPayload` helper, it does not
  redefine the `AlertRule` or `AlertEvent`
  contract; the bounded
  `AutoDisableOrchestrator` is read-only with
  respect to alert state).
- `docs/product/connector-health-surface.md`
  (`US-046` contract; this story consumes the
  `ConnectorHealthSnapshot` rows and the
  closed `ConnectorHealthStatus` enum, it
  does not redefine the snapshot shape or the
  bounded computation algorithm).
- `docs/product/real-environment-cutover-and-live-operations.md`
  (`US-040` contract; the auto-disable
  evaluation window is bounded by the
  `EnvironmentMode` from `US-040`, the
  bounded runbook is covered by the same
  launch-gate seam).
- `docs/product/audit-log-and-governance.md`
  (`US-026` contract; the auto-disable and
  recovery actions emit
  `connector.auto_disable.*` audit entries
  with the same secret-safe payload
  contract).
- `docs/product/discovery-job-lifecycle.md`
  (`US-004` contract; the source-side helper
  is called from the orchestrator seam; the
  bounded rejection code is
  `SOURCE_AUTO_DISABLED`, the same envelope
  as the existing `SOURCE_POLICY_DENIED`).
- `docs/product/live-feed-and-api-discovery.md`
  (`US-032` contract; the bounded
  source-side helper is consumed by the live
  external discovery orchestrator).
- `docs/product/public-website-playwright-discovery.md`
  (`US-033` contract; the bounded
  source-side helper is consumed by the
  Playwright discovery orchestrator).
- `docs/product/selenium-and-alternate-adapter-discovery.md`
  (`US-034` contract; the bounded
  source-side helper is consumed by the
  Selenium discovery orchestrator).
- `docs/product/connector-auto-disable-and-recovery.md`
  (new product doc that this story seeds as
  the living contract for the auto-disable
  domain).

## Non-Goals

- Distributed auto-disable coordination. This
  story ships the contract, not a UI for
  multi-host coordination.
- External runbook automation (PagerDuty,
  Opsgenie, Slack auto-recovery). The slice
  reuses the `AlertEvent` from `US-041` and
  the `AlertEvaluator` from `US-041`; a later
  story can wire an external runbook consumer
  behind the same contract.
- Auto-recovery. The bounded recovery flow is
  human-confirmed; the slice does not
  auto-flip a source back to `enabled`.
- Per-tenant rule templates. The slice ships
  one rule per source at a time; per-tenant
  templates are a follow-on story.
- Customer-facing status pages or external
  incident communication.
- Replacing the existing source registry from
  `US-003`. This story extends the `Source`
  row with auto-disable metadata; it does not
  redefine the source registry, the policy
  evaluation, or the manual `enabled` /
  `disabled` flow.
- Replacing the existing observability and
  alerting surface from `US-041`. This
  story consumes the `AlertEvent` rows and
  the `SanitizeAlertPayload` helper; it does
  not redefine the `AlertRule` or
  `AlertEvent` contract; the bounded
  `AutoDisableOrchestrator` is read-only with
  respect to alert state.
- Replacing the existing connector health
  surface from `US-046`. This story consumes
  the `ConnectorHealthSnapshot` rows and the
  closed `ConnectorHealthStatus` enum; it
  does not redefine the snapshot shape or the
  bounded computation algorithm.
- Replacing the existing audit log from
  `US-026`. This story extends the audit
  entry shape with
  `connector.auto_disable.*`; it does not
  redefine the `AuditEntryRow` or the audit
  retention guarantee.
- Replacing the existing real-environment
  cutover from `US-040`. This story consumes
  the `EnvironmentMode` from `US-040`; it
  does not redefine the launch-gate seam.
- Replacing the existing discovery job
  lifecycle from `US-004`. This story
  extends the orchestrator seam with the
  bounded source-side helper; it does not
  redefine the job state machine.
