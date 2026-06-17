# Validation

## Required Proof

| Layer | Expectation |
| --- | --- |
| Unit | `AutoDisableEvaluator.evaluate_rule` reads the bounded `ConnectorHealthSnapshot` and `AlertEvent` rows and returns the bounded `AutoDisableEvaluationResult` dataclass. `AutoDisableEvaluator.count_consecutive_breaches` returns the closed `consecutive_breaches` counter. `AutoDisableEvaluator.in_cooldown` returns the bounded `cooldown_seconds` window. `AutoDisableEvaluator.bounded_window` returns the bounded `(window_start, window_end)` pair. `AutoDisableService.evaluate_source` applies the closed trigger rules with the `consecutive_breaches` and `cooldown_seconds` bounds. `AutoDisableService.recover_source` transitions the event from `active` to `recovering` and writes the audit entry. `evaluate_source_for_discovery` returns `RUN_ALLOWED`, `RUN_AUTO_DISABLED`, or `RUN_MANUAL_DISABLED`. `SanitizeAlertPayload` strips keys, cookies, raw PII, browser storage state, and full connection strings from every rule, event, and audit entry before persistence. The `AutoDisableTrigger` and `AutoDisableEventStatus` enums are closed; unknown values return `AUTO_DISABLE_RULE_INVALID`. |
| Integration | `GET /admin/connectors/auto-disable/rules` returns the paginated rule list with sanitized payloads. `POST /admin/connectors/auto-disable/rules` creates a rule after validation against the closed enums and the `EnvironmentMode` bound; a `window_seconds` that exceeds the bound returns `AUTO_DISABLE_RULE_INVALID_WINDOW`. `GET /admin/connectors/auto-disable/rules/{id}` returns a single rule with the sanitized payload. `PATCH /admin/connectors/auto-disable/rules/{id}` updates threshold, window, `consecutive_breaches`, `cooldown_seconds`, and `enabled` state. `DELETE /admin/connectors/auto-disable/rules/{id}` soft-deletes the rule. `GET /admin/connectors/auto-disable/events` returns paginated event history with sanitized payloads. `POST /admin/connectors/auto-disable/events/{id}/recover` transitions the event to `recovering` and writes the audit entry; a recovery action on a non-`active` event returns `AUTO_DISABLE_RECOVERY_REJECTED`. `POST /admin/connectors/{source_id}/auto-disable/evaluate` triggers a bounded evaluation cycle and returns the result inline. The bounded window is enforced by the `EnvironmentMode` from `US-040` (max 24 hours in `pilot_live`, max 1 hour in `test_like`); a window that exceeds the bound is clipped to the bound. Every rule create / update / delete, every trigger, every recovery, and every rejected evaluation emits a durable audit entry with the same secret-safe payload contract as `US-026` and `US-041`. The source-side helper refuses to run a discovery job against an `auto_disabled` source; the orchestrator from `US-004` / `US-032` / `US-033` / `US-034` honors the bounded rejection code `SOURCE_AUTO_DISABLED`. |
| E2E | An authenticated owner can open the new operator panel, see the per-source rule list, see the per-source event list, run a single bounded evaluation cycle, see the result inline, and acknowledge the result. The bounded verification harness runs a deterministic evaluation for a seeded source with a seeded `ConnectorHealthSnapshot` and a seeded `AlertEvent`, asserts the recorded event stays within the contract, and asserts the audit entry was written. The bounded recovery flow is exercised end-to-end: a `recover_source` action transitions the event to `recovering`; the next evaluation cycle transitions the event to `resolved` and clears `Source.auto_disabled_at`, `Source.auto_disabled_reason`, and `Source.auto_disabled_by_event_id`. The bounded window is exercised end-to-end by an evaluation cycle whose `window_seconds` exceeds the `EnvironmentMode` bound; the evaluation is clipped to the bound and a `connector.auto_disable.evaluation.rejected` audit entry is written. The migration is exercised end-to-end by the verify script so a missing `connector_auto_disable_rules` table, a missing `connector_auto_disable_events` table, or a missing `Source.auto_disabled_at` column fails the E2E check, not just the data check. |
| Security | Direct API calls to the new endpoints with viewer, analyst, sales, and reviewer sessions are rejected with the same error envelope as the existing admin surfaces. Sanitizer tests prove that rules, events, and audit entries carrying API keys, cookies, raw PII, browser storage state, and full connection strings are rejected or redacted before persistence. The bounded evaluation refuses to read signals for a source that does not exist. The bounded window refuses zero or negative values. The bounded `cooldown_seconds` window refuses negative values. The new `AutoDisableTrigger` and `AutoDisableEventStatus` enums do not weaken the existing `AlertMetric` enum from `US-041`, the existing `MetricRegistry` from `US-042`, or the existing `ConnectorHealthStatus` enum from `US-046`. The migration does not weaken the existing audit retention guarantee from `NFR-SEC-008`. The bounded `evaluate_source_for_discovery` helper refuses to be called outside the orchestrator seam; the helper is rejected with `SOURCE_AUTO_DISABLED` only when the source is `auto_disabled`. |
| Operational | A runbook entry for the connector auto-disable domain documents what an operator does when a source flips to `auto_disabled`, when a `captcha_rate_breach` fires, when a `failure_rate_breach` fires, when a `needs_user_action_storm` fires, and when a recovery action is denied because the cooldown has not elapsed. The verification script proves that the bounded verification harness can run a deterministic evaluation for a seeded source with a seeded `ConnectorHealthSnapshot` and a seeded `AlertEvent` and assert the recorded event stays within the contract. The new endpoints are covered by the health probe contract from `US-040`: a missing or failing `GET /admin/connectors/auto-disable/events` must not fail `GET /health/ready`, only surface as a degraded warning. The bounded `AutoDisableOrchestrator` actor is wired into the existing scheduler tick from `US-035`; the actor emits a `connector.auto_disable.evaluation.rejected` audit entry on a sanitization rejection. |
| Platform | The `scripts/verify-us-048.sh` command wires the unit, integration, E2E, security, and operational checks together and is the same command run by `harness-cli story verify` and `harness-cli story verify-all`. The `connector_auto_disable_rules` and `connector_auto_disable_events` migrations are exercised by the verify script so a missing table fails the platform check, not just the data check. The `Source.auto_disabled_at` column migration is exercised by the verify script so a missing column fails the platform check, not just the data check. The new `AutoDisableTrigger` and `AutoDisableEventStatus` enums and the new audit entry types are exercised by the verify script so a missing enum value fails the platform check, not just the data check. |

