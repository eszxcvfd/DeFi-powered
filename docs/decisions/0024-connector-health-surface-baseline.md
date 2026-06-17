# 0024 Connector Health Surface Baseline

Date: 2026-06-16

## Status

Planned (companion decision to `US-046`).

## Context

`US-041` shipped the first operational observability
and alerting baseline for LiveLead and explicitly
carved the connector health surface out as a
follow-up. The relevant extracts from the durable
record are:

- `docs/decisions/0019-observability-and-alerting-baseline.md`,
  "Context" section: "A connector health surface
  (`FR-ADM-002`) with success rate, recent errors,
  latency, item counts, CAPTCHA rate, and last
  run."
- `docs/stories/epics/E05-hardening/US-041-operational-observability-and-alerting-baseline/design.md`,
  "Application Flow" section: "The bounded
  observability surface covers per-connector
  health rollup, but a dedicated connector health
  surface is a follow-on."

`SPEC.md` section 5.14 (`FR-ADM-002`) commits the
product to a connector health surface that admins
can read:

> **FR-ADM-002 — Connector health**
> **Ưu tiên:** Must
> Admin xem được tỷ lệ thành công, lỗi gần nhất,
> latency, số item, CAPTCHA rate và lần chạy gần
> nhất của connector.

`US-001` through `US-045` delivered a broad MVP
and the first bounded hardening slices. The
product now has:

- A first operational observability and alerting
  baseline (`US-041`) that ships six seed rules
  for stale backup, worker heartbeat, connector
  failure rate, discovery `NEEDS_USER_ACTION`
  rate, browser crash loop, and audit retention
  risk.
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

The product still has no bounded connector health
surface. The observability summary endpoint from
`US-041` reports the `LaunchGateReport` and the
most recent alerts, but it does not report a
per-connector success rate, recent errors,
latency, item counts, CAPTCHA rate, or last run
timestamp. The `connector.failure_rate` metric
from `US-041` and the `US-042` `MetricRegistry`
expose a single ratio, not the full health surface
from `FR-ADM-002`. Operators who want to answer
"is connector X healthy right now?" still have to
read raw tables or run ad-hoc scripts.

The next step in the hardening epic is therefore a
bounded connector health surface slice that turns
`FR-ADM-002` into a documented contract, a
per-connector health snapshot, an owner/admin-only
REST surface, and a reusable computation service
that a future alerting story can extend without
re-opening the observability and metrics contracts.

## Decision

`US-046` introduces the first connector health
surface baseline for LiveLead.

### Domain objects

- **`ConnectorHealthSnapshot`** — durable record
  of a per-connector health computation result.
  The row carries enough information to answer
  the `FR-ADM-002` question "is connector X
  healthy right now?" without reading raw
  tables.
- **`ConnectorHealthError`** — durable record
  of a recent error rollup. The table is
  bounded to the most recent N errors per
  source so a single failing connector cannot
  fill the table.
- **`ConnectorHealthStatus`** — closed enum of
  connector health status. The bounded
  computation reads from the closed
  `success_rate` and `captcha_rate` thresholds
  and returns one of these four values:
  - `healthy` — success rate ≥ `0.9` and
    CAPTCHA rate ≤ `0.05`.
  - `degraded` — success rate in `[0.7, 0.9)`
    or CAPTCHA rate in `(0.05, 0.2]`.
  - `unhealthy` — success rate `< 0.7` or
    CAPTCHA rate `> 0.2`.
  - `unknown` — the source has never run in
    the window or the bounded computation found
    no signals to read.

### Bounded operations

- **`ConnectorHealthService`** — application
  service that owns the bounded operations. The
  service is the only place that mutates
  `connector_health_snapshots` and
  `connector_health_errors` and emits the
  `connector.health.*` audit entries; the REST
  layer calls it from the request handlers.
- **`ConnectorHealthComputer`** — small helper
  that derives the bounded metrics from a list
  of `discovery_jobs` and `audit_entries` rows.
  The computer is the only place that owns the
  `ConnectorHealthStatus` mapping; the service
  and the test fixtures call it from a single
  seam.

### REST surface

- `GET /admin/connectors/health/summary` —
  owner/admin only. Returns the latest snapshot
  per source with the status, success rate,
  last run, and CAPTCHA rate.
- `GET /admin/connectors/health/snapshots?source_id=&status=&limit=&offset=`
  — owner/admin only. Returns paginated
  snapshot history with sanitized payloads.
