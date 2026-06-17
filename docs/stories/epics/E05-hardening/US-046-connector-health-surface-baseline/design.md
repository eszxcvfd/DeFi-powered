# Design

## Domain Model

The first connector health surface slice formalizes
the durable objects and bounded services that turn
`FR-ADM-002` into a documented contract, a
per-connector health snapshot, an owner/admin-only
REST surface, and a reusable computation service.

### `ConnectorHealthSnapshot`

A single record of a per-connector health
computation result. The row carries enough
information to answer the `FR-ADM-002` question
"is connector X healthy right now?" without
reading raw tables.

- `id`
- `organization_id`
- `source_id`
- `connector_type` (`api`, `rss`, `ics`,
  `playwright`, `selenium`, `cloakbrowser`,
  `manual`, `unknown`)
- `window_start`
- `window_end`
- `total_runs`
- `success_count`
- `failure_count`
- `success_rate` (closed `[0.0, 1.0]`)
- `p50_latency_ms`
- `p95_latency_ms`
- `captcha_count`
- `captcha_rate` (closed `[0.0, 1.0]`)
- `last_run_at` (nullable when the source has
  never run in the window)
- `last_error_code` (nullable)
- `last_error_message` (bounded to 500
  characters; the secret-safe payload contract
  from `US-041` is enforced before persistence)
- `status` (`healthy`, `degraded`, `unhealthy`,
  `unknown`)
- `audit_correlation_id` (links the snapshot row
  to the matching `AuditEntry` row)
- `computed_at`
- `created_at`, `updated_at`

### `ConnectorHealthError`

A single record of a recent error rollup. The
table is bounded to the most recent N errors per
source so a single failing connector cannot fill
the table.

- `id`
- `organization_id`
- `source_id`
- `error_code`
- `error_message` (bounded to 500 characters;
  the secret-safe payload contract from
  `US-041` is enforced before persistence)
- `first_seen_at`
- `last_seen_at`
- `occurrence_count`
- `audit_correlation_id`
- `created_at`

### `ConnectorHealthStatus` (closed enum)

A closed enumeration of connector health status.
The bounded computation reads from the closed
`success_rate` and `captcha_rate` thresholds and
returns one of these four values. New statuses
cannot be added without first extending the
`ConnectorHealthService` and the audit entry
shape.

- `healthy` — success rate ≥ `0.9` and CAPTCHA
  rate ≤ `0.05`.
- `degraded` — success rate in `[0.7, 0.9)` or
  CAPTCHA rate in `(0.05, 0.2]`.
- `unhealthy` — success rate `< 0.7` or CAPTCHA
  rate `> 0.2`.
- `unknown` — the source has never run in the
  window or the bounded computation found no
  signals to read.

### `ConnectorHealthThresholds`

The closed set of thresholds the bounded
computation reads. The thresholds follow the
defaults documented in
`docs/product/connector-health-surface.md` and
are exposed as a single dataclass so a future
story can extend the surface with per-tenant
tuning without redefining the contract.

- `healthy_min_success_rate = 0.9`
- `degraded_min_success_rate = 0.7`
- `healthy_max_captcha_rate = 0.05`
- `degraded_max_captcha_rate = 0.2`
- `default_window_seconds = 3600`
- `recent_errors_limit = 20`
- `max_error_message_length = 500`

### `ConnectorHealthService`

The application service that owns the bounded
operations. The service is the only place that
mutates `connector_health_snapshots` and
`connector_health_errors` and emits the
`connector.health.*` audit entries; the REST
layer calls it from the request handlers.

- `compute_snapshot(source_id, *, window_seconds)`
  — reads the `discovery_jobs` and
  `audit_entries` rows for the source, derives
  the bounded metrics, persists a
  `connector_health_snapshots` row, and emits a
  `connector.health.snapshot.computed` audit
  entry.
- `list_snapshots(*, source_id, status, limit,
  offset)` — returns the most recent snapshots
  for the operator panel and the verify script.
- `build_summary(*, source_id, status)` —
  returns the latest snapshot per source with
  the bounded thresholds, the current values,
  and the breach flag for the operator panel.
- `list_recent_errors(*, source_id, limit)` —
  returns the most recent
  `connector_health_errors` rows for the source
  detail surface.

### `ConnectorHealthComputer`

A small helper that derives the bounded metrics
from a list of `discovery_jobs` and
`audit_entries` rows. The computer is the only
place that owns the `ConnectorHealthStatus`
mapping; the service and the test fixtures call
it from a single seam.

