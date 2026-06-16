# Design

## Domain Model

The first external metrics pipeline baseline formalizes the
sink side of the observability contract that `US-041` already
shipped. The slice is local-first and vendor-agnostic: it
adds a per-workspace policy, a closed metric registry, three
pluggable transports, and a sanitization contract that
re-uses the helper from `US-041`.

### `MetricsExportPolicy`

A single row per organization that holds the configuration
for each external sink.

- `id`
- `organization_id` (unique)
- `prometheus_exposition_json`
  - `enabled` (bool)
  - `scrape_token_hash` (argon2id hash; never plaintext)
  - `allowed_source_cidrs` (list of CIDR strings; default
    `127.0.0.1/32` and `::1/128`)
  - `retention_note` (free-text, surfaced in the operator
    panel)
  - `last_successful_export_at` (nullable)
  - `last_export_status` (`success` | `sanitizer_rejected` |
    `transport_error` | `disabled`)
- `otel_collector_json`
  - `enabled` (bool)
  - `endpoint` (URL; validated as `https://` or `http://`
    on `localhost` only)
  - `protocol` (`http/protobuf` | `grpc`)
  - `sampling_ratio` (0.0..1.0; default 0.1)
  - `redaction_header_keys` (list of strings; default
    `["authorization", "cookie", "set-cookie", "x-api-key"]`)
  - `last_successful_export_at` (nullable)
  - `last_export_status`
- `sentry_ingest_json`
  - `enabled` (bool)
  - `dsn_ref` (reference to the secret manager entry; the
    DSN itself is never stored in the policy row)
  - `environment` (string; default `pilot_live`)
  - `release` (string; default git SHA at build time)
  - `sample_rate` (0.0..1.0; default 0.2)
  - `before_send_redaction_keys` (list of strings; default
    the `SanitizeAlertPayload` deny list)
  - `last_successful_export_at` (nullable)
  - `last_export_status`
- `accepted_by` (user id of the admin who last turned a sink
  on; nullable until the first sink is enabled)
- `accepted_at` (nullable)
- `created_at`, `updated_at`

### `MetricRegistry`

A closed enumeration of metric names that the exporter is
allowed to publish. The registry mirrors the
`SignalProvider` enum from `US-041` and adds explicit
metadata.

- `name` (string; e.g. `backup.age_hours`)
- `unit` (string; e.g. `hours`)
- `type` (`gauge` | `counter` | `histogram`)
- `cardinality_budget` (int; the maximum number of label
  combinations the exporter is allowed to emit)
- `secret_safety` (`safe` | `redact_before_export` |
  `forbidden`); the registry refuses to export a metric
  marked `forbidden`
- `signal_provider` (the class name of the
  `SignalProvider` that reads the value)
- `description` (string; surfaced in the operator panel
  and the runbook)

The registry is populated at process startup from the
`SignalProviderFactory` from `US-041`. A new metric cannot
be added to the registry without first being added to the
enum, the seed rule set, and the `US-041` alert evaluator;
this prevents the exporter and the alert evaluator from
drifting apart.

### `ExportTransport` Protocol

A small interface that the three concrete transports
implement.

```python
class ExportTransport(Protocol):
    name: str

    async def export(
        self,
        *,
        organization_id: str,
        samples: Iterable[MetricSample],
        policy: MetricsExportPolicy,
    ) -> ExportResult: ...


@dataclass(frozen=True, slots=True)
class MetricSample:
    name: str
    value: float
    labels: Mapping[str, str]
    timestamp: datetime | None = None


@dataclass(frozen=True, slots=True)
class ExportResult:
    transport: str
    status: Literal["success", "sanitizer_rejected", "transport_error", "disabled"]
    accepted: int
    rejected: int
    error: str | None = None
    exported_at: datetime
```

Concrete transports:

- `PrometheusExposition` — serializes the samples to
  Prometheus text format, runs each sample through
  `SanitizeAlertPayload`, and either returns
  `ExportResult` or, when the transport is invoked from
  the `GET /metrics` endpoint, streams the text body.
