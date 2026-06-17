# Design

## Domain Model

The first performance baseline and SLO guardrails
slice formalizes the durable objects and bounded
services that turn `NFR-PERF-001..005` into a
documented baseline, a set of SLO alert rules, and
a bounded load-test harness.

### `PerformanceSnapshot`

A single record of a load-test scenario result. The
row carries enough information to prove that the
SLO is achievable on the pilot hardware.

- `id`
- `organization_id`
- `scenario` (`api_read_latency`,
  `event_list_pagination`, `discovery_first_progress`,
  `concurrency_cap`, `browser_session_budget`)
- `started_at`
- `completed_at` (nullable until the run finishes)
- `p50_ms`
- `p95_ms`
- `p99_ms`
- `rps`
- `error_rate`
- `concurrent_users`
- `audit_correlation_id`
- `created_at`, `updated_at`

### `PerformanceMetric` (extends `US-041` `AlertMetric`)

A closed enumeration of performance metrics that
the bounded load-test harness, the SLO alert
rules, and the metrics exporter consume. The
enumeration extends the `US-041` `AlertMetric`
enum and the `US-042` `MetricRegistry` with five
new metrics:

- `api.read.latency_ms` (NFR-PERF-001)
- `event.list.pagination.latency_ms`
  (NFR-PERF-002)
- `discovery.first_progress_ms` (NFR-PERF-003)
- `concurrency.users` (NFR-PERF-004)
- `browser.session.budget_pct` (NFR-PERF-005)

New metrics cannot be added to the
`PerformanceMetric` enum without first being
added to the `US-041` `AlertMetric` enum and the
`US-042` `MetricRegistry`; this keeps the
scenario harness, the SLO alert rules, and the
metrics exporter aligned.

### `PerformanceScenario`

A closed enumeration of scenario identifiers that
the bounded load-test harness accepts:

- `api_read_latency`
- `event_list_pagination`
- `discovery_first_progress`
- `concurrency_cap`
- `browser_session_budget`

The first slice ships one fixed default scenario
set; per-tenant tuning of the scenario list is a
follow-on story.

### `PerformanceBaselineService`

The application service that owns the bounded
operations. The service is the only place that
mutates `performance_snapshots` and emits the
`performance.*` audit entries; the worker
actors and the REST layer call it from the
request handlers.

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
- `build_summary` — returns the latest snapshot
  per scenario with the SLO budget, the current
  percentile, and the breach flag.

### `BrowserSessionBudgetEnforcer`

The application service that owns the browser
session budget enforcement path. The service is
the only place that records `memory_rss_mb` and
`cpu_pct` samples and stops a session when the
budget is exceeded.

- `record_sample(session_id, memory_rss_mb,
  cpu_pct)` — records a sample and stops the
  session safely when the budget is exceeded.
  The stop is gated by the existing
  confirmation flow from `US-022`; the slice
  extends the lifecycle, it does not redefine
  it.
- `build_session_summary(session_id)` — returns
  the most recent sample, the rolling average,
  and the budget breach flag for the operator
  panel.

Business rules:

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

## Application Flow

- `RunPerformanceScenario` (owner/admin) —
  validates the scenario against the closed
  `PerformanceScenario` enum, executes the
  deterministic in-process scenario, records
  the `performance_snapshots` row, and emits a
  `performance.scenario.completed` audit
  entry.
- `ListPerformanceSnapshots` (owner/admin) —
  returns the most recent snapshots for the
  operator panel and the verify script.
- `BuildPerformanceSummary` (owner/admin) —
  composes a single payload containing the
  latest snapshot per scenario with the SLO
  budget, the current percentile, and the
  breach flag.
- `RecordBrowserSessionSample` (worker) —
  records a `memory_rss_mb` and a `cpu_pct`
  sample for the session, stops the session
  safely when the budget is exceeded, and
  emits a `browser.session.budget_exceeded`
  audit entry.
- `EvaluateSloRules` (worker tick) — runs
  through the existing `AlertEvaluator` from
  `US-041` with the new seed SLO rules.
- `SanitizeAlertPayload` (shared helper) —
  runs every payload through the existing
  helper from `US-041` so the contract is
  defined once and reused.

## Interface Contract

