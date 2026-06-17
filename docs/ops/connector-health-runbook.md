# Connector Health Runbook

Operational entry for the `US-046` connector
health surface baseline. This runbook documents
what an operator does when a connector flips to
`degraded` or `unhealthy`, when a CAPTCHA rate
breaches the threshold, and when a user reports
a missing connector.

The runbook reuses the existing operator workflow
from the observability, alert, audit, and
notification runbooks. It is intentionally
narrow: the connector health surface is
read-only, owner/admin-scoped, and bounded by the
`EnvironmentMode` from `US-040`.

## What this runbook covers

- Connector health surface lifecycle:
  compute, summary, snapshot, and recent-errors
  rollup.
- Connector health status transitions:
  `healthy`, `degraded`, `unhealthy`, `unknown`.
- Connector health audit entry shape and the
  matching admin audit log filter from
  `US-026`.
- Connector health response to a reported
  missing connector.
- Connector health response to a CAPTCHA rate
  breach.

## What this runbook does NOT cover

- Distributed tracing of connector calls. The
  first slice ships the contract, not a UI.
- External health APIs (Datadog, Sentry
  Performance, a managed Prometheus service).
  The first slice reuses the `MetricsExporter`
  from `US-042` and the `AlertEvaluator` from
  `US-041`; a later story can wire an external
  health consumer behind the same contract.
- Auto-remediation or self-healing actions
  driven by a connector health breach. The
  health surface is advisory, not authoritative.
- Per-tenant thresholds. The first slice ships
  one fixed default set; per-tenant tuning is a
  follow-on story.
- Customer-facing status pages or external
  incident communication.
- Reading browser-session or browser-debug rows
  for the bounded computation. The first slice
  reads only the `discovery_jobs` and
  `audit_entries` rows; a future story can
  extend the computation to read those rows
  behind the same `ConnectorHealthComputer`
  seam.
- Per-connector CAPTCHA detection policy. The
  first slice reads the existing CAPTCHA
  detection events from the `audit_entries`
  rows; the per-connector policy remains a
  follow-on story.

## Connector health surface lifecycle

The `ConnectorHealthService` is the only place
that mutates `connector_health_snapshots` and
`connector_health_errors` and emits the
`connector.health.*` audit entries. The
operator panel and the verify script read the
snapshots through the same service.

1. `POST /admin/connectors/health/snapshots:compute`
   executes a bounded, confirmation-gated
   per-source computation. The computation reads
   the `discovery_jobs` and `audit_entries` rows
   for the source, derives the bounded metrics,
   persists a `connector_health_snapshots` row,
   and emits a
   `connector.health.snapshot.computed` audit
   entry.
2. `GET /admin/connectors/health/summary`
   returns the latest snapshot per source with
   the `ConnectorHealthStatus` badge, success
   rate, last run, and CAPTCHA rate. The summary
   endpoint emits a
   `connector.health.summary.requested` audit
   entry.
3. `GET /admin/connectors/health/snapshots?source_id=&status=&limit=&offset=`
   returns paginated snapshot history with
   sanitized payloads. The snapshot history
   endpoint emits a
   `connector.health.summary.requested` audit
   entry.
4. `GET /admin/connectors/{source_id}/health/errors?limit=`
   returns the recent error rollup for the
   source detail surface. The recent-errors
   endpoint emits a
   `connector.health.errors.requested` audit
   entry.

## Connector health status transitions

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

A status transition is the bounded computation
writing a new `connector_health_snapshots` row
with a different `status` value than the
previous snapshot for the same source. The
operator panel reads the latest snapshot per
source and surfaces the transition to the
operator.

## Responding to a `degraded` connector

When a connector flips to `degraded`, the
operator should:

1. Identify the affected source through the
   in-app inbox from `US-029` or the admin
   audit log filter from `US-026` (filter by
   `connector.health.snapshot.computed` and
   the source id).
2. Open the connector health panel and
   identify the affected source through the
   `ConnectorHealthStatus` badge.
3. Read the recent-errors rollup for the source
   through
   `GET /admin/connectors/{source_id}/health/errors?limit=`.
   The rollup is bounded to the most recent
   N errors per source.
4. Cross-check the affected source against the
   existing source policy from `US-003` and
   the existing rate-limit metadata. The
   source policy may be the root cause of the
   degradation.
5. If the root cause is a transient external
   failure, run a new bounded computation
   through
   `POST /admin/connectors/health/snapshots:compute`
   and watch the status transition back to
   `healthy`. If the root cause is a policy
   mismatch, update the source policy and
   re-run the computation.

