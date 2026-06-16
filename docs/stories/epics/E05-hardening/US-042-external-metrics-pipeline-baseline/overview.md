# Overview

## Current Behavior

`US-041` shipped the first operational observability and alerting
baseline for LiveLead. It established:

- A durable `AlertRule` and `AlertEvent` model with a closed metric
  grammar (`backup.age_hours`, `worker.heartbeat.age_seconds`,
  `connector.failure_rate`, `discovery.needs_user_action_rate`,
  `browser.crash_loop`, `audit.retention_breach_risk`).
- A `SignalProvider` Protocol and a `SignalProviderFactory` in
  `src/livelead/application/observability/signals.py` that read
  metric values from existing durable tables.
- A `SanitizeAlertPayload` helper shared with the audit log so
  secrets, cookies, raw PII, browser storage state, and full
  connection strings are redacted before any alert event is
  persisted.
- A `/admin/observability/summary` endpoint that combines the
  `LaunchGateReport` from `US-040`, recent `AlertEvent` rows,
  backup age, worker heartbeat, and per-connector health.
- An in-app inbox and email delivery path that reuses the
  `NotificationService` from `US-029`.
- A `docs/ops/observability-runbook.md` entry for operators.

`US-041` deliberately stopped at the local-first baseline and
carved the external metrics pipeline out as an explicit follow-up.
The relevant out-of-scope items, copied verbatim from
`docs/decisions/0019-observability-and-alerting-baseline.md` and
`docs/ops/observability-runbook.md`, are:

- "External metrics pipeline (Prometheus, OTel, Sentry, Grafana) —
  out of scope for US-041; a later hardening story adds it behind
  the existing `SignalProviderFactory` seam."
- "Wire a Prometheus exporter and an OpenTelemetry collector
  behind the existing sanitization helper so the same rules and
  events can feed a Grafana dashboard without re-opening the
  contracts."

`SPEC.md` sections 3.3 (technology baseline) and 10.6
(`NFR-OBS-001..004`) commit the product to OpenTelemetry,
Prometheus, Grafana, and Sentry at the technology level, but no
code in `src/livelead/infrastructure/observability/` wires any of
those providers today. The current `hooks.py` only registers a
logger and a request hook; it does not export metrics, emit
spans, or report errors to an external sink.

Operators running the first pilot-live environment therefore have
no Prometheus-format metrics to scrape, no OpenTelemetry traces
to inspect, and no Sentry errors to triage. The `US-041` rules
are the only durable signal pipeline, and they are limited to the
closed metric set and the in-app inbox.

## Target Behavior

This story establishes the first external metrics pipeline
baseline for LiveLead, sitting behind the seams that `US-041`
already shipped. After the story is complete:

- A new `MetricsExportPolicy` table stores the per-workspace
  configuration for each external sink: `prometheus_exposition`
  (on/off, allowed source networks, auth token hash, retention
  note), `otel_collector` (endpoint URL, protocol, sampling
  ratio, header redaction), and `sentry_ingest` (DSN reference,
  environment, release, sample rate, before-send redaction).
- A `MetricRegistry` defines the closed set of metric names
  exported by the product (built on top of the `SignalProvider`
  enum), with explicit unit, label cardinality budget, and
  secret-safety contract for each metric. New metrics must be
  added to the registry before they are exported.
- A new `GET /metrics` endpoint, owner/admin-only, serves a
  Prometheus text-format exposition backed by the same signal
  providers that the alert evaluator uses. No new metric is
  invented; the exporter only re-uses the `SignalProvider`
  protocol that `US-041` already defined.
- A new OpenTelemetry tracer is wired into the request,
  worker-job, and browser-action spans. The tracer is off by
  default and is configured per workspace through
  `MetricsExportPolicy.otel_collector`. Spans carry a tenant id
  and a correlation id; they never carry secrets, raw PII, or
  browser storage state.
- A new Sentry error reporter is wired into the existing
  FastAPI exception handler and the worker task error path. The
  reporter is off by default and is configured per workspace
  through `MetricsExportPolicy.sentry_ingest`. It uses a
  `before_send` hook that runs the same `SanitizeAlertPayload`
  filter from `US-041` so the export contract is defined once.
- A new `GET /admin/observability/export-policy` and
  `PATCH /admin/observability/export-policy` endpoint pair
  manages the policy for owner/admin users. The endpoints
  validate that each sink is configured, that the sanitization
  hook is present, and that the workspace has at least one
  active admin who has accepted the sink activation.
- A new runbook entry (`docs/ops/metrics-export-runbook.md`)
  documents what an operator does when a sink is enabled,
  disabled, or misconfigured, and what to do when a metric
  leaks a secret value.
- A small operator panel widget under `/admin/observability`
  shows which sinks are enabled, the last successful export
  timestamp, and a "Test export" button that performs a single
  round-trip and asserts that the export passed the sanitizer.

The slice stops at a local-first, opt-in external pipeline. No
specific vendor is required to pass the story's acceptance
criteria; a test exporter and a `MemorySpanExporter` are used to
prove the contract. Wiring a real vendor (Grafana Cloud, Sentry
SaaS, a self-hosted OTel collector) is a deployment decision
that the new policy endpoint makes straightforward but is not
required for this story.

## Affected Users

- Owners and Admins who need a vendor-agnostic way to export
  metrics, traces, and errors from the first pilot-live
  environment.
- Operators on call for the pilot-live environment who need to
  confirm that the system can talk to a Prometheus scrape
  target, an OpenTelemetry collector, and a Sentry project
  before something goes wrong.
- Future agents and engineers extending observability,
  performance, security, or production-readiness work that
  needs stable export contracts and a sanitization seam that
  cannot regress.

## Affected Product Docs

- `docs/product/observability-and-alerting.md` (US-041 contract;
  this story adds the export side, it does not redefine the
  in-app alerting contract).
- `docs/product/audit-log-and-governance.md` (the export
  sanitization seam is the same helper used by the audit log).
- `docs/product/notification-delivery-and-preferences.md`
  (delivery preferences remain authoritative for in-app and
  email; this story does not add a parallel channel).
- `docs/product/platform-and-automation-policy.md` (the new
  export policy is a workspace-level capability, not a
  per-source policy).
- `docs/product/external-metrics-and-tracing.md` (new product
  doc that this story seeds as the living contract for the
  external export domain).
- `docs/RUNTIME_CONFIGURATION.md` (the new env vars and the
  per-workspace policy endpoints need a runtime section).
- `docs/FOUNDATION_RUNTIME.md` (the new entrypoints — the
  metrics endpoint, the OTel tracer, the Sentry reporter —
  must be wired into the documented process layout).

## Non-Goals

- Choosing or contracting with a specific external vendor
  (Grafana Cloud, Sentry SaaS, a particular managed
  Prometheus, a particular OTel vendor).
- Distributed tracing UI, APM, or call-graph analysis across
  the modular monolith; this story ships the contract, not a
  UI.
- Auto-remediation or self-healing actions driven by an
  exported metric; the export pipeline is read-only with
  respect to product state.
- Customer-facing status pages or external incident
  communication.
- Replacing or removing the in-app alerts from `US-041`; this
  story extends them, it does not replace them.
- Adding new metric names beyond the `SignalProvider` enum
  from `US-041`; new metrics must be added to the enum, the
  `MetricRegistry`, and the seed rule set in a follow-on
  story.
- Per-tenant tuning of export sampling ratios, label
  cardinality budgets, or before-send redaction lists; the
  slice ships one fixed set per sink and exposes policy
  management for follow-on tuning.
