# Exec Plan

## Goal

Add the first bounded connector health surface to
LiveLead. The slice turns `FR-ADM-002` into a
documented contract, a per-connector health
snapshot, an owner/admin-only REST surface, and a
reusable computation service that a future
alerting story can extend without re-opening the
observability and metrics contracts.

## Scope

In scope:

- New durable `connector_health_snapshots` table
  with the minimum fields required to record a
  per-connector health computation result:
  `source_id`, `connector_type`, `window_start`,
  `window_end`, `total_runs`, `success_count`,
  `failure_count`, `success_rate`,
  `p50_latency_ms`, `p95_latency_ms`,
  `captcha_count`, `captcha_rate`, `last_run_at`,
  `last_error_code`, `last_error_message`,
  `status`, and `audit_correlation_id`. Forward-
  only Alembic migration with a documented
  rollback note in the migration header.
- New durable `connector_health_errors` table
  with the minimum fields required to record a
  bounded recent-errors rollup: `source_id`,
  `error_code`, `error_message`, `first_seen_at`,
  `last_seen_at`, `occurrence_count`, and
  `audit_correlation_id`. Forward-only Alembic
  migration with a documented rollback note in
  the migration header.
- New closed `ConnectorHealthStatus` enum
  (`healthy`, `degraded`, `unhealthy`, `unknown`)
  with a closed mapping from the bounded
  `success_rate` and `captcha_rate` thresholds.
- New `ConnectorHealthThresholds` dataclass
  that exposes the closed default thresholds
  and the `default_window_seconds` bound.
- New `ConnectorHealthService` that exposes the
  bounded operations:
  - `compute_snapshot(source_id, *,
    window_seconds)`
  - `list_snapshots(*, source_id, status,
    limit, offset)`
  - `build_summary(*, source_id, status)`
  - `list_recent_errors(*, source_id, limit)`
- New `ConnectorHealthComputer` that owns the
  metrics derivation, the status classification,
  and the bounded window helper.
- New owner/admin-only REST surface:
  - `GET /admin/connectors/health/summary`
  - `GET /admin/connectors/health/snapshots`
  - `POST /admin/connectors/health/snapshots:compute`
  - `GET /admin/connectors/{source_id}/health/errors`
- New audit entry types:
  `connector.health.snapshot.computed`,
  `connector.health.summary.requested`,
  `connector.health.errors.requested`, and
  `connector.health.snapshot.rejected`.
- A new bounded window bound by the
  `EnvironmentMode` from `US-040` (max 24 hours
  in `pilot_live`, max 1 hour in `test_like`).
- A new product doc
  (`docs/product/connector-health-surface.md`).
- A new runbook
  (`docs/ops/connector-health-runbook.md`).
- A new decision record
  (`docs/decisions/0024-connector-health-surface-baseline.md`).
- Reuse of the `SanitizeAlertPayload` helper
  from `US-041` for every snapshot and audit
  payload before persistence.
- Reuse of the `AuditService` from `US-026` for
  every `connector.health.*` audit entry.
- Reuse of the `MetricRegistry` from `US-042`
  for the new connector health metrics.
- Reuse of the `AlertMetric` enum from
  `US-041` for the new connector health metrics.
- Reuse of the `EnvironmentMode` from `US-040`
  for the bounded window bound.
- Reuse of the source registry from `US-003`
  for the per-source health surface.
- Reuse of the `audit_entries` table from
  `US-026` for the source signal rollup.
- Reuse of the existing settings and inbox
  surfaces from `US-026` and `US-029` for the
  operator panel widget.
- Unit, integration, E2E, security,
  operational, and platform checks wired into
  a `scripts/verify-us-046.sh` command that
  `harness-cli story verify` can run.

Out of scope:

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
- Reading browser-session or browser-debug rows
  for the bounded computation. The slice reads
  only the `discovery_jobs` and `audit_entries`
  rows; a future story can extend the
  computation to read those rows behind the
  same `ConnectorHealthComputer` seam.
- Per-connector CAPTCHA detection policy. The
  slice reads the existing CAPTCHA detection
  events from the `audit_entries` rows; the
  per-connector policy remains a follow-on
  story.

## Risk Classification

Risk flags:

- Authorization — owner/admin role gate for
  every new endpoint; tenant scope for the
  connector health surface.
- Data model — new `connector_health_snapshots`
  and `connector_health_errors` tables, new
  indexes, forward-only migrations; new
  `ConnectorHealthStatus` enum.
- Audit/security — every snapshot computation,
  summary request, and recent-errors request
  must carry a secret-safe payload and a
  `connector.health.*` audit entry; the
  bounded window is enforced by the
  `EnvironmentMode` from `US-040`.
