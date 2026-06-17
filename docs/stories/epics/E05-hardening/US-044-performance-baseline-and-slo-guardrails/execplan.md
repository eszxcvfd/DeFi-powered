# Exec Plan

## Goal

Add the first bounded performance baseline and SLO
guardrails slice to LiveLead. The slice turns
`NFR-PERF-001..005` into a documented baseline, a
set of SLO alert rules, a browser session budget
enforcement path, and a bounded load-test harness,
all sitting behind the seams that `US-041`
(observability and alerting) and `US-042`
(external metrics pipeline) already shipped.

## Scope

In scope:

- New durable `performance_snapshots` table with
  the minimum fields required to record a
  scenario result: `started_at`, `completed_at`,
  `scenario`, `p50_ms`, `p95_ms`, `p99_ms`,
  `rps`, `error_rate`, `concurrent_users`, and
  `audit_correlation_id`. Forward-only Alembic
  migration with a documented rollback note in
  the migration header.
- New `PerformanceMetric` enum that extends the
  `US-041` `AlertMetric` enum and the `US-042`
  `MetricRegistry` with five new metrics:
  - `api.read.latency_ms` (NFR-PERF-001)
  - `event.list.pagination.latency_ms`
    (NFR-PERF-002)
  - `discovery.first_progress_ms` (NFR-PERF-003)
  - `concurrency.users` (NFR-PERF-004)
  - `browser.session.budget_pct` (NFR-PERF-005)
- New seed SLO alert rules in the `US-041`
  migration. The rules are `is_system = true`
  and owners/admins can tune the thresholds but
  cannot delete the system rules:
  - `api.read.slo_breach`
  - `event.list.pagination.slo_breach`
  - `discovery.first_progress.slo_breach`
  - `concurrency.cap.slo_breach`
  - `browser.session.budget.slo_breach`
- New `PerformanceBaselineService` that exposes
  the bounded operations:
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
- New browser session budget enforcement path.
  The browser session worker from `US-020`
  records a `memory_rss_mb` and a `cpu_pct`
  sample at session start, every 30 seconds
  during the session, and at session end. When
  a sample exceeds the configured budget, the
  session is stopped safely and a
  `browser.session.budget_exceeded` audit entry
  is written.
- New owner/admin-only REST surface:
  - `GET /admin/performance/summary`
  - `GET /admin/performance/snapshots?scenario=`
  - `POST /admin/performance/scenarios:run`
- New bounded load-test harness in
  `scripts/verify-us-044.sh` that runs a
  deterministic scenario for each NFR-PERF
  target and asserts the recorded snapshot
  stays within the SLO budget.
- A new product doc
  (`docs/product/performance-baseline-and-slo-guardrails.md`).
- A new runbook
  (`docs/ops/performance-baseline-runbook.md`).
- A new decision record
  (`docs/decisions/0022-performance-baseline-and-slo-guardrails.md`).
- Reuse of the `SanitizeAlertPayload` helper
  from `US-041` for every payload that flows
  through the scenario runner or the browser
  budget enforcement path.
- Reuse of the `AuditService` from `US-026` for
  every `performance.*` and
  `browser.session.budget_exceeded` audit
  entry.
- Reuse of the `AlertEvaluator` from `US-041`
  for the SLO alert rule evaluation.
- Reuse of the `MetricsExporter` from `US-042`
  for the new performance metrics.
- Reuse of the browser session worker from
  `US-020` for the budget enforcement path.
- Reuse of the `LaunchGateReport` from
  `US-040` for the operator summary endpoint.
- Reuse of the `BackupSnapshot` from `US-040`
  for the bounded restore rehearsal.
- Unit, integration, E2E, security,
  operational, and platform checks wired into
  a `scripts/verify-us-044.sh` command that
  `harness-cli story verify` can run.

Out of scope:

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
- Replacing the existing
  `LaunchGateReport` from `US-040`. This story
  consumes it, it does not redefine it.
- Replacing the existing alert rule set from
  `US-041`. This story adds the SLO rules; it
  does not redefine the seed rules from
  `US-041`.
- Replacing the existing `MetricRegistry` from
  `US-042`. This story extends it with the new
  performance metrics; it does not redefine
  the existing metric set.

## Risk Classification

Risk flags:

- Auth — admin-only performance summary
  endpoint and scenario runner.
- Authorization — owner/admin role gate for
  every new endpoint; tenant scope for the
  performance snapshot.
- Data model — new `performance_snapshots`
  table, new indexes, forward-only migration;
  new `PerformanceMetric` enum that extends the
  `US-041` `AlertMetric` enum and the `US-042`
  `MetricRegistry`.
- Audit/security — every scenario run and every
  browser session budget breach must carry a
  secret-safe payload and an audit entry; the
  SLO alert rules are advisory, not
  authoritative.
- External systems — the slice is local-first
  and single-host, but the bounded load-test
  harness is a deployment decision and the
  slice must not commit to a particular load
  testing tool (Locust, k6, Locust Cloud, k6
  Cloud).