## Suggested Checks

- Backend unit tests for:
  - `AutoDisableEvaluator.evaluate_rule`
  - `AutoDisableEvaluator.count_consecutive_breaches`
  - `AutoDisableEvaluator.in_cooldown`
  - `AutoDisableEvaluator.bounded_window`
  - `AutoDisableService.evaluate_source`
  - `AutoDisableService.list_rules`
  - `AutoDisableService.create_rule`
  - `AutoDisableService.update_rule`
  - `AutoDisableService.delete_rule`
  - `AutoDisableService.list_events`
  - `AutoDisableService.recover_source`
  - `evaluate_source_for_discovery` source-side
    helper
  - `SanitizeAlertPayload` reuse for every
    rule, event, and audit entry
  - `AutoDisableTrigger` enum closure
  - `AutoDisableEventStatus` enum closure
  - `EnvironmentMode` bound for the bounded
    window
  - `MetricRegistry` extension
  - `AlertMetric` enum extension
  - `ConnectorHealthStatus` enum reuse
- Backend integration tests for:
  - `GET /admin/connectors/auto-disable/rules`
  - `POST /admin/connectors/auto-disable/rules`
  - `GET /admin/connectors/auto-disable/rules/{id}`
  - `PATCH /admin/connectors/auto-disable/rules/{id}`
  - `DELETE /admin/connectors/auto-disable/rules/{id}`
  - `GET /admin/connectors/auto-disable/events`
  - `POST /admin/connectors/auto-disable/events/{id}/recover`
  - `POST /admin/connectors/{source_id}/auto-disable/evaluate`
  - Cross-tenant denial for every new
    endpoint
  - Audit entries for every successful and
    failed rule, trigger, recovery, and
    evaluation
  - `SOURCE_AUTO_DISABLED` rejection from
    the source-side helper
  - Bounded window enforcement
  - Bounded recovery flow
- E2E tests for:
  - Operator panel renders the per-source
    rule list, the per-source event list,
    the `AutoDisableTrigger` badge, the
    `AutoDisableEventStatus` badge, the
    `Recover` button, the
    `Compute evaluation` button, and the
    `Create rule` button.
  - The bounded verification harness runs
    a deterministic evaluation for a
    seeded source and asserts the recorded
    event stays within the contract.
  - The bounded recovery flow is exercised
    end-to-end.
  - The bounded window is exercised
    end-to-end.
  - The migrations are exercised by the
    verify script.
- Security tests for:
  - Role enforcement on every new
    endpoint.
  - Rule, event, and audit entry
    sanitization for every new write path.
  - The bounded evaluation refuses to read
    signals for a source that does not
    exist.
  - The bounded window refuses zero or
    negative values.
  - The bounded `cooldown_seconds` window
    refuses negative values.
