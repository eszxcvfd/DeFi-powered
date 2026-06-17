# Performance Baseline Runbook (US-044)

This runbook is the operator-facing companion to
the `/admin/performance` panel and the `US-044`
story packet. It is read-only documentation:
nothing here mutates product state outside the
documented bounded operations.

## What this surface is

The performance baseline and SLO guardrails slice
ships:

- A `PerformanceSnapshot` row per scenario that
  records `p50_ms`, `p95_ms`, `p99_ms`, `rps`,
  `error_rate`, `concurrent_users`, and
  `audit_correlation_id`.
- A closed `PerformanceMetric` enum that extends
  the `US-041` `AlertMetric` enum and the
  `US-042` `MetricRegistry` with five new metrics.
- A `PerformanceBaselineService` that exposes the
  bounded operations: `run_scenario`,
  `list_snapshots`, and `build_summary`.
- A `BrowserSessionBudgetEnforcer` that records
  `memory_rss_mb` and `cpu_pct` samples at
  session start, every 30 seconds during the
  session, and at session end. When a sample
  exceeds the configured budget, the session is
  stopped safely and a
  `browser.session.budget_exceeded` audit entry
  is written.
- A new seed SLO alert rule set in the `US-041`
  migration. The rules are `is_system = true`
  and owners/admins can tune the thresholds but
  cannot delete the system rules.
- A new
  `/admin/performance` panel for owner/admin
  roles that exposes the SLO summary, the most
  recent snapshots, and a `Run scenario` button
  that executes a single in-process scenario
  and asserts the SLO contract.

The bounded load-test harness runs against an
in-memory SQLite plus a stubbed external
provider so the contract is reviewable in CI.
Load testing against real external providers is
a deployment decision; a later story can wire a
specific tool (Locust, k6, Locust Cloud, k6
Cloud) behind the same scenario contract.

The SLO alert rules are advisory, not
authoritative. The rules emit audit entries
through the existing notification dispatcher
from `US-029`; they do not pause jobs, disable
connectors, flip live toggles, or roll back the
environment.

## Where to look

| Surface | Path | Owner |
| --- | --- | --- |
| Operator panel | `frontend/src/pages/AdminPerformance.tsx` | frontend |
| REST surface | `src/livelead/interfaces/rest/performance.py` | interfaces |
| Service | `src/livelead/application/performance/performance_baseline_service.py` | application |
| Enforcer | `src/livelead/application/performance/browser_session_budget.py` | application |
| Migration | `alembic/versions/20260616_0034_performance_snapshots.py` | alembic |
| Product doc | `docs/product/performance-baseline-and-slo-guardrails.md` | docs |

## Seed SLO rules at a glance

| Name | Default Threshold | Severity | Channels |
| --- | --- | --- | --- |
| `api.read.slo_breach` | `> 500 ms` over 300 s | `warning` | in_app |
| `event.list.pagination.slo_breach` | `> 2 000 ms` over 600 s | `warning` | in_app |
| `discovery.first_progress.slo_breach` | `> 5 000 ms` over 300 s | `warning` | in_app |
| `concurrency.cap.slo_breach` | `> 100` over 60 s | `warning` | in_app |
| `browser.session.budget.slo_breach` | `> 90%` over 120 s | `critical` | in_app, email |

The full grammar is documented in
`docs/product/performance-baseline-and-slo-guardrails.md`.

## What to do when an SLO alert fires

1. Open `/admin/performance` and read the SLO
   summary. The summary exposes the latest
   snapshot per scenario with the SLO budget,
   the current percentile, and the breach
   flag.
2. For each breach, look at the
   `performance_snapshots` row that triggered
   the alert. The row carries `p50_ms`,
   `p95_ms`, `p99_ms`, `rps`, `error_rate`, and
   `concurrent_users`.
3. If the breach is `api.read.slo_breach`,
   check the API logs for slow database queries
   and the Redis broker for slow downstream
   calls. The `LaunchGateReport` from `US-040`
   exposes the readiness profile.
4. If the breach is
   `event.list.pagination.slo_breach`, check
   the event list query plan and the
   `event_watchlist` table size. The bounded
   load-test harness runs the
   `event_list_pagination` scenario with 10 000
   seeded events; a breach above 2 000 ms
   indicates a missing index or a slow query
   plan.
