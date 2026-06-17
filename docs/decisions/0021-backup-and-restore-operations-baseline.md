# 0021 Backup And Restore Operations Baseline

Date: 2026-06-16

## Status

Planned (companion decision to `US-043`).

## Context

`US-040` shipped the first real-environment cutover
slice for LiveLead. The slice introduced:

- A durable `BackupSnapshot` table with metadata
  (`backup_id`, `created_at`, `verification_status`,
  `retention_until`, `size_bytes`, `location_uri`,
  `manifest_hash`, `last_verified_at`).
- A `POST /admin/backup-snapshots:record` endpoint
  that records a backup execution against the
  durable store.
- A `POST /admin/backup-snapshots/{id}:verify`
  endpoint that transitions a backup row to
  `verified` after a manual integrity check.
- A `backup.stale` alert rule (US-041) that fires
  when the most recent backup is older than 26
  hours.
- A `pilot-live-rollback-runbook.md` entry that
  documents a manual
  `sqlite3 data/livelead.sqlite3 < last_backup.sql`
  restore flow followed by a manual `verify` call.
- An `observability-runbook.md` entry that
  references a "restore rehearsal contract from
  US-040" — but no such contract has been shipped
  yet.

`US-040` deliberately stopped at the metadata and
the manual restore flow. The product still has no
bounded backup and restore operations baseline:

- There is no automated restore rehearsal. The
  `verification_status` column stays at `recorded`
  or `verified` because an operator has to manually
  copy the backup into a fresh location, run
  integrity checks, and call the verify endpoint.
- There is no dry-run restore path. An operator
  who wants to rehearse a restore has to allocate
  a scratch location, copy the backup, and run the
  integrity check by hand.
- There is no retention enforcement. `FR-ADM-004`
  requires Admin to configure retention, but the
  system has no scheduled job that prunes expired
  backups and audits the deletion.
- There is no governed data-deletion path.
  `FR-ADM-005` requires Admin to delete or
  anonymize data by tenant, user, lead, or source
  observation, but the system has no REST surface
  for the path.
- The RPO 24h / RTO 8h target from `NFR-REL-005` is
  not backed by an automated rehearsal.

The next step in the hardening epic is therefore a
bounded backup and restore operations baseline that
turns the `BackupSnapshot` metadata into a usable
contract.

## Decision

`US-043` introduces the first backup and restore
operations baseline for LiveLead.

### Domain objects

- **`BackupRestoreRun`** — durable record of a
  restore attempt. The row carries enough
  information to prove that a backup can be
  restored within the RTO target from
  `NFR-REL-005`.
- **`RetentionPolicy`** — per-workspace retention
  policy with `backup_retention_days`,
  `audit_retention_days`, `prune_enabled`, and the
  `accepted_by` / `accepted_at` acceptance
  metadata.

### Bounded operations

- **`BackupRestoreService`** — application service
  that owns the bounded restore, retention prune,
  and data-deletion paths. The service is the only
  place that mutates `backup_snapshots`,
  `backup_restore_runs`, and `retention_policies`.
- **`schedule_rehearsal`** — enqueues a worker task
  that restores the most recent verified backup
  into a scratch location, runs integrity checks,
  records a `backup_restore_runs` row, and emits a
  `backup.restore.rehearsed` audit entry.
- **`dry_run_restore`** — synchronously restores a
  backup into a scratch location and reports the
  result inline.
- **`prune_expired_backups`** — runs from a
  periodic worker tick, reads the configured
  retention policy, deletes expired
  `BackupSnapshot` rows, and emits a
  `backup.retention.pruned` audit entry.
- **`restore_backup`** — bounded, confirmation-
  gated real restore. Refuses to overwrite the
  production database without an `accepted_by` and
  a `paused` environment mode from `US-040`.
- **`DataDeletionService`** — application service
  that owns the governed data-deletion path. The
  service is the only place that deletes or
  anonymizes a lead, a user, or a source
  observation.

### Admin surface

