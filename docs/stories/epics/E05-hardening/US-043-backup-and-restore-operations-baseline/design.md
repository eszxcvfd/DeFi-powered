# Design

## Domain Model

The first backup and restore operations baseline
formalizes the durable objects and bounded services
that turn the `BackupSnapshot` metadata from `US-040`
into a usable contract.

### `BackupRestoreRun`

A single record of a restore attempt. The row carries
enough information to prove that a backup can be
restored within the RTO target from `NFR-REL-005`.

- `id`
- `organization_id`
- `backup_id` (FK to `backup_snapshots.id`)
- `started_at`
- `completed_at` (nullable until the run finishes)
- `status` (`pending`, `succeeded`, `failed`,
  `sanitizer_rejected`)
- `target_location` (the scratch or production path
  the restore wrote to)
- `manifest_hash` (the SHA-256 of the restored
  database file; matches the `manifest_hash` on the
  `BackupSnapshot` row when the restore is faithful)
- `row_count` (the number of rows the integrity
  check counted in the restored database)
- `audit_correlation_id` (the correlation id of the
  audit entry the run emitted)
- `created_at`, `updated_at`

### `RetentionPolicy`

A single per-workspace retention policy. The row
holds the retention floor, the prune enablement flag,
and the acceptance metadata that gates the prune
and the data-deletion paths.

- `id`
- `organization_id` (unique)
- `backup_retention_days` (default 30, floor 1)
- `audit_retention_days` (default 90, floor 90 per
  `NFR-SEC-008`)
- `prune_enabled` (bool, default false)
- `accepted_by` (nullable; required before the prune
  actor runs)
- `accepted_at` (nullable)
- `created_at`, `updated_at`

### `BackupRestoreService`

The application service that owns the bounded
operations. The service is the only place that
mutates `backup_snapshots`, `backup_restore_runs`,
and `retention_policies`; the worker actors call it
from the worker queue and the REST layer calls it
from the request handlers.

- `schedule_rehearsal` — enqueues a worker task
  through the existing Dramatiq broker. The actor
  calls `dry_run_restore` against the most recent
  verified `BackupSnapshot` row and writes a
  `backup_restore_runs` row.
- `dry_run_restore(backup_id)` — synchronously
  restores the backup into a scratch location
  (`<sqlite_path>.restore-rehearsal-<uuid>.sqlite3`),
  runs an integrity check, and returns a result
  dataclass.
- `prune_expired_backups` — runs from a periodic
  worker tick. Reads the per-workspace retention
  policy, deletes expired `BackupSnapshot` rows,
  and emits a `backup.retention.pruned` audit
  entry.
- `restore_backup(backup_id, accepted_by)` —
  bounded, single-action, confirmation-gated real
  restore. Refuses to overwrite the production
  database without an `accepted_by` recorded in
  the request payload and a `paused` environment
  mode from `US-040`.

### `DataDeletionService`

The application service that owns the governed
data-deletion path. The service is the only place
that deletes or anonymizes a lead, a source
observation, or a user; the REST layer calls it
from the request handlers.

- `delete_lead(lead_id, accepted_by, reason)` —
  marks the lead as `anonymized` in the
  repository, removes the public profile URL,
  anonymizes the display name, and emits a
  `data.lead.deleted` audit entry.
- `delete_user(user_id, accepted_by, reason)` —
  disables the user, removes the email, and emits
  a `data.user.deleted` audit entry.
- `delete_observation(observation_id, accepted_by,
  reason)` — marks the observation as `redacted`
  in the repository and emits a
  `data.observation.deleted` audit entry.
- `delete_tenant(tenant_id, accepted_by, reason)` —
  refuses without a second-owner confirmation; the
  slice stops short of cascading delete.

Business rules:

- Every new endpoint requires an authenticated
  session with `owner` or `admin` role. Viewer,
  analyst, sales, and reviewer roles get no access
  to the restore, retention, or deletion paths.