- Operational checks for:
  - The bounded verification harness can
    run a deterministic evaluation for a
    seeded source with a seeded
    `ConnectorHealthSnapshot` and a seeded
    `AlertEvent` and assert the recorded
    event stays within the contract.
  - The new endpoints are covered by the
    health probe contract from `US-040`.
  - The runbook entry exists and references
    the right surfaces.
  - The bounded `AutoDisableOrchestrator`
    actor is wired into the existing
    scheduler tick from `US-035`.
- Platform proof is the
  `scripts/verify-us-048.sh` command wired
  into `harness-cli story verify` and
  `harness-cli story verify-all`.

## Evidence Hooks

- `tests/unit/test_auto_disable_evaluator.py`
  — evaluator unit tests
- `tests/unit/test_auto_disable_service.py`
  — service unit tests
- `tests/unit/test_auto_disable_trigger_enum.py`
  — `AutoDisableTrigger` enum closure
- `tests/unit/test_auto_disable_event_status_enum.py`
  — `AutoDisableEventStatus` enum closure
- `tests/unit/test_auto_disable_window_bound.py`
  — `EnvironmentMode` bound for the bounded
  window
- `tests/unit/test_auto_disable_metric_registry.py`
  — `MetricRegistry` extension
- `tests/unit/test_auto_disable_alert_metric.py`
  — `AlertMetric` enum extension
- `tests/unit/test_auto_disable_connector_health_status.py`
  — `ConnectorHealthStatus` enum reuse
- `tests/unit/test_auto_disable_audit_sanitizer.py`
  — `SanitizeAlertPayload` reuse for every
  rule, event, and audit entry
- `tests/unit/test_evaluate_source_for_discovery.py`
  — source-side helper unit tests
- `tests/integration/test_auto_disable_api.py`
  — REST surface integration tests
- `tests/integration/test_auto_disable_audit.py`
  — audit entry integration tests
- `tests/integration/test_auto_disable_window.py`
  — bounded window integration tests
- `tests/integration/test_auto_disable_recovery.py`
  — bounded recovery flow integration tests
- `tests/integration/test_auto_disable_orchestrator.py`
  — `AutoDisableOrchestrator` actor
  integration tests
- `tests/integration/test_source_auto_disabled_helper.py`
  — source-side helper integration tests
- `tests/security/test_auto_disable_role_gates.py`
  — RBAC contract from `US-027`
- `tests/security/test_auto_disable_sanitizer.py`
  — secret-safe payload contract
- `tests/e2e/auto_disable.py`
  — operator panel, recovery flow, and
  bounded window
- `frontend/e2e/auto-disable.spec.ts`
  — frontend e2e
- `scripts/verify-us-048.sh`
  — bounded verification harness
- `docs/ops/connector-auto-disable-runbook.md`
  (operational entry)
- `docs/product/connector-auto-disable-and-recovery.md`
  (living product contract)
- `docs/decisions/0026-connector-auto-disable-and-policy-recovery-baseline.md`
  (durable decision record)

## Open Questions

- Should the bounded window be configurable
  per workspace, or should it always follow
  the closed `EnvironmentMode` bound from
  `US-040`? The first implementation follows
  the closed bound; per-workspace tuning is a
  follow-on story.
- Should the `AutoDisableTrigger` enum
  include a `manual_kill_switch` value, or
  should a manual kill switch be a separate
  `Source.disabled_reason` entry? The first
  implementation includes `manual_kill_switch`
  as a closed enum value; a follow-on story
  can add additional manual triggers with
  explicit acceptance criteria.
- Should the bounded evaluation read
  browser-session or browser-debug rows, or
  should it stay scoped to
  `ConnectorHealthSnapshot` and
  `AlertEvent`? The first implementation
  stays scoped; a follow-on story can extend
  the evaluation to read those rows behind
  the same `AutoDisableEvaluator` seam.
- Should the bounded evaluation run on a
  periodic worker tick, or should it stay
  bounded to explicit
  `POST
  /admin/connectors/{source_id}/auto-disable/evaluate`
  requests? The first implementation runs on
  a periodic worker tick (the bounded
  `AutoDisableOrchestrator` actor is wired
  into the existing scheduler tick from
  `US-035`); a follow-on story can disable
  the periodic tick per workspace.
- Should the operator panel widget expose a
  bulk recovery action, or should the widget
  only expose the per-event `Recover`
  button? The first implementation exposes
  the per-event button; a follow-on story
  can add the bulk action behind the same
  RBAC contract.
- Should the bounded `cooldown_seconds`
  window be configurable per rule, or should
  it always follow the closed default? The
  first implementation allows per-rule
  configuration; a follow-on story can lock
  the cooldown to the closed default per
  workspace.
