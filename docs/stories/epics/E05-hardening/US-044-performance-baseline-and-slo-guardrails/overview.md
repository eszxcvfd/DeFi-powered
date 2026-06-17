# Overview

## Current Behavior

`US-001` through `US-043` delivered a broad MVP and the
first bounded hardening slices for LiveLead. The
product now has:

- A modular monolith with a Python API, a worker, a
  scheduler, a browser worker, a SQLite store, a
  Redis broker, and a React/TypeScript UI.
- A durable audit log (`US-026`), an identity and
  RBAC boundary (`US-027`), a member-management
  surface (`US-028`), and a notification surface
  (`US-029`).
- A first observability and alerting baseline
  (`US-041`) that ships six seed rules for backup
  freshness, worker heartbeat, connector failure
  rate, discovery `NEEDS_USER_ACTION` storms,
  browser crash loops, and audit retention risk.
- A first external metrics pipeline baseline
  (`US-042`) that exposes the same signals to a
  Prometheus scrape target, an OpenTelemetry
  collector, and a Sentry project.
- A planned backup and restore operations baseline
  (`US-043`) that turns the `BackupSnapshot`
  metadata into a bounded restore contract.

`SPEC.md` section 10.1 (`NFR-PERF-001..005`) commits
the product to a documented performance baseline:

- `NFR-PERF-001`: 95% of API read requests must
  respond within 500 ms, excluding job time and
  external dependencies.
- `NFR-PERF-002`: The event list page must load
  the first 10 000 events in 2 seconds at the
  target infrastructure baseline.
- `NFR-PERF-003`: A discovery job must stream
  its first progress event within 5 seconds of the
  worker accepting the job.
- `NFR-PERF-004`: The MVP must support at least
  100 concurrent UI users, 20 concurrent discovery
  jobs, and 10 concurrent browser sessions per
  browser-worker node.
- `NFR-PERF-005`: Every browser session must have a
  memory and CPU budget; when the budget is
  exceeded, the session must be stopped safely
  and the error must be logged.

The product still has no bounded performance
baseline slice:

- There is no SLO alert rule. The seed rule set
  from `US-041` covers operational signals (backup,
  heartbeat, connector, discovery, browser crash,
  audit retention) but not API latency, event
  list pagination, discovery job progress, or
  browser session budget.
- There is no performance snapshot. The observability
  summary endpoint from `US-041` reports the
  `LaunchGateReport` and the most recent alerts,
  but it does not report the SLO budget, the
  current percentile, or the trend.
- There is no bounded load-test harness. The
  acceptance criteria in `SPEC.md` section 14
  require E2E and performance tests, but the
  test matrix only records E2E coverage; there is
  no performance budget command in
  `scripts/verify-*.sh`.
- The `metric.exporter.duration_ms` and
  `alert.evaluator.duration_ms` counters in
  `US-042` record the exporter and evaluator
  duration, but no counter records the API read
  latency, the event list pagination latency, or
  the discovery job first-progress latency.
- `NFR-PERF-005` (browser session budget) is not
  enforced. The browser session surface from
  `US-020` records `started_at` and `ended_at`,
  but it does not record memory or CPU usage and
  does not stop the session when the budget is
  exceeded.

The next step in the hardening epic is therefore a
bounded performance baseline and SLO guardrails
slice that turns `NFR-PERF-001..005` into a
documented baseline, a set of SLO alert rules, and
a bounded load-test harness.

## Target Behavior

This story establishes the first bounded performance
baseline and SLO guardrails slice for LiveLead. After
the story is complete:

- A new durable `performance_snapshots` table
  records the result of every bounded load test
  with `started_at`, `completed_at`, `scenario`,
  `p50_ms`, `p95_ms`, `p99_ms`, `rps`,
  `error_rate`, `concurrent_users`, and
  `audit_correlation_id`.
- A new `PerformanceBaselineService` exposes the
  bounded operations:
  - `run_scenario(scenario)` — executes a
    deterministic, in-process load scenario
    against an in-memory SQLite plus a stubbed
    external provider, records the
    `performance_snapshots` row, and emits a
    `performance.scenario.completed` audit entry.
  - `list_snapshots(scenario?)` — returns the
    most recent snapshots for the operator
    panel and the verify script.
  - `build_summary` — returns the latest snapshot
    per scenario with the SLO budget, the
    current percentile, and the breach flag.
- A new closed `PerformanceMetric` enum that
  extends the `US-042` `MetricRegistry` and the
  `US-041` `AlertMetric` enum with five new
  metrics:
  - `api.read.latency_ms` (NFR-PERF-001)
  - `event.list.pagination.latency_ms` (NFR-PERF-002)
  - `discovery.first_progress_ms` (NFR-PERF-003)
  - `concurrency.users` (NFR-PERF-004)
  - `browser.session.budget_pct` (NFR-PERF-005)
