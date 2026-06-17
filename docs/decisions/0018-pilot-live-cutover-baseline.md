# 0018 Pilot Live Cutover Baseline

Date: 2026-06-16

## Status

Accepted

## Context

`US-001` through `US-039` delivered a broad MVP across discovery, events,
scoring, engagement, lead pipeline, reporting, browser operations, identity,
notifications, query expansion, copilot, feedback signals, and feedback-driven
scoring suggestions. The product still behaves primarily as a test-only
system: it assumes local `.env`, dev-friendly defaults, dev-header trust, mock
connectors, and verify-script proof. `SPEC.md` (sections 2.4, 3.2, 3.3, 10,
11, 14, 15) and the `US-040` story packet require a first governed real
operator environment for the current modular-monolith stack without claiming
full enterprise production maturity.

`US-040` must:

- Move the system from "works in test/local proof" to "can be operated in a
  real environment" for the first pilot.
- Keep authentication, authorization, audit, backup, and rollback under
  control.
- Gate live connectors, AI providers, notifications, and risky external
  actions behind explicit enablement controls.
- Provide the minimum operator-facing runbook and runtime status needed to go
  live safely and pause quickly if something goes wrong.
- Stop at the pilot-live boundary (single-host or small footprint) and avoid
  full HA, multi-region, blue/green, or Kubernetes migration.

## Decision

`US-040` introduces the first pilot-live cutover slice for LiveLead:

### Environment and runtime mode

- **`EnvironmentMode`**: `test_like` (default), `pilot_live`, `paused`. The
  active mode is read from the `LIVELEAD_ENVIRONMENT_MODE` setting and may be
  promoted or demoted at runtime by the cutover API.
- **Mode rules**:
  - `pilot_live` cannot be entered while `auth_allow_dev_headers` is true.
  - `paused` disables live integration toggles but preserves read-only
    visibility and audit history.
  - `test_like` keeps the existing test-friendly defaults and dev headers
    allowed.

### Launch gate and live readiness

- **`LaunchGateCheck` / `LaunchGateReport`**: structured per-check status
  with `blocking` and `warning` severity, reason, and a deterministic
  classifier.
- **Required checks** for `pilot_live`:
  - Auth hardening: `auth_allow_dev_headers` must be off.
  - Secrets: `secret_master_key` is not the documented dev placeholder.
  - Cookie: `auth_cookie_secure` is on.
  - Database: SQLite path writable, `SELECT 1` succeeds.
  - Redis: broker reachable.
  - Worker heartbeat: most recent row in `worker_heartbeats` is within
    `launch_gate_worker_heartbeat_max_seconds`.
  - Backup: at least one `verified` or `recorded` snapshot exists in
    `backup_snapshots` and the most recent is no older than
    `launch_gate_backup_max_age_hours`.
- `GET /health/live` returns `ok` whenever the API process is up.
- `GET /health/ready` returns `ok` only when blocking checks pass; it never
  reveals secret material or full connection strings.
- `GET /admin/runtime-readiness` (owner/admin) returns the full
  `LaunchGateReport` plus per-toggle state, last backup summary, worker
  heartbeat summary, and the current `EnvironmentMode`.

### Live integration toggles

- **`LiveIntegrationToggle`**: explicit enablement record for
  `discovery`, `ai_copilot`, `notifications`, `browser_external` with states
  `disabled`, `enabled`. A toggle is only `enabled` when:
  - The actor is `owner` or `admin`.
  - The actor supplies a non-empty `approval_note` (recorded in audit).
  - The current `EnvironmentMode` is `pilot_live` and the launch gate passes.
- All toggle transitions emit an `environment.toggle` audit entry
  (target_type `live_integration_toggle`) with reason, previous state, and
  approval note. Secret material is never persisted on the toggle row.

### Backup metadata

- **`BackupSnapshot`**: records `backup_id`, `created_at`, `database_path`,
  `database_size_bytes`, `verification_status`
  (`recorded`, `verified_restore`, `failed_restore`), `notes`, and `recorded_by`.