- The bounded restore path refuses to overwrite the
  production database while the environment mode
  from `US-040` is `pilot_live` or `test_like`. The
  operator must first transition the environment to
  `paused` mode.
- The bounded restore path refuses to run without
  an `accepted_by` recorded in the request payload.
  The `accepted_at` is set to the current time when
  the request is accepted.
- The retention prune actor refuses to run without
  a `RetentionPolicy.accepted_by`. The
  `prune_enabled` flag is the master switch; the
  actor is read-only with respect to the policy
  row.
- The data-deletion path refuses to run without an
  `accepted_by` and a `reason` recorded in the
  request payload. The reason is stored on the
  audit entry and surfaced in the operator panel.
- The `BackupRestoreService.dry_run_restore` path
  refuses to write to a target location that is
  the same as the production database path. The
  path is a scratch location under the same parent
  directory.
- The `SanitizeAlertPayload` helper from `US-041`
  runs on every payload before it is persisted on
  `backup_restore_runs` or on the audit entries.
- The restore rehearsal, the retention prune, and
  the data-deletion path emit `backup.*` and
  `data.*` audit entries using the same secret-safe
  payload contract as `US-026` and `US-041`.
- The restore rehearsal respects the
  `LaunchGateReport.backup_freshness` check from
  `US-040`. A rehearsal that runs while the
  environment is `paused` writes a
  `backup.restore.rehearsed` audit entry with the
  `paused` mode flag.

## Application Flow

- `ScheduleRestoreRehearsal` (owner/admin) — reads
  the most recent verified `BackupSnapshot` row,
  enqueues a worker task through the Dramatiq
  broker, and returns the `restore_run_id` to the
  caller.
- `RestoreRehearsalActor` (worker) — calls
  `dry_run_restore` against the snapshot, writes a
  `backup_restore_runs` row, and emits a
  `backup.restore.rehearsed` audit entry.
- `DryRunRestore` (owner/admin) — synchronously
  restores the backup into a scratch location,
  runs an integrity check, and returns the result
  inline. The path refuses to write to the
  production database.
- `RestoreBackup` (owner/admin) — bounded,
  confirmation-gated real restore. Refuses to
  overwrite the production database while the
  environment mode is `pilot_live` or `test_like`.
  Refuses to run without an `accepted_by`.
- `PruneRetention` (owner/admin) — bounded,
  confirmation-gated retention prune. Refuses to
  run without a `RetentionPolicy.accepted_by`.
- `DeleteData` (owner/admin) — bounded,
  confirmation-gated data deletion by tenant,
  user, lead, or source observation. Refuses to
  run without an `accepted_by` and a `reason`.
- `SanitizeAlertPayload` (shared helper) — runs
  every payload through the existing helper from
  `US-041` so the contract is defined once and
  reused.

## Interface Contract

This slice adds the minimum REST surface that
owners and admins need to see, configure, and
trigger the bounded restore, retention, and
data-deletion paths.

- `GET /admin/backup-snapshots/{id}` — owner/admin
  only. Returns the snapshot plus the last
  `backup_restore_runs` row.
- `GET /admin/backup-restore-runs?status=&backup_id=`
  — owner/admin only. Returns paginated restore
  history with sanitized payloads.
- `POST /admin/backup-snapshots/{id}:restore:dry-run`
  — owner/admin only. Synchronous dry-run that
  returns the result inline.
- `POST /admin/backup-snapshots/{id}:restore` —
  owner/admin only. Bounded, confirmation-gated
  real restore.
- `POST /admin/retention/prune` — owner/admin only.
  Bounded, confirmation-gated retention prune.
- `POST /admin/data-deletion` — owner/admin only.
  Bounded, confirmation-gated data deletion by
  tenant, user, lead, or source observation.

Expected payload concerns:

- All new error responses follow the existing error
  envelope (`code`, `message`, `request_id`,
  `details`).
- Restore without an `accepted_by` returns
  `RESTORE_ACCEPTANCE_REQUIRED`.
