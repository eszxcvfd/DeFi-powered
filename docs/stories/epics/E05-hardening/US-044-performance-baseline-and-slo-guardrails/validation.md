# Validation

## Required Proof

| Layer | Expectation |
| --- | --- |
| Unit | `PerformanceBaselineService.run_scenario` validates the scenario against the closed `PerformanceScenario` enum, executes a deterministic in-process scenario, records a `performance_snapshots` row, and emits a `performance.scenario.completed` audit entry. `PerformanceBaselineService.list_snapshots` returns the most recent snapshots for the operator panel and the verify script. `PerformanceBaselineService.build_summary` returns the latest snapshot per scenario with the SLO budget, the current percentile, and the breach flag. `BrowserSessionBudgetEnforcer.record_sample` records a `memory_rss_mb` and a `cpu_pct` sample, stops the session safely when the budget is exceeded, and emits a `browser.session.budget_exceeded` audit entry. `SanitizeAlertPayload` strips keys, cookies, raw PII, browser storage state, and full connection strings from every snapshot and audit entry before persistence. The SLO alert rule set is registered with the `US-041` `AlertMetric` enum and the `US-042` `MetricRegistry`; the seed SLO rules are `is_system = true` and cannot be deleted through the management API. |
| Integration | `GET /admin/performance/summary` returns the latest snapshot per scenario with the SLO budget, the current percentile, and the breach flag. `GET /admin/performance/snapshots?scenario=` returns paginated snapshot history with sanitized payloads. `POST /admin/performance/scenarios:run` executes a deterministic in-process scenario and returns the result inline. The SLO alert rules are evaluated by the existing `AlertEvaluator` from `US-041` and the existing `MetricsExporter` from `US-042` exports the new performance metrics. The browser session worker from `US-020` records `memory_rss_mb` and `cpu_pct` samples and stops the session safely when the budget is exceeded. Every scenario run, SLO alert rule firing, and browser session budget breach emits a durable audit entry with the same secret-safe payload contract as `US-026` and `US-041`. |
| E2E | An authenticated owner can open the new operator panel, see the SLO summary, run a single in-process scenario, see the result inline, and acknowledge the result. The bounded load-test harness runs a deterministic scenario for each NFR-PERF target and asserts the recorded snapshot stays within the SLO budget. The browser session budget enforcement path is exercised end-to-end by a session that exceeds the budget; the session is stopped safely and a `browser.session.budget_exceeded` audit entry is written. The migration is exercised end-to-end by the verify script so a missing `performance_snapshots` table fails the E2E check, not just the data check. |
| Security | Direct API calls to the new endpoints with viewer, analyst, sales, and reviewer sessions are rejected with the same error envelope as the existing admin surfaces. Sanitizer tests prove that snapshots and audit entries carrying API keys, cookies, raw PII, browser storage state, and full connection strings are rejected or redacted before persistence. The bounded scenario runner refuses to run against real external providers. The browser session budget enforcement path refuses to stop a session that is in the middle of a confirmation-gated action. The migration does not weaken the existing audit retention guarantee from `NFR-SEC-008`. The new `PerformanceMetric` enum does not weaken the existing `AlertMetric` enum from `US-041` or the existing `MetricRegistry` from `US-042`. |
| Operational | A runbook entry for the performance baseline domain documents what an operator does when an SLO alert fires and when a browser session budget breach is recorded. The verification script proves that the bounded load-test harness can run a deterministic scenario for each NFR-PERF target and assert the recorded snapshot stays within the SLO budget. The browser session budget enforcement path records the `memory_rss_mb` and `cpu_pct` samples in the audit log so an operator can reconstruct the breach. The SLO summary endpoint is itself covered by the health probe contract from `US-040`: a missing or failing summary must not fail `GET /health/ready`, only surface as a degraded warning. |
| Platform | The `scripts/verify-us-044.sh` command wires the unit, integration, E2E, security, and operational checks together and is the same command run by `harness-cli story verify` and `harness-cli story verify-all`. The `performance_snapshots` migration is exercised by the verify script so a missing table fails the platform check, not just the data check. The new `PerformanceMetric` enum and the seed SLO rules are exercised by the verify script so a missing enum value fails the platform check, not just the data check. |

## Suggested Checks