- `derive_metrics(*, discovery_jobs, audit_entries,
  window_start, window_end)` — returns the
  bounded metrics dataclass.
- `classify_status(*, success_rate, captcha_rate,
  total_runs, thresholds)` — returns the closed
  `ConnectorHealthStatus` value.
- `bounded_window(*, now, window_seconds)` —
  returns the bounded `(window_start, window_end)`
  pair the computation reads.

Business rules:

- All new endpoints require an authenticated
  session with `owner` or `admin` role.
  Viewer, analyst, sales, and reviewer roles get
  no access to the connector health surface.
- The bounded computation refuses to read signals
  outside the closed `window_seconds` bound. A
  window of zero or negative is rejected with
  `CONNECTOR_HEALTH_INVALID_WINDOW`; a window
  that exceeds the `EnvironmentMode` bound from
  `US-040` is clipped to the bound.
- The `SanitizeAlertPayload` helper from
  `US-041` runs on every snapshot and audit
  payload before persistence. The
  `connector_health_snapshots` and
  `connector_health_errors` tables never store
  raw PII, secrets, cookies, browser storage
  state, or full connection strings. The
  `last_error_message` column is bounded to
  `max_error_message_length` characters.
- The bounded computation reads only the
  `discovery_jobs` and `audit_entries` rows for
  the source. It does not read browser-session
  or browser-debug rows. A future story can
  extend the computation to read those rows
  behind the same `ConnectorHealthComputer`
  seam.
- The `ConnectorHealthStatus` enum is closed. A
  later story can extend the enum with explicit
  acceptance criteria; the first slice follows
  the four-value mapping above.
- The `connector_health_snapshots` and
  `connector_health_errors` tables are durable
  and additive. The documented rollback path is
  to drop the new tables. No existing rows are
  touched.
- The bounded computation refuses to read signals
  for a source that does not exist. A missing
  source returns `CONNECTOR_HEALTH_SOURCE_NOT_FOUND`.
- The bounded computation never reads the
  `last_error_message` from a raw `audit_entries`
  row. The computation reads the
  `error_message` field that the existing
  audit-log contract sanitizes at write time;
  the bounded path applies the same
  `SanitizeAlertPayload` helper to the derived
  value before persistence.
- The `compute_snapshot` operation is bounded
  to a single source. A future story can extend
  the surface to compute a workspace-wide rollup
  behind the same `ConnectorHealthService` seam.

## Application Flow

- `ComputeConnectorHealthSnapshot` (owner/admin)
  — validates the `source_id` and the
  `window_seconds`, reads the bounded signals,
  calls `ConnectorHealthComputer.derive_metrics`,
  persists the `ConnectorHealthSnapshot` row,
  and emits a
  `connector.health.snapshot.computed` audit
  entry.
- `ListConnectorHealthSnapshots` (owner/admin)
  — returns the most recent snapshots for the
  operator panel and the verify script.
- `BuildConnectorHealthSummary` (owner/admin)
  — composes a single payload containing the
  latest snapshot per source with the bounded
  thresholds, the current values, and the
  breach flag.
- `ListConnectorHealthErrors` (owner/admin) —
  returns the most recent
  `ConnectorHealthErrors` rows for the source
  detail surface.
- `SanitizeConnectorHealthPayload` (shared
  helper) — runs every audit payload through
  the existing helper from `US-041` so the
  contract is defined once and reused.

## Interface Contract

This slice adds the minimum REST surface that
owners and admins need to see, configure, and
trigger the bounded connector health surface.

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

Expected payload concerns:

- All new error responses follow the existing
  error envelope (`code`, `message`,
  `request_id`, `details`).
- Unknown sources, invalid windows, missing
  acceptance metadata, and missing signals
  return `CONNECTOR_HEALTH_SOURCE_NOT_FOUND`,
  `CONNECTOR_HEALTH_INVALID_WINDOW`,
  `CONNECTOR_HEALTH_ACCEPTANCE_REQUIRED`, and
  `CONNECTOR_HEALTH_NO_SIGNALS` respectively.
- Every snapshot computation and recent-errors
  rollup emits a durable audit entry with the
  same secret-safe payload contract as
  `US-026` and `US-041`.

## Data Model

New durable objects, each with a forward-only
migration and an index strategy sized for the
current SQLite baseline:

