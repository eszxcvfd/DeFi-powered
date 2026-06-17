# Overview

## Current Behavior

`US-001` through `US-045` delivered a broad MVP and the
first bounded hardening slices for LiveLead. The
product now has:

- A modular monolith with a Python API, a worker, a
  scheduler, a browser worker, a SQLite store, a
  Redis broker, and a React/TypeScript UI.
- A first operational observability and alerting
  baseline (`US-041`) that ships six seed rules for
  stale backup, worker heartbeat, connector failure
  rate, discovery `NEEDS_USER_ACTION` rate, browser
  crash loop, and audit retention risk.
- A first external metrics pipeline baseline
  (`US-042`) that exposes the same signals to a
  Prometheus scrape target, an OpenTelemetry
  collector, and a Sentry project.
- A first backup and restore operations baseline
  (`US-043`), a first bounded performance baseline
  (`US-044`), and a first calendar export slice
  (`US-045`).
- A real-environment pilot cutover baseline
  (`US-040`) with `EnvironmentMode`,
  `LaunchGateReport`, `LiveIntegrationToggle`, and
  `BackupSnapshot`.

`SPEC.md` section 5.14 (`FR-ADM-002`) commits the
product to a connector health surface that admins
can read:

> **FR-ADM-002 — Connector health**
> **Ưu tiên:** Must
> Admin xem được tỷ lệ thành công, lỗi gần nhất,
> latency, số item, CAPTCHA rate và lần chạy gần
> nhất của connector.

`docs/decisions/0019-observability-and-alerting-baseline.md`
explicitly carves the connector health surface out
as a follow-up. The relevant extract from the
durable record is:

> A connector health surface (`FR-ADM-002`) with
> success rate, recent errors, latency, item
> counts, CAPTCHA rate, and last run.

`docs/stories/epics/E05-hardening/US-041-operational-observability-and-alerting-baseline/design.md`
documents the seam:

> The bounded observability surface covers
> per-connector health rollup, but a dedicated
> connector health surface is a follow-on.

The product still has no bounded connector health
surface:

- The observability summary endpoint from `US-041`
  reports the `LaunchGateReport` and the most
  recent alerts, but it does not report a
  per-connector success rate, recent errors,
  latency, item counts, CAPTCHA rate, or last
  run timestamp.
- The `connector.failure_rate` metric from
  `US-041` and the `US-042` `MetricRegistry`
  expose a single ratio, not the full health
  surface from `FR-ADM-002`.
- The discovery job rows from `US-004` and the
  `audit_entries` rows from `US-026` already
  carry the source signals that the health
  surface needs (run timestamps, success
  counts, error counts, latency samples, and
  CAPTCHA rate), but no bounded computation
  reads them together.
- The browser-session and Playwright discovery
  surfaces from `US-020` through `US-025`
  carry CAPTCHA detection events that the
  health surface must aggregate.
- Operators who want to answer "is connector
  X healthy right now?" still have to read raw
  tables or run ad-hoc scripts.

The next step in the hardening epic is therefore
a bounded connector health surface slice that
turns `FR-ADM-002` into a documented contract, a
per-connector health snapshot, an owner/admin-only
REST surface, and a reusable computation service
that a future alerting story can extend without
re-opening the observability and metrics contracts.

## Target Behavior

This story establishes the first bounded connector
health surface for LiveLead. After the story is
complete:

- A new durable `connector_health_snapshots`
  table records the bounded per-connector health
  state with `id`, `organization_id`, `source_id`,
  `connector_type`, `window_start`, `window_end`,
  `total_runs`, `success_count`, `failure_count`,
  `success_rate`, `p50_latency_ms`, `p95_latency_ms`,
  `captcha_count`, `captcha_rate`, `last_run_at`,
  `last_error_code`, `last_error_message`,
  `audit_correlation_id`, `computed_at`,
  `created_at`, and `updated_at`.
- A new durable `connector_health_errors` table
  records the bounded recent-errors rollup with
  `id`, `organization_id`, `source_id`, `error_code`,
  `error_message`, `first_seen_at`, `last_seen_at`,
  `occurrence_count`, `audit_correlation_id`, and
  `created_at`. The table is bounded to the most
  recent N errors per source so a single failing
  connector cannot fill the table.
- A new closed `ConnectorHealthStatus` enum
  (`healthy`, `degraded`, `unhealthy`,
  `unknown`) that the bounded computation reads
  from the closed `success_rate` and `captcha_rate`
  thresholds. The thresholds are documented and
  adjustable per workspace, but the status enum
  is closed.
- A new `ConnectorHealthService` exposes the
  bounded operations:
  - `compute_snapshot(source_id, *, window_seconds)`
    — reads the `discovery_jobs` and `audit_entries`
    rows for the source, derives the bounded
    metrics, persists a `connector_health_snapshots`
    row, and emits a `connector.health.snapshot.computed`
    audit entry.
  - `list_snapshots(*, status, limit, offset)` —
    returns the most recent snapshots for the
    operator panel and the verify script.
  - `build_summary(*, status)` — returns the latest
    snapshot per source with the bounded
    thresholds, the current values, and the
    breach flag for the operator panel.
  - `list_recent_errors(*, source_id, limit)` —
    returns the most recent `connector_health_errors`
    rows for the source detail surface.
