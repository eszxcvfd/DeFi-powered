# External Metrics Pipeline And Tracing

Source: `SPEC.md` sections 3.3, 10.6, and the deferred
external metrics pipeline listed as a follow-up in
`docs/decisions/0019-observability-and-alerting-baseline.md`
and `docs/ops/observability-runbook.md`.

## Product Goal

`US-041` shipped the first operational observability and
alerting baseline for LiveLead: durable alert rules, an
evaluator, an operator summary, an in-app inbox, and an
email delivery path. `US-041` deliberately stopped at the
local-first baseline and carved the external metrics
pipeline out as an explicit follow-up.

This product slice is the first step toward the export side
of the observability contract. It is a supporting governance
slice for the core MVP jobs in
`docs/product/mvp-scope-and-priorities.md`, not a new
primary value track by itself.

The slice is local-first and vendor-agnostic by design. It
does not commit to a specific external vendor (Grafana
Cloud, Sentry SaaS, a managed Prometheus service, a
particular OTel collector vendor) in this step; it
preserves a stable seam for a later deployment story to
wire one. The OpenTelemetry SDK and the Sentry SDK are
treated as optional dependencies so the local-first slice
runs in CI without forcing a vendor install.

## MVP Scope

This product slice covers:

- A durable `MetricsExportPolicy` table that holds the
  per-workspace configuration for three sinks:
  `prometheus_exposition`, `otel_collector`, and
  `sentry_ingest`.
- A `MetricRegistry` that mirrors the closed
  `SignalProvider` enum from `US-041` and adds explicit
  unit, type, cardinality budget, and secret-safety
  metadata for each metric.
- An `ExportTransport` Protocol with three concrete
  transports: `PrometheusExposition`, `OtelCollector`,
  and `SentryIngest`.
- A `GET /metrics` endpoint that returns a Prometheus
  text-format exposition of the registered metrics, gated
  by a per-workspace scrape token and an allowlist of
  source CIDRs.
- An OpenTelemetry tracer integration in
  `src/livelead/infrastructure/observability/tracing.py`
  that emits spans for the FastAPI request path, the
  Dramatiq worker job path, and the browser action path.
- A Sentry error reporter in
  `src/livelead/infrastructure/observability/sentry_reporter.py`
  that emits events for unhandled exceptions in the
  FastAPI request path and the worker task error path.
- A new owner/admin REST surface:
  - `GET /admin/observability/export-policy`
  - `PUT /admin/observability/export-policy`
  - `POST /admin/observability/export-policy/test`
- Reuse of the `SanitizeAlertPayload` helper from `US-041`
  for every export payload. No new redaction helper is
  introduced.
- Reuse of the `SignalProviderFactory` and
  `SignalProvider` Protocol from `US-041` so the exporter
  reads metrics through the same seam that the alert
  evaluator uses.
- A small operator panel widget under `/admin/observability`
  that shows the current policy, the per-sink
  `last_export_status`, and a `Test export` button that
  performs a single round-trip and asserts the
  sanitization contract.

This product slice does not yet cover:

- Choosing, signing, or paying for a specific external
  vendor (Grafana Cloud, Sentry SaaS, a managed Prometheus
  service, a particular OTel vendor).
- Distributed tracing UI, APM, or call-graph analysis
  across the modular monolith.
- Auto-remediation or self-healing actions driven by an
  exported metric.
- Customer-facing status pages or external incident
  communication.
- Replacing or removing the in-app alerts from `US-041`.
- New metric names beyond the closed `SignalProvider`
  enum from `US-041`.
- Per-tenant tuning of sampling ratios, label cardinality
  budgets, or `before_send` redaction lists.

## Contract Rules

- All new admin endpoints require an authenticated session
  with `owner` or `admin` role. Viewer, analyst, sales,
  and reviewer roles get no export policy and cannot
  scrape `/metrics`.
- The `GET /metrics` endpoint is gated by the
  `scrape_token_hash` in the policy and the
  `allowed_source_cidrs`. A request from a non-allowlisted
  source returns `403 METRICS_SOURCE_NOT_ALLOWED`.
- A sink cannot be enabled without an `accepted_by` and an
  `accepted_at` recorded in the policy row. The acceptance
  is gated by an owner/admin confirmation step in the
  operator panel and in the
  `PUT /admin/observability/export-policy` endpoint.
- A metric that is not in `MetricRegistry` cannot be
  exported; the exporter raises `METRIC_NOT_REGISTERED`
  and the `last_export_status` becomes
  `sanitizer_rejected`.
- A sample whose label set exceeds the metric's
  `cardinality_budget` is dropped, recorded as
  `cardinality_exceeded` in the audit log, and the
  `last_export_status` becomes `sanitizer_rejected`.
- A payload that fails `SanitizeAlertPayload` is dropped
  before it leaves the process; the audit log records the
  attempt with the secret marker and no payload detail.
- The exporter is read-only with respect to product state.
  It does not pause jobs, disable connectors, flip live
  toggles, or roll back the environment.
- The OpenTelemetry SDK and the Sentry SDK are optional
  dependencies. If the SDK is not installed, the
  corresponding transport returns
  `ExportResult(status="disabled", error="sdk_not_installed")`
  and the policy row records the same.
