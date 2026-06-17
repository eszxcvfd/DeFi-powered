# Backup And Restore Runbook (US-043)

This runbook is the operator-facing companion to the
`/admin/backup-snapshots` and `/admin/backup-restore-runs`
endpoints and the `US-043` story packet. It is
read-only documentation: nothing here mutates product
state outside the documented bounded operations.

## What this surface is

The backup and restore operations slice ships:

- One `RetentionPolicy` row per organization with
  `backup_retention_days`, `audit_retention_days`,
  `prune_enabled`, and `accepted_by` / `accepted_at`.
- A `BackupRestoreService` that owns the bounded
  restore, retention prune, and data-deletion paths.
  The service is the only place that mutates
  `backup_snapshots`, `backup_restore_runs`, and
  `retention_policies`.
- A `RestoreRehearsalActor` worker that runs the
  bounded restore rehearsal through the existing
  Dramatiq broker.
- A `PruneRetentionActor` worker that runs the
  bounded retention prune through the existing
  Dramatiq broker.
- A `DataDeletionService` that owns the governed
  data-deletion path. The service is the only
  place that deletes or anonymizes a lead, a user,
  or a source observation.
- A new
  `/admin/backup-restore` panel for owner/admin
  roles that exposes the most recent
  `BackupSnapshot` row, the last
  `backup_restore_runs` row, the retention policy,
  and a `Dry-run restore` button that performs a
  single round-trip and asserts the integrity
  contract.

The bounded restore path requires the application
to be in `paused` mode. Live restore is a deployment
decision; the slice refuses to overwrite the
production database while the environment mode is
`pilot_live` or `test_like`.

The bounded retention prune and the data-deletion
path require an `accepted_by` and a `reason`
recorded in the request payload. The audit entry
records both.

## Where to look

| Surface | Path | Owner |
| --- | --- | --- |
| Operator panel | `frontend/src/pages/AdminBackupRestore.tsx` | frontend |
| REST surface | `src/livelead/interfaces/rest/backup_restore.py` | interfaces |
| Service | `src/livelead/application/backup_restore/backup_restore_service.py` | application |
| Rehearsal actor | `apps/worker/backup_restore_tasks.py` | apps |
| Prune actor | `apps/worker/retention_tasks.py` | apps |
| Data deletion | `src/livelead/application/backup_restore/data_deletion_service.py` | application |
| Sanitization helper | `src/livelead/domain/observability/sanitization.py` | domain |
| Migration | `alembic/versions/20260616_0033_backup_restore_operations.py` | alembic |
| Product doc | `docs/product/backup-and-restore-operations.md` | docs |

## Bounded operations at a glance

| Operation | Trigger | Outcome | Acceptance |
| --- | --- | --- | --- |
| `dry_run_restore` | owner/admin | writes to a scratch location, reports the result inline | none |
| `schedule_rehearsal` | owner/admin | enqueues a worker task that performs a dry-run | none |
| `restore_backup` | owner/admin with `accepted_by`, environment in `paused` mode | overwrites the production database | `accepted_by` + `paused` mode |
| `prune_expired_backups` | owner/admin via the worker tick | deletes expired `BackupSnapshot` rows | `RetentionPolicy.accepted_by` + `prune_enabled = true` |
| `delete_lead` | owner/admin with `accepted_by` + `reason` | marks the lead as `anonymized` | `accepted_by` + `reason` |
| `delete_user` | owner/admin with `accepted_by` + `reason` | disables the user and removes the email | `accepted_by` + `reason` |
| `delete_observation` | owner/admin with `accepted_by` + `reason` | marks the observation as `redacted` | `accepted_by` + `reason` |

## What to do when a restore fails

1. Open `/admin/backup-snapshots/{id}` and read the
   last `backup_restore_runs` row. The row carries
   the `status` (`succeeded`, `failed`,
   `sanitizer_rejected`) and the `manifest_hash`.
2. If the `status` is `failed`, check the
   `target_location` and the `manifest_hash` against
   the `BackupSnapshot.manifest_hash`. A mismatch
   means the backup is corrupted; the operator
   should escalate per the runbook associated with
   the failing surface.
3. If the `status` is `sanitizer_rejected`, the
   payload contained a secret value. Update the
   source of the payload to stop emitting the
   secret value. The bounded restore path will not
   retry until the source is fixed.
4. If the `status` is `succeeded` but the
   `manifest_hash` does not match the
   `BackupSnapshot.manifest_hash`, the integrity
   check failed. The operator should escalate per
   the runbook associated with the failing surface.
