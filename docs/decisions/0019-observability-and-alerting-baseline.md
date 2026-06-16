# 0019 Observability And Alerting Baseline

Date: 2026-06-16

## Status

Accepted

## Context

`US-001` through `US-040` delivered a broad MVP and a first governed
real-environment pilot cutover. `US-040` introduced `EnvironmentMode`
(`test_like`, `pilot_live`, `paused`), `LaunchGateReport`,
`LiveIntegrationToggle`, `BackupSnapshot`, and a runtime-readiness
surface. The design notes for `US-040` explicitly call out that
"runtime metrics should expose API health, queue depth, job outcomes,
connector health, browser crashes, CAPTCHA detection, AI latency, and
backup freshness", but no durable observability or alerting slice has
been defined yet.

`SPEC.md` (sections 5.14, 6.3, 10.1, 10.2, 10.3) requires:

- A connector health surface (`FR-ADM-002`) with success rate, recent
  errors, latency, item counts, CAPTCHA rate, and last run.
- Performance thresholds (`NFR-PERF-001..005`) for API reads, event
  list pagination, discovery job progress, concurrent users, and
  browser session budgets.
- A backup reliability target (`NFR-REL-005`) of RPO 24h / RTO 8h that
  implies a daily backup and an alert when the backup is missing or
  stale.
- An audit retention guarantee (`NFR-SEC-008`) of at least 90 days with
  application-level tamper resistance.
- Operator visibility that today exists only as scattered tables and
  the `LaunchGateReport`.

The product still has no bounded observability or alerting slice, so
operators have to read raw tables or run ad-hoc scripts to answer
"is anything on fire right now?". The next story after the pilot
cutover is therefore an observability and alerting baseline that turns
existing durable signals into alerts and a single operator view.

## Decision

`US-041` introduces the first operational observability and alerting
baseline for LiveLead.

### Domain objects

- **`AlertRule`** — durable rule with a closed set of metrics
  (`backup.age_hours`, `worker.heartbeat.age_seconds`,
  `connector.failure_rate`, `discovery.needs_user_action_rate`,
  `browser.crash_loop`, `audit.retention_breach_risk`), a closed set of
  operators (`gt`, `gte`, `lt`, `lte`, `eq`), a numeric threshold, a
  rolling window in seconds, a severity, a delivery channel subset of
  `in_app` and `email`, an enabled flag, and an `is_system` flag.
- **`AlertEvent`** — durable record of a single firing, with a
  sanitized payload, a `deduplication_key`, a status (`firing`,
  `acknowledged`, `resolved`, `suppressed`), and audit linkage.
- **`SanitizeAlertPayload`** — shared secret-safe helper. Built on top
  of the same filter that the audit log uses in `US-026`. Rejects or
  redacts API keys, cookies, raw PII, browser storage state, and full
  connection strings.

### Evaluator and delivery

- **`AlertEvaluator`** — runs from a periodic worker tick and from
  targeted product paths (job completion, backup recording, worker
  heartbeat, browser session lifecycle). Evaluator is read-only with
  respect to product state. It persists `AlertEvent` rows and
  dispatches through the in-app inbox and email channels from
  `US-029`. It does not pause jobs, disable connectors, flip live
  toggles, or roll back the environment.
- **`cooldown_seconds`** — minimum seconds between firings of the same
  rule. Implemented through a `deduplication_key` hash of
  `rule_id` + window bucket. Suppression transitions the existing
  open event to `suppressed` rather than creating a duplicate row.
- **`DeliverAlert`** — reuses the existing notification dispatcher
  from `US-029`. No new external provider is added in this slice.

### Admin surface

- New owner/admin-only REST surface:
  - `GET /admin/observability/summary`
  - `GET /admin/alert-rules`
  - `POST /admin/alert-rules`
  - `PATCH /admin/alert-rules/{id}`
  - `DELETE /admin/alert-rules/{id}`
  - `GET /admin/alert-events?status=&severity=&rule_id=&limit=`
  - `POST /admin/alert-events/{id}/acknowledge`
- Acknowledge and resolve actions emit `alert.acknowledged` and
  `alert.resolved` audit entries using the same secret-safe payload
  contract as `US-026`.
