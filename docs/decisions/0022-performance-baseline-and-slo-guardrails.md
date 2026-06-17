# 0022 Performance Baseline And SLO Guardrails

Date: 2026-06-16

## Status

Planned (companion decision to `US-044`).

## Context

`US-041` shipped the first operational observability
and alerting baseline for LiveLead and explicitly
carved the performance baseline out as a follow-up.
The relevant extracts from the durable record are:

- `docs/decisions/0019-observability-and-alerting-baseline.md`,
  "Follow-Up" section: "Add SLO burn-rate alerts and
  multi-window burn-rate evaluation once the MVP
  performance baselines are stable."
- `docs/ops/observability-runbook.md`, "Tuning a
  rule" section: "Owners and admins can adjust
  threshold, window, severity, cooldown, channels,
  and the `enabled` flag from `/admin/observability`.
  The grammar is closed."

`US-042` shipped the first external metrics pipeline
baseline and explicitly carved the performance
metrics out as a follow-up. The relevant extracts
are:

- `docs/decisions/0020-external-metrics-pipeline-baseline.md`,
  "Follow-Up" section: "Add per-tenant tuning of
  sampling ratios, label cardinality budgets, and
  `before_send` redaction lists through a
  configuration surface, gated on the same
  owner/admin role as the policy endpoints."
- `docs/ops/metrics-export-runbook.md`, "What
  this runbook does NOT cover" section:
  "Auto-remediation or self-healing actions —
  the exporter is read-only by design."

`SPEC.md` section 10.1 (`NFR-PERF-001..005`)
commits the product to a documented performance
baseline:

- `NFR-PERF-001`: 95% of API read requests must
  respond within 500 ms, excluding job time and
  external dependencies.
- `NFR-PERF-002`: The event list page must load
  the first 10 000 events in 2 seconds at the
  target infrastructure baseline.
- `NFR-PERF-003`: A discovery job must stream
  its first progress event within 5 seconds of
  the worker accepting the job.
- `NFR-PERF-004`: The MVP must support at least
  100 concurrent UI users, 20 concurrent
  discovery jobs, and 10 concurrent browser
  sessions per browser-worker node.
- `NFR-PERF-005`: Every browser session must
  have a memory and CPU budget; when the budget
  is exceeded, the session must be stopped
  safely and the error must be logged.

The product still has no bounded performance
baseline and SLO guardrails slice. The seed rule
set from `US-041` covers operational signals
(backup, heartbeat, connector, discovery,
browser crash, audit retention) but not API
latency, event list pagination, discovery job
progress, or browser session budget. The
`MetricRegistry` from `US-042` does not export
the new performance metrics. The browser session
worker from `US-020` does not enforce a memory
or CPU budget.

The next step in the hardening epic is therefore a
bounded performance baseline and SLO guardrails
slice that turns `NFR-PERF-001..005` into a
documented baseline, a set of SLO alert rules,
and a bounded load-test harness.

## Decision

`US-044` introduces the first performance baseline
and SLO guardrails slice for LiveLead.

### Domain objects

- **`PerformanceSnapshot`** — durable record of a
  load-test scenario result. The row carries
  enough information to prove that the SLO is
  achievable on the pilot hardware.
- **`PerformanceMetric`** — closed enumeration of
  performance metrics that the bounded load-test
  harness, the SLO alert rules, and the metrics
  exporter consume. The enumeration extends the
  `US-041` `AlertMetric` enum and the `US-042`
  `MetricRegistry` with five new metrics.
- **`PerformanceScenario`** — closed enumeration
  of scenario identifiers that the bounded
  load-test harness accepts.
- **`PerformanceBaselineService`** — application
  service that owns the bounded operations.
- **`BrowserSessionBudgetEnforcer`** —
  application service that owns the browser
  session budget enforcement path.

### Seed SLO alert rules

The migration adds five new seed rules with
`is_system = true` and the documented thresholds
in
`docs/product/performance-baseline-and-slo-guardrails.md`:

| Rule | Default Threshold | Default Severity |
| --- | --- | --- |
| `api.read.slo_breach` | `> 500 ms` over 300 s | `warning` |
| `event.list.pagination.slo_breach` | `> 2 000 ms` over 600 s | `warning` |
| `discovery.first_progress.slo_breach` | `> 5 000 ms` over 300 s | `warning` |
| `concurrency.cap.slo_breach` | `> 100` over 60 s | `warning` |
| `browser.session.budget.slo_breach` | `> 90%` over 120 s | `critical` |

Owners and admins can adjust threshold, window,
severity, and channels through the rule
management endpoints; they cannot delete or
rename a system rule, and they cannot change
the `metric` of a system rule.

### Admin surface

- New owner/admin-only REST surface:
  - `GET /admin/performance/summary`
  - `GET /admin/performance/snapshots?scenario=`
  - `POST /admin/performance/scenarios:run`
