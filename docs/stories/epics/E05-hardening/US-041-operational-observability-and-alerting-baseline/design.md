# Design

## Domain Model

The first observability and alerting slice formalizes a small set of
durable concepts that turn scattered runtime signals into actionable
alerts and a single operator view.

### `AlertRule`

A persistent definition of a condition that should fire an alert.

- `id`
- `organization_id`
- `name` (unique per organization, e.g. `backup.stale`)
- `metric` (a closed enumeration of supported metrics such as
  `backup.age_hours`, `worker.heartbeat.age_seconds`,
  `connector.failure_rate`, `discovery.needs_user_action_rate`,
  `browser.crash_loop`, `audit.retention_breach_risk`)
- `operator` (a closed enumeration: `gt`, `gte`, `lt`, `lte`, `eq`)
- `threshold` (numeric)
- `window_seconds` (rolling evaluation window)
- `severity` (`info`, `warning`, `critical`)
- `cooldown_seconds` (minimum seconds between firings of the same rule)
- `channels` (subset of `in_app`, `email`)
- `enabled`
- `is_system` (true for seed rules owned by the platform; cannot be
  deleted by users)
- `created_by`, `created_at`, `updated_at`

### `AlertEvent`

A single firing of an `AlertRule`, with sanitized payload and audit
linkage.

- `id`
- `organization_id`
- `rule_id`
- `fired_at`
- `resolved_at` (nullable; set by the evaluator when the condition
  clears)
- `status` (`firing`, `acknowledged`, `resolved`, `suppressed`)
- `severity`
- `payload_json` (sanitized snapshot of the metric value, window, and
  correlation id; never raw secret material)
- `correlation_id`
- `acknowledged_by` (nullable), `acknowledged_at` (nullable)
- `deduplication_key` (hash of `rule_id` + window bucket; suppresses
  duplicate firings inside the cooldown window)

### `MetricCounter` (lightweight, per process)

A bounded in-process counter surface (not a separate table) that the
evaluator reads. Counters are sourced from existing durable signals
when possible and from thin in-memory increments when not:

- `backup.age_hours` — derived from `backup_snapshots.created_at`
- `worker.heartbeat.age_seconds` — derived from `worker_heartbeats`
- `connector.failure_rate` — derived from
  `discovery_jobs.error_summary` and `audit_logs` over the rolling
  window
- `discovery.needs_user_action_rate` — derived from `discovery_jobs`
  status transitions over the rolling window
- `browser.crash_loop` — derived from `browser_sessions` and audit
  events with action `browser.crashed`
- `audit.retention_breach_risk` — derived from the age of the oldest
  `audit_logs` row compared to the configured retention floor

Business rules:

- All new endpoints require an authenticated session with `owner` or
  `admin` role. Viewer, analyst, sales, and reviewer roles get no
  observability summary and cannot manage rules.
- `AlertRule.payload_json` must pass the existing secret-safe
  sanitization helper before it is persisted. The helper rejects keys,
  cookies, raw PII, browser storage state, and full connection strings.
- `AlertEvaluator` is read-only with respect to product state. It
  persists `AlertEvent` rows and dispatches through the existing
  notification channels; it does not pause jobs, disable connectors,
  flip live toggles, or roll back the environment.
- Seed rules are inserted by the migration with `is_system = true` and
  are owned by the platform. Owners and admins can adjust thresholds,
  windows, and channels but cannot delete or rename a system rule.
- A `cooldown_seconds` window suppresses duplicate firings per
  `deduplication_key`. Suppression is recorded by transitioning the
  existing open `AlertEvent` to `suppressed` and creating a new row only
  after the cooldown expires.

## Application Flow

- `DefineAlertRule` (owner/admin) — validates the rule against the
  closed `metric`, `operator`, `severity`, and `channels` enumerations,
  rejects unknown combinations, and records the rule.
- `EvaluateAlertRules` (worker tick + targeted calls) — iterates
  enabled rules, reads the source signal, applies the operator and
  threshold, computes a `deduplication_key`, checks the cooldown
  window, and either fires a new `AlertEvent`, suppresses, or
  transitions an open event to `resolved`.
- `DeliverAlert` (reuses `US-029`) — maps `severity` and `channels` to
  the in-app inbox and, when the user has email enabled for that
  severity, the existing email dispatcher. No new external provider is
  added in this slice.
