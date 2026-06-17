# Backup And Restore Operations

Source: `SPEC.md` sections 10.2 (`NFR-REL-005`),
10.4 (`FR-ADM-004`, `FR-ADM-005`), 14.2, 17, and the
deferred restore rehearsal commitment referenced by
`US-040`, `US-041`, and `US-042`.

## Product Goal

`US-040` shipped the first real-environment cutover
slice for LiveLead. The slice introduced the
`BackupSnapshot` table and a manual restore flow that
relies on a `sqlite3 data/livelead.sqlite3 <
last_backup.sql` script followed by a manual
`POST /admin/backup-snapshots/{id}:verify` call.
`US-040` deliberately stopped at the metadata and the
manual flow.

`US-041` introduced the `backup.stale` alert that
fires when the most recent backup is older than 26
hours. The alert references a "restore rehearsal
contract from US-040" that has not been shipped yet.

This product slice is the first bounded backup and
restore operations baseline for LiveLead. It turns
the `BackupSnapshot` metadata into a usable contract:
automated restore rehearsal, retention enforcement,
and governed data deletion, all behind owner/admin
role gates and audit entries.

The slice is local-first and single-host by design.
It does not commit to a specific object storage
provider (S3, GCS, Azure Blob) in this step; it
preserves a stable seam for a later deployment story
to wire one. The bounded restore path requires the
application to be in `paused` mode; live restore is
a deployment decision.

## MVP Scope

This product slice covers:

- A durable `BackupRestoreRun` table that records
  every restore attempt — manual, dry-run, or
  scheduled rehearsal — with a `started_at`,
  `completed_at`, `status`, `target_location`,
  `backup_id`, `manifest_hash`, `row_count`, and
  `audit_correlation_id`.
- A durable `RetentionPolicy` row per organization
  with `backup_retention_days`,
  `audit_retention_days`, `prune_enabled`, and the
  `accepted_by` / `accepted_at` acceptance metadata.
- A `BackupRestoreService` that exposes the bounded
  operations:
  - `schedule_rehearsal` — enqueues a worker task
    that restores the most recent verified backup
    into a scratch location, runs integrity
    checks, records a `backup_restore_runs` row,
    and emits a `backup.restore.rehearsed` audit
    entry.
  - `dry_run_restore` — synchronously restores a
    backup into a scratch location and reports the
    result inline.
  - `prune_expired_backups` — runs from a periodic
    worker tick, reads the configured retention
    policy, deletes expired `BackupSnapshot` rows,
    and emits a `backup.retention.pruned` audit
    entry.
  - `restore_backup` — bounded, single-action,
    confirmation-gated real restore. Refuses to
    overwrite the production database without an
    `accepted_by` and a `paused` environment mode
    from `US-040`.
- A `DataDeletionService` that owns the governed
  data-deletion path:
  - `delete_lead(lead_id, accepted_by, reason)` —
    marks the lead as `anonymized` and emits a
    `data.lead.deleted` audit entry.
  - `delete_user(user_id, accepted_by, reason)` —
    disables the user and emits a
    `data.user.deleted` audit entry.
  - `delete_observation(observation_id, accepted_by,
    reason)` — marks the observation as `redacted`
    and emits a `data.observation.deleted` audit
    entry.
- A new owner/admin-only REST surface:
  - `GET /admin/backup-snapshots/{id}` — returns
    the snapshot plus the last `backup_restore_runs`
    row.
  - `GET /admin/backup-restore-runs?status=&backup_id=`
    — paginated restore history with sanitized
    payloads.
  - `POST /admin/backup-snapshots/{id}:restore:dry-run`
    — synchronous dry-run that returns the result
    inline.
  - `POST /admin/backup-snapshots/{id}:restore`
    — bounded, confirmation-gated real restore.
  - `POST /admin/retention/prune` — bounded,
    confirmation-gated retention prune.
  - `POST /admin/data-deletion` — bounded,
    confirmation-gated data deletion by tenant,
    user, lead, or source observation.
- A first bounded backup-and-restore E2E test that
  records a backup, restores it into a scratch
  location, verifies the row count, and asserts the
  `backup.restore.rehearsed` audit entry was
  written.
- A new runbook
  (`docs/ops/backup-restore-runbook.md`) that
  documents what an operator does when a restore
  fails, when a backup is stale, and when a retention
  prune needs to be reversed.

This product slice does not yet cover:

- Cross-region restore, hot-standby failover, or
  zero-downtime restore orchestration. The slice is
  single-host and bounded.
- Per-tenant retention floors. The slice ships one
  fixed default set; per-tenant tuning is a follow-on
  story.
- Encrypted-at-rest backups beyond the file-system
  encryption already provided by the storage layer.
- Long-term cold-storage tiering. The slice treats
  all backups equally; cold storage is a deployment
  decision.
- Distributed backup verification. The integrity
  check is local to the worker process.
- Restoring across SQLite versions. The restore path
  assumes the target SQLite is the same version as
  the source.
- Restoring the running application while it is
  live. The bounded restore path requires the
  application to be in `paused` mode; live restore
  is a deployment decision.
- Replacing the existing `LaunchGateReport` from
  `US-040`. This story consumes it, it does not
  redefine it.
