# Exec Plan

## Goal

Add the first bounded connector auto-disable and
policy recovery surface to LiveLead. The slice
turns the implicit `FR-SRC-004` + `SPEC.md` 11.1
kill-switch requirements into a documented
contract, a durable
`connector_auto_disable_rules` and
`connector_auto_disable_events` pair, a closed
`AutoDisableTrigger` enum, a bounded
`AutoDisableService` that consumes the `US-046`
health surface and the `US-041` alerting
channel, a bounded recovery flow with
owner/admin re-enable, and a reusable
verification command.

## Scope

In scope:

- New durable `connector_auto_disable_rules`
  table with the minimum fields required to
  record a per-source auto-disable policy:
  `source_id`, `trigger` (closed enum),
  `threshold_value`, `window_seconds`,
  `consecutive_breaches`, `cooldown_seconds`,
  `enabled`, `created_by`, `created_at`, and
  `updated_at`. Forward-only Alembic migration
  with a documented rollback note in the
  migration header.
- New durable `connector_auto_disable_events`
  table with the minimum fields required to
  record a bounded per-event auto-disable
  history: `source_id`, `trigger`, `reason`,
  `breach_count`, `window_start`, `window_end`,
  `status` (closed enum), `alert_event_id`
  (links to `AlertEvent` from `US-041`),
  `health_snapshot_id` (links to
  `ConnectorHealthSnapshot` from `US-046`),
  `recovery_actor_id`, `recovery_reason`,
  `recovered_at`, and `audit_correlation_id`.
  Forward-only Alembic migration with a
  documented rollback note in the migration
  header.
- New `Source` extension with
  `auto_disabled_at` (nullable timestamp),
  `auto_disabled_reason` (nullable string,
  bounded to 500 characters), and
  `auto_disabled_by_event_id` (nullable
  foreign key to
  `connector_auto_disable_events.id`).
  Forward-only Alembic migration with a
  documented rollback note in the migration
  header.
- New closed `AutoDisableTrigger` enum
  (`health_unhealthy`, `captcha_rate_breach`,
  `failure_rate_breach`,
  `needs_user_action_storm`, `error_spike`,
  `manual_kill_switch`) that the bounded
  service reads from the closed
  `ConnectorHealthStatus` enum from `US-046`
  and the closed `AlertMetric` enum from
  `US-041`.
- New closed `AutoDisableEventStatus` enum
  (`active`, `recovering`, `resolved`,
  `superseded`) that the bounded service
  uses to track the lifecycle of an
  auto-disable event.
- New `AutoDisableThresholds` dataclass
  that exposes the closed default thresholds
  and the `default_window_seconds` bound.
- New `AutoDisableService` that exposes the
  bounded operations:
  - `evaluate_source(source_id, *, now=None)`
  - `list_rules(*, source_id, enabled,
    limit, offset)`
  - `create_rule(*, source_id, trigger,
    threshold_value, window_seconds,
    consecutive_breaches, cooldown_seconds,
    enabled)`
  - `update_rule(*, rule_id, ...)`
  - `delete_rule(*, rule_id)`
  - `list_events(*, source_id, status,
    limit, offset)`
  - `recover_source(*, source_id, *,
    event_id, reason)`
- New `AutoDisableEvaluator` that owns the
  trigger rule evaluation, the
  consecutive-breach counter, the cooldown,
  and the bounded window helper.
- New `AutoDisableOrchestrator` that runs
  from a periodic worker tick and from the
  `POST /discovery-jobs` boundary.
- New source-side helper
  `evaluate_source_for_discovery` that
  the orchestrator from `US-004` /
  `US-032` / `US-033` / `US-034` calls
  before a job is dispatched. The helper
  returns `RUN_ALLOWED`, `RUN_AUTO_DISABLED`,
  or `RUN_MANUAL_DISABLED` and the matching
  reason.
- New owner/admin-only REST surface:
  - `GET /admin/connectors/auto-disable/rules`
  - `POST /admin/connectors/auto-disable/rules`
  - `GET /admin/connectors/auto-disable/rules/{id}`
  - `PATCH /admin/connectors/auto-disable/rules/{id}`
  - `DELETE /admin/connectors/auto-disable/rules/{id}`
  - `GET /admin/connectors/auto-disable/events`
  - `POST /admin/connectors/auto-disable/events/{id}/recover`
  - `POST /admin/connectors/{source_id}/auto-disable/evaluate`
- New audit entry types:
  `connector.auto_disable.rule.created`,
  `connector.auto_disable.rule.updated`,
  `connector.auto_disable.rule.deleted`,
  `connector.auto_disable.triggered`,
  `connector.auto_disable.recovered`,
  `connector.auto_disable.evaluation.rejected`,
  and
  `connector.auto_disable.recovery.rejected`.
- A new bounded window bound by the
  `EnvironmentMode` from `US-040` (max 24
  hours in `pilot_live`, max 1 hour in
  `test_like`).
- A new product doc
  (`docs/product/connector-auto-disable-and-recovery.md`).
- A new runbook
  (`docs/ops/connector-auto-disable-runbook.md`).
