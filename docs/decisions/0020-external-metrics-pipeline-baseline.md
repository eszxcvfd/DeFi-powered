# 0020 External Metrics Pipeline Baseline

Date: 2026-06-16

## Status

Planned (companion decision to `US-042`).

## Context

`US-041` shipped the first operational observability and
alerting baseline for LiveLead and explicitly carved the
external metrics pipeline out as a follow-up. The relevant
extracts from the durable record are:

- `docs/decisions/0019-observability-and-alerting-baseline.md`,
  "Follow-Up" section: "Wire a Prometheus exporter and an
  OpenTelemetry collector behind the existing sanitization
  helper so the same rules and events can feed a Grafana
  dashboard without re-opening the contracts."
- `docs/ops/observability-runbook.md`, "What this runbook
  does NOT cover": "External metrics pipeline (Prometheus,
  OTel, Sentry, Grafana) — out of scope for US-041; a
  later hardening story adds it behind the existing
  `SignalProviderFactory` seam."
- `docs/stories/epics/E05-hardening/US-041-.../design.md`:
  "A stable interface sits between the evaluator and the
  counter/log surface so a later hardening story can wire
  a Prometheus exporter, an OpenTelemetry collector, Sentry
  ingestion, or a Grafana dashboard without changing the
  rule, event, or summary contracts."

`SPEC.md` sections 3.3 (technology baseline) and 10.6
(`NFR-OBS-001..004`) commit the product to OpenTelemetry,
Prometheus, Grafana, and Sentry at the technology level,
but no code in
`src/livelead/infrastructure/observability/` wires any of
those providers today. The current `hooks.py` only
registers a logger and a request hook; it does not export
metrics, emit spans, or report errors to an external sink.

Operators running the first pilot-live environment
therefore have no Prometheus-format metrics to scrape, no
OpenTelemetry traces to inspect, and no Sentry errors to
triage. The `US-041` rules are the only durable signal
pipeline, and they are limited to the closed metric set
and the in-app inbox.

The next hardening step is therefore a vendor-agnostic,
local-first external metrics pipeline baseline that sits
behind the seams that `US-041` already shipped.

## Decision

`US-042` introduces the first external metrics pipeline
baseline for LiveLead.

### Domain objects

- **`MetricsExportPolicy`** — durable per-workspace
  configuration for three sinks:
  `prometheus_exposition`, `otel_collector`, and
  `sentry_ingest`. The row stores a `scrape_token_hash`
  (argon2id), `allowed_source_cidrs`, a `dsn_ref` for
  Sentry, and a per-sink `last_export_status`. The DSN and
  the scrape token are never stored in plaintext.
- **`MetricRegistry`** — closed enumeration of metric
  names that the exporter is allowed to publish. The
  registry mirrors the `SignalProvider` enum from
  `US-041` and adds explicit unit, type, cardinality
  budget, and secret-safety metadata for each metric. New
  metrics cannot be added to the registry without first
  being added to the enum, the seed rule set, and the
  `US-041` alert evaluator.
- **`ExportTransport` Protocol** — small interface that
  the three concrete transports implement. The protocol
  carries an `ExportResult` with the transport name, the
  sanitization status, the number of accepted and
  rejected samples, and the error message.

### Exporter and delivery

- **`MetricsExporter`** — runs from a periodic worker
  tick and from the `GET /metrics` endpoint. The exporter
  is read-only with respect to product state. It reads
  metric values through the `SignalProviderFactory` from
  `US-041`, applies the `MetricRegistry` cardinality
  budget, runs the payload through `SanitizeAlertPayload`
  from `US-041`, and dispatches to the configured
  transports.
- **`PrometheusExposition`** — serializes the samples to
  Prometheus text format, runs each sample through the
  sanitizer, and either returns `ExportResult` or, when
  invoked from `GET /metrics`, streams the text body.
- **`OtelCollector`** — converts each sample to an OTel
  metric data point and ships it through the configured
  protocol. Spans are produced separately by
  `BuildOtelSpans`.
- **`SentryIngest`** — converts each sample to a Sentry
  breadcrumb or metric and ships it through the SDK.
  Errors are produced separately by `BuildSentryEvent`.
- **`BuildOtelSpans`** — produces spans for the FastAPI
  request path, the Dramatiq worker job path, and the
  browser action path. The tracer is off by default; it
  is enabled when the `otel_collector` policy is active.
  Spans carry `tenant.id`, `request.id`, and
  `correlation_id` attributes and never carry secrets,
  raw PII, or browser storage state.
- **`BuildSentryEvent`** — produces a Sentry event for
  unhandled exceptions, the FastAPI request path, and
  the worker task error path. The reporter is off by
  default; it is enabled when the `sentry_ingest` policy
  is active. The reporter uses a `before_send` hook that
  runs `SanitizeAlertPayload` on the event payload.

### Admin surface

- New owner/admin-only REST surface:
  - `GET /admin/observability/export-policy`
  - `PUT /admin/observability/export-policy`
  - `POST /admin/observability/export-policy/test`
