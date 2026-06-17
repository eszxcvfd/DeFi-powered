# Performance Baseline And SLO Guardrails

Source: `SPEC.md` sections 10.1 (`NFR-PERF-001..005`),
14.2, 17, and the deferred performance baseline
listed as a follow-up in
`docs/decisions/0019-observability-and-alerting-baseline.md`
and `docs/decisions/0020-external-metrics-pipeline-baseline.md`.

## Product Goal

`US-041` shipped the first operational observability
and alerting baseline for LiveLead. The slice
introduced six seed rules for backup freshness,
worker heartbeat, connector failure rate,
discovery `NEEDS_USER_ACTION` storms, browser crash
loops, and audit retention risk. The slice
deliberately stopped at the operational signals
and carved the performance baseline out as a
follow-up.

`US-042` shipped the first external metrics pipeline
baseline. The slice introduced a `MetricRegistry`
that mirrors the closed `SignalProvider` enum from
`US-041` and an `ExportTransport` Protocol with
three concrete transports. The slice deliberately
stopped at the operational metrics and carved the
performance metrics out as a follow-up.

This product slice is the first step toward the
performance side of the observability contract. It
is a supporting governance slice for the core MVP
jobs in `docs/product/mvp-scope-and-priorities.md`,
not a new primary value track by itself.

The slice is local-first and tool-agnostic by
design. It does not commit to a specific load
testing tool (Locust, k6, Locust Cloud, k6 Cloud)
in this step; it preserves a stable seam for a
later deployment story to wire one.

## MVP Scope

This product slice covers:

- A durable `PerformanceSnapshot` table that
  records every bounded load-test scenario result
  with `started_at`, `completed_at`, `scenario`,
  `p50_ms`, `p95_ms`, `p99_ms`, `rps`,
  `error_rate`, `concurrent_users`, and
  `audit_correlation_id`.
- A closed `PerformanceMetric` enum that extends
  the `US-041` `AlertMetric` enum and the
  `US-042` `MetricRegistry` with five new metrics:
  - `api.read.latency_ms` (NFR-PERF-001)
  - `event.list.pagination.latency_ms`
    (NFR-PERF-002)
  - `discovery.first_progress_ms` (NFR-PERF-003)
  - `concurrency.users` (NFR-PERF-004)
  - `browser.session.budget_pct` (NFR-PERF-005)
- A `PerformanceBaselineService` that exposes the
  bounded operations:
  - `run_scenario(scenario)` — executes a
    deterministic, in-process load scenario
    against an in-memory SQLite plus a stubbed
    external provider, records the
    `performance_snapshots` row, and emits a
    `performance.scenario.completed` audit
    entry.
  - `list_snapshots(scenario?)` — returns the
    most recent snapshots for the operator
    panel and the verify script.
  - `build_summary` — returns the latest
    snapshot per scenario with the SLO budget,
    the current percentile, and the breach
    flag.
- A `BrowserSessionBudgetEnforcer` that records
  `memory_rss_mb` and `cpu_pct` samples at session
  start, every 30 seconds during the session, and
  at session end. When a sample exceeds the
  configured budget, the session is stopped
  safely and a `browser.session.budget_exceeded`
  audit entry is written.
- A new seed SLO alert rule set in the `US-041`
  migration. The rules are `is_system = true`
  and owners/admins can tune the thresholds but
  cannot delete the system rules:
  - `api.read.slo_breach`
  - `event.list.pagination.slo_breach`
  - `discovery.first_progress.slo_breach`
  - `concurrency.cap.slo_breach`
  - `browser.session.budget.slo_breach`
- A new owner/admin-only REST surface:
  - `GET /admin/performance/summary`
  - `GET /admin/performance/snapshots?scenario=`
  - `POST /admin/performance/scenarios:run`
- A new bounded load-test harness in
  `scripts/verify-us-044.sh` that runs a
  deterministic scenario for each NFR-PERF target
  and asserts the recorded snapshot stays within
  the SLO budget.
- A new runbook
  (`docs/ops/performance-baseline-runbook.md`)
  that documents what an operator does when an
  SLO alert fires.

This product slice does not yet cover:

- Distributed tracing, APM, and call-graph
  analysis across the modular monolith. This
  story ships the contract, not a UI.
- External SLO tooling (Prometheus RuleFiles,
  Datadog SLO, Sentry Performance). The slice
  reuses the `MetricsExporter` from `US-042`
  and the `AlertEvaluator` from `US-041`; a
  later story can wire an external SLO consumer
  behind the same contract.
- Auto-remediation or self-healing actions
  driven by an SLO breach. The SLO alert rules
  are advisory, not authoritative.
- Customer-facing status pages or external
  incident communication.
- Load testing against real external providers.
  The bounded load-test harness runs against
  in-memory SQLite plus stubbed external
  providers so the contract is reviewable in
  CI.
- Replacing the existing browser session
  lifecycle from `US-020`. This story extends
  it with the budget enforcement path.
- Per-tenant SLO budgets. The slice ships one
  fixed default set; per-tenant tuning is a
  follow-on story.

## Contract Rules

- All new admin endpoints require an
  authenticated session with `owner` or
  `admin` role. Viewer, analyst, sales, and
  reviewer roles get no access to the
  performance summary or the scenario runner.