- A new decision record
  (`docs/decisions/0026-connector-auto-disable-and-policy-recovery-baseline.md`).
- Reuse of the `SanitizeAlertPayload` helper
  from `US-041` for every rule, event, and
  audit payload before persistence.
- Reuse of the `AuditService` from `US-026`
  for every `connector.auto_disable.*` audit
  entry.
- Reuse of the `EnvironmentMode` from
  `US-040` for the bounded window bound.
- Reuse of the `ConnectorHealthService`
  from `US-046` for the
  `evaluate_source` health read.
- Reuse of the `AlertEvaluator` from
  `US-041` for the `evaluate_source` alert
  read.
- Reuse of the source registry from
  `US-003` for the per-source auto-disable
  rule and the per-source auto-disable event.
- Reuse of the existing settings and inbox
  surfaces from `US-026` and `US-029` for
  the operator panel widget.
- Unit, integration, E2E, security,
  operational, and platform checks wired
  into a `scripts/verify-us-048.sh` command
  that `harness-cli story verify` can run.

Out of scope:

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
- Reading browser-session or browser-debug
  rows for the bounded evaluation. The slice
  reads only the
  `ConnectorHealthSnapshot` rows from
  `US-046` and the `AlertEvent` rows from
  `US-041`; a future story can extend the
  evaluation to read those rows behind the
  same `AutoDisableEvaluator` seam.
- Per-tenant thresholds. The slice ships one
  fixed default set; per-tenant tuning is a
  follow-on story.

## Risk Classification

Risk flags:

- Authorization — owner/admin role gate for
  every new endpoint; tenant scope for the
  auto-disable surface; per-source rule
  ownership.
- Data model — new
  `connector_auto_disable_rules` and
  `connector_auto_disable_events` tables;
  `Source` extension with
  `auto_disabled_at`,
  `auto_disabled_reason`, and
  `auto_disabled_by_event_id`; new indexes;
  forward-only migrations; new
  `AutoDisableTrigger` enum; new
  `AutoDisableEventStatus` enum.
- Audit/security — every rule create / update
  / delete, every trigger, every recovery,
  and every rejected evaluation must carry a
  secret-safe payload and a
  `connector.auto_disable.*` audit entry;
  the bounded window is enforced by the
  `EnvironmentMode` from `US-040`.
- Public contracts — new REST endpoints, new
  error codes (`SOURCE_AUTO_DISABLED`,
  `AUTO_DISABLE_RULE_INVALID`,
  `AUTO_DISABLE_EVENT_NOT_FOUND`,
  `AUTO_DISABLE_RECOVERY_REJECTED`), new
  operator panel widget, new audit entry
  types; consumed by the same admin surfaces
  that already speak to the source policy,
  observability, and connector health
  endpoints from `US-003`, `US-041`, and
  `US-046`.
- External systems — the bounded
  `AutoDisableOrchestrator` interacts with
  the discovery orchestrator from `US-004`
  / `US-032` / `US-033` / `US-034`; the
  recovery flow can re-enable a source that
  is currently paused.
- Existing behavior — the source-side helper
  changes the discovery dispatch path; the
  recovery flow changes the
  `Source.enabled` flag; the bounded
  evaluation consumes the
  `ConnectorHealthSnapshot` rows and the
  `AlertEvent` rows; the bounded
  `AutoDisableOrchestrator` is read-only with
  respect to alert state.
- Weak proof — there is currently no bounded
  verification command for the auto-disable
  loop; the new `scripts/verify-us-048.sh`
  command must wire the unit, integration,
  E2E, security, operational, and platform
  checks together.
- Multi-domain — the slice touches sources
  (`US-003`), observability (`US-041`),
  metrics (`US-042`), connector health
  (`US-046`), real-environment cutover
  (`US-040`), audit (`US-026`), and
  discovery (`US-004` / `US-032` /
  `US-033` / `US-034`).

Hard gates:

- Any rule create / update / delete, any
  trigger, any recovery, or any rejected
  evaluation that mutates product state
  without an authenticated session with
  `owner` or `admin` role.
- Any rule create / update / delete, any
  trigger, any recovery, or any rejected
  evaluation that leaks a secret, a cookie,
  browser storage state, raw PII, or a full
  connection string.
- Any change that weakens the
  `SanitizeAlertPayload` contract from
  `US-041` or the audit retention guarantee
  from `NFR-SEC-008`.
- Any change that bypasses the existing
  `AuditService` from `US-026` or the
  existing `SanitizeAlertPayload` helper
  from `US-041`.
- Any change that adds a new value to the
  `AutoDisableTrigger` or
  `AutoDisableEventStatus` enum without
  first extending the `AutoDisableService`
  and the audit entry shape.
- Any change that bypasses the existing
  `EnvironmentMode` bound from `US-040` for
  the bounded window.
- Any change that bypasses the existing
  `ConnectorHealthService` from `US-046` for
  the `evaluate_source` health read.
- Any change that bypasses the existing
  `AlertEvaluator` from `US-041` for the
  `evaluate_source` alert read.