- `AcknowledgeAlert` (owner/admin) — transitions a firing event to
  `acknowledged`, records the actor, and writes an audit entry.
- `BuildOperatorSummary` (owner/admin) — composes a single payload
  containing the current `LaunchGateReport` summary, the five most
  recent open `AlertEvent` rows, backup age, worker heartbeat, and a
  per-connector health rollup. The payload is sanitized by the same
  helper used for `AlertEvent.payload_json`.
- `SanitizeAlertPayload` (shared helper) — runs every payload through
  the existing secret-safe filter from `US-026` so the contract is
  defined once and reused.

## Interface Contract

This slice adds the minimum REST surface that owners and admins need
to see, configure, and acknowledge alerts.

- `GET /admin/observability/summary` — owner/admin only. Returns the
  aggregated `OperatorSummary` payload: environment mode, launch-gate
  status, open alert count by severity, five most recent open alerts,
  backup age, worker heartbeat age, per-connector health rollup, and
  CAPTCHA rate rollup. Never returns secrets, raw PII, or sensitive
  browser state.
- `GET /admin/alert-rules` — owner/admin only. Lists rules visible to
  the current organization. System rules are flagged with `is_system`.
- `POST /admin/alert-rules` — owner/admin only. Creates a user rule.
  Validates against the closed enumerations.
- `PATCH /admin/alert-rules/{id}` — owner/admin only. Updates
  threshold, window, severity, channels, and enabled state. Renaming
  and `metric` changes are rejected for system rules.
- `DELETE /admin/alert-rules/{id}` — owner/admin only. Refuses to
  delete a system rule. Soft-deletes user rules and keeps the row for
  audit linkage.
- `GET /admin/alert-events?status=&severity=&rule_id=&limit=` —
  owner/admin only. Returns paginated alert history with sanitized
  payloads.
- `POST /admin/alert-events/{id}/acknowledge` — owner/admin only.
  Transitions a firing event to `acknowledged`, records the actor, and
  writes an `alert.acknowledged` audit entry.

Expected payload concerns:

- All new error responses follow the existing error envelope
  (`code`, `message`, `request_id`, `details`).
- Unknown metrics, operators, severities, or channels return
  `ALERT_RULE_INVALID` so the failure mode is reviewable in CI.
- Acknowledge and resolve actions emit durable audit entries
  (`alert.acknowledged`, `alert.resolved`) with the same secret-safe
  payload contract as `US-026`.

## Data Model

New durable objects, each with a forward-only migration and an
index strategy sized for the current SQLite baseline:

- `alert_rules` (organization-scoped, unique on `(organization_id, name)`,
  index on `metric` for evaluator lookups, index on `enabled` for the
  evaluation tick)
- `alert_events` (organization-scoped, index on
  `(organization_id, status, fired_at)` for the summary endpoint, index
  on `deduplication_key` for cooldown lookups, index on `rule_id` for
  the events filter)

No raw payload, secret, cookie, or browser storage state is stored in
either table. The migration header documents that the change is
additive and that dropping the new tables is the documented rollback
path; no data outside the new tables is affected.

## UI / Platform Impact

- The admin settings surface gains an `Observability` panel for
  owner/admin roles. The panel renders the operator summary, the
  recent alert list, and the rule management table.
- The dashboard already shows connector health warnings; the
  observability panel complements it with a single page that combines
  environment readiness, alert history, and rule configuration.
- The existing in-app inbox from `US-029` shows alert events with a
  dedicated severity icon and a deep link to the alert event detail
  in the operator panel.
- The frontend does not need a parallel notification channel; it
  reuses the inbox and settings surfaces already shipped by `US-026`
  and `US-029`.

## Observability

This story is itself the first slice of observability, so it must set
the standard the next story will be measured against.

- Every request handled by the new endpoints keeps a correlation id
  that matches the existing request envelope.
- Every fired, acknowledged, and resolved alert emits a structured log
  line and a matching audit entry.
- The evaluator publishes a heartbeat row into `worker_heartbeats` so
  the launch-gate contract from `US-040` keeps a live signal of
  observability health.
- Rule evaluation timing is recorded as a thin counter
  (`alert.evaluator.duration_ms`) so a future performance story can
  detect a slow evaluator before it becomes a launch-gate blocker.
- The `/admin/observability/summary` endpoint is itself covered by the
  health probe contract: a missing or failing summary must not fail
  `GET /health/ready`, only surface as a degraded warning.