- Public contracts — new REST endpoints, new
  error codes, new operator panel widget, new
  audit entry types; consumed by the same
  admin surfaces that already speak to the
  observability and metrics endpoints from
  `US-041` and `US-042`.

Hard gates:

- Any snapshot computation, summary request,
  or recent-errors request that mutates product
  state without an authenticated session with
  `owner` or `admin` role.
- Any snapshot computation, summary request,
  or recent-errors request that leaks a
  secret, a cookie, browser storage state, raw
  PII, or a full connection string.
- Any change that weakens the
  `SanitizeAlertPayload` contract from
  `US-041` or the audit retention guarantee
  from `NFR-SEC-008`.
- Any change that bypasses the existing
  `AuditService` from `US-026` or the existing
  `SanitizeAlertPayload` helper from
  `US-041`.
- Any change that adds a new status to the
  `ConnectorHealthStatus` enum without first
  extending the `ConnectorHealthService` and
  the audit entry shape.
- Any change that bypasses the existing
  `EnvironmentMode` bound from `US-040` for
  the bounded window.
- Any change that bypasses the existing
  `MetricRegistry` from `US-042` for the new
  connector health metrics.
- Any change that bypasses the existing
  `AlertMetric` enum from `US-041` for the new
  connector health metrics.
- Any change that bypasses the existing source
  registry from `US-003` for the per-source
  health surface.

## Work Phases

1. Discovery — read `SPEC.md` §5.14, the
   `US-041` story packet, the `US-042` story
   packet, the `US-026` audit log contract, the
   `US-027` RBAC contract, the `US-040`
   environment mode contract, the `US-003`
   source registry contract, and the
   `pilot-live-rollback-runbook.md` entry.
   Confirm the seams that the slice consumes
   are stable and reusable.
2. Design — define `ConnectorHealthSnapshot`,
   `ConnectorHealthError`, `ConnectorHealthStatus`,
   `ConnectorHealthThresholds`,
   `ConnectorHealthService`, and
   `ConnectorHealthComputer`. Lock the
   sanitization contract to the existing
   `SanitizeAlertPayload` helper from `US-041`
   and refuse any snapshot or audit entry that
   fails the filter. Lock the bounded window
   to the existing `EnvironmentMode` from
   `US-040`.
3. Validation planning — design a per-source
   test harness that runs a deterministic
   computation for a seeded source, asserts
   the recorded snapshot stays within the
   contract, and asserts the audit entry was
   written. Add a `POST
   /admin/connectors/health/snapshots:compute`
   smoke test that an admin can run from the
   operator panel.
4. Implementation — add the migrations, the
   domain models, the `ConnectorHealthStatus`
   enum, the `ConnectorHealthService`, the
   `ConnectorHealthComputer`, the admin
   endpoints, the operator panel widget, the
   runbook entry, and the
   `scripts/verify-us-046.sh` harness. Reuse
   the existing `SanitizeAlertPayload`
   helper; do not introduce a parallel
   redaction helper.
5. Verification — run unit, integration, E2E,
   security, operational, and platform checks
   defined in `validation.md`. Run a
   deterministic computation for a seeded
   source and assert the recorded snapshot
   stays within the contract.
6. Harness update — add the new product doc,
   the decision record, the durable story
   status, the `scripts/verify-us-046.sh`
   command, and a final trace. Capture any
   friction in the `harness_friction` field.

## Stop Conditions

Pause for human confirmation if:

- The story starts requiring a specific health
  service (Datadog, Sentry Performance, a
  managed Prometheus service) to meet the
  acceptance criteria. This slice is
  local-first and tool-agnostic by design.
- Product direction becomes ambiguous between
  "owner/admin-only connector health surface"
  and "ship a full external health stack this
  cycle".
- Validation would need to weaken the
  `SanitizeAlertPayload` contract, the audit
  retention guarantee, or the existing
  `EnvironmentMode` bound from `US-040` to
  fit schedule.
- A new `ConnectorHealthStatus` value is needed
  that cannot be justified from `FR-ADM-002`;
  the value must be deferred or added to the
  spec in the same story with explicit
  acceptance criteria.
- A later story wants to ship a per-tenant
  threshold or a per-connector CAPTCHA
  detection policy before this slice is
  implemented; in that case, the integration
  must wait until the local-first baseline is
  in place.
- The bounded window needs to weaken the
  existing `EnvironmentMode` bound from
  `US-040`; the slice must extend the bound,
  not redefine it.
- The per-source health surface needs to
  weaken the existing source registry from
  `US-003`; the slice must extend the source
  catalog, not redefine it.
- The metrics export needs to weaken the
  existing `MetricRegistry` from `US-042`; the
  slice must extend the registry, not redefine
  it.
- The alert evaluation needs to weaken the
  existing `AlertMetric` enum from `US-041`;
  the slice must extend the enum, not redefine
  it.