- Any change that bypasses the existing
  source registry from `US-003` for the
  per-source auto-disable rule and the
  per-source auto-disable event.
- Any auto-recovery (the slice ships a
  human-confirmed recovery flow only; the
  slice does not auto-flip a source back to
  `enabled`).
- Any change that weakens the
  `FR-SRC-004` rejection contract; the
  orchestrator must refuse to dispatch a
  discovery job against an `auto_disabled`
  source.

## Work Phases

1. Discovery — read `SPEC.md` §5.3
   (`FR-SRC-001..007`), `SPEC.md` §11
   (browser automation and responsible use),
   the `US-003` source registry contract,
   the `US-041` alerting contract, the
   `US-046` connector health contract, the
   `US-040` environment mode contract, the
   `US-026` audit log contract, the
   `US-004` discovery job lifecycle, and the
   `pilot-live-rollback-runbook.md` entry.
   Confirm the seams that the slice consumes
   are stable and reusable.
2. Design — define
   `ConnectorAutoDisableRule`,
   `ConnectorAutoDisableEvent`,
   `AutoDisableTrigger`,
   `AutoDisableEventStatus`,
   `AutoDisableThresholds`,
   `AutoDisableService`, `AutoDisableEvaluator`,
   and `AutoDisableOrchestrator`. Lock the
   sanitization contract to the existing
   `SanitizeAlertPayload` helper from
   `US-041` and refuse any rule, event, or
   audit entry that fails the filter. Lock
   the bounded window to the existing
   `EnvironmentMode` from `US-040`. Lock
   the bounded evaluation algorithm to
   `consecutive_breaches` and
   `cooldown_seconds` with the closed
   defaults documented in
   `AutoDisableThresholds`.
3. Validation planning — design a
   per-source test harness that runs a
   deterministic evaluation for a seeded
   source with a seeded
   `ConnectorHealthSnapshot` and a seeded
   `AlertEvent`, asserts the recorded event
   stays within the contract, and asserts
   the audit entry was written. Add a
   `POST
   /admin/connectors/{source_id}/auto-disable/evaluate`
   smoke test that an admin can run from
   the operator panel.
4. Implementation — add the migrations, the
   domain models, the `AutoDisableTrigger`
   and `AutoDisableEventStatus` enums, the
   `Source` extension, the
   `AutoDisableService`, the
   `AutoDisableEvaluator`, the
   `AutoDisableOrchestrator`, the
   source-side helper, the admin endpoints,
   the operator panel widget, the runbook
   entry, and the `scripts/verify-us-048.sh`
   harness. Reuse the existing
   `SanitizeAlertPayload` helper; do not
   introduce a parallel redaction helper.
5. Verification — run unit, integration,
   E2E, security, operational, and platform
   checks defined in `validation.md`. Run a
   deterministic evaluation for a seeded
   source and assert the recorded event
   stays within the contract. Assert the
   source-side helper returns
   `RUN_AUTO_DISABLED` for an
   `auto_disabled` source. Assert the
   recovery flow transitions the event to
   `recovering` and then to `resolved` and
   writes the audit entry.
6. Harness update — add the new product doc,
   the decision record, the durable story
   status, the `scripts/verify-us-048.sh`
   command, and a final trace. Capture any
   friction in the `harness_friction` field.

## Stop Conditions

Pause for human confirmation if:

- The story starts requiring a specific
  external runbook service (PagerDuty,
  Opsgenie, a managed Slack channel) to
  meet the acceptance criteria. This slice
  is local-first and tool-agnostic by design.
- Product direction becomes ambiguous between
  "human-confirmed recovery" and
  "auto-recovery after a clean
  `cooldown_seconds` window".
- Validation would need to weaken the
  `SanitizeAlertPayload` contract, the
  audit retention guarantee, or the existing
  `EnvironmentMode` bound from `US-040` to
  fit schedule.
- A new `AutoDisableTrigger` value is needed
  that cannot be justified from
  `FR-SRC-004` or `SPEC.md` 11.1; the value
  must be deferred or added to the spec in
  the same story with explicit acceptance
  criteria.
- A later story wants to ship a per-tenant
  rule template or an auto-recovery flow
  before this slice is implemented; in that
  case, the integration must wait until the
  local-first baseline is in place.
- The bounded window needs to weaken the
  existing `EnvironmentMode` bound from
  `US-040`; the slice must extend the
  bound, not redefine it.
- The per-source auto-disable rule needs to
  weaken the existing source registry from
  `US-003`; the slice must extend the source
  catalog, not redefine it.
- The evaluation needs to weaken the
  existing `ConnectorHealthService` from
  `US-046`; the slice must extend the
  surface, not redefine it.
- The evaluation needs to weaken the
  existing `AlertEvaluator` from `US-041`;
  the slice must extend the evaluator, not
  redefine it.
- The recovery flow needs to weaken the
  existing `FR-SRC-004` rejection contract;
  the orchestrator must continue to refuse
  to dispatch a discovery job against an
  `auto_disabled` source until a
  human-confirmed recovery transitions the
  event to `resolved`.