5. If the breach is
   `discovery.first_progress.slo_breach`, check
   the worker queue depth and the SSE stream
   from `US-004`. A breach above 5 000 ms
   indicates a stalled worker or a slow source.
6. If the breach is `concurrency.cap.slo_breach`,
   check the worker queue depth and the browser
   worker node count. A breach above 100
   concurrent users indicates a saturated
   worker or a missing horizontal scale.
7. If the breach is
   `browser.session.budget.slo_breach`, check
   the browser session audit log for the
   `browser.session.budget_exceeded` entries.
   The entries carry the `memory_rss_mb` and
   `cpu_pct` samples that triggered the stop.
8. Acknowledge the alert from the panel.
   Acknowledgement does not resolve the alert;
   the alert evaluator transitions `firing` to
   `resolved` only when the signal clears.

## What to do when a browser session is stopped for budget breach

1. Open the audit log and find the
   `browser.session.budget_exceeded` entry that
   recorded the stop. The entry carries the
   `memory_rss_mb` and `cpu_pct` samples that
   triggered the stop, the `session_id`, and
   the `profile_id`.
2. Open `/admin/browser-profiles` and read the
   profile that generated the breach. The
   profile carries the `storage_state_uri` and
   the `last_used_at`.
3. If the breach is a one-off, the operator
   can re-issue the session with a higher
   budget. The default budget is 90% of the
   configured memory and CPU ceiling.
4. If the breach is a pattern, the operator
   should investigate the recipe and the
   connector policy. A pattern of breaches
   indicates a slow source or a recipe that
   triggers expensive DOM operations.
5. Acknowledge the alert from the panel.
   Acknowledgement does not resolve the alert;
   the alert evaluator transitions `firing` to
   `resolved` only when the signal clears.

## Tuning an SLO rule

Owners and admins can adjust threshold, window,
severity, cooldown, channels, and the `enabled`
flag from `/admin/performance`. The grammar is
closed:

- `metric ∈ {api.read.latency_ms, event.list.pagination.latency_ms, discovery.first_progress_ms, concurrency.users, browser.session.budget_pct}`
- `operator ∈ {gt, gte, lt, lte, eq}`
- `severity ∈ {info, warning, critical}`
- `channels ⊆ {in_app, email}`

System rules cannot be deleted or renamed;
their `metric` cannot be changed. Other fields
are owner-tunable.

## Disabling noisy SLO rules

Toggle `enabled = false` from the panel or the
API. The evaluator skips disabled rules; the
row stays visible so the operator remembers
the rule exists.

## Running a scenario

The operator panel exposes a `Run scenario`
button that executes a single in-process
scenario and asserts the SLO contract. The
button is gated by the existing
`accepted_by` flow from the `US-041` rule
management endpoints.

The bounded load-test harness runs the
following scenarios:

- `api_read_latency` (NFR-PERF-001)
- `event_list_pagination` (NFR-PERF-002)
- `discovery_first_progress` (NFR-PERF-003)
- `concurrency_cap` (NFR-PERF-004)
- `browser_session_budget` (NFR-PERF-005)

Each scenario records a `performance_snapshots`
row and emits a `performance.scenario.completed`
audit entry. The verify script
`scripts/verify-us-044.sh` runs the harness
end-to-end and asserts the recorded snapshot
stays within the SLO budget.

## Pausing the bounded load-test harness

The bounded load-test harness is a worker
actor. Pause it by stopping the worker
process. No code path in the harness mutates
product state, so pausing it does not leave
the system in an inconsistent state. The
in-app SLO alerts from `US-041` continue to
fire because the alert evaluator runs from a
separate worker tick.

## What this runbook does NOT cover

- Distributed tracing, APM, and call-graph
  analysis across the modular monolith —
  out of scope for `US-044`; a later story
  adds it behind the same `PerformanceMetric`
  enum.
- External SLO tooling (Prometheus RuleFiles,
  Datadog SLO, Sentry Performance) — out of
  scope for `US-044`; a later story wires it
  behind the existing `MetricsExporter` from
  `US-042`.
- Auto-remediation or self-healing actions
  driven by an SLO breach — the SLO alert
  rules are advisory, not authoritative.
- Load testing against real external
  providers — the bounded load-test harness
  runs against an in-memory SQLite plus a
  stubbed external provider.
- Per-tenant SLO budgets — the slice ships one
  fixed default set; per-tenant tuning is a
  follow-on story.