- A new owner/admin-only REST surface:
  - `GET /admin/connectors/health/summary` —
    returns the latest snapshot per source with
    the status, success rate, last run, and
    CAPTCHA rate.
  - `GET /admin/connectors/health/snapshots?source_id=&status=&limit=&offset=`
    — paginated snapshot history with sanitized
    payloads.
  - `POST /admin/connectors/health/snapshots:compute`
    — bounded, confirmation-gated computation
    that executes a single per-source snapshot
    and returns the result inline.
  - `GET /admin/connectors/{source_id}/health/errors?limit=`
    — recent error rollup for the source detail
    surface.
- A new operator panel widget that lists the
  latest snapshot per source, shows the
  `ConnectorHealthStatus` badge, and exposes a
  `Compute snapshot` button for each source.
- A new product doc
  (`docs/product/connector-health-surface.md`)
  that documents the bounded thresholds, the
  status enum, the snapshot shape, the recent
  error rollup, and the audit entry shape.
- A new runbook
  (`docs/ops/connector-health-runbook.md`) that
  documents what an operator does when a
  connector flips to `degraded` or `unhealthy`,
  when a CAPTCHA rate breaches the threshold,
  and when a user reports a missing connector.
- A new decision record
  (`docs/decisions/0024-connector-health-surface-baseline.md`)
  that locks the `ConnectorHealthStatus` enum,
  the per-connector snapshot shape, the bounded
  computation window, the recent-errors rollup
  shape, and the audit entry shape.
- A new bounded verification command
  (`scripts/verify-us-046.sh`) that runs the
  unit, integration, E2E, security, operational,
  and platform checks defined in `validation.md`
  and is wired into `harness-cli story verify`
  and `harness-cli story verify-all`.

The slice stops at the local-first, single-host
baseline. Distributed tracing of connector calls,
external health APIs (Datadog, Sentry Performance),
and per-tenant thresholds remain in the follow-up
backlog.

## Affected Users

- Owners and Admins responsible for the
  real-environment pilot. They need an at-a-glance
  view of every connector's success rate, recent
  errors, latency, item counts, CAPTCHA rate, and
  last run timestamp, plus a bounded `Compute
  snapshot` button for each source.
- Operators on call for the pilot-live environment.
  They need a `connector-health-runbook.md` entry
  that explains what to do when a connector flips
  to `degraded` or `unhealthy`, when a CAPTCHA rate
  breaches the threshold, and when a user reports
  a missing connector.
- Performance and SRE engineers who need a
  documented connector health baseline and a
  bounded computation service they can extend for
  future alerting stories.
- Future implementation agents and engineers
  extending connector alerts, per-tenant thresholds,
  or external health APIs that need a stable
  connector health contract.

## Affected Product Docs

- `docs/product/source-registry-and-policy.md`
  (`US-003` contract; this story extends the
  source catalog with a connector health surface,
  it does not redefine the source registry or the
  policy evaluation).
- `docs/product/observability-and-alerting.md`
  (`US-041` contract; this story extends the
  observability surface with a per-connector
  health rollup, it does not redefine the
  `AlertRule` or `AlertEvent` contract).
- `docs/product/external-metrics-and-tracing.md`
  (`US-042` contract; this story extends the
  `MetricRegistry` with the new connector health
  metrics, it does not redefine the export policy
  or the transport contract).
- `docs/product/audit-log-and-governance.md`
  (`US-026` contract; the snapshot computation
  and the recent-errors rollup emit
  `connector.health.*` audit entries with the
  same secret-safe payload contract).
- `docs/product/real-environment-cutover-and-live-operations.md`
  (`US-040` contract; the connector health summary
  references the `EnvironmentMode` from `US-040`
  and is covered by the same launch-gate seam).
- `docs/product/connector-health-surface.md` (new
  product doc that this story seeds as the living
  contract for the connector health domain).

## Non-Goals

- Distributed tracing of connector calls. This
  story ships the contract, not a UI.
- External health APIs (Datadog, Sentry
  Performance, a managed Prometheus service).
  The slice reuses the `MetricsExporter` from
  `US-042` and the `AlertEvaluator` from
  `US-041`; a later story can wire an external
  health consumer behind the same contract.
- Auto-remediation or self-healing actions
  driven by a connector health breach. The
  health surface is advisory, not authoritative.
- Per-tenant thresholds. The slice ships one
  fixed default set; per-tenant tuning is a
  follow-on story.
- Customer-facing status pages or external
  incident communication.
- Replacing the existing observability and
  alerting surface from `US-041`. This story
  extends the observability metrics and the
  alert seed rules; it does not redefine the
  `AlertRule` or `AlertEvent` contract.
- Replacing the existing external metrics
  pipeline from `US-042`. This story extends
  the `MetricRegistry` with the new connector
  health metrics; it does not redefine the
  export policy or the transport contract.
- Replacing the existing source registry from
  `US-003`. This story extends the source catalog
  with a connector health surface; it does not
  redefine the source policy or the rate-limit
  metadata.
