# Operational Observability And Alerting

Source: `SPEC.md` sections 5.14, 6.3, 10.1, 10.2, 10.3, and the runtime
contracts established by `US-040` and `US-026`.

## Product Goal

LiveLead already exposes a number of durable runtime signals
(`LaunchGateReport`, `worker_heartbeats`, `backup_snapshots`,
`live_integration_toggles`, `audit_logs`, `discovery_jobs`,
`browser_sessions`, per-connector policy metadata) and the in-app inbox
plus email channels from `US-029` are already wired to operators. The
product still does not have one bounded observability and alerting
contract that turns those scattered signals into actionable alerts and
a single operator view.

This product slice is the first step toward operational observability
for the pilot-live environment. It is a supporting governance slice for
the core MVP jobs in `docs/product/mvp-scope-and-priorities.md`, not a
new primary value track by itself.

The slice is local-first by design. It does not commit to a specific
external metrics stack (Prometheus, OpenTelemetry, Sentry, Grafana) in
this step; it preserves a stable seam for a later hardening story to
wire one.

## MVP Scope

This product slice covers:

- A durable `AlertRule` model with a closed set of supported metrics,
  operators, severities, and delivery channels.
- A durable `AlertEvent` model with sanitized payloads, deduplication
  keys, status transitions, and audit linkage.
- An `AlertEvaluator` that runs from a periodic worker tick and from
  key product paths (job completion, backup recording, worker
  heartbeat, browser session lifecycle).
- A `BuildOperatorSummary` view that combines the `LaunchGateReport`
  from `US-040`, the most recent open `AlertEvent` rows, backup age,
  worker heartbeat, and a per-connector health rollup.
- A `SanitizeAlertPayload` helper shared with the audit log so secrets,
  cookies, raw PII, browser storage state, and full connection strings
  are stripped before any alert event is persisted.
- Seed alert rules for: stale backup, missing worker heartbeat,
  connector failure spike, discovery `NEEDS_USER_ACTION` rate, browser
  crash loop, and audit retention breach risk.
- New bounded admin REST surface:
  - `GET /admin/observability/summary`
  - `GET /admin/alert-rules`
  - `POST /admin/alert-rules`
  - `PATCH /admin/alert-rules/{id}`
  - `DELETE /admin/alert-rules/{id}`
  - `GET /admin/alert-events`
  - `POST /admin/alert-events/{id}/acknowledge`
- Reuse of the in-app inbox and email channels from `US-029` for alert
  delivery. No new external notification provider is introduced in this
  slice.
- A settings/operator panel for owner/admin roles that exposes the
  summary, the recent alert list, and the rule management table.

This product slice does not yet cover:

- External metrics pipeline (Prometheus exporters, OpenTelemetry
  collectors, Sentry ingestion, Grafana dashboards).
- Distributed tracing, APM, and cross-service call graph analysis.
- SLO burn-rate alerts, multi-window burn-rate evaluation, and anomaly
  detection.
- Auto-remediation, self-healing, or any action that mutates product
  state from an alert evaluation.
- Customer-facing status pages or external incident communication.
- Per-tenant tuning of seed rule thresholds; the slice ships one fixed
  seed set and exposes rule management for follow-on tuning.
- Migration of historical `audit_logs` rows into the alert pipeline.

## Contract Rules

- All new admin endpoints require an authenticated session with `owner`
  or `admin` role. Viewer, analyst, sales, and reviewer roles get no
  observability summary and cannot manage rules.
- Every `AlertEvent` payload must pass `SanitizeAlertPayload` before
  persistence. The helper rejects or redacts API keys, cookies, raw
  PII, browser storage state, and full connection strings.
- The evaluator is read-only with respect to product state. It
  persists `AlertEvent` rows and dispatches alerts through the existing
  in-app inbox and email channels; it does not pause jobs, disable
  connectors, flip live toggles, or roll back the environment.
- Seed rules are owned by the platform. Owners and admins can adjust
  thresholds, windows, severities, and channels but cannot delete or
  rename a system rule. Renaming and `metric` changes are rejected for
  system rules.
