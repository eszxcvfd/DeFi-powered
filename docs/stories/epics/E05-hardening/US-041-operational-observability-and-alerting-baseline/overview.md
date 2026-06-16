# Overview

## Current Behavior

US-001 through US-040 delivered a broad MVP and a first governed
real-environment pilot cutover. `US-040` introduced environment modes
(`test_like`, `pilot_live`, `paused`), launch-gate checks, live integration
toggles, backup metadata recording, and a runtime-readiness surface.

The product still has no bounded observability or alerting slice:

- Runtime signals are scattered: per-request logs, `worker_heartbeats`,
  `audit_logs`, `backup_snapshots`, `live_integration_toggles`, and per-job
  status live in separate tables without a unified operator view.
- There is no persisted alert rule, so every signal that needs to wake a human
  is hand-coded into application paths.
- There is no in-app or email alert for a stale backup, a missing worker
  heartbeat, a sustained connector failure rate, a discovery job that keeps
  landing in `NEEDS_USER_ACTION`, or a browser-session crash loop.
- `FR-ADM-002` (connector health), `NFR-REL-005` (RPO 24h, RTO 8h), `NFR-SEC-008`
  (audit retention 90 days), and `NFR-PERF-001..005` (performance thresholds)
  are stated in `SPEC.md` but not yet backed by durable alert paths.
- Operators have to read raw tables or run ad-hoc scripts to answer
  "is anything on fire right now?".

## Target Behavior

This story establishes the first bounded operational observability and
alerting baseline for LiveLead. After the story is complete:

- A durable `AlertRule` table holds owner/admin-defined or system-defined
  rules that match a named metric, condition, severity, and delivery channel.
- A durable `AlertEvent` table records every fired/acknowledged/resolved alert
  with a sanitized payload, correlation id, and audit linkage.
- A new `EvaluationTick` runs from the worker queue and from key product paths
  (job completion, backup recording, worker heartbeat, browser session
  lifecycle) to evaluate rules and dispatch alerts.
- A new `GET /admin/observability/summary` returns a single owner/admin view
  that aggregates `LaunchGateReport`, recent alerts, backup age, worker
  heartbeat, connector health, and per-source CAPTCHA rate.
- New bounded alert surfaces include: stale backup, missing worker heartbeat,
  connector failure spike, discovery job stuck in `NEEDS_USER_ACTION`,
  browser session crash loop, and audit retention breach risk.
- Alerts are delivered through the existing in-app inbox and (when enabled)
  email channels from `US-029`; no new external provider is required for
  this slice.
- Alert payloads are secret-safe: no API keys, cookies, browser storage
  state, raw PII, or full connection strings ever enter an alert event.
- The story stops at the local-first baseline. External systems such as
  Prometheus, OTel collectors, Sentry, and Grafana remain behind an
  adapter seam for a later hardening story.

## Affected Users

- Owners and Admins who need an at-a-glance operational view of the live
  pilot and need alerts to wake them when something is wrong.
- Operators on call for the first pilot-live environment who need a single
  summary endpoint and durable alert history.
- Future agents and engineers extending observability, performance, or
  production-readiness work that needs stable alert and signal contracts.

## Affected Product Docs

- `docs/product/real-environment-cutover-and-live-operations.md` (US-040
  contract; this story consumes the readiness, heartbeat, and backup
  surfaces it introduced).
- `docs/product/audit-log-and-governance.md` (alert events are written
  through the same secret-safe audit boundary).
- `docs/product/notification-delivery-and-preferences.md` (alert delivery
  reuses the in-app inbox and email channels from `US-029`).
- `docs/product/source-registry-and-policy.md` (connector health aggregation
  builds on top of the policy and rate-limit metadata from `US-003`).
- `docs/product/observability-and-alerting.md` (new product doc that this
  story seeds as the living contract for the observability domain).

## Non-Goals

- Wiring a full external metrics pipeline (Prometheus, OTel exporters,
  Grafana dashboards, Sentry ingestion) into production.
- Distributed tracing, APM, or call-graph analysis across the modular
  monolith.
- SLO burn-rate alerts, multi-window multi-burn-rate evaluations, or
  anomaly detection.
- Auto-remediation or self-healing actions; alerts are advisory, not
  authoritative.
- Customer-facing status pages or external incident communication.
- Replacing the existing `LaunchGateReport` from `US-040`; this story
  consumes it, it does not redefine it.