- Backend unit tests for:
  - `PerformanceBaselineService.run_scenario`
  - `PerformanceBaselineService.list_snapshots`
  - `PerformanceBaselineService.build_summary`
  - `BrowserSessionBudgetEnforcer.record_sample`
  - `BrowserSessionBudgetEnforcer.build_session_summary`
  - `SanitizeAlertPayload` reuse for every
    snapshot and audit entry
  - SLO alert rule set registration
  - `PerformanceMetric` enum extension
- Backend integration tests for:
  - `GET /admin/performance/summary`
  - `GET /admin/performance/snapshots`
  - `POST /admin/performance/scenarios:run`
  - SLO alert rule evaluation through the
    existing `AlertEvaluator` from `US-041`
  - Performance metric export through the
    existing `MetricsExporter` from `US-042`
  - Browser session budget enforcement through
    the existing browser session worker from
    `US-020`
  - Audit entries for every scenario run, SLO
    alert rule firing, and browser session
    budget breach
- E2E tests for:
  - Operator panel renders the SLO summary, the
    most recent snapshots, and the `Run
    scenario` button.
  - The bounded load-test harness runs a
    deterministic scenario for each NFR-PERF
    target and asserts the recorded snapshot
    stays within the SLO budget.
  - The browser session budget enforcement
    path is exercised end-to-end by a session
    that exceeds the budget.
  - The migration is exercised by the verify
    script.
- Security tests for:
  - Role enforcement on every new endpoint.
  - Snapshot and audit entry sanitization for
    every new write path.
  - Bounded scenario runner refuses to run
    against real external providers.
  - Browser session budget enforcement path
    refuses to stop a session that is in the
    middle of a confirmation-gated action.
- Operational checks for:
  - The bounded load-test harness can run a
    deterministic scenario for each NFR-PERF
    target and assert the recorded snapshot
    stays within the SLO budget.
  - The browser session budget enforcement
    path records the `memory_rss_mb` and
    `cpu_pct` samples in the audit log.
  - The SLO summary endpoint is covered by
    the health probe contract from `US-040`.
  - The runbook entry exists and references
    the right surfaces.
- Platform proof is the
  `scripts/verify-us-044.sh` command wired into
  `harness-cli story verify` and
  `harness-cli story verify-all`.

## Evidence Hooks

- `tests/unit/test_performance_baseline_service.py`
  — service unit tests
- `tests/unit/test_browser_session_budget.py` —
  browser session budget enforcement unit tests
- `tests/unit/test_performance_metric_enum.py` —
  `PerformanceMetric` enum extension
- `tests/unit/test_slo_alert_rules.py` — SLO
  alert rule registration
- `tests/integration/test_performance_api.py`
- `tests/integration/test_slo_alert_evaluation.py`
- `tests/integration/test_browser_session_budget_api.py`
- `tests/security/test_performance_role_gates.py`
- `tests/security/test_performance_sanitizer.py`
- `tests/e2e/performance_baseline_slo.py`
- `frontend/e2e/performance-panel.spec.ts`
- `scripts/verify-us-044.sh`
- `docs/ops/performance-baseline-runbook.md`
  (operational entry)
- `docs/product/performance-baseline-and-slo-guardrails.md`
  (living product contract)
- `docs/decisions/0022-performance-baseline-and-slo-guardrails.md`
  (durable decision record)

## Open Questions

- Should the bounded load-test harness support
  a custom scenario list, or should it always
  run the closed `PerformanceScenario` enum?
  The first implementation runs the closed
  enum; a follow-on story can add per-tenant
  custom scenarios.
- Should the SLO alert rule thresholds be
  tunable per tenant, or should they always
  follow the closed `NFR-PERF-001..005` values?
  The first implementation follows the closed
  values; per-tenant tuning is a follow-on
  story.
- Should the browser session budget enforcement
  path support a grace period before the
  session is stopped, or should the session be
  stopped immediately when the budget is
  exceeded? The first implementation stops the
  session immediately; a follow-on story can
  add a grace period.
- Should the bounded scenario runner return
  the result inline, or should it return a
  `scenario_run_id` and let the caller poll
  for the result? The first implementation
  returns the result inline; a follow-on
  story can add a polling mode for long
  scenarios.
- Should the SLO summary endpoint support a
  custom time window, or should it always
  return the latest snapshot per scenario? The
  first implementation returns the latest
  snapshot per scenario; a follow-on story
  can add a custom time window.