- A new seed rule set in the `US-041` migration
  for the SLO alerts. The seed rules are
  `is_system = true` and owners/admins can tune
  the thresholds but cannot delete the system
  rules:
  - `api.read.slo_breach` — fires when the
    95th-percentile `api.read.latency_ms` is
    greater than 500 ms over a 300 s window.
  - `event.list.pagination.slo_breach` — fires
    when the 95th-percentile
    `event.list.pagination.latency_ms` is greater
    than 2 000 ms over a 600 s window.
  - `discovery.first_progress.slo_breach` —
    fires when the 95th-percentile
    `discovery.first_progress_ms` is greater than
    5 000 ms over a 300 s window.
  - `concurrency.cap.slo_breach` — fires when
    the rolling `concurrency.users` exceeds 100
    over a 60 s window.
  - `browser.session.budget.slo_breach` —
    fires when the rolling
    `browser.session.budget_pct` exceeds 90%
    over a 120 s window.
- A new browser session budget enforcement
  path. The browser session worker from `US-020`
  records a `memory_rss_mb` and a `cpu_pct`
  sample at session start, every 30 seconds
  during the session, and at session end. When a
  sample exceeds the configured budget, the
  session is stopped safely and a
  `browser.session.budget_exceeded` audit entry
  is written.
- A new owner/admin-only REST surface:
  - `GET /admin/performance/summary` — returns
    the latest snapshot per scenario with the
    SLO budget, the current percentile, and the
    breach flag.
  - `GET /admin/performance/snapshots?scenario=`
    — paginated snapshot history with sanitized
    payloads.
  - `POST /admin/performance/scenarios:run` —
    bounded, confirmation-gated scenario runner
    that executes a single in-process scenario
    and returns the result inline.
- A new bounded load-test harness in
  `scripts/verify-us-044.sh` that runs a
  deterministic scenario for each NFR-PERF target
  and asserts the recorded snapshot stays within
  the SLO budget. The harness is wired into
  `harness-cli story verify` and
  `harness-cli story verify-all`.
- A new product doc
  (`docs/product/performance-baseline-and-slo-guardrails.md`)
  that documents the SLO budget, the scenario
  list, and the alert rule set.
- A new runbook
  (`docs/ops/performance-baseline-runbook.md`)
  that documents what an operator does when an
  SLO alert fires.

The slice stops at the local-first, single-host
baseline. Distributed tracing, APM, call-graph
analysis, and external SLO tooling (Prometheus
RuleFiles, Datadog SLO, Sentry Performance) remain
in the follow-up backlog.

## Affected Users

- Owners and Admins responsible for the first
  real-environment pilot. They need an at-a-glance
  SLO summary and a bounded scenario runner that
  proves the SLO is achievable on the pilot
  hardware.
- Operators on call for the pilot-live environment.
  They need a `performance-baseline-runbook.md`
  entry that explains what to do when an SLO
  alert fires.
- Performance and SRE engineers who need a
  documented baseline and a bounded load-test
  harness they can extend for future hardening
  stories.
- Future implementation agents and engineers
  extending performance, security, or
  production-readiness work that needs stable
  SLO contracts.

## Affected Product Docs

- `docs/product/observability-and-alerting.md`
  (US-041 contract; this story adds the SLO
  alert rule set, it does not redefine the
  in-app alerting contract).
- `docs/product/external-metrics-and-tracing.md`
  (US-042 contract; this story extends the
  `MetricRegistry` with the new performance
  metrics, it does not redefine the existing
  metric set).
- `docs/product/audit-log-and-governance.md`
  (US-026 contract; the scenario runner and the
  browser budget enforcement emit `performance.*`
  and `browser.session.budget_exceeded` audit
  entries with the same secret-safe payload
  contract).
- `docs/product/backup-and-restore-operations.md`
  (US-043 contract; the SLO summary endpoint
  references the launch-gate `backup_freshness`
  check from `US-040`).
- `docs/product/real-environment-cutover-and-live-operations.md`
  (US-040 contract; the SLO summary endpoint
  references the `LaunchGateReport` from
  `US-040`).
- `docs/product/browser-session-console-and-isolation.md`
  (US-020 contract; the browser session budget
  enforcement extends the session lifecycle from
  `US-020`).
- `docs/product/performance-baseline-and-slo-guardrails.md`
  (new product doc that this story seeds as the
  living contract for the performance baseline
  domain).

## Non-Goals

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
