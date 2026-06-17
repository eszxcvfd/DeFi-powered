# Validation

## Required Proof

| Layer | Expectation |
| --- | --- |
| Unit | `ConnectorHealthComputer.derive_metrics` reads the bounded `discovery_jobs` and `audit_entries` rows and returns the bounded metrics dataclass. `ConnectorHealthComputer.classify_status` maps the closed `success_rate` and `captcha_rate` thresholds to the closed `ConnectorHealthStatus` enum: `healthy` (success_rate ≥ `0.9` and captcha_rate ≤ `0.05`), `degraded` (success_rate in `[0.7, 0.9)` or captcha_rate in `(0.05, 0.2]`), `unhealthy` (success_rate `< 0.7` or captcha_rate `> 0.2`), `unknown` (no signals). `ConnectorHealthComputer.bounded_window` returns the bounded `(window_start, window_end)` pair. `SanitizeAlertPayload` strips keys, cookies, raw PII, browser storage state, and full connection strings from every snapshot, error, and audit entry before persistence. The `ConnectorHealthStatus` enum is closed; unknown statuses return `CONNECTOR_HEALTH_INVALID_STATUS`. |
| Integration | `GET /admin/connectors/health/summary` returns the latest snapshot per source with the status, success rate, last run, and CAPTCHA rate. `GET /admin/connectors/health/snapshots?source_id=&status=&limit=&offset=` returns paginated snapshot history with sanitized payloads. `POST /admin/connectors/health/snapshots:compute` executes a bounded, confirmation-gated per-source computation and returns the result inline. `GET /admin/connectors/{source_id}/health/errors?limit=` returns the recent error rollup for the source detail surface. The bounded window is enforced by the `EnvironmentMode` from `US-040` (max 24 hours in `pilot_live`, max 1 hour in `test_like`); a window that exceeds the bound is clipped to the bound. Every snapshot computation, summary request, and recent-errors request emits a durable audit entry with the same secret-safe payload contract as `US-026` and `US-041`. |
| E2E | An authenticated owner can open the new operator panel, see the per-source health summary, see the `ConnectorHealthStatus` badge, run a single per-source computation, see the result inline, and acknowledge the result. The bounded verification harness runs a deterministic computation for a seeded source and asserts the recorded snapshot stays within the contract. The bounded window is exercised end-to-end by a computation that exceeds the `EnvironmentMode` bound; the computation is clipped to the bound and a `connector.health.snapshot.computed` audit entry is written. The migration is exercised end-to-end by the verify script so a missing `connector_health_snapshots` table or a missing `connector_health_errors` table fails the E2E check, not just the data check. |
| Security | Direct API calls to the new endpoints with viewer, analyst, sales, and reviewer sessions are rejected with the same error envelope as the existing admin surfaces. Sanitizer tests prove that snapshots and audit entries carrying API keys, cookies, raw PII, browser storage state, and full connection strings are rejected or redacted before persistence. The bounded computation refuses to read signals for a source that does not exist. The bounded window refuses zero or negative values. The new `ConnectorHealthStatus` enum does not weaken the existing `AlertMetric` enum from `US-041` or the existing `MetricRegistry` from `US-042`. The migration does not weaken the existing audit retention guarantee from `NFR-SEC-008`. |
| Operational | A runbook entry for the connector health domain documents what an operator does when a connector flips to `degraded` or `unhealthy`, when a CAPTCHA rate breaches the threshold, and when a user reports a missing connector. The verification script proves that the bounded verification harness can run a deterministic computation for a seeded source and assert the recorded snapshot stays within the contract. The new endpoints are covered by the health probe contract from `US-040`: a missing or failing `GET /admin/connectors/health/summary` must not fail `GET /health/ready`, only surface as a degraded warning. |
| Platform | The `scripts/verify-us-046.sh` command wires the unit, integration, E2E, security, and operational checks together and is the same command run by `harness-cli story verify` and `harness-cli story verify-all`. The `connector_health_snapshots` and `connector_health_errors` migrations are exercised by the verify script so a missing table fails the platform check, not just the data check. The new `ConnectorHealthStatus` enum and the new audit entry types are exercised by the verify script so a missing enum value fails the platform check, not just the data check. |

## Suggested Checks

- Backend unit tests for:
  - `ConnectorHealthComputer.derive_metrics`
  - `ConnectorHealthComputer.classify_status`
  - `ConnectorHealthComputer.bounded_window`
  - `ConnectorHealthService.compute_snapshot`
  - `ConnectorHealthService.list_snapshots`
  - `ConnectorHealthService.build_summary`
  - `ConnectorHealthService.list_recent_errors`
  - `SanitizeAlertPayload` reuse for every
    snapshot, error, and audit entry
  - `ConnectorHealthStatus` enum closure
  - `EnvironmentMode` bound for the bounded
    window
  - `MetricRegistry` extension
  - `AlertMetric` enum extension