- Restore while the environment mode is
  `pilot_live` or `test_like` returns
  `RESTORE_MODE_NOT_PAUSED`.
- Retention prune without a
  `RetentionPolicy.accepted_by` returns
  `RETENTION_ACCEPTANCE_REQUIRED`.
- Data deletion without an `accepted_by` and a
  `reason` returns `DATA_DELETION_ACCEPTANCE_REQUIRED`.
- Every restore, retention prune, and data-deletion
  attempt emits a durable audit entry with the
  same secret-safe payload contract as `US-026` and
  `US-041`.

## Data Model

New durable objects, each with a forward-only
migration and an index strategy sized for the
current SQLite baseline:

- `backup_restore_runs` (organization-scoped, index
  on `(organization_id, status, started_at)` for
  the history endpoint, index on `backup_id` for
  the per-snapshot filter, index on
  `manifest_hash` for the integrity check).
- `retention_policies` (one row per
  `organization_id`; unique on `organization_id`
  for the policy read path).

No raw payload, secret, cookie, or browser storage
state is stored in either table. The migration
header documents that the change is additive and
that dropping the new tables is the documented
rollback path; no data outside the new tables is
affected.

## UI / Platform Impact

- The admin settings surface gains a `Backup &
  Restore` panel for owner/admin roles. The panel
  renders the most recent `BackupSnapshot` row, the
  last `backup_restore_runs` row, the retention
  policy, and a `Dry-run restore` button that
  performs a single round-trip and asserts the
  integrity contract.
- The in-app inbox from `US-029` shows
  `backup.restore.rehearsed`,
  `backup.retention.pruned`, `data.lead.deleted`,
  `data.user.deleted`, and `data.observation.deleted`
  audit entries with a dedicated severity icon
  and a deep link to the operator panel.
- The frontend does not need a parallel
  notification channel; it reuses the inbox and
  settings surfaces already shipped by `US-026`
  and `US-029`.
- The `scripts/verify-us-043.sh` command wires the
  unit, integration, E2E, security, operational,
  and platform checks together and is the same
  command run by `harness-cli story verify` and
  `harness-cli story verify-all`.

## Observability

This story is the restore and retention side of
the observability slice, so it must set the
standard that the next story will be measured
against.

- Every restore, retention prune, and data-deletion
  attempt keeps a correlation id that matches the
  existing request envelope and is forwarded to
  the audit entry.
- Every successful restore rehearsal emits a
  `backup.restore.rehearsed` audit entry and a
  matching `backup_restore_runs` row.
- The bounded restore path publishes a thin counter
  (`backup.restore.duration_ms`) so a future
  performance story can detect a slow restore
  before it breaches the RTO target from
  `NFR-REL-005`.
- The `POST /admin/backup-snapshots/{id}:restore:dry-run`
  endpoint is itself covered by the health probe
  contract: a missing or failing dry-run must not
  fail `GET /health/ready`, only surface as a
  degraded warning.

## Alternatives Considered

1. **Skip the bounded restore path and keep the
   manual `sqlite3` script.** This would have
   committed the MVP to a manual, error-prone
   restore flow that is not auditable, not
   tenant-scoped, and not reviewable. The
   bounded path provides a single source of
   truth for restore, retention, and data
   deletion.
2. **Restrict the bounded restore path to the
   worker queue and refuse synchronous
   restoration.** This would have forced an
   operator to wait for the worker to pick up the
   task. The slice keeps the dry-run synchronous
   so the operator panel can surface the result
   inline.
3. **Push the restore, retention, and data
   deletion paths through a new external channel
   instead of the existing in-app inbox and audit
   log.** This would have added a new provider
   before the local-first baseline was proven and
   would have created a parallel channel that
   could drift away from the existing
   notification preferences from `US-029` and the
   sanitization helper from `US-041`. Reusing the
   same helper and the same audit entry shape
   keeps the contract aligned with the rest of
   the product.