- Public contracts — new REST endpoints, new
  error codes, new operator panel widget;
  consumed by the same admin surfaces that
  already speak to the observability and
  metrics endpoints from `US-041` and
  `US-042`.
- Existing behavior — `US-041` alert evaluator,
  `US-042` metric registry, `US-020` browser
  session worker, and `US-026` audit log are
  adjacent; this story extends them, it does
  not redefine them.
- Weak proof — performance is exactly the area
  where "we added tests" is not the same as
  "we proved the SLO is achievable on the
  pilot hardware"; this story adds a dedicated
  verification layer that runs a deterministic
  scenario for each NFR-PERF target and asserts
  the recorded snapshot stays within the SLO
  budget.
- Multi-domain — touches observability
  (`US-041`), metrics export (`US-042`),
  browser operations (`US-020`), audit
  (`US-026`), runtime readiness (`US-040`),
  and notification (`US-029`).

Hard gates:

- Any scenario run, browser session budget
  enforcement, or SLO alert rule that mutates
  product state without an `accepted_by` and
  an `accepted_at` recorded in the policy
  row.
- Any scenario run, browser session budget
  enforcement, or SLO alert rule that leaks a
  secret, a cookie, browser storage state,
  raw PII, or a full connection string.
- Any change that weakens the
  `SanitizeAlertPayload` contract from
  `US-041` or the audit retention guarantee
  from `NFR-SEC-008`.
- Any change that bypasses the existing
  `AlertEvaluator` from `US-041` or the
  existing `MetricsExporter` from `US-042`.
- Any change that adds a new metric to the
  `US-042` `MetricRegistry` without first
  adding it to the closed
  `PerformanceMetric` enum and the
  `US-041` `AlertMetric` enum.
- Any change that weakens the existing
  browser session lifecycle from `US-020`.
- Any change that bypasses the existing
  `LaunchGateReport` from `US-040`.

## Work Phases

1. Discovery — read `SPEC.md` §10.1, the
   `US-041` story packet, the `US-042` story
   packet, the `US-020` story packet, the
   `US-026` audit log contract, the `US-029`
   notification contract, and the
   `pilot-live-rollback-runbook.md` entry.
   Confirm the seams that the slice consumes
   are stable and reusable.
2. Design — define `PerformanceSnapshot`,
   `PerformanceMetric`, `PerformanceScenario`,
   `PerformanceBaselineService`,
   `BrowserSessionBudgetEnforcer`, and
   `BuildPerformanceSummary` services. Lock
   the sanitization contract to the existing
   `SanitizeAlertPayload` helper from `US-041`
   and refuse any snapshot or audit entry
   that fails the filter.
3. Validation planning — design a per-scenario
   test harness that runs a deterministic
   scenario for each NFR-PERF target, asserts
   the recorded snapshot stays within the SLO
   budget, and asserts the audit entry was
   written. Add a `POST
   /admin/performance/scenarios:run` smoke
   test that an admin can run from the
   operator panel.
4. Implementation — add the migration, the
   domain models, the `PerformanceMetric` enum
   extension, the seed SLO alert rules, the
   `PerformanceBaselineService`, the browser
   session budget enforcement path, the
   admin endpoints, the operator panel widget,
   the runbook entry, and the
   `scripts/verify-us-044.sh` harness. Reuse
   the existing `SanitizeAlertPayload`
   helper; do not introduce a parallel
   redaction helper.
5. Verification — run unit, integration, E2E,
   security, operational, and platform checks
   defined in `validation.md`. Run a
   deterministic scenario for each NFR-PERF
   target and assert the recorded snapshot
   stays within the SLO budget.
6. Harness update — add the new product doc,
   the decision record, the durable story
   status, the `scripts/verify-us-044.sh`
   command, and a final trace. Capture any
   friction in the `harness_friction` field.

## Stop Conditions

Pause for human confirmation if:

- The story starts requiring a specific load
  testing tool (Locust, k6, Locust Cloud, k6
  Cloud) to meet the acceptance criteria. This
  slice is local-first and tool-agnostic by
  design.
- Product direction becomes ambiguous between
  "local-first bounded load-test harness" and
  "ship a full external SLO stack this cycle".
- Validation would need to weaken the
  `SanitizeAlertPayload` contract, the audit
  retention guarantee, or the existing
  `AlertEvaluator` from `US-041` to fit
  schedule.
- A new SLO threshold is needed that cannot
  be justified from `NFR-PERF-001..005`; the
  threshold must be deferred or added to the
  spec in the same story with explicit
  acceptance criteria.
- A later story wants to subscribe a paid
  external SLO consumer (Datadog, Sentry
  Performance, a managed Prometheus service)
  before this slice is implemented; in that
  case, the integration must wait until the
  local-first baseline is in place.
- The browser session budget enforcement path
  needs to weaken the existing browser session
  lifecycle from `US-020`; the slice must
  extend the lifecycle, not redefine it.