This slice adds the minimum REST surface that
owners and admins need to see, configure, and
trigger the bounded performance baseline.

- `GET /admin/performance/summary` — owner/admin
  only. Returns the latest snapshot per
  scenario with the SLO budget, the current
  percentile, and the breach flag.
- `GET /admin/performance/snapshots?scenario=`
  — owner/admin only. Returns paginated
  snapshot history with sanitized payloads.
- `POST /admin/performance/scenarios:run` —
  owner/admin only. Bounded, confirmation-gated
  scenario runner that executes a single
  in-process scenario and returns the result
  inline.

Expected payload concerns:

- All new error responses follow the existing
  error envelope (`code`, `message`,
  `request_id`, `details`).
- Unknown scenarios, unknown metrics, missing
  acceptance metadata, and budget enforcement
  during a confirmation-gated action return
  `PERFORMANCE_INVALID`, `METRIC_NOT_REGISTERED`,
  `PERFORMANCE_ACCEPTANCE_REQUIRED`, and
  `BROWSER_BUDGET_CONFIRMATION_REQUIRED`
  respectively.
- Every scenario run, SLO alert rule firing,
  and browser session budget breach emits a
  durable audit entry with the same secret-safe
  payload contract as `US-026` and `US-041`.

## Data Model

New durable objects, each with a forward-only
migration and an index strategy sized for the
current SQLite baseline:

- `performance_snapshots` (organization-scoped,
  index on `(organization_id, scenario,
  started_at)` for the per-scenario history
  endpoint, index on `scenario` for the verify
  script).

No raw payload, secret, cookie, or browser
storage state is stored in the new table. The
migration header documents that the change is
additive and that dropping the new table is the
documented rollback path; no data outside the
new table is affected.

The slice also extends:

- The `US-041` `AlertMetric` enum with five new
  values.
- The `US-042` `MetricRegistry` with five new
  descriptors.
- The `US-041` seed rule set with five new
  SLO rules.
- The `US-020` browser session worker with a
  budget enforcement path.

## UI / Platform Impact

- The admin settings surface gains a
  `Performance` panel for owner/admin roles.
  The panel renders the SLO summary, the most
  recent snapshots, and a `Run scenario` button
  that executes a single in-process scenario
  and asserts the SLO contract.
- The in-app inbox from `US-029` shows
  `performance.slo_breach` and
  `browser.session.budget_exceeded` audit
  entries with a dedicated severity icon and a
  deep link to the operator panel.
- The frontend does not need a parallel
  notification channel; it reuses the inbox
  and settings surfaces already shipped by
  `US-026` and `US-029`.
- The `scripts/verify-us-044.sh` command wires
  the unit, integration, E2E, security,
  operational, and platform checks together
  and is the same command run by
  `harness-cli story verify` and
  `harness-cli story verify-all`.

## Observability

This story is the performance side of the
observability slice, so it must set the
standard that the next story will be measured
against.

- Every request handled by the new endpoints
  keeps a correlation id that matches the
  existing request envelope and is forwarded
  to the SLO alert rule evaluation.
- Every scenario run, SLO alert rule firing,
  and browser session budget breach emits a
  structured log line and a matching audit
  entry.
- The bounded scenario harness publishes a
  thin counter (`performance.scenario.duration_ms`)
  so a future performance story can detect a
  slow scenario before it becomes a launch-gate
  blocker.
- The `/admin/performance/summary` endpoint is
  itself covered by the health probe contract
  from `US-040`: a missing or failing summary
  must not fail `GET /health/ready`, only
  surface as a degraded warning.

## Alternatives Considered

1. **Wire a specific load testing tool (Locust,
   k6, Locust Cloud, k6 Cloud) directly.** This
   would have committed the MVP to a particular
   load testing tool before any operator had
   used the local-first baseline. The slice
   keeps the harness tool-agnostic so a later
   story can wire a vendor without re-opening
   the scenario, snapshot, or alert rule
   contracts.
2. **Skip the SLO alert rule set and rely on
   the existing seed rules from `US-041`.** This
   would have left `NFR-PERF-001..005` without a
   durable alert path. The slice adds the SLO
   rules; it does not redefine the existing
   seed rules.
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
