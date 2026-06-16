# Exec Plan

## Goal

Add the first external metrics pipeline baseline to LiveLead,
sitting behind the `SignalProviderFactory` seam and the
`SanitizeAlertPayload` helper that `US-041` already shipped.
The slice is local-first and vendor-agnostic: it ships a
Prometheus exposition endpoint, an OpenTelemetry tracer, a
Sentry error reporter, a per-workspace export policy, and the
minimum runbook and operator UI to make the pipeline
reviewable.

## Scope

In scope:

- New durable `metrics_export_policies` table (one row per
  organization) with a `prometheus_exposition`, an
  `otel_collector`, and a `sentry_ingest` configuration
  payload, all secret-safe and validated. Forward-only
  Alembic migration with a documented rollback note in the
  migration header.
- A new `MetricRegistry` that re-exports the closed
  `SignalProvider` enum from `US-041` and adds a small
  bridge to the exporter layer. The registry carries an
  explicit unit, a label-cardinality budget, and a
  secret-safety tag for each metric.
- New `MetricsExporter` service with three pluggable
  transports (`PrometheusExposition`, `OtelCollector`,
  `SentryIngest`). Each transport implements the same
  `ExportTransport` Protocol so a later story can add a new
  sink without changing the registry or the operator panel.
- New `GET /metrics` endpoint (owner/admin only) that
  returns a Prometheus text-format exposition of the
  metrics that the registry exposes. The endpoint is
  scrape-gated by a per-workspace admin token and refuses
  to serve a metric that has not been registered.
- New OpenTelemetry tracer integration in
  `src/livelead/infrastructure/observability/tracing.py`.
  The tracer is off by default; when an
  `otel_collector` policy is active, the existing request
  hook from `US-041` adds a span, the worker job loop adds
  a span, and the browser action path adds a span. Spans
  carry `tenant.id`, `request.id`, and a `correlation_id`
  attribute. They never carry secrets, raw PII, or
  browser storage state.
- New Sentry error reporter in
  `src/livelead/infrastructure/observability/sentry_reporter.py`.
  The reporter is off by default; when a `sentry_ingest`
  policy is active, the existing FastAPI exception handler
  and the worker task error path call
  `sentry_sdk.capture_exception` through a `before_send`
  hook that runs `SanitizeAlertPayload` on the event
  payload. The reporter never sends an event that fails
  the sanitizer.
- New owner/admin REST surface:
  - `GET /admin/observability/export-policy`
  - `PUT /admin/observability/export-policy`
  - `POST /admin/observability/export-policy/test`
- New operator UI widget under
  `/admin/observability` that shows the current policy,
  the last successful export timestamp per sink, and a
  "Test export" button that performs a single round-trip
  and asserts the sanitizer passed.
- New runbook entry
  `docs/ops/metrics-export-runbook.md` that documents
  what an operator does when a sink is enabled, disabled,
  misconfigured, or suspected of leaking a secret.
- A new decision record
  (`docs/decisions/0020-external-metrics-pipeline-baseline.md`)
  that captures the contract and the deferred work.
- A new product doc
  (`docs/product/external-metrics-and-tracing.md`) that
  becomes the living contract for the external export
  domain.
- Reuse of `SanitizeAlertPayload` from `US-041`; no
  parallel redaction helper is introduced.
- Reuse of the `SignalProvider` and
  `SignalProviderFactory` from `US-041`; the exporter
  reads metrics through the existing seam so a new metric
  only needs to be added once.
- Unit, integration, E2E, security, operational, and
  platform checks wired into a `scripts/verify-us-042.sh`
  command that the `harness-cli story verify` command can
  run.

Out of scope:

- Choosing, signing, or paying for a specific external
  vendor (Grafana Cloud, Sentry SaaS, a managed Prometheus
  service, a particular OTel vendor).
- Distributed tracing UI, APM, or call-graph analysis;
  this story ships the contract, not a UI.
- Auto-remediation or self-healing actions driven by an
  exported metric; the export pipeline is read-only with
  respect to product state.
- Customer-facing status pages or external incident
  communication.
- Replacing or removing the in-app alerts from `US-041`.
- New metric names beyond the `SignalProvider` enum from
  `US-041`; the registry mirrors the enum and refuses to
  export a metric that is not in the enum.
- Per-tenant tuning of export sampling ratios, label
  cardinality budgets, or before-send redaction lists; the
  slice ships one fixed set per sink and exposes policy
  management for follow-on tuning.
- Long-term metric retention, time-series compaction, or
  storage; the exporter is a sink, not a database.

## Risk Classification

Risk flags:

- Auth — admin-only policy endpoints and metrics endpoint.
- Authorization — owner/admin role gate for policy
  management and metrics scrape; tenant scope for the
  metrics registry.