5. Acknowledge the run from the panel. Acknowledgement
   does not resolve the run; the run is closed only
   when the next rehearsal succeeds.

## What to do when a backup is stale

The `backup.stale` alert from `US-041` fires when
the most recent backup is older than 26 hours. The
alert references this runbook.

1. Open `/admin/backup-snapshots` and read the
   most recent `BackupSnapshot` row. Confirm the
   `created_at` and the `verification_status`.
2. If the most recent backup is older than the
   `NFR-REL-005` RPO 24h target, the operator
   should record a new backup through the
   `POST /admin/backup-snapshots:record` endpoint.
3. If the most recent backup is older than the
   `NFR-REL-005` RPO 24h target and the
   `verification_status` is `failed`, the operator
   should investigate the backup scheduler and
   escalate per the runbook associated with the
   failing surface.
4. After recording a new backup, the operator
   should run a bounded restore rehearsal through
   the `POST /admin/backup-snapshots/{id}:restore:dry-run`
   endpoint. The rehearsal writes to a scratch
   location and reports the result inline.

## What to do when a retention prune needs to be reversed

The bounded retention prune is irreversible. The
slice refuses to add a dry-run mode; the prune is
the only supported flow.

1. Open `/admin/retention/prune` and confirm the
   `RetentionPolicy.accepted_by` and the
   `prune_enabled` flag.
2. If the prune was a mistake, the operator must
   restore the deleted `BackupSnapshot` rows from
   a previous backup. The bounded restore path
   requires the application to be in `paused` mode.
3. After the restore, the operator must update the
   `RetentionPolicy` row to disable the prune
   (`prune_enabled = false`) and to record the
   incident in the audit log.
4. If the restore is not possible, the operator
   must escalate per the runbook associated with
   the failing surface and add a friction note
   via
   `scripts/bin/harness-cli intervention --kind review --summary …`
   so the next retention prune can avoid the same
   failure.

## What to do when a data deletion needs to be reversed

The bounded data-deletion path marks related
records as `anonymized` or `redacted` rather than
cascading delete. The cascade is the caller's
responsibility.

1. Open the audit log and find the
   `data.lead.deleted`, `data.user.deleted`, or
   `data.observation.deleted` entry that recorded
   the deletion. The entry carries the `accepted_by`
   and the `reason`.
2. If the deletion was a mistake, the operator
   must restore the anonymized or redacted record
   from a previous backup. The bounded restore path
   requires the application to be in `paused` mode.
3. After the restore, the operator must record a
   follow-up audit entry that explains the reversal
   and the reason.
4. If the restore is not possible, the operator
   must escalate per the runbook associated with
   the failing surface.

## Pausing the restore rehearsal

The restore rehearsal is a worker actor
(`apps/worker/backup_restore_tasks.py`). Pause it
by stopping the worker process. No code path in
the actor mutates product state, so pausing it
does not leave the system in an inconsistent
state.

## Restore rehearsal contract

`backup.stale` and `audit.retention_breach_risk`
both depend on durability paths. The bounded
restore rehearsal runs from the worker tick and
records a `backup_restore_runs` row. Operators
verify the rehearsal contract by:

1. Running a bounded restore rehearsal through
   the operator panel.
2. Confirming the `backup_restore_runs` row is
   `succeeded`.
3. Confirming the `manifest_hash` matches the
   `BackupSnapshot.manifest_hash`.
4. Confirming the `backup.restore.rehearsed`
   audit entry was written.

The bounded restore rehearsal respects the RTO
target from `NFR-REL-005` (8 hours). The
verification script asserts the rehearsal
duration is within the target.

## What this runbook does NOT cover

- Cross-region restore, hot-standby failover, or
  zero-downtime restore orchestration — out of
  scope for `US-043`; a later deployment story
  adds it behind the stable interface.
- Live restore while the application is in
  `pilot_live` or `test_like` mode — the slice
  refuses to overwrite the production database;
  live restore is a deployment decision.
- Encrypted-at-rest backups beyond the file-system
  encryption already provided by the storage
  layer.
- Long-term cold-storage tiering. The slice treats
  all backups equally; cold storage is a
  deployment decision.
- Restoring across SQLite versions. The restore
  path assumes the target SQLite is the same
  version as the source.
- Per-tenant retention floors. The slice ships one
  fixed default set; per-tenant tuning is a
  follow-on story.