- The summary endpoint is itself covered by the health probe contract:
  a missing or failing summary must not fail `GET /health/ready`, only
  surface as a degraded warning.

### Seed rule set

The migration inserts the following seed rules with `is_system = true`
and the documented thresholds in
`docs/product/observability-and-alerting.md`:

| Rule | Default Threshold | Default Severity |
| --- | --- | --- |
| `backup.stale` | `> 26` hours (RPO 24h + grace) | `critical` |
| `worker.heartbeat.missing` | `> 120` seconds | `warning` |
| `connector.failure_spike` | `> 0.5` over `1800`s | `warning` |
| `discovery.needs_user_action_storm` | `> 0.3` over `3600`s | `warning` |
| `browser.crash_loop` | `>= 3` crashes in `600`s for the same profile | `critical` |
| `audit.retention_breach_risk` | oldest audit row `> 90` days | `warning` |

Owners and admins can adjust threshold, window, severity, and channels;
they cannot delete or rename a system rule, and they cannot change the
`metric` of a system rule.

### Seam for a later external metrics pipeline

- A stable interface sits between the evaluator and the
  counter/log surface so a later hardening story can wire a
  Prometheus exporter, an OpenTelemetry collector, Sentry ingestion, or
  a Grafana dashboard without changing the rule, event, or summary
  contracts. This slice does not commit to a particular provider.

## Alternatives Considered

1. **Skip the local-first baseline and wire Prometheus/OTel/Sentry
   directly.** This would have committed the MVP to a specific
   external stack before any operator had used the local alerts. It
   would also have made the seed rules depend on a metrics pipeline
   that does not exist yet. The local-first baseline keeps the
   observability contract stable and lets a later story pick a vendor
   without re-opening the rule and event contracts.
2. **Use a single in-process counter table without a rule model.**
   This would have hard-coded every signal into application code. The
   rule model makes it possible for an owner/admin to adjust
   thresholds and disable noisy rules at runtime, and it gives the
   audit log a stable, reviewable contract for what fired and why.
3. **Push alerts through a new external channel (Slack, PagerDuty,
   Opsgenie) instead of the existing in-app inbox and email.** This
   would have added a new provider before the local-first baseline
   was proven, and it would have created a parallel channel that
   could drift away from the existing notification preferences from
   `US-029`. Reusing the existing channels keeps the alert delivery
   path aligned with the rest of the product.

## Consequences

Positive:

- The first pilot-live environment gets an operator-visible signal
  for stale backups, missing heartbeats, connector failure spikes,
  discovery storms, browser crash loops, and audit retention risk.
- A reusable secret-safe payload helper is established before any
  future alert consumer (Prometheus, OTel, Sentry) is wired, so the
  next observability story inherits the same redaction contract.
- Owners and admins can adjust thresholds, windows, severities, and
  channels at runtime without a code change, which keeps the alert
  contract reviewable in product code while still being tunable.
- The `LaunchGateReport` from `US-040` and the new
  `OperatorSummary` together cover both readiness and ongoing
  operations without duplicating state.

Tradeoffs:

- The evaluator must read from multiple existing tables and counters
  to compute its metrics, which means a missing or slow signal
  surfaces as a noisy alert until a follow-on story adds the missing
  counter.
- The seed rules are fixed in this slice. Per-tenant tuning of
  thresholds is a follow-on story, not a contract change.
- The closed set of metrics, operators, and channels is intentionally
  small. New metrics will require a new rule kind and a migration; the
  trade-off is reviewability over flexibility.

## Follow-Up

- Add per-tenant tuning of seed rule thresholds through a
  configuration surface, gated on the same owner/admin role as the
  rule management endpoints.
- Wire a Prometheus exporter and an OpenTelemetry collector behind
  the existing sanitization helper so the same rules and events can
  feed a Grafana dashboard without re-opening the contracts.
- Add SLO burn-rate alerts and multi-window burn-rate evaluation
  once the MVP performance baselines are stable.
- Add auto-remediation or self-healing actions only after an explicit
  product decision; this slice commits the evaluator to read-only
  semantics.
- Evaluate the need for a customer-facing status page once the
  internal observability surface has been used in production for at
  least one operational cycle.