- Data model — new `metrics_export_policies` table,
  per-workspace one-row policy, forward-only migration.
- Audit/security — export sanitization is the same
  `SanitizeAlertPayload` helper that the audit log uses;
  secret-leak detection is a hard gate.
- External systems — the slice is local-first and
  vendor-agnostic, but it ships the contract for a real
  Prometheus scrape target, an OTel collector endpoint, and
  a Sentry DSN; the policy endpoints must validate
  configuration shape but must not enable a sink without
  admin confirmation.
- Public contracts — new REST endpoints, new
  `/metrics` exposition, new OTel tracer attributes, new
  Sentry tags; consumed by operators and external sinks.
- Existing behavior — `US-041` alerting and
  `SanitizeAlertPayload` are adjacent; this story extends
  them, it does not redefine either.
- Weak proof — observability is exactly the area where
  "we added tests" is not the same as "we can prove we
  never leak a secret"; this story adds a dedicated
  sanitization test harness that runs every export
  payload through the same filter the alert events use.
- Multi-domain — touches audit (`US-026`), notifications
  (`US-029`), runtime readiness (`US-040`), alerting
  (`US-041`), source policy (`US-003`), and identity
  (`US-027`).

Hard gates:

- Any export path that can leak a secret, cookie, browser
  storage state, raw PII, or full connection string.
- Any export path that mutates product state as a side
  effect of evaluation.
- Any change that weakens the in-app alert contract from
  `US-041` or the audit retention guarantee from
  `NFR-SEC-008`.
- Any change that bypasses the existing
  `SanitizeAlertPayload` helper from `US-041`.
- Any change that exports a metric that is not in the
  closed `SignalProvider` enum from `US-041` and the
  `MetricRegistry` from this story.

## Work Phases

1. Discovery — read `SPEC.md` §3.3 and §10.6, the
   `US-041` story packet, the `US-040` story packet, the
   `US-026` audit log contract, the `US-029` notification
   contract, and the `US-027` identity contract. Confirm
   that the `SignalProviderFactory` and
   `SanitizeAlertPayload` seams are stable and reusable.
2. Design — define `MetricsExportPolicy`, `MetricRegistry`,
   `ExportTransport` Protocol, `PrometheusExposition`,
   `OtelCollector`, `SentryIngest`, `BuildMetricsRequest`,
   `BuildOtelSpans`, `BuildSentryEvent`, and
   `TestExportPolicy` services. Lock the sanitization
   contract to the existing `SanitizeAlertPayload` helper
   and refuse any metric that fails the filter.
3. Validation planning — design a per-sink test harness
   that runs a deterministic fake signal through the
   exporter, asserts the right transport call, and
   asserts the sanitization contract. Add a
   `/admin/observability/export-policy/test` smoke test
   that an admin can run from the operator panel.
4. Implementation — add the migration, the domain
   models, the exporter services, the
   `/admin/observability/export-policy` endpoints, the
   `GET /metrics` endpoint, the OTel tracer integration,
   the Sentry reporter integration, the operator panel
   widget, and the runbook entry. Reuse the existing
   `SanitizeAlertPayload` helper; do not introduce a
   parallel redaction helper.
5. Verification — run unit, integration, E2E, security,
   operational, and platform checks defined in
   `validation.md`. Simulate each sink, assert the
   transport call, and assert the sanitization contract
   holds even when the underlying signal is poisoned.
6. Harness update — add the new product doc, the
   decision record, the durable story status, the
   `scripts/verify-us-042.sh` command, and a final trace.
   Capture any friction in the `harness_friction` field.

## Stop Conditions

Pause for human confirmation if:

- The story starts requiring a specific external vendor
  (Grafana Cloud, Sentry SaaS, a managed Prometheus
  service, a particular OTel vendor) to meet the
  acceptance criteria. This slice is local-first and
  vendor-agnostic by design.
- Product direction becomes ambiguous between
  "local-first metrics pipeline" and "ship a full vendor
  integration this cycle".
- Validation would need to weaken the
  `SanitizeAlertPayload` contract, the audit retention
  guarantee, or the existing in-app alert contract from
  `US-041` to fit schedule.
- A new metric name is needed that cannot be justified
  from the closed `SignalProvider` enum from `US-041`;
  the metric must be deferred or added to the enum and
  the registry in the same story with explicit
  acceptance criteria.
- A later story wants to subscribe a paid external
  consumer (Grafana Cloud, Sentry SaaS, a managed
  Prometheus service) before this slice is implemented;
  in that case, the integration must wait until the
  local-first baseline is in place.
- The OpenTelemetry SDK or the Sentry SDK is not present
  in `pyproject.toml`; the implementation phase must
  stop and request the dependency addition through the
  normal maintenance path before continuing.