- `POST /admin/connectors/health/snapshots:compute`
  — owner/admin only. Bounded, confirmation-
  gated computation that executes a single
  per-source snapshot and returns the result
  inline.
- `GET /admin/connectors/{source_id}/health/errors?limit=`
  — owner/admin only. Returns the recent error
  rollup for the source detail surface.

### Audit entry types

- `connector.health.snapshot.computed`
- `connector.health.summary.requested`
- `connector.health.errors.requested`
- `connector.health.snapshot.rejected`

### Connector Health Status mapping

- `healthy` — `success_rate >= 0.9` and
  `captcha_rate <= 0.05`.
- `degraded` — `success_rate in [0.7, 0.9)` or
  `captcha_rate in (0.05, 0.2]`.
- `unhealthy` — `success_rate < 0.7` or
  `captcha_rate > 0.2`.
- `unknown` — no signals in the window.

The mapping is fixed and follows `FR-ADM-002`. A
later story can extend the mapping with explicit
acceptance criteria; the first slice follows the
mapping above.

### Bounded window bound

- `pilot_live` — max 24 hours
- `test_like` — max 1 hour

The bound is derived from the `EnvironmentMode`
shipped by `US-040`. A user asking for a longer
window is rejected with
`CONNECTOR_HEALTH_INVALID_WINDOW`.

### Follow-Up

A follow-on story can extend the connector health
surface with:

- Distributed tracing of connector calls.
- External health APIs (Datadog, Sentry
  Performance, a managed Prometheus service).
- Auto-remediation or self-healing actions
  driven by a connector health breach.
- Per-tenant thresholds.
- Customer-facing status pages or external
  incident communication.
- Reading browser-session or browser-debug rows
  for the bounded computation.
- Per-connector CAPTCHA detection policy.
- Periodic worker tick that runs the bounded
  computation on a schedule.
- Bulk compute action for the operator panel.

The follow-on stories must keep the bounded
window bound, the `SanitizeAlertPayload`
contract, the audit entry shape, the RBAC
contract from `US-027`, the `MetricRegistry` from
`US-042`, the `AlertMetric` enum from `US-041`,
and the source registry from `US-003` stable.

## Consequences

- LiveLead now has a dedicated connector health
  surface that closes `FR-ADM-002` and the
  explicit follow-up from decision `0019`.
- Operators can answer "is connector X healthy
  right now?" from a single operator panel
  without reading raw tables or running ad-hoc
  scripts.
- The connector health surface is bounded to
  the `EnvironmentMode` from `US-040`, so the
  pilot-live environment ships a 24-hour
  maximum window and the test-like environment
  ships a 1-hour maximum window.
- The closed `ConnectorHealthStatus` enum
  keeps the bounded thresholds stable; a later
  story can extend the enum with explicit
  acceptance criteria.
- The `X-LIVELEAD-CONNECTOR-HEALTH-STATUS`
  extension is the only LiveLead-specific
  extension to the existing `MetricRegistry`
  from `US-042`; a later story can add
  additional metrics behind the same
  `ConnectorHealthComputer` seam.

## References

- `SPEC.md` section 5.14 (`FR-ADM-002`).
- `docs/product/connector-health-surface.md`
  (living product contract seeded by `US-046`).
- `docs/product/source-registry-and-policy.md`
  (`US-003` contract; this story extends the
  source catalog with a connector health
  surface).
- `docs/product/observability-and-alerting.md`
  (`US-041` contract; this story extends the
  observability surface with a per-connector
  health rollup).
- `docs/product/external-metrics-and-tracing.md`
  (`US-042` contract; this story extends the
  `MetricRegistry` with the new connector health
  metrics).
- `docs/product/audit-log-and-governance.md`
  (`US-026` contract; the snapshot computation
  and the recent-errors rollup emit
  `connector.health.*` audit entries with the
  same secret-safe payload contract).
- `docs/product/real-environment-cutover-and-live-operations.md`
  (`US-040` contract; the bounded window is
  enforced by the `EnvironmentMode` from
  `US-040`).
- `docs/stories/epics/E05-hardening/US-041-operational-observability-and-alerting-baseline/`
  (predecessor story packet; the observability
  design notes preserve the connector health
  seam).
- `docs/stories/epics/E05-hardening/US-046-connector-health-surface-baseline/`
  (this story packet).
- `docs/ops/connector-health-runbook.md`
  (operational entry seeded by this story).