- `OtelCollector` — converts each sample to an OTel
  metric data point and ships it through the configured
  protocol. Spans are produced separately by
  `BuildOtelSpans`.
- `SentryIngest` — converts each sample to a Sentry
  breadcrumb or metric and ships it through the SDK.
  Errors are produced separately by `BuildSentryEvent`.

Business rules:

- All new admin endpoints require an authenticated session
  with `owner` or `admin` role. Viewer, analyst, sales, and
  reviewer roles get no export policy and cannot scrape
  `/metrics`.
- The `GET /metrics` endpoint is gated by the
  `scrape_token_hash` in the policy and the
  `allowed_source_cidrs`. A request from a non-allowlisted
  source returns `403 METRICS_SOURCE_NOT_ALLOWED`.
- A metric that is not in `MetricRegistry` cannot be
  exported; the exporter raises
  `METRIC_NOT_REGISTERED` and the `last_export_status`
  becomes `sanitizer_rejected`.
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
- A sink cannot be enabled without an `accepted_by` and an
  `accepted_at` recorded in the policy row. The acceptance
  is gated by an owner/admin confirmation step in the
  operator panel and in the `PUT /admin/observability/export-policy`
  endpoint.
- The OpenTelemetry SDK and the Sentry SDK are optional
  dependencies. If the SDK is not installed, the
  corresponding transport returns
  `ExportResult(status="disabled", error="sdk_not_installed")`
  and the policy row records the same. This keeps the
  local-first slice runnable in CI without forcing a
  vendor install.

## Application Flow

- `DefineMetricsExportPolicy` (owner/admin) — validates the
  policy against the closed enumeration of sinks and
  stores the policy. Refuses to enable a sink without an
  `accepted_by` and an `accepted_at`.
- `UpdateMetricsExportPolicy` (owner/admin) — partial
  update of one or more sinks; same validation rules.
- `TestMetricsExportPolicy` (owner/admin) — performs a
  single round-trip through each enabled sink, asserts
  that the sanitization contract holds, and returns a
  per-sink result. The operator panel renders the result
  inline.
- `ExportMetrics` (worker tick + targeted calls) —
  iterates the registry, reads each metric through the
  `SignalProviderFactory` from `US-041`, applies
  `SanitizeAlertPayload`, applies the cardinality budget,
  and dispatches to the configured transports. Writes a
  `metrics.exported` audit entry per sink on success and
  a `metrics.export_rejected` audit entry on
  `sanitizer_rejected` or `cardinality_exceeded`.
- `BuildMetricsRequest` (read path for `GET /metrics`) —
  builds the Prometheus text body in a streaming
  generator, applying the sanitization and cardinality
  rules on the fly.
- `BuildOtelSpans` (request hook + worker hook) — produces
  spans for the FastAPI request, the Dramatiq worker job,
  and the browser action path. The tracer is off by
  default; it is enabled when the `otel_collector` policy
  is active.
- `BuildSentryEvent` (exception handler + worker error
  path) — produces a Sentry event for unhandled
  exceptions, the FastAPI request, and the worker task
  error. The reporter is off by default; it is enabled
  when the `sentry_ingest` policy is active.
- `SanitizeAlertPayload` (shared helper) — runs every
  payload through the existing helper from `US-041` so the
  contract is defined once and reused. The exporter
  imports the same symbol and does not redefine it.

## Interface Contract

This slice adds the minimum REST surface that owners and
admins need to see, configure, and test the export policy.

- `GET /admin/observability/export-policy` — owner/admin
  only. Returns the current policy with secret references
  redacted and the per-sink `last_export_status`.
- `PUT /admin/observability/export-policy` — owner/admin
  only. Updates one or more sinks. Validates the payload
  shape, requires `accepted_by` and `accepted_at` to
  enable a sink, and refuses unknown keys.
- `POST /admin/observability/export-policy/test` —
  owner/admin only. Performs a single round-trip through
  each enabled sink and returns a per-sink result. The
  result is logged and audited; no external side effect
  beyond a single test call per sink.