## Responding to an `unhealthy` connector

When a connector flips to `unhealthy`, the
operator should:

1. Follow the `degraded` response steps first.
2. The `unhealthy` threshold (success rate
   `< 0.7` or CAPTCHA rate `> 0.2`) is the
   bounded surface's "wake a human" signal.
   The operator should treat the threshold as
   a launch-gate blocker for the connector.
3. Disable the connector through the source
   policy from `US-003` if the operator
   cannot resolve the root cause within the
   bounded window. The disabled connector
   returns `unknown` for subsequent
   computations.
4. Open a security incident if the root cause
   is a CAPTCHA bypass attempt, a bot
   challenge storm, or a credentials leak. The
   audit entries from `US-026` and the
   connector health surface together provide
   the bounded signal trail.

## Responding to a CAPTCHA rate breach

When a connector's CAPTCHA rate breaches the
`degraded_max_captcha_rate` (default `0.2`),
the operator should:

1. Identify the affected source through the
   in-app inbox from `US-029` or the admin
   audit log filter from `US-026`.
2. Read the recent-errors rollup for the
   source. The rollup is bounded to the most
   recent N errors per source.
3. Cross-check the affected source against the
   existing `CloakBrowser` policy from
   `US-025`. The CAPTCHA detection events
   may indicate that the source is sending
   challenges that the current policy cannot
   handle.
4. If the root cause is a transient CAPTCHA
   challenge storm, run a new bounded
   computation through
   `POST /admin/connectors/health/snapshots:compute`
   and watch the CAPTCHA rate fall back below
   the threshold.
5. If the root cause is a permanent policy
   mismatch, disable the connector through
   the source policy from `US-003` and update
   the `CloakBrowser` policy from `US-025`.

## Responding to a missing connector report

When a user reports a missing connector, the
operator should:

1. Identify the affected source through the
   user report.
2. List the source through the admin
   connectors surface from `US-003` and
   confirm the source is registered.
3. Run a bounded computation through
   `POST /admin/connectors/health/snapshots:compute`
   and read the latest snapshot. A missing
   connector returns `unknown` for the
   status.
4. Cross-check the affected source against the
   existing rate-limit metadata and the
   existing audit entries from `US-026`. The
   `unknown` status is the bounded surface's
   "no signals in the window" indicator; the
   operator should treat the indicator as a
   "the source has not run in the window"
   signal, not as a "the source is missing"
   signal.
5. If the source is registered but the bounded
   computation returns `unknown`, the
   operator should check the source policy
   from `US-003` and the source rate-limit
   metadata for a configuration that would
   prevent the source from running in the
   window.

## Connector health alert rules

The `US-041` alert evaluator does not currently
ship a connector health-specific rule. Operators
who want to be notified when a connector flips
to `unhealthy` or when a CAPTCHA rate breaches
the threshold can build a custom rule through
the existing alert rule surface from `US-041`
(for example,
`connector.health.snapshot.status` over a
5-minute window with `status == unhealthy`).
The custom rule must respect the existing
`SanitizeAlertPayload` contract and the
existing audit retention guarantee from
`NFR-SEC-008`.

## Connector health health probe

The new endpoints are covered by the health
probe contract from `US-040`: a missing or
failing `GET /admin/connectors/health/summary`
must not fail `GET /health/ready`, only surface
as a degraded warning. The health probe is
intentionally shallow; the connector health
surface is read-only, owner/admin-scoped, and
bounded by the `EnvironmentMode` from `US-040`.

## References

- `docs/product/connector-health-surface.md`
  (living product contract for the connector
  health domain).
- `docs/decisions/0024-connector-health-surface-baseline.md`
  (durable decision record for the connector
  health baseline).
- `docs/stories/epics/E05-hardening/US-046-connector-health-surface-baseline/`
  (this story packet).
- `docs/ops/observability-runbook.md`
  (operator workflow for the alert evaluator).
- `docs/ops/audit-runbook.md` (operator
  workflow for the admin audit log filter).
- `docs/product/audit-log-and-governance.md`
  (`US-026` contract).
- `docs/product/observability-and-alerting.md`
  (`US-041` contract).
- `docs/product/external-metrics-and-tracing.md`
  (`US-042` contract).
- `docs/product/source-registry-and-policy.md`
  (`US-003` contract).
- `docs/product/real-environment-cutover-and-live-operations.md`
  (`US-040` contract).