- All export attempts (success, sanitizer rejection,
  transport error) emit durable audit entries
  (`metrics.exported`, `metrics.export_rejected`,
  `metrics.test_run`) using the same secret-safe payload
  contract as `US-026`.

## Supported Sinks

| Sink | Config | Default State | Default Off Reason |
| --- | --- | --- | --- |
| `prometheus_exposition` | `scrape_token_hash`, `allowed_source_cidrs`, `retention_note` | disabled | owner/admin must enable |
| `otel_collector` | `endpoint`, `protocol`, `sampling_ratio`, `redaction_header_keys` | disabled | owner/admin must enable |
| `sentry_ingest` | `dsn_ref`, `environment`, `release`, `sample_rate`, `before_send_redaction_keys` | disabled | owner/admin must enable |

Each sink is shipped with one fixed default set of
configuration values. Owners and admins can adjust the
configuration through the policy endpoints; per-tenant
tuning of sampling ratios, label cardinality budgets, and
`before_send` redaction lists is a follow-on story.

## Supported Metric Registry

The registry mirrors the closed `SignalProvider` enum from
`US-041`. New metrics cannot be added to the registry
without first being added to the enum, the seed rule set,
and the `US-041` alert evaluator; this prevents the
exporter and the alert evaluator from drifting apart.

| Metric | Type | Unit | Cardinality Budget | Secret Safety |
| --- | --- | --- | --- | --- |
| `backup.age_hours` | gauge | hours | 1 | safe |
| `worker.heartbeat.age_seconds` | gauge | seconds | 16 | safe |
| `connector.failure_rate` | gauge | ratio | 64 | safe |
| `discovery.needs_user_action_rate` | gauge | ratio | 64 | safe |
| `browser.crash_loop` | counter | events | 32 | safe |
| `audit.retention_breach_risk` | gauge | days | 1 | safe |
| `alert.evaluator.duration_ms` | histogram | ms | 16 | safe |
| `metrics.exporter.duration_ms` | histogram | ms | 16 | safe |

These are the seed defaults. Owners and admins can disable
a metric through the registry configuration; adding a new
metric is a code change that requires updating the enum,
the registry, and the seed rule set in the same change.

## Runtime And Admin Surface

- `GET /admin/observability/export-policy` — owner/admin
  only. Returns the current policy with secret references
  redacted and the per-sink `last_export_status`.
- `PUT /admin/observability/export-policy` — owner/admin
  only. Updates one or more sinks. Validates the payload
  shape, requires `accepted_by` and `accepted_at` to
  enable a sink, and refuses unknown keys.
- `POST /admin/observability/export-policy/test` —
  owner/admin only. Performs a single round-trip through
  each enabled sink and returns a per-sink result.
- `GET /metrics` — owner/admin only by default; may be
  opened to a scrape target through the
  `scrape_token_hash` and the `allowed_source_cidrs`.

All new error responses follow the existing error envelope
(`code`, `message`, `request_id`, `details`). Unknown
sinks, unknown metric names, missing `accepted_by` /
`accepted_at`, source CIDR violations, and cardinality
budget overflow return `EXPORT_POLICY_INVALID`,
`METRIC_NOT_REGISTERED`, `EXPORT_POLICY_ACCEPTANCE_REQUIRED`,
`METRICS_SOURCE_NOT_ALLOWED`, and `CARDINALITY_EXCEEDED`
respectively.

## UI / Ops Surface

- The admin settings surface gains an `External exports`
  panel for owner/admin roles. The panel renders the
  current policy, the per-sink `last_export_status`, and
  a `Test export` button that performs a single
  round-trip and asserts the sanitization contract.
- The in-app inbox from `US-029` shows
  `metrics.export_rejected` audit entries with a
  dedicated severity icon and a deep link to the export
  policy in the operator panel.
- The first metrics export runbook
  (`docs/ops/metrics-export-runbook.md`) documents what
  an operator does when a sink is enabled, disabled,
  misconfigured, or suspected of leaking a secret, and
  what to do when a metric is rejected by the sanitizer
  or the cardinality budget.

## Validation Implications

- Unit tests must prove that the `MetricRegistry` mirrors
  the `SignalProvider` enum, that the payload sanitizer
  strips secrets, cookies, raw PII, browser storage state,
  and full connection strings, and that the policy
  validation rejects unknown sinks, missing
  `accepted_by` / `accepted_at`, and cardinality budget
  overflow.
- Integration tests must exercise every new endpoint
  against an in-memory SQLite plus a stubbed exporter
  transport and prove that role gates, source CIDR
  gating, scrape-token gating, and sanitization are
  enforced.
- E2E tests must cover the operator panel render, the
  simulated poisoned signal rejection, the OTel tracer
  integration, and the Sentry reporter integration.
- Security tests must prove that viewer, analyst, sales,
  and reviewer sessions are rejected on every new
  endpoint, that the source CIDR gating and the
  scrape-token gating hold, and that a poisoned payload
  is dropped before it leaves the process.
- Operational tests must prove the registry mirrors the
  enum, the runbook entry exists, and the verify script
  exercises each sink and each rejection mode.
- Platform proof is the `scripts/verify-us-042.sh`
  command wired into `harness-cli story verify` and
  `harness-cli story verify-all`.