- A `cooldown_seconds` window suppresses duplicate firings per
  `deduplication_key`. Suppression is recorded by transitioning the
  existing open `AlertEvent` to `suppressed` and creating a new row
  only after the cooldown expires.
- Alert acknowledgement and resolution emit durable audit entries
  (`alert.acknowledged`, `alert.resolved`) using the same secret-safe
  contract as `US-026`.
- The `/admin/observability/summary` endpoint is covered by the health
  probe contract: a missing or failing summary must not fail
  `GET /health/ready`, only surface as a degraded warning.

## Supported Seed Metrics

| Metric | Source | Default Threshold | Default Severity |
| --- | --- | --- | --- |
| `backup.age_hours` | `backup_snapshots.created_at` | `> 26` (RPO 24h + grace) | `critical` |
| `worker.heartbeat.age_seconds` | `worker_heartbeats` | `> 120` | `warning` |
| `connector.failure_rate` | rolling window of `discovery_jobs` and `audit_logs` | `> 0.5` over `1800`s | `warning` |
| `discovery.needs_user_action_rate` | `discovery_jobs.status` transitions | `> 0.3` over `3600`s | `warning` |
| `browser.crash_loop` | `browser_sessions` and `browser.crashed` audit events | `>= 3` crashes in `600`s for the same profile | `critical` |
| `audit.retention_breach_risk` | oldest `audit_logs.occurred_at` vs `NFR-SEC-008` floor | `> 90` days without retention action | `warning` |

These thresholds are the seed defaults. Owners and admins can adjust
threshold, window, severity, and channels through the rule management
endpoints; the rules themselves are seeded by the migration and remain
visible with `is_system = true`.

## Runtime And Admin Surface

- `GET /admin/observability/summary` — owner/admin only. Aggregates
  environment mode, launch-gate status, open alert count by severity,
  the five most recent open alerts, backup age, worker heartbeat, and
  per-connector health rollup.
- `GET /admin/alert-rules` — owner/admin only. Lists rules with
  `is_system` flag.
- `POST /admin/alert-rules` — owner/admin only. Creates a user rule
  after validation against the closed enumerations.
- `PATCH /admin/alert-rules/{id}` — owner/admin only. Updates
  threshold, window, severity, channels, and enabled state.
- `DELETE /admin/alert-rules/{id}` — owner/admin only. Soft-deletes
  user rules; refuses to delete system rules.
- `GET /admin/alert-events?status=&severity=&rule_id=&limit=` —
  owner/admin only. Returns paginated alert history with sanitized
  payloads.
- `POST /admin/alert-events/{id}/acknowledge` — owner/admin only.
  Transitions a firing event to `acknowledged` and writes an audit
  entry.

All new error responses follow the existing error envelope
(`code`, `message`, `request_id`, `details`). Unknown metric, operator,
severity, or channel combinations return `ALERT_RULE_INVALID`.

## UI / Ops Surface

- Settings gains an `Observability` panel for owner/admin roles. The
  panel renders the operator summary, the recent alert list, and the
  rule management table.
- The in-app inbox from `US-029` shows alert events with a dedicated
  severity icon and a deep link to the alert event detail in the
  observability panel.
- The first observability runbook (`docs/ops/observability-runbook.md`)
  documents what an operator does when a `critical` alert fires,
  including the read-only nature of the evaluator and the need to act
  through the existing admin surfaces.

## Validation Implications

- Unit tests must prove that rule validation, payload sanitization, and
  evaluator cooldown and deduplication logic all reject or correctly
  process the documented input space.
- Integration tests must exercise every new endpoint against an
  in-memory SQLite plus a stubbed notification dispatcher and prove
  that role gates and sanitization are enforced.
- E2E tests must cover the operator panel render, the simulated seed
  signal fire, the inbox handoff, and the acknowledge flow.
- Security tests must prove that viewer, analyst, sales, and reviewer
  sessions are rejected on every new endpoint.
- Operational tests must prove the seed rule set matches the documented
  table, the runbook entry exists, and the verify script exercises
  each seed signal.
- Platform proof is the `scripts/verify-us-041.sh` command wired into
  `story verify` and `story verify-all`.
