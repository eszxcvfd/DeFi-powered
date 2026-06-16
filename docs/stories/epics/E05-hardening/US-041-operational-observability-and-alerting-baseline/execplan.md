# Exec Plan

## Goal

Add the first bounded operational observability and alerting slice to
LiveLead: durable alert rules, evaluation tick, secret-safe alert events,
an operator summary endpoint, and a small but defensible set of starter
alerts that cover backup freshness, worker heartbeat, connector failure
spikes, discovery `NEEDS_USER_ACTION` storms, browser-session crash loops,
and audit retention risk.

## Scope

In scope:

- New durable `alert_rules` and `alert_events` tables with the minimum
  fields required for evaluation, deduplication, correlation, and audit
  linkage. Migration is forward-only with a documented rollback note in
  the migration header.
- A new `AlertEvaluator` service that runs from a periodic worker tick and
  from key product paths (job completion, backup recording, worker
  heartbeat, browser session lifecycle) using the existing Dramatiq
  broker.
- Reuse of the in-app inbox and (when enabled) email channels from
  `US-029` for alert delivery. No new external notification provider is
  introduced in this slice.
- New bounded REST surface for owners/admins:
  - `GET /admin/observability/summary`
  - `GET /admin/alert-rules`
  - `POST /admin/alert-rules`
  - `PATCH /admin/alert-rules/{id}`
  - `DELETE /admin/alert-rules/{id}`
  - `GET /admin/alert-events?status=&severity=&rule_id=`
  - `POST /admin/alert-events/{id}/acknowledge`
- Seed alert rules for: stale backup, missing worker heartbeat, connector
  failure spike (rolling window), discovery `NEEDS_USER_ACTION` rate,
  browser-session crash loop, audit retention breach risk.
- A small settings/operator panel that exposes the summary and the
  recent alert list to owner/admin users.
- Secret-safe payload sanitization helpers shared with the audit log so
  alert events can never carry API keys, cookies, browser storage state,
  raw PII, or full connection strings.
- Durable decision record for the new observability domain.

Out of scope:

- External metrics pipeline (Prometheus exporters, OTel collectors,
  Grafana dashboards, Sentry ingestion).
- Distributed tracing, APM, and cross-service call graph analysis.
- SLO burn-rate alerts, multi-window burn-rate evaluation, and anomaly
  detection.
- Auto-remediation, self-healing, or any action that mutates product
  state from an alert evaluation.
- Customer-facing status pages or external incident communication.
- Replacing the existing `LaunchGateReport` from `US-040`.
- A migration of historical `audit_logs` rows into the alert pipeline.
- Per-tenant customization of alert thresholds for the seed rules. This
  slice seeds sensible defaults and exposes rule management; per-tenant
  tuning is a follow-on story.

## Risk Classification

Risk flags:

- Auth — admin-only summary and rule management endpoints.
- Authorization — owner/admin role gate for all new endpoints and the
  operator panel.
- Data model — new `alert_rules` and `alert_events` tables, new indexes,
  forward-only migration.
- Audit/security — alert events must never carry secrets, raw PII, or
  sensitive browser state; this is enforced by a sanitization helper that
  the audit log already uses.
- External systems — alert delivery reuses the in-app inbox and email
  channels from `US-029`; no new external provider is added in this slice,
  but the surface is documented so a later Prometheus/OTel/Sentry adapter
  can be added behind a stable interface.
- Public contracts — new REST endpoints, new error codes, new operator
  panel widget; consumed by the same admin surfaces that already speak to
  the runtime-readiness and audit-log endpoints from `US-040` and
  `US-026`.
- Existing behavior — `US-040` runtime-readiness contract and `US-029`
  notification contract are adjacent; this story consumes both, it does
  not redefine either.
- Weak proof — observability is exactly the area where "we added tests"
  is not the same as "we can prove we alert on the right things"; this
  story adds a dedicated verification layer that simulates each seed
  signal and asserts the expected `AlertEvent` row and the sanitized
  payload.
- Multi-domain — touches audit (`US-026`), notifications (`US-029`),
  runtime readiness (`US-040`), source policy (`US-003`), and connector
  health (`FR-ADM-002`).

Hard gates:

- Any alert path that can leak a secret, cookie, browser storage state,
  raw PII, or full connection string.
- Any alert that mutates product state as a side effect of evaluation.
- Any change that weakens the existing `LaunchGateReport` from `US-040`
  or the audit retention guarantee from `NFR-SEC-008`.
- Any change that bypasses the in-app inbox and email channel ownership
  defined in `US-029`.

## Work Phases

1. Discovery — read `SPEC.md` NFR-PERF, NFR-REL, NFR-SEC sections, the
   `US-040` story packet, the `US-026` audit log contract, the `US-029`
   notification contract, the `US-003` source policy contract, and the
   `LaunchGateReport` interface. Confirm which signals already exist
   durably and which need a thin counter.
2. Design — define `AlertRule`, `AlertEvent`, `AlertEvaluator`,
   `DeliverAlert`, and `BuildOperatorSummary` services. Lock the payload
   sanitization contract and the rule evaluation grammar to a small,
   reviewable set of operators.
3. Validation planning — design a per-rule simulation test harness and a
   `/admin/observability/summary` snapshot test so a future regression in
   the seed rules or the sanitizer fails fast in CI.
4. Implementation — add the migration, the domain models, the
   evaluation tick, the admin endpoints, the operator panel widget, and
   the sanitization helper. Reuse the existing notification dispatcher
   from `US-029`; do not introduce a parallel channel.
5. Verification — run unit, integration, E2E, security, operational, and
   platform checks defined in `validation.md`. Simulate each seed signal
   and assert that the right `AlertEvent` row, severity, channel, and
   sanitized payload are produced.
6. Harness update — add the new product doc, the decision record, the
   durable story status, and a final trace. Capture any friction in the
   `harness_friction` field.

## Stop Conditions

Pause for human confirmation if:

- The story starts requiring external metrics pipeline integration
  (Prometheus, OTel, Sentry, Grafana) to meet the seed rule acceptance
  criteria. This slice is local-first by design.
- Product direction becomes ambiguous between "local-first dashboard and
  alerts" and "ship a full external observability stack this cycle".
- Validation would need to weaken payload sanitization, the audit
  retention guarantee, or the existing `LaunchGateReport` to fit
  schedule.
- A seed rule needs a threshold that cannot be justified from the
  existing durable signals (for example, a metric we do not actually
  record). The rule must be deferred or the signal must be added in the
  same story with explicit acceptance criteria.
- A later story wants to subscribe an external alerting consumer (Slack,
  PagerDuty, Opsgenie) before this slice is implemented; in that case,
  the integration must wait until the local-first baseline is in place.