- `GET /metrics` — owner/admin only by default; may be
  opened to a scrape target through the
  `scrape_token_hash` and the `allowed_source_cidrs`.
  Returns a Prometheus text body. Returns
  `403 METRICS_SOURCE_NOT_ALLOWED` for non-allowlisted
  sources and `404 METRICS_DISABLED` when the sink is
  disabled. The endpoint never returns secrets, raw PII,
  or browser storage state.

Expected payload concerns:

- All new error responses follow the existing error
  envelope (`code`, `message`, `request_id`, `details`).
- Unknown sinks, unknown metric names, missing
  `accepted_by` / `accepted_at`, and cardinality budget
  overflow return `EXPORT_POLICY_INVALID`,
  `METRIC_NOT_REGISTERED`, and `CARDINALITY_EXCEEDED`
  respectively.
- All export attempts (success, sanitizer rejection,
  transport error) emit durable audit entries
  (`metrics.exported`, `metrics.export_rejected`,
  `metrics.test_run`) with the same secret-safe payload
  contract as `US-026`.

## Data Model

New durable objects, each with a forward-only migration and
an index strategy sized for the current SQLite baseline:

- `metrics_export_policies` (one row per
  `organization_id`; index on `organization_id` for the
  policy read path; the JSON columns are stored as
  TEXT and parsed at the boundary)

No raw payload, secret, cookie, or browser storage state
is stored in the new table. The migration header documents
that the change is additive and that dropping the new
table is the documented rollback path; no data outside the
new table is affected.

## UI / Platform Impact

- The admin settings surface gains an `External exports`
  panel for owner/admin roles. The panel renders the
  current policy, the per-sink `last_export_status`, and
  a `Test export` button that performs a single round-trip
  and asserts the sanitization contract.
- The existing in-app inbox from `US-029` shows
  `metrics.export_rejected` audit entries with a
  dedicated severity icon and a deep link to the export
  policy in the operator panel.
- The frontend does not need a parallel notification
  channel; it reuses the inbox and settings surfaces
  already shipped by `US-041` and `US-029`.
- The `scripts/verify-us-042.sh` command wires the unit,
  integration, E2E, security, operational, and platform
  checks together and is the same command run by
  `harness-cli story verify` and
  `harness-cli story verify-all`.

## Observability

This story is the export side of the observability slice,
so it must set the standard that the next story will be
measured against.

- Every request handled by the new endpoints keeps a
  correlation id that matches the existing request
  envelope and is forwarded to the OTel span attributes.
- Every export attempt (success, sanitizer rejection,
  transport error) emits a structured log line and a
  matching audit entry.
- The exporter publishes a thin counter
  (`metrics.exporter.duration_ms`) so a future
  performance story can detect a slow exporter before it
  becomes a launch-gate blocker.
- The `/admin/observability/export-policy/test` endpoint
  is itself covered by the health probe contract: a
  missing or failing test must not fail
  `GET /health/ready`, only surface as a degraded
  warning.

## Alternatives Considered

1. **Wire a specific vendor (Grafana Cloud, Sentry SaaS, a
   managed Prometheus service) directly.** This would
   have committed the MVP to a particular vendor before
   any operator had used the local-first baseline from
   `US-041`. It would also have made the secret-safe
   export contract depend on a third-party SDK that is
   not yet present in the project. The local-first
   baseline keeps the export contract stable and lets a
   later deployment story pick a vendor without
   re-opening the registry or the sanitization contract.
2. **Export raw JSON dumps of the alert events.** This
   would have bypassed the metric registry and made the
   Prometheus exposition shape drift away from the
   in-app alert contract. Routing every export through
   the `SignalProviderFactory` and the
   `MetricRegistry` keeps the two surfaces aligned and
   prevents the exporter from publishing a metric that
   the alert evaluator does not know about.
3. **Push traces and errors through a new external
   channel instead of OTel and Sentry.** This would have
   added a new provider before the local-first baseline
   was proven and would have created a parallel channel
   that could drift away from the existing notification
   preferences from `US-029` and the sanitization helper
   from `US-041`. Reusing the same helper and the same
   audit entry shape keeps the export path aligned with
   the rest of the product.