- Replacing the existing `backup.stale` alert from
  `US-041`. This story consumes it, it does not
  redefine it.

## Contract Rules

- All new admin endpoints require an authenticated
  session with `owner` or `admin` role. Viewer,
  analyst, sales, and reviewer roles get no access
  to the restore, retention, or deletion paths.
- The bounded restore path refuses to overwrite the
  production database while the environment mode from
  `US-040` is `pilot_live` or `test_like`. The
  operator must first transition the environment to
  `paused` mode.
- The bounded restore path refuses to run without
  an `accepted_by` recorded in the request payload.
  The `accepted_at` is set to the current time when
  the request is accepted.
- The retention prune actor refuses to run without
  a `RetentionPolicy.accepted_by`. The
  `prune_enabled` flag is the master switch.
- The data-deletion path refuses to run without an
  `accepted_by` and a `reason` recorded in the
  request payload. The reason is stored on the audit
  entry and surfaced in the operator panel.
- The `BackupRestoreService.dry_run_restore` path
  refuses to write to a target location that is the
  same as the production database path. The path is
  a scratch location under the same parent
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

## Supported Operations

| Operation | Trigger | Outcome | Acceptance |
| --- | --- | --- | --- |
| `dry_run_restore` | owner/admin | writes to a scratch location, reports the result inline | none |
| `schedule_rehearsal` | owner/admin | enqueues a worker task that performs a dry-run | none |
| `restore_backup` | owner/admin with `accepted_by`, environment in `paused` mode | overwrites the production database | `accepted_by` + `paused` mode |
| `prune_expired_backups` | owner/admin via the worker tick | deletes expired `BackupSnapshot` rows | `RetentionPolicy.accepted_by` + `prune_enabled = true` |
| `delete_lead` | owner/admin with `accepted_by` + `reason` | marks the lead as `anonymized` | `accepted_by` + `reason` |
| `delete_user` | owner/admin with `accepted_by` + `reason` | disables the user and removes the email | `accepted_by` + `reason` |
| `delete_observation` | owner/admin with `accepted_by` + `reason` | marks the observation as `redacted` | `accepted_by` + `reason` |

The table is the single source of truth for the
acceptance matrix. The REST layer, the worker
actor, and the application service all consult the
table before they execute a bounded operation.

## Default Retention

| Setting | Default | Floor | Source |
| --- | --- | --- | --- |
| `backup_retention_days` | 30 | 1 | operator policy |
| `audit_retention_days` | 90 | 90 | `NFR-SEC-008` |
| `prune_enabled` | false | n/a | operator policy |

The default `audit_retention_days` follows the
`NFR-SEC-008` floor. Owners and admins can adjust
`backup_retention_days` and `prune_enabled` through
the retention policy endpoint; the audit retention
floor is enforced by the application layer and
cannot be lowered below 90 days.

## Runtime And Admin Surface

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

All new error responses follow the existing error
envelope (`code`, `message`, `request_id`,
`details`). Restore without an `accepted_by` returns
`RESTORE_ACCEPTANCE_REQUIRED`. Restore while the
environment mode is `pilot_live` or `test_like`
returns `RESTORE_MODE_NOT_PAUSED`. Retention prune
without a `RetentionPolicy.accepted_by` returns
`RETENTION_ACCEPTANCE_REQUIRED`. Data deletion
without an `accepted_by` and a `reason` returns
`DATA_DELETION_ACCEPTANCE_REQUIRED`.

## UI / Ops Surface

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
  audit entries with a dedicated severity icon and
  a deep link to the operator panel.
- The first backup and restore runbook
  (`docs/ops/backup-restore-runbook.md`)
  documents what an operator does when a restore
  fails, when a backup is stale, and when a
  retention prune needs to be reversed.

## Validation Implications

- Unit tests must prove that the bounded restore
  path refuses to run without an `accepted_by` and
  refuses to overwrite the production database
  while the environment mode is `pilot_live` or
  `test_like`, that the retention prune refuses to
  run without a `RetentionPolicy.accepted_by`, and
  that the data-deletion path refuses to run
  without an `accepted_by` and a `reason`.
- Integration tests must exercise every new endpoint
  against an in-memory SQLite plus a stubbed
  restore actor and prove that role gates,
  acceptance gates, and sanitization are enforced.
- E2E tests must cover the operator panel render,
  the bounded restore rehearsal, the retention
  prune acceptance, and the data-deletion
  acceptance.
- Security tests must prove that viewer, analyst,
  sales, and reviewer sessions are rejected on
  every new endpoint, that payload sanitization
  holds, and that the bounded restore path refuses
  to overwrite the production database while the
  environment mode is `pilot_live` or `test_like`.
- Operational tests must prove that the bounded
  restore path can restore a backup into a scratch
  location within the RTO target from `NFR-REL-005`,
  that the retention prune respects the
  `NFR-SEC-008` audit retention floor, and that the
  data-deletion path emits a `data.*` audit entry
  for every attempt.
- Platform proof is the `scripts/verify-us-043.sh`
  command wired into `harness-cli story verify` and
  `harness-cli story verify-all`.