- Backend integration tests for:
  - `GET /admin/connectors/health/summary`
  - `GET /admin/connectors/health/snapshots`
  - `POST /admin/connectors/health/snapshots:compute`
  - `GET /admin/connectors/{source_id}/health/errors`
  - Cross-tenant denial for every new endpoint
  - Audit entries for every successful and
    failed computation, summary, and
    recent-errors request
- E2E tests for:
  - Operator panel renders the per-source
    health summary, the `ConnectorHealthStatus`
    badge, and the `Compute snapshot` button.
  - The bounded verification harness runs a
    deterministic computation for a seeded
    source and asserts the recorded snapshot
    stays within the contract.
  - The bounded window is exercised end-to-end
    by a computation that exceeds the
    `EnvironmentMode` bound; the computation is
    clipped to the bound.
  - The migrations are exercised by the
    verify script.
- Security tests for:
  - Role enforcement on every new endpoint.
  - Snapshot, error, and audit entry
    sanitization for every new write path.
  - The bounded computation refuses to read
    signals for a source that does not exist.
  - The bounded window refuses zero or
    negative values.
- Operational checks for:
  - The bounded verification harness can run
    a deterministic computation for a seeded
    source and assert the recorded snapshot
    stays within the contract.
  - The new endpoints are covered by the
    health probe contract from `US-040`.
  - The runbook entry exists and references
    the right surfaces.
- Platform proof is the
  `scripts/verify-us-046.sh` command wired
  into `harness-cli story verify` and
  `harness-cli story verify-all`.

## Evidence Hooks

- `tests/unit/test_connector_health_computer.py`
  — computer unit tests
- `tests/unit/test_connector_health_service.py`
  — service unit tests
- `tests/unit/test_connector_health_status_enum.py`
  — `ConnectorHealthStatus` enum closure
- `tests/unit/test_connector_health_window_bound.py`
  — `EnvironmentMode` bound for the bounded
  window
- `tests/unit/test_connector_health_metric_registry.py`
  — `MetricRegistry` extension
- `tests/unit/test_connector_health_alert_metric.py`
  — `AlertMetric` enum extension
- `tests/unit/test_connector_health_audit_sanitizer.py`
  — `SanitizeAlertPayload` reuse for every
  snapshot, error, and audit entry
- `tests/integration/test_connector_health_api.py`
  — REST surface integration tests
- `tests/integration/test_connector_health_audit.py`
  — audit entry integration tests
- `tests/integration/test_connector_health_window.py`
  — bounded window integration tests
- `tests/security/test_connector_health_role_gates.py`
  — RBAC contract from `US-027`
- `tests/security/test_connector_health_sanitizer.py`
  — secret-safe payload contract
- `tests/e2e/connector_health.py`
  — operator panel, compute button, and
  bounded window
- `frontend/e2e/connector-health.spec.ts`
  — frontend e2e
- `scripts/verify-us-046.sh`
  — bounded verification harness
- `docs/ops/connector-health-runbook.md`
  (operational entry)
- `docs/product/connector-health-surface.md`
  (living product contract)
- `docs/decisions/0024-connector-health-surface-baseline.md`
  (durable decision record)

## Open Questions

- Should the bounded window be configurable
  per workspace, or should it always follow
  the closed `EnvironmentMode` bound from
  `US-040`? The first implementation follows
  the closed bound; per-workspace tuning is a
  follow-on story.
- Should the `ConnectorHealthStatus` enum
  include a `paused` value, or should a paused
  connector return `unknown`? The first
  implementation returns `unknown`; a follow-on
  story can add `paused` with explicit
  acceptance criteria.
- Should the bounded computation read
  browser-session or browser-debug rows, or
  should it stay scoped to `discovery_jobs`
  and `audit_entries`? The first implementation
  stays scoped; a follow-on story can extend
  the computation to read those rows behind
  the same `ConnectorHealthComputer` seam.
- Should the bounded computation run on a
  periodic worker tick, or should it stay
  bounded to explicit
  `POST /admin/connectors/health/snapshots:compute`
  requests? The first implementation stays
  bounded to explicit requests; a follow-on
  story can add a periodic tick behind the
  same `ConnectorHealthService` seam.
- Should the operator panel widget expose a
  bulk compute action, or should the widget
  only expose the per-source `Compute snapshot`
  button? The first implementation exposes the
  per-source button; a follow-on story can add
  the bulk action behind the same RBAC
  contract.