- `POST /admin/backup-snapshots:record` accepts a snapshot from an operator
  or a backup script. The `verified_restore` transition can only be set when
  an admin/owner explicitly confirms restore rehearsal, and the transition is
  audited.
- `GET /admin/backup-snapshots` lists the most recent snapshots and
  classifies them as `fresh`, `stale`, or `unknown` based on
  `launch_gate_backup_max_age_hours`.

### Cutover events

- **`CutoverEvent`**: records every `enter_pilot_live`, `pause`, and
  `rollback` with reason, actor, previous mode, target mode, gate snapshot,
  and notes. These are exposed via `GET /admin/cutover/events`.
- `POST /admin/cutover/pause` is always allowed for owner/admin.
- `POST /admin/cutover/enter-pilot-live` requires the launch gate to pass
  and a non-empty reason. It also requires at least one recorded backup.
- `POST /admin/cutover/rollback` records the rollback, disables all live
  toggles, and returns the environment to `test_like` (default) or `paused`.

### Audit vocabulary

- New `AuditAction` values:
  `ENVIRONMENT_MODE_CHANGED`, `ENVIRONMENT_PAUSED`, `ENVIRONMENT_ROLLED_BACK`,
  `ENVIRONMENT_TOGGLE_CHANGED`, `BACKUP_SNAPSHOT_RECORDED`,
  `BACKUP_SNAPSHOT_VERIFIED`, `BACKUP_SNAPSHOT_FAILED`.
- New `AuditTargetType` values: `ENVIRONMENT`, `LIVE_INTEGRATION_TOGGLE`,
  `BACKUP_SNAPSHOT`.

### Worker heartbeat

- The Dramatiq worker writes a `worker_heartbeats` row on each completed
  task (or via a small periodic actor). The launch gate reads the latest row
  and fails closed if it is missing or older than the configured threshold.

### Boundaries and front-end impact

- Domain rules, evaluation, and persistence live under
  `src/livelead/domain/runtime/`, `src/livelead/application/runtime/`, and
  `src/livelead/infrastructure/db/models.py` + repositories. REST surfaces
  live in `src/livelead/interfaces/rest/`.
- The frontend is not required to gain a full live-readiness panel in this
  slice. The existing admin connector / audit / browser-profile surfaces
  remain the live control points; this slice adds a documented
  `GET /admin/runtime-readiness` API and an operator runbook so the operator
  UI can be added later without changing the underlying contract.

### Out of scope

- Multi-region deployment, blue/green routing, zero-downtime orchestration.
- Kubernetes migration or distributed microservice control plane.
- Automatic horizontal autoscaling.
- Global adaptive operations or cost optimization.
- Broad performance tuning beyond the first live guardrails.

## Consequences

- The first pilot-live cutover is single-host or small-footprint. Operators
  follow the documented runbook (`docs/ops/pilot-live-cutover-runbook.md`)
  with checklist evidence; the runbook and verify script together satisfy
  the validation matrix's "operational" and "platform" rows.
- The launch gate is fail-closed: a missing backup, stale worker heartbeat,
  or development auth headers block `pilot_live` entry.
- Audit history is the source of truth for "who turned what on, when, and
  why" — secret material is never persisted, logged, or returned through
  the readiness API.
- Future HA/multi-region stories can extend `EnvironmentMode` and the
  `LaunchGate` checks without breaking this contract.

## Proof

- `./scripts/verify-us-040.sh`
- `tests/unit/test_runtime_environment_profile.py`
- `tests/unit/test_runtime_launch_gate.py`
- `tests/unit/test_runtime_live_toggles.py`
- `tests/unit/test_runtime_backup.py`
- `tests/unit/test_runtime_cutover.py`
- `tests/integration/test_runtime_readiness_api.py`
- `tests/integration/test_live_toggles_api.py`
- `tests/integration/test_backup_api.py`
- `tests/integration/test_cutover_api.py`
- `tests/integration/test_health_ready_api.py`
- `docs/ops/pilot-live-cutover-runbook.md`
- `docs/ops/pilot-live-rollback-runbook.md`
- `docs/ops/pilot-live-pause-runbook.md`