- `connector_health_snapshots` (organization-scoped,
  index on `(organization_id, source_id,
  computed_at)` for the per-source history
  endpoint, index on `(organization_id, status,
  computed_at)` for the operator panel).
- `connector_health_errors` (organization-scoped,
  index on `(organization_id, source_id,
  last_seen_at)` for the recent-errors
  endpoint, index on `(organization_id,
  error_code)` for the admin audit log filter
  from `US-026`).

No raw payload, secret, cookie, or browser
storage state is stored in the new tables. The
migration header documents that the change is
additive and that dropping the new tables is
the documented rollback path; no data outside
the new tables is affected.

The slice also extends:

- The `MetricRegistry` from `US-042` with five
  new descriptors that mirror the bounded
  metrics:
  - `connector.success_rate`
  - `connector.p95_latency_ms`
  - `connector.captcha_rate`
  - `connector.runs_total`
  - `connector.last_run_at_seconds`
- The `AlertMetric` enum from `US-041` with the
  same five metric names so the existing
  `AlertEvaluator` can reason about the new
  signals without a parallel alert path.
- The `audit_entries` table with four new
  `connector.health.*` event types:
  `connector.health.snapshot.computed`,
  `connector.health.summary.requested`,
  `connector.health.errors.requested`, and
  `connector.health.snapshot.rejected`.

## UI / Platform Impact

- The admin settings surface gains a
  `Connector health` panel for owner/admin
  roles. The panel renders the latest snapshot
  per source, the `ConnectorHealthStatus` badge,
  and a `Compute snapshot` button for each
  source.
- The admin connectors surface from `US-003`
  gains a `Health` link to the new panel so
  operators can jump from the connector
  registry to the health view.
- The in-app inbox from `US-029` shows
  `connector.health.*` audit entries with a
  dedicated severity icon and a deep link to
  the operator panel.
- The frontend does not need a parallel
  notification channel; it reuses the inbox
  and settings surfaces already shipped by
  `US-026` and `US-029`.
- The `scripts/verify-us-046.sh` command wires
  the unit, integration, E2E, security,
  operational, and platform checks together
  and is the same command run by
  `harness-cli story verify` and
  `harness-cli story verify-all`.

## Observability

This story is the connector health side of the
existing observability surface, so it must set
the standard that the next story will be measured
against.

- Every request handled by the new endpoints
  keeps a correlation id that matches the
  existing request envelope and is forwarded
  to the audit entry and the
  `connector_health_snapshots` row.
- Every snapshot computation, summary request,
  and recent-errors request emits a structured
  log line and a matching audit entry.
- The bounded verification harness publishes
  a thin counter
  (`connector.health.compute.duration_ms`) so a
  future performance story can detect a slow
  computation before it becomes a launch-gate
  blocker.
- The new endpoints are themselves covered by
  the health probe contract from `US-040`: a
  missing or failing
  `GET /admin/connectors/health/summary` must
  not fail `GET /health/ready`, only surface as
  a degraded warning.

## Alternatives Considered

1. **Wire a specific health service (Datadog,
   Sentry Performance, a managed Prometheus
   service).** This would have committed the
   MVP to a particular health consumer before
   any operator had used the local-first
   baseline. The slice keeps the harness
   tool-agnostic so a later story can wire a
   vendor without re-opening the snapshot,
   status, or audit contracts.
2. **Skip the snapshot table and compute on
   read.** This would have made the bounded
   surface slow at scale and would have
   prevented the operator panel from rendering
   the historical trend. The slice ships a
   durable snapshot table so a future alerting
   story can read the bounded signal without
   re-running the computation.
3. **Push the connector health surface through
   a new external channel instead of the
   existing in-app inbox and settings
   surfaces.** This would have added a new
   provider before the local-first baseline was
   proven and would have created a parallel
   channel that could drift away from the
   existing notification preferences from
   `US-029` and the sanitization helper from
   `US-041`. Reusing the same helper and the
   same audit entry shape keeps the contract
   aligned with the rest of the product.
4. **Bundle the connector health surface into
   the existing `US-041` observability slice.**
   This would have inflated the observability
   surface beyond its bounded contract. The
   `US-041` design notes explicitly carve the
   connector health surface out as a follow-on;
   the slice ships the follow-on.
5. **Skip the closed `ConnectorHealthStatus`
   enum and use a free-text status.** This
   would have hidden the bounded thresholds
   from the operator panel and would have
   forced a later alert story to re-open the
   status contract. The slice ships the closed
   enum; a later story can extend it with
   explicit acceptance criteria.
