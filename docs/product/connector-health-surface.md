# Connector Health Surface

Source: `SPEC.md` sections 5.3, 5.14, 7.2, 11, 12, 14.1, and 14.2,
plus `docs/decisions/0024-connector-health-surface-baseline.md`.

## Product Goal

Owners and admins need a bounded way to read the
current health of every configured connector
without running ad-hoc scripts. The product
contract must define how LiveLead records a
per-connector health snapshot, derives the
bounded metrics (success rate, recent errors,
latency, item counts, CAPTCHA rate, last run),
and exposes the surface through a single
operator panel and a closed set of admin-only
REST endpoints. The slice reuses the
observability contract from `US-041`, the
external metrics contract from `US-042`, the
audit log contract from `US-026`, and the
environment mode bound from `US-040`; it does
not redefine any of those contracts.

## MVP Scope

This product slice covers:

- A durable per-connector health snapshot table
  with `source_id`, `connector_type`, `window_start`,
  `window_end`, `total_runs`, `success_count`,
  `failure_count`, `success_rate`, `p50_latency_ms`,
  `p95_latency_ms`, `captcha_count`, `captcha_rate`,
  `last_run_at`, `last_error_code`,
  `last_error_message`, `status`, and
  `audit_correlation_id`.
- A durable recent-errors rollup table bounded
  to the most recent N errors per source so a
  single failing connector cannot fill the
  table.
- A closed `ConnectorHealthStatus` enum
  (`healthy`, `degraded`, `unhealthy`,
  `unknown`) with a closed mapping from the
  bounded `success_rate` and `captcha_rate`
  thresholds.
- A bounded computation that reads the existing
  `discovery_jobs` and `audit_entries` rows for
  the source, derives the bounded metrics,
  persists the snapshot, and emits a
  `connector.health.snapshot.computed` audit
  entry.
- An owner/admin-only REST surface that lists
  the per-source summary, the snapshot history,
  the recent-errors rollup, and a bounded
  per-source computation trigger.
- An operator panel widget that lists the latest
  snapshot per source, shows the
  `ConnectorHealthStatus` badge, and exposes a
  `Compute snapshot` button for each source.
- An audit entry shape that reuses the existing
  `AuditEntryRow` from `US-026` and the
  `SanitizeAlertPayload` helper from `US-041`.
- A bounded window bound by the `EnvironmentMode`
  from `US-040` (max 24 hours in `pilot_live`,
  max 1 hour in `test_like`).

This product slice does not yet cover:

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

## Contract Rules

- The bounded computation reads only the
  `discovery_jobs` and `audit_entries` rows for
  the source. It does not read browser-session
  or browser-debug rows.
- The `ConnectorHealthStatus` enum is closed. A
  later story can extend the enum with explicit
  acceptance criteria; the first slice follows
  the four-value mapping documented in
  `docs/decisions/0024-connector-health-surface-baseline.md`.
- The bounded window is enforced by the
  `EnvironmentMode` from `US-040` (max 24 hours
  in `pilot_live`, max 1 hour in `test_like`).
  A window of zero or negative is rejected with
  `CONNECTOR_HEALTH_INVALID_WINDOW`; a window
  that exceeds the bound is clipped to the
  bound.
- The `SanitizeAlertPayload` helper from
  `US-041` runs on every snapshot, error, and
  audit payload before persistence. The
  `connector_health_snapshots` and
  `connector_health_errors` tables never store
  raw PII, secrets, cookies, browser storage
  state, or full connection strings. The
  `last_error_message` column is bounded to
  `max_error_message_length` characters.
- All new endpoints require an authenticated
  session with `owner` or `admin` role.
  Viewer, analyst, sales, and reviewer roles
  get no access to the connector health
  surface.
- The bounded computation refuses to read
  signals for a source that does not exist. A
  missing source returns
  `CONNECTOR_HEALTH_SOURCE_NOT_FOUND`.