- New owner/admin-only REST surface:
  - `GET /admin/backup-snapshots/{id}`
  - `GET /admin/backup-restore-runs?status=&backup_id=`
  - `POST /admin/backup-snapshots/{id}:restore:dry-run`
  - `POST /admin/backup-snapshots/{id}:restore`
  - `POST /admin/retention/prune`
  - `POST /admin/data-deletion`
- Every restore, retention prune, and data
  deletion attempt emits a durable audit entry
  with the same secret-safe payload contract as
  `US-026` and `US-041`.
- The bounded restore path refuses to overwrite
  the production database while the environment
  mode from `US-040` is `pilot_live` or
  `test_like`. The operator must first transition
  the environment to `paused` mode.

### Sanitization contract

- Every payload that flows through the restore
  rehearsal or the data-deletion path runs through
  the `SanitizeAlertPayload` helper from `US-041`.
  The slice imports the same symbol and does not
  redefine it.
- A payload that fails the sanitizer is dropped
  before it is persisted, the run is marked as
  `sanitizer_rejected`, and a `backup.export_rejected`
  audit entry is written with the secret marker
  and no payload detail.

### Seam for a later deployment story

- A stable interface sits between the bounded
  operations and the file-system / object-storage
  layer so a later deployment story can wire a
  specific object storage provider (S3, GCS, Azure
  Blob) without changing the bounded operations.
  This slice does not commit to a particular
  provider.

## Alternatives Considered

1. **Skip the bounded restore path and keep the
   manual `sqlite3` script.** This would have
   committed the MVP to a manual, error-prone
   restore flow that is not auditable, not
   tenant-scoped, and not reviewable. The bounded
   path provides a single source of truth for
   restore, retention, and data deletion.
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

## Consequences

Positive:

- The first real-environment pilot gets a
  bounded, confirmation-gated restore path that
  does not require a manual `sqlite3` script and
  is auditable end-to-end.
- The `NFR-REL-005` RPO 24h / RTO 8h target is
  backed by an automated rehearsal. Operators can
  prove that a backup can be restored within the
  RTO window without running a manual script.
- The `FR-ADM-004` retention policy is enforced
  by a periodic worker tick and audited through
  the same secret-safe payload contract as
  `US-026` and `US-041`.
- The `FR-ADM-005` data-deletion path is
  tenant-scoped, role-gated, and audit-bound. The
  slice refuses to run without an `accepted_by`
  and a `reason` recorded in the request payload.
- The slice reuses the `SanitizeAlertPayload`
  helper from `US-041` and the `AuditService` from
  `US-026`. No new redaction helper, no new
  audit-emit contract.

Tradeoffs:

- The bounded restore path requires the
  application to be in `paused` mode. Live
  restore is a deployment decision; the slice
  refuses to overwrite the production database
  while the environment mode is `pilot_live` or
  `test_like`.
- The default `audit_retention_days` follows the
  `NFR-SEC-008` floor and cannot be lowered below
  90 days. Per-tenant retention floors are a
  follow-on story.
- The data-deletion path marks related records as
  `anonymized` or `redacted` rather than cascading
  delete. The cascade is the caller's
  responsibility; the slice emits a separate
  audit entry for each cascade step.

## Follow-Up

- Add per-tenant retention floors through a
  configuration surface, gated on the same
  owner/admin role as the retention policy
  endpoint.
- Wire a specific object storage provider (S3,
  GCS, Azure Blob) behind the stable interface
  so the bounded restore path can target remote
  storage.
- Add cross-region restore, hot-standby failover,
  and zero-downtime restore orchestration once
  the local-first baseline has been used in
  production for at least one operational cycle.
- Evaluate the need for a tenant-deletion path
  that cascades across related records; the
  first implementation marks related records as
  `anonymized` or `redacted` and emits a separate
  audit entry for each cascade step.
- Add a point-in-time recovery path that restores
  against a transaction-log backup; the first
  implementation supports full-database restore
  only.
