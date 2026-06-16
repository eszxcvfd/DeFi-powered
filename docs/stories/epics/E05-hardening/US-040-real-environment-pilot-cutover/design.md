# Design

## Domain Model

The first real-environment cutover slice should formalize the operational
objects that turn a tested MVP into a live pilot system:

- `EnvironmentProfile`: runtime mode definition such as `test_like`,
  `pilot_live`, or `paused`, including which trust paths and integrations are
  enabled.
- `LaunchGate`: explicit readiness requirement for auth hardening, connector
  safety, backup freshness, worker health, and critical feature flags before the
  environment can be treated as live.
- `LiveIntegrationToggle`: controlled enablement record for live connectors, AI
  providers, notifications, browser external actions, and other risky runtime
  capabilities.
- `BackupSnapshot`: metadata record for backup execution, retention, restore
  eligibility, and last verified restore outcome.
- `CutoverRunbookStep`: structured go-live, pause, rollback, and post-cutover
  verification checkpoint.

Business rules:

- `pilot_live` cannot be entered while development auth headers remain trusted.
- Live integration toggles are off by default and can be enabled only when the
  corresponding policy, approval, and runtime dependencies are present.
- Readiness must fail closed when critical dependencies such as Redis, writable
  SQLite storage, or required secrets are missing.
- Rollback must preserve enough metadata to identify the last good config,
  backup point, and live-toggle state.
- `paused` mode must allow operators to halt new risky activity quickly without
  erasing data or breaking safe read-only visibility.

## Application Flow

- `BuildEnvironmentProfile` loads runtime settings, feature flags, and live
  integration state into one environment-readiness view.
- `ValidateLaunchGate` checks auth mode, TLS expectations, Redis reachability,
  SQLite path health, backup age, worker heartbeat, browser-worker status,
  object or artifact storage path, and critical connector policy readiness.
- `EnterPilotLiveMode` records the cutover decision, enables approved live
  integrations, and exposes the environment as live-ready only after readiness
  and smoke checks pass.
- `PauseLiveOperations` disables risky live toggles such as new discovery runs,
  notifications, or external browser actions while preserving operator review
  access.
- `ExecuteRollbackPlan` records the rollback reason, freezes risky flows,
  restores the last approved config or backup point when needed, and returns the
  environment to `test_like` or `paused`.

## Interface Contract

This slice should add bounded runtime and ops surfaces rather than treating
deployment as an undocumented shell-only activity:

- `GET /health/live` for process liveness.
- `GET /health/ready` for dependency readiness and environment profile checks.
- `GET /admin/runtime-readiness` for authorized operators to inspect launch
  blockers, backup status, worker heartbeat, and live-toggle state.
- Optional admin actions for `pilot_live` enter, `paused` enter, or rollback may
  be added only if they remain approval-gated and auditable; otherwise the first
  cutover may use documented runbook steps plus read-only API visibility.

Expected payload concerns:

- Readiness output should clearly distinguish blocking vs warning conditions.
- Runtime status must not expose raw secrets, full connection strings, or
  sensitive cookie/storage-state material.
- Responses should make it obvious whether risky live capabilities are enabled.

## Data Model

- Add durable storage only where needed for environment-profile state,
  backup-snapshot metadata, launch history, and rollback decisions.
- Reuse existing audit mechanisms to record live-mode entry, pause, rollback,
  and critical toggle changes.
- Preserve linkage to source approvals, feature flags, and backup state without
  duplicating raw secret values into new tables.
- Avoid introducing a full deployment-control-plane schema in this baseline.

## UI / Platform Impact

- Settings should gain an owner/admin runtime-readiness panel with launch
  blockers, live-toggle state, and backup freshness.
- Existing admin surfaces should reflect live vs paused connector state clearly.
- Frontend should surface a degraded or paused banner when the environment has
  intentionally frozen risky operations.
- Platform work should remain aligned with the accepted single-host MVP
  packaging direction rather than introducing a second deployment stack.

## Observability

- Every request, job, worker heartbeat, connector run, backup event, and live
  toggle change should keep correlation ids and structured logs.
- Runtime metrics should expose API health, queue depth, job outcomes, connector
  health, browser crashes, CAPTCHA detection, AI latency, and backup freshness.
- Readiness checks should be explainable enough that operators know exactly why
  the environment is blocked from live mode.
- Audit entries should exist for pilot-live entry, pause, rollback, and critical
  enablement changes.

## Alternatives Considered

1. Keep proving features with tests only and delay real-environment work until
   later. Rejected because the business need is to operate now, not only to
   verify locally.
2. Treat the first live cutover as a full-scale production program. Rejected
   because urgency and current architecture favor a narrower single-host pilot
   contract first.
3. Let deployment remain entirely outside the product and harness docs.
   Rejected because the repo needs a governed source of truth for live mode,
   readiness, and rollback if operators are going to trust the system.