- The bounded computation never reads the
  `last_error_message` from a raw
  `audit_entries` row. The computation reads
  the `error_message` field that the existing
  audit-log contract sanitizes at write time;
  the bounded path applies the same
  `SanitizeAlertPayload` helper to the derived
  value before persistence.
- The `compute_snapshot` operation is bounded
  to a single source. A future story can
  extend the surface to compute a workspace-
  wide rollup behind the same
  `ConnectorHealthService` seam.

## API Surface

- `GET /admin/connectors/health/summary` —
  owner/admin only. Returns the latest snapshot
  per source with the status, success rate,
  last run, and CAPTCHA rate.
- `GET /admin/connectors/health/snapshots?source_id=&status=&limit=&offset=`
  — owner/admin only. Returns paginated
  snapshot history with sanitized payloads.
- `POST /admin/connectors/health/snapshots:compute`
  — owner/admin only. Body shape:
  `{ source_id, window_seconds? }`. Bounded,
  confirmation-gated computation that executes
  a single per-source snapshot and returns the
  result inline.
- `GET /admin/connectors/{source_id}/health/errors?limit=`
  — owner/admin only. Returns the recent error
  rollup for the source detail surface.

## Connector Health Status Contract

The closed `ConnectorHealthStatus` enum maps
the bounded `success_rate` and `captcha_rate`
thresholds to one of four values:

- `healthy` — success rate ≥ `0.9` and CAPTCHA
  rate ≤ `0.05`.
- `degraded` — success rate in `[0.7, 0.9)` or
  CAPTCHA rate in `(0.05, 0.2]`.
- `unhealthy` — success rate `< 0.7` or CAPTCHA
  rate `> 0.2`.
- `unknown` — the source has never run in the
  window or the bounded computation found no
  signals to read.

A future story can extend the enum with explicit
acceptance criteria; the first slice follows the
four-value mapping above.

## Audit Entry Contract

The audit entry shape reuses the existing
`AuditService` from `US-026`:

- `connector.health.snapshot.computed` — single
  per-source snapshot computation.
- `connector.health.summary.requested` —
  per-source summary request.
- `connector.health.errors.requested` —
  recent-errors rollup request.
- `connector.health.snapshot.rejected` —
  bounded computation rejected (missing
  source, invalid window, missing acceptance
  metadata).

Every audit payload runs through the existing
`SanitizeAlertPayload` helper from `US-041`.
The `connector_health_snapshots` table stores
the `audit_correlation_id`; the
`connector_health_errors` table stores the
`audit_correlation_id`.

## UI Surface

The first connector health slice should extend
existing admin surfaces:

- `Connector health` panel on the settings
  surface for owner/admin roles. The panel
  renders the latest snapshot per source, the
  `ConnectorHealthStatus` badge, and the
  `Compute snapshot` button.
- `Health` link from the admin connectors
  surface from `US-003` to the new panel so
  operators can jump from the connector
  registry to the health view.
- In-app inbox entry from `US-029` for every
  `connector.health.*` audit entry with a
  dedicated severity icon and a deep link to
  the operator panel.

## Validation Implications

- Unit proof should cover the
  `ConnectorHealthComputer` operations, the
  `ConnectorHealthStatus` enum closure, the
  `EnvironmentMode` bound for the bounded
  window, the `MetricRegistry` extension, the
  `AlertMetric` enum extension, and the
  `SanitizeAlertPayload` reuse for every
  snapshot, error, and audit entry.
- Integration proof should cover the REST
  surface, the audit entry shape, the bounded
  window enforcement, and the cross-tenant
  denial paths.
- E2E proof should cover the operator panel,
  the per-source computation, the bounded
  window enforcement, and the deterministic
  computation for a seeded source.
- Logs or audit proof should confirm who
  computed, requested, or rejected a connector
  health snapshot and when.
- Platform proof should keep the connector
  health verification path wired into the
  Harness matrix before per-tenant thresholds,
  external health APIs, or per-connector
  CAPTCHA detection policy stories build on it.