- The bounded scenario runner refuses to run
  against real external providers. The harness
  runs against an in-memory SQLite plus a
  stubbed external provider so the contract
  is reviewable in CI.
- The SLO alert rules are advisory, not
  authoritative. The rules emit audit entries
  through the existing notification dispatcher
  from `US-029`; they do not pause jobs,
  disable connectors, flip live toggles, or
  roll back the environment.
- The browser session budget enforcement path
  refuses to stop a session that is in the
  middle of a confirmation-gated action. The
  slice extends the existing browser session
  lifecycle from `US-020`; it does not
  redefine it.
- The `SanitizeAlertPayload` helper from
  `US-041` runs on every payload before it is
  persisted on `performance_snapshots` or on
  the audit entries.
- The scenario runner, the SLO alert rules,
  and the browser session budget enforcement
  path emit `performance.*` and
  `browser.session.budget_exceeded` audit
  entries using the same secret-safe payload
  contract as `US-026` and `US-041`.
- The `performance_snapshots` table never
  stores secret material, cookies, raw PII,
  or full connection strings. The SLO summary
  endpoint is covered by the health probe
  contract from `US-040`: a missing or failing
  summary must not fail `GET /health/ready`,
  only surface as a degraded warning.

## Supported Scenarios

| Scenario | NFR | SLO Budget | Default Threshold | Default Severity |
| --- | --- | --- | --- | --- |
| `api_read_latency` | NFR-PERF-001 | 95th percentile < 500 ms | `> 500 ms` over 300 s | `warning` |
| `event_list_pagination` | NFR-PERF-002 | 95th percentile < 2 000 ms | `> 2 000 ms` over 600 s | `warning` |
| `discovery_first_progress` | NFR-PERF-003 | 95th percentile < 5 000 ms | `> 5 000 ms` over 300 s | `warning` |
| `concurrency_cap` | NFR-PERF-004 | Rolling count < 100 | `> 100` over 60 s | `warning` |
| `browser_session_budget` | NFR-PERF-005 | Rolling average < 90% | `> 90%` over 120 s | `critical` |

These are the seed defaults. Owners and admins can
adjust the threshold, window, severity, and
cooldown through the rule management endpoints;
per-tenant tuning is a follow-on story.

## Runtime And Admin Surface

- `GET /admin/performance/summary` — owner/admin
  only. Returns the latest snapshot per scenario
  with the SLO budget, the current percentile,
  and the breach flag.
- `GET /admin/performance/snapshots?scenario=` —
  owner/admin only. Returns paginated snapshot
  history with sanitized payloads.
- `POST /admin/performance/scenarios:run` —
  owner/admin only. Bounded, confirmation-gated
  scenario runner that executes a single
  in-process scenario and returns the result
  inline.

All new error responses follow the existing error
envelope (`code`, `message`, `request_id`,
`details`). Unknown scenarios, unknown metrics,
missing acceptance metadata, and budget
enforcement during a confirmation-gated action
return `PERFORMANCE_INVALID`,
`METRIC_NOT_REGISTERED`,
`PERFORMANCE_ACCEPTANCE_REQUIRED`, and
`BROWSER_BUDGET_CONFIRMATION_REQUIRED`
respectively.

## UI / Ops Surface

- The admin settings surface gains a
  `Performance` panel for owner/admin roles.
  The panel renders the SLO summary, the most
  recent snapshots, and a `Run scenario`
  button that executes a single in-process
  scenario and asserts the SLO contract.
- The in-app inbox from `US-029` shows
  `performance.slo_breach` and
  `browser.session.budget_exceeded` audit
  entries with a dedicated severity icon and
  a deep link to the operator panel.
- The first performance baseline runbook
  (`docs/ops/performance-baseline-runbook.md`)
  documents what an operator does when an
  SLO alert fires.

## Validation Implications

- Unit tests must prove that the bounded
  scenario runner validates the scenario
  against the closed enum, that the browser
  session budget enforcement path records
  the `memory_rss_mb` and `cpu_pct` samples,
  that the `SanitizeAlertPayload` helper
  strips secrets, cookies, raw PII, browser
  storage state, and full connection strings,
  and that the SLO alert rule set is
  registered with the `US-041` `AlertMetric`
  enum and the `US-042` `MetricRegistry`.
- Integration tests must exercise every new
  endpoint against an in-memory SQLite plus
  a stubbed external provider and prove that
  role gates, acceptance gates, and
  sanitization are enforced.
- E2E tests must cover the operator panel
  render, the bounded load-test harness, the
  browser session budget enforcement path,
  and the migration.
- Security tests must prove that viewer,
  analyst, sales, and reviewer sessions are
  rejected on every new endpoint, that
  payload sanitization holds, and that the
  bounded scenario runner refuses to run
  against real external providers.
- Operational tests must prove that the
  bounded load-test harness can run a
  deterministic scenario for each NFR-PERF
  target and assert the recorded snapshot
  stays within the SLO budget, and that the
  browser session budget enforcement path
  records the `memory_rss_mb` and `cpu_pct`
  samples in the audit log.
- Platform proof is the
  `scripts/verify-us-044.sh` command wired
  into `harness-cli story verify` and
  `harness-cli story verify-all`.