- `GET /metrics` — owner/admin only by default; may be
  opened to a scrape target through the
  `scrape_token_hash` and the `allowed_source_cidrs`.
- The acceptance of a sink is gated by an `accepted_by`
  and an `accepted_at` recorded in the policy row. The
  acceptance is enforced in the operator panel and in
  the `PUT /admin/observability/export-policy` endpoint.
- All export attempts (success, sanitizer rejection,
  transport error) emit `metrics.exported`,
  `metrics.export_rejected`, and `metrics.test_run`
  audit entries using the same secret-safe payload
  contract as `US-026`.
- The `/admin/observability/export-policy/test` endpoint
  is itself covered by the health probe contract: a
  missing or failing test must not fail
  `GET /health/ready`, only surface as a degraded
  warning.

### Sanitization contract

- Every export payload runs through
  `SanitizeAlertPayload` from `US-041` before it leaves
  the process. The exporter imports the same symbol and
  does not redefine it.
- A payload that fails the sanitizer is dropped, the
  `last_export_status` becomes `sanitizer_rejected`, and
  a `metrics.export_rejected` audit entry is written
  with the secret marker and no payload detail.
- A sample whose label set exceeds the metric's
  `cardinality_budget` is dropped, the
  `last_export_status` becomes `sanitizer_rejected`, and
  a `metrics.export_rejected` audit entry is written
  with the `cardinality_exceeded` marker.

### Seam for a later vendor decision

- A stable interface sits between the exporter and the
  three transports so a later deployment story can wire
  a specific vendor (Grafana Cloud, Sentry SaaS, a
  managed Prometheus service, a particular OTel
  collector vendor) without changing the registry, the
  policy, or the sanitization contract. This slice does
  not commit to a particular vendor.

## Alternatives Considered

1. **Wire a specific vendor (Grafana Cloud, Sentry SaaS,
   a managed Prometheus service, a particular OTel
   vendor) directly.** This would have committed the
   MVP to a particular vendor before any operator had
   used the local-first baseline from `US-041`. It would
   also have made the secret-safe export contract depend
   on a third-party SDK that is not yet present in the
   project. The local-first baseline keeps the export
   contract stable and lets a later deployment story
   pick a vendor without re-opening the registry or the
   sanitization contract.
2. **Export raw JSON dumps of the alert events.** This
   would have bypassed the metric registry and made the
   Prometheus exposition shape drift away from the
   in-app alert contract. Routing every export through
   the `SignalProviderFactory` and the `MetricRegistry`
   keeps the two surfaces aligned and prevents the
   exporter from publishing a metric that the alert
   evaluator does not know about.
3. **Push traces and errors through a new external
   channel instead of OTel and Sentry.** This would
   have added a new provider before the local-first
   baseline was proven and would have created a
   parallel channel that could drift away from the
   existing notification preferences from `US-029` and
   the sanitization helper from `US-041`. Reusing the
   same helper and the same audit entry shape keeps the
   export path aligned with the rest of the product.

## Consequences

Positive:

- The first pilot-live environment gets a
  vendor-agnostic way to export metrics, traces, and
  errors from the same signal sources that the alert
  evaluator uses, behind the same sanitization helper
  that the audit log uses.
- A reusable secret-safe payload helper is established
  before any specific vendor is wired, so a later
  deployment story can pick a vendor without re-opening
  the registry, the policy, or the sanitization
  contract.
- The `MetricRegistry` mirrors the `SignalProvider`
  enum, which prevents the exporter and the alert
  evaluator from drifting apart and prevents the
  exporter from publishing a metric that the alert
  evaluator does not know about.
- The `accepted_by` / `accepted_at` field on the policy
  row makes the sink activation auditable and reviewable
  in the operator panel and in the audit log.

Tradeoffs:

- The OpenTelemetry SDK and the Sentry SDK are treated
  as optional dependencies so the local-first slice
  runs in CI without forcing a vendor install. A later
  deployment story can promote them to required
  dependencies when a vendor decision is made.
- The per-sink sampling ratios, label cardinality
  budgets, and `before_send` redaction lists are
  shipped with one fixed set per sink. Per-tenant
  tuning is a follow-on story, not a contract change.
- The closed set of metrics is intentionally the same
  as the closed `SignalProvider` enum from `US-041`.
  New metrics will require a new rule kind, a new
  registry entry, and a migration; the trade-off is
  reviewability over flexibility.

## Follow-Up

- Add per-tenant tuning of sampling ratios, label
  cardinality budgets, and `before_send` redaction
  lists through a configuration surface, gated on the
  same owner/admin role as the policy endpoints.
- Promote the OpenTelemetry SDK and the Sentry SDK to
  required dependencies once a vendor decision is
  made.
- Add a Grafana dashboard definition (or a vendor
  equivalent) behind the registry, the policy, and the
  sanitization contract so the first pilot-live
  environment has a default view of the exported
  metrics.
- Evaluate the need for a customer-facing status page
  once the export pipeline has been used in production
  for at least one operational cycle.
- Consider adding a `application/openmetrics-text`
  accept path to `GET /metrics` once a vendor decision
  is made.
