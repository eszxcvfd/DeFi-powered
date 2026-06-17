# Metrics Export Runbook (US-042)

This runbook is the operator-facing companion to the
`/admin/observability/export-policy` panel and the
`US-042` story packet. It is read-only documentation:
nothing here mutates product state outside the documented
policy endpoints.

## What this surface is

The external metrics pipeline slice ships:

- One `MetricsExportPolicy` row per organization with
  three sink sections: `prometheus_exposition`,
  `otel_collector`, and `sentry_ingest`.
- A `MetricRegistry` that mirrors the closed
  `SignalProvider` enum from `US-041`. New metrics must
  be added to the enum, the registry, and the seed rule
  set in the same change.
- An `ExportTransport` Protocol with three concrete
  transports. A later deployment story can add a new
  transport without changing the registry or the policy.
- A `GET /metrics` endpoint, owner/admin only by
  default, that returns a Prometheus text-format
  exposition. The endpoint is gated by a per-workspace
  scrape token and an allowlist of source CIDRs.
- An OpenTelemetry tracer integration for the FastAPI
  request path, the Dramatiq worker job path, and the
  browser action path. The tracer is off by default and
  is enabled when the `otel_collector` policy is active.
- A Sentry error reporter for unhandled exceptions in
  the FastAPI request path and the worker task error
  path. The reporter is off by default and is enabled
  when the `sentry_ingest` policy is active.
- A new
  `/admin/observability/export-policy` panel for
  owner/admin roles that exposes the current policy, the
  per-sink `last_export_status`, and a `Test export`
  button that performs a single round-trip through each
  enabled sink.

The exporter is read-only with respect to product state.
It never pauses jobs, disables connectors, flips live
toggles, or rolls back the environment. Acting on an
export policy is the operator's job; the runbook
documents the read paths and the policy endpoints.

## Where to look

| Surface | Path | Owner |
| --- | --- | --- |
| Operator panel | `frontend/src/pages/AdminObservabilityExportPolicy.tsx` | frontend |
| REST surface | `src/livelead/interfaces/rest/observability_export_policy.py` | interfaces |
| Service | `src/livelead/application/observability/export_policy_service.py` | application |
| Exporter | `src/livelead/application/observability/exporter.py` | application |
| OTel tracer | `src/livelead/infrastructure/observability/tracing.py` | infrastructure |
| Sentry reporter | `src/livelead/infrastructure/observability/sentry_reporter.py` | infrastructure |
| Sanitization helper | `src/livelead/domain/observability/sanitization.py` | domain |
| Migration | `alembic/versions/20260616_0032_metrics_export_policy.py` | alembic |
| Product doc | `docs/product/external-metrics-and-tracing.md` | docs |

## Sinks at a glance

| Sink | Default State | Acceptance Required | Default Off Reason |
| --- | --- | --- | --- |
| `prometheus_exposition` | disabled | yes | owner/admin must enable |
| `otel_collector` | disabled | yes | owner/admin must enable |
| `sentry_ingest` | disabled | yes | owner/admin must enable |

Each sink is shipped with one fixed set of configuration
values. The acceptance is enforced by the
`accepted_by` / `accepted_at` field on the policy row
and by the `PUT /admin/observability/export-policy`
endpoint.

## What to do when a sink is enabled

1. Open `/admin/observability/export-policy` and read
   the current policy.
2. Confirm that the `accepted_by` and `accepted_at`
   fields are populated and that the change is
   attributable to a real owner/admin user.
3. Click `Test export` and confirm that the per-sink
   result is `success` for every enabled sink.
4. If the per-sink result is `sanitizer_rejected`,
   check the audit log for a `metrics.export_rejected`
   entry with the secret marker or the
   `cardinality_exceeded` marker. Do not export the
   payload; the policy endpoint must be updated to fix
   the underlying issue.
5. If the per-sink result is `transport_error`, check
   the transport configuration (URL, protocol, DSN
   reference) and confirm that the destination is
   reachable from the worker process. Do not export
   the payload; the policy endpoint must be updated to
   fix the underlying issue.
6. If the per-sink result is `disabled`, confirm that
   the sink is intentionally disabled and that the
   `enabled` flag matches the operator's intent.

## What to do when a sink is disabled

1. Open `/admin/observability/export-policy` and read
   the current policy.
2. Confirm that the `enabled` flag is `false` and that
   the sink is not actively exporting.
3. Update the policy through the
   `PUT /admin/observability/export-policy` endpoint
   and record the change in the audit log.
4. Confirm that the in-app inbox from `US-029` shows a
   `metrics.export_disabled` audit entry with the
   dedicated severity icon and a deep link to the
   policy.

## What to do when a metric is rejected

1. Open `/admin/observability/export-policy` and read
   the `last_export_status` for the relevant sink.
2. If the status is `sanitizer_rejected`, check the
   audit log for a `metrics.export_rejected` entry with
   the secret marker or the `cardinality_exceeded`
   marker.
3. If the marker is `secret`, the payload contained a
   secret value. Update the source of the metric to
   stop emitting the secret value. The exporter will
   not retry until the source is fixed.
4. If the marker is `cardinality_exceeded`, the label
   set exceeded the metric's cardinality budget. Update
   the source of the metric to reduce the label
   cardinality or update the registry to increase the
   budget. The exporter will not retry until the source
   or the registry is fixed.
5. If the marker is neither, check the transport
   configuration and confirm that the destination is
   reachable from the worker process.

## What to do when a metric is missing

1. Open `/admin/observability/export-policy` and read
   the registry section.
2. Confirm that the metric is registered in
   `MetricRegistry`. The registry mirrors the closed
   `SignalProvider` enum from `US-041`; a metric that
   is not in the enum cannot be exported.
3. If the metric is not registered, add it to the enum,
   the registry, and the seed rule set in the same
   change. The exporter will not publish a metric that
   the alert evaluator does not know about.
4. If the metric is registered but not exported, check
   the cardinality budget and confirm that the label
   set does not exceed the budget. The exporter will
   drop a sample whose label set exceeds the budget.

## Pausing the exporter

The exporter is a worker actor
(`apps/worker/export_tasks.py`). Pause it by stopping
the worker process. No code path in the exporter
mutates product state, so pausing it does not leave the
system in an inconsistent state. The in-app alerts from
`US-041` continue to fire because the alert evaluator
runs from a separate worker tick.

## What this runbook does NOT cover

- Choosing, signing, or paying for a specific external
  vendor (Grafana Cloud, Sentry SaaS, a managed
  Prometheus service, a particular OTel vendor) — out
  of scope for `US-042`; a later deployment story adds
  it behind the existing `ExportTransport` Protocol.
- Auto-remediation or self-healing actions driven by an
  exported metric — the exporter is read-only by
  design.
- Per-tenant tuning of sampling ratios, label
  cardinality budgets, and `before_send` redaction
  lists — the slice ships one fixed set per sink and
  exposes policy management for follow-on tuning.
- A Grafana dashboard definition (or a vendor
  equivalent) — the slice ships the registry and the
  exposition endpoint; the dashboard is a follow-on
  story.
