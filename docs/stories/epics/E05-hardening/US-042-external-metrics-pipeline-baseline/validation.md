# Validation

## Required Proof

| Layer | Expectation |
| --- | --- |
| Unit | `MetricRegistry` refuses to register a metric that is not in the closed `SignalProvider` enum from `US-041`. `SanitizeAlertPayload` strips keys, cookies, raw PII, browser storage state, and full connection strings from every export payload before it is serialized. `MetricsExportPolicy` validation rejects unknown sinks, missing `accepted_by` / `accepted_at`, and cardinality budget overflow with `EXPORT_POLICY_INVALID`. The exporter's cardinality budget logic drops a label set that exceeds the metric's budget and records `cardinality_exceeded` in the audit log. |
| Integration | `GET /admin/observability/export-policy` and `PUT /admin/observability/export-policy` enforce owner/admin and refuse to enable a sink without an `accepted_by` and an `accepted_at`. `POST /admin/observability/export-policy/test` performs a single round-trip through each enabled sink, asserts the sanitization contract holds, and returns a per-sink result. `GET /metrics` is gated by the `scrape_token_hash` and the `allowed_source_cidrs`; a request from a non-allowlisted source returns `403 METRICS_SOURCE_NOT_ALLOWED`. Every export attempt (success, sanitizer rejection, transport error) emits a durable audit entry with the same secret-safe payload contract as `US-026`. |
| E2E | An authenticated owner can open the new operator panel, see the current policy, enable a sink with an explicit acceptance, click `Test export`, see the per-sink result inline, and disable the sink. A simulated poisoned signal (an API key in a label, a cookie in a label, raw PII in a label) is rejected by the sanitizer before it leaves the process. The OTel tracer integration is exercised end-to-end by a request that asserts a span is emitted with the right `tenant.id`, `request.id`, and `correlation_id` attributes and no secret attributes. The Sentry reporter integration is exercised end-to-end by an unhandled exception that asserts the event is reported with the right environment, release, and sample rate and no secret payload. |
| Security | Direct API calls to the new endpoints with viewer, analyst, sales, and reviewer sessions are rejected with the same error envelope as the existing admin surfaces. Sanitizer tests prove that payloads carrying API keys, cookies, raw PII, browser storage state, and full connection strings are rejected or redacted before any export call. The `GET /metrics` endpoint refuses to serve a metric that has not been registered. The migration does not weaken the existing audit retention guarantee. The `accepted_by` / `accepted_at` field is required to enable any sink. |
| Operational | A runbook entry for the export policy documents what an operator does when a sink is enabled, disabled, misconfigured, or suspected of leaking a secret, and what to do when a metric is rejected by the sanitizer or the cardinality budget. The verification script proves that the registry mirrors the `SignalProvider` enum, that the per-sink `last_export_status` is updated, and that the audit log records the expected entries. |
| Platform | The `scripts/verify-us-042.sh` command wires the unit, integration, E2E, security, and operational checks together and is the same command run by `harness-cli story verify` and `harness-cli story verify-all`. The export policy migration is exercised by the verify script so a missing policy row fails the platform check, not just the data check. |

## Suggested Checks

- Backend unit tests for:
  - `MetricRegistry` mirroring the `SignalProvider` enum
    and refusing unregistered metrics.
  - `SanitizeAlertPayload` against secrets, cookies, raw
    PII, browser storage state, and full connection
    strings.
  - `MetricsExportPolicy` validation against unknown
    sinks, missing `accepted_by` / `accepted_at`, and
    cardinality budget overflow.
  - Exporter cardinality budget logic.
  - OTel tracer integration attributes.
  - Sentry reporter integration environment, release, and
    sample rate.
- Backend integration tests for:
  - `GET /admin/observability/export-policy`
  - `PUT /admin/observability/export-policy`
  - `POST /admin/observability/export-policy/test`
  - `GET /metrics` scrape-token and CIDR gating
  - Audit entries for every export attempt
  - Reuse of `SanitizeAlertPayload` from `US-041`
  - Reuse of `SignalProviderFactory` from `US-041`
- E2E tests for:
  - Operator panel renders the export policy, the
    `last_export_status`, and the `Test export` button.
  - Enable / disable / test flows are visible and
    auditable.
  - A simulated poisoned signal is rejected by the
    sanitizer.
  - OTel tracer integration emits a span with the right
    attributes.
  - Sentry reporter integration reports an unhandled
    exception with the right environment, release, and
    sample rate.
- Security tests for:
  - Role enforcement on every new endpoint.
  - Source CIDR gating on `GET /metrics`.
  - Scrape-token gating on `GET /metrics`.
  - Payload sanitization for every new write path.
- Operational checks for:
  - `MetricRegistry` mirrors the `SignalProvider` enum.
  - The runbook entry exists and references the right
    surfaces.
  - The verify script exercises each sink and each
    rejection mode.
- Platform proof is the
  `scripts/verify-us-042.sh` command wired into
  `harness-cli story verify` and
  `harness-cli story verify-all`.

## Evidence Hooks

- `tests/unit/test_metric_registry.py` — registry
  mirroring the `SignalProvider` enum and refusing
  unregistered metrics.
- `tests/unit/test_metrics_sanitizer.py` — payload
  sanitization matrix (extends the `US-041` matrix).
- `tests/unit/test_metrics_export_policy.py` — policy
  validation against unknown sinks, missing
  `accepted_by` / `accepted_at`, and cardinality budget
  overflow.
- `tests/unit/test_otel_tracer.py` — tracer integration
  attributes.
- `tests/unit/test_sentry_reporter.py` — reporter
  integration environment, release, and sample rate.
- `tests/integration/test_export_policy_api.py`
- `tests/integration/test_metrics_endpoint_api.py`
- `tests/integration/test_metrics_audit.py`
- `tests/security/test_export_policy_role_gates.py`
- `tests/security/test_metrics_source_gating.py`
- `frontend/e2e/metrics-export-panel.spec.ts`
- `frontend/e2e/metrics-test-export.spec.ts`
- `scripts/verify-us-042.sh`
- `docs/ops/metrics-export-runbook.md` (operational
  entry)
- `docs/product/external-metrics-and-tracing.md`
  (living product contract)
- `docs/decisions/0020-external-metrics-pipeline-baseline.md`
  (durable decision record)

## Open Questions

- Should the per-sink sampling ratios, label cardinality
  budgets, and `before_send` redaction lists be tunable
  per tenant? This slice ships one fixed set per sink and
  exposes policy management for follow-on tuning.
- Should the OpenTelemetry SDK and the Sentry SDK be
  declared as optional or required dependencies? The
  current design treats them as optional so the
  local-first slice runs in CI without forcing a vendor
  install. A later story can promote them to required
  dependencies when a vendor decision is made.
- Should the `GET /metrics` endpoint support a
  Prometheus `Accept` header for `application/openmetrics-text`
  in addition to the legacy text format? The first
  implementation returns the legacy text format only.
- Should the OTel tracer carry the same `correlation_id`
  attribute as the in-app alerts, or should it use a
  different attribute to keep the two surfaces
  decoupled? The first implementation reuses
  `correlation_id` so a single correlation id is enough
  to grep across logs, alerts, and traces.
- Should the Sentry reporter emit a Sentry metric for
  every alert event, or only for unhandled exceptions?
  The first implementation emits a Sentry metric for
  every alert event and a Sentry event for unhandled
  exceptions; a follow-on story can split the two
  surfaces if a vendor decision prefers one or the
  other.