- The bounded scenario runner refuses to run
  against real external providers. The harness
  runs against an in-memory SQLite plus a
  stubbed external provider so the contract is
  reviewable in CI.
- The SLO alert rules are evaluated by the
  existing `AlertEvaluator` from `US-041` and
  the existing `MetricsExporter` from `US-042`
  exports the new performance metrics.
- The browser session budget enforcement path
  extends the existing browser session worker
  from `US-020`; it does not redefine it.
- Every scenario run, SLO alert rule firing,
  and browser session budget breach emits a
  durable audit entry with the same secret-safe
  payload contract as `US-026` and `US-041`.
- The SLO summary endpoint is itself covered
  by the health probe contract from `US-040`:
  a missing or failing summary must not fail
  `GET /health/ready`, only surface as a
  degraded warning.

### Sanitization contract

- Every snapshot and audit entry runs through
  the `SanitizeAlertPayload` helper from
  `US-041` before it leaves the process. The
  slice imports the same symbol and does not
  redefine it.
- A snapshot or audit entry that fails the
  sanitizer is dropped, the run is marked as
  `sanitizer_rejected`, and a
  `performance.export_rejected` audit entry is
  written with the secret marker and no
  payload detail.

### Seam for a later deployment story

- A stable interface sits between the bounded
  load-test harness and the scenario runner so
  a later deployment story can wire a specific
  load testing tool (Locust, k6, Locust Cloud,
  k6 Cloud) without changing the scenario,
  snapshot, or alert rule contracts. This slice
  does not commit to a particular tool.

## Alternatives Considered

1. **Wire a specific load testing tool (Locust,
   k6, Locust Cloud, k6 Cloud) directly.** This
   would have committed the MVP to a particular
   load testing tool before any operator had
   used the local-first baseline. It would
   also have made the snapshot contract depend
   on a third-party tool that is not yet
   present in the project. The local-first
   baseline keeps the scenario harness
   tool-agnostic and lets a later deployment
   story pick a vendor without re-opening the
   scenario, snapshot, or alert rule
   contracts.
2. **Skip the SLO alert rule set and rely on
   the existing seed rules from `US-041`.**
   This would have left `NFR-PERF-001..005`
   without a durable alert path. The slice adds
   the SLO rules; it does not redefine the
   existing seed rules.
3. **Push the SLO summary through a new
   external channel instead of the existing
   in-app inbox and email channels.** This
   would have added a new provider before the
   local-first baseline was proven and would
   have created a parallel channel that could
   drift away from the existing notification
   preferences from `US-029` and the
   sanitization helper from `US-041`. Reusing
   the same helper and the same audit entry
   shape keeps the contract aligned with the
   rest of the product.

## Consequences

Positive:

- The first real-environment pilot gets a
  vendor-agnostic, local-first SLO guardrails
  baseline that turns `NFR-PERF-001..005`
  into a documented baseline, a set of SLO
  alert rules, and a bounded load-test
  harness.
- A reusable secret-safe payload helper is
  established before any specific load testing
  tool is wired, so a later deployment story
  can pick a tool without re-opening the
  scenario, snapshot, or alert rule
  contracts.
- The `PerformanceMetric` enum mirrors the
  `US-041` `AlertMetric` enum and the `US-042`
  `MetricRegistry`, which prevents the
  scenario harness, the SLO alert rules, and
  the metrics exporter from drifting apart
  and prevents the exporter from publishing a
  metric that the alert evaluator does not
  know about.
- The browser session budget enforcement path
  extends the existing browser session
  lifecycle from `US-020`; it does not
  redefine it.

Tradeoffs:

- The bounded load-test harness runs against
  an in-memory SQLite plus a stubbed external
  provider. Load testing against real external
  providers is a deployment decision; a later
  story can wire a vendor behind the same
  scenario contract.
- The SLO alert rule thresholds are shipped
  with one fixed default set. Per-tenant
  tuning is a follow-on story, not a
  contract change.
- The closed set of scenarios is intentionally
  the same as the closed `PerformanceScenario`
  enum. New scenarios will require a new
  scenario kind, a new rule kind, and a
  migration; the trade-off is reviewability
  over flexibility.

## Follow-Up

- Add per-tenant tuning of SLO alert rule
  thresholds through a configuration surface,
  gated on the same owner/admin role as the
  rule management endpoints.
- Wire a specific load testing tool (Locust,
  k6, Locust Cloud, k6 Cloud) behind the
  stable interface so the bounded load-test
  harness can target real external providers.
- Add SLO burn-rate alerts and multi-window
  burn-rate evaluation once the MVP
  performance baselines are stable.
- Add auto-remediation or self-healing
  actions only after an explicit product
  decision; this slice commits the SLO alert
  rules to advisory semantics.
- Evaluate the need for a customer-facing
  status page once the SLO guardrails have
  been used in production for at least one
  operational cycle.
