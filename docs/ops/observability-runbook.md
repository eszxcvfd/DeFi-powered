# Observability Operator Runbook (US-041)

This runbook is the operator-facing companion to the
`/admin/observability` page and the `US-041` story packet. It is
read-only documentation: nothing here mutates product state.

## What this surface is

The observability and alerting slice ships:

- Six seed alert rules in `alert_rules` (system rules, owner-tunable).
- A `AlertEvaluator` worker tick that reads the durable signals,
  applies the closed rule grammar, and produces `alert_events`
  rows.
- An in-app inbox and email delivery path that reuses the
  `NotificationService` (US-029) so the alert delivery channel
  is shared with the rest of the product.
- A `GET /admin/observability/summary` endpoint that combines
  the `LaunchGateReport` (US-040), the most recent alert
  events, and the rule counts.
- A `docs/ops/observability-runbook.md` entry that explains what
  an operator does when a `critical` alert fires.

The evaluator is read-only with respect to product state. It
never pauses jobs, disables connectors, flips live toggles, or
rolls back the environment. Acting on an alert is the
operator's job; the runbook documents the read paths.

## Where to look

| Surface | Path | Owner |
| --- | --- | --- |
| Operator panel | `frontend/src/pages/AdminObservability.tsx` | frontend |
| REST surface | `src/livelead/interfaces/rest/observability.py` | interfaces |
| Service | `src/livelead/application/observability/alert_service.py` | application |
| Evaluator | `src/livelead/application/observability/evaluator.py` | application |
| Worker actor | `apps/worker/alert_tasks.py` | apps |
| Migration | `alembic/versions/20260616_0031_alerting.py` | alembic |
| Seed rule doc | `docs/product/observability-and-alerting.md` | docs |

## Seed rules at a glance

| Name | Default threshold | Severity | Channels |
| --- | --- | --- | --- |
| `backup.stale` | `> 26 h` (RPO 24 h + grace) | critical | in_app, email |
| `worker.heartbeat.missing` | `> 120 s` | warning | in_app |
| `connector.failure_spike` | `> 0.5` over `1800 s` | warning | in_app |
| `discovery.needs_user_action_storm` | `> 0.3` over `3600 s` | warning | in_app |
| `browser.crash_loop` | `>= 3` crashes in `600 s` per profile | critical | in_app, email |
| `audit.retention_breach_risk` | `> 90 d` since oldest audit row | warning | in_app |

The full grammar is documented in
`docs/product/observability-and-alerting.md`.

## What to do when a `critical` alert fires

1. Open `/admin/observability` and read the recent events table.
2. For each firing event, look at the `metric` and `payload.value`
   fields (sanitized; secrets are stripped).
3. If the metric is `backup.age_hours`, check the latest
   `backup_snapshots` row in the API and the backup scheduler
   per `docs/ops/pilot-live-cutover-runbook.md`.
4. If the metric is `browser.crash_loop`, open
   `/admin/browser-profiles` to see which profile generated
   the crashes and decide whether to lock or delete it.
5. Acknowledge the event from the panel. Acknowledgement does
   not resolve the event; the evaluator transitions `firing`
   to `resolved` only when the signal clears.
6. If the signal does not clear after the documented
   mitigation, escalate per the runbook associated with the
   failing surface.

## Tuning a rule

Owners and admins can adjust threshold, window, severity,
cooldown, channels, and the `enabled` flag from
`/admin/observability`. The grammar is closed:

- `metric ∈ {backup.age_hours, worker.heartbeat.age_seconds, connector.failure_rate, discovery.needs_user_action_rate, browser.crash_loop, audit.retention_breach_risk}`
- `operator ∈ {gt, gte, lt, lte, eq}`
- `severity ∈ {info, warning, critical}`
- `channels ⊆ {in_app, email}`

System rules cannot be deleted or renamed; their `metric`
cannot be changed. Other fields are owner-tunable.

## Disabling noisy rules

Toggle `enabled = false` from the panel or the API. The
evaluator skips disabled rules; the row stays visible so the
operator remembers the rule exists.

## Pausing the evaluator

The evaluator is a worker actor (`apps/worker/alert_tasks.py`).
Pause it by stopping the worker process. No code path in the
evaluator mutates product state, so pausing it does not leave
the system in an inconsistent state.

## Restore rehearsal

`backup.stale` and `audit.retention_breach_risk` both depend on
durability paths. The backup surface ships with a restore
rehearsal contract from US-040; the audit log retention
contract is documented in `docs/product/audit-log-and-governance.md`.
Operators verify both contracts every release.

## What this runbook does NOT cover

- External metrics pipeline (Prometheus, OTel, Sentry, Grafana)
  — out of scope for US-041; a later hardening story adds it
  behind the existing `SignalProviderFactory` seam.
- Auto-remediation or self-healing actions — the evaluator is
  read-only by design.
- Per-tenant tuning of seed rule thresholds — the seed
  thresholds are the same for every workspace; per-tenant tuning
  is a follow-on story.
