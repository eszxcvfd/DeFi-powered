# Overview

## Current Behavior

`US-040` shipped the first real-environment cutover slice for
LiveLead. The slice introduced:

- A durable `BackupSnapshot` table with metadata
  (`backup_id`, `created_at`, `verification_status`,
  `retention_until`, `size_bytes`, `location_uri`,
  `manifest_hash`, `last_verified_at`).
- A `POST /admin/backup-snapshots:record` endpoint that
  records a backup execution against the durable store.
- A `POST /admin/backup-snapshots/{id}:verify` endpoint that
  transitions a backup row to `verified` after a manual
  integrity check.
- A `backup.stale` alert rule (US-041) that fires when the
  most recent backup is older than 26 hours.
- A `pilot-live-rollback-runbook.md` entry that documents a
  manual `sqlite3 data/livelead.sqlite3 < last_backup.sql`
  restore flow followed by a manual `verify` call.
- An `observability-runbook.md` entry that references a
  "restore rehearsal contract from US-040" — but no such
  contract has been shipped yet.

`US-040` deliberately stopped at the metadata and the
manual restore flow. The product still has no bounded
backup and restore operations baseline:

- There is no automated restore rehearsal. The
  `verification_status` column stays at `recorded` or
  `verified` because an operator has to manually copy the
  backup into a fresh location, run integrity checks, and
  call the verify endpoint.
- There is no dry-run restore path. An operator who wants
  to rehearse a restore has to allocate a scratch location,
  copy the backup, and run the integrity check by hand.
- There is no retention enforcement. `FR-ADM-004` requires
  Admin to configure retention, but the system has no
  scheduled job that prunes expired backups and audits the
  deletion.
- There is no governed data-deletion path. `FR-ADM-005`
  requires Admin to delete or anonymize data by tenant,
  user, lead, or source observation, but the system has no
  REST surface for the path. The closest analog today is
  the SQLAlchemy `delete()` calls in the repositories,
  which are not auditable, not tenant-scoped, and not
  reviewable.
- The RPO 24h / RTO 8h target from `NFR-REL-005` is not
  backed by an automated rehearsal. Operators cannot prove
  that a backup can be restored within the RTO window
  without running a manual script.

The next step in the hardening epic is therefore a
bounded backup and restore operations baseline that turns
the `BackupSnapshot` metadata into a usable contract:
automated restore rehearsal, retention enforcement, and
governed data deletion.

## Target Behavior

This story establishes the first bounded backup and
restore operations baseline for LiveLead. After the story
is complete:

- A new durable `backup_restore_runs` table records every
  restore attempt — manual, dry-run, or scheduled
  rehearsal — with a `started_at`, `completed_at`,
  `status` (`pending`, `succeeded`, `failed`,
  `sanitizer_rejected`), `target_location`, `backup_id`,
  `manifest_hash`, `row_count`, and `audit_correlation_id`.
- A new `BackupRestoreService` exposes the bounded
  operations:
  - `schedule_rehearsal` — enqueues a worker task that
    restores the most recent verified backup into a
    scratch location, runs integrity checks, records a
    `backup_restore_runs` row, and emits a
    `backup.restore.rehearsed` audit entry.
  - `dry_run_restore` — synchronously restores a backup
    into a scratch location and reports the result
    without touching the production database. Used by
    the operator panel before a real restore.
  - `prune_expired_backups` — runs from a periodic worker
    tick, reads the configured retention policy, deletes
    expired `BackupSnapshot` rows, and emits a
    `backup.retention.pruned` audit entry.
  - `delete_data` — a governed REST path that an owner or
    admin can use to delete or anonymize a lead, a
    source observation, or a user. The path is
    tenant-scoped, role-gated, and audit-bound.
- A new owner/admin-only REST surface:
  - `GET /admin/backup-snapshots/{id}` — returns the
    snapshot plus the last `backup_restore_runs` row.
  - `GET /admin/backup-restore-runs?status=&backup_id=`
    — paginated restore history with sanitized payloads.
  - `POST /admin/backup-snapshots/{id}:restore:dry-run`
    — synchronous dry-run that returns the result inline.
  - `POST /admin/backup-snapshots/{id}:restore`
    — bounded, single-action, confirmation-gated real
    restore. Refuses to overwrite the production
    database without an `accepted_by` and an
    `accepted_at` recorded in the policy row.
  - `POST /admin/retention/prune` — bounded,
    confirmation-gated retention prune. Refuses to prune
    without an `accepted_by`.
  - `POST /admin/data-deletion` — bounded,
    confirmation-gated data deletion by tenant, user,
    lead, or source observation.
- A new `RetentionPolicy` row per organization with
  `backup_retention_days`, `audit_retention_days`, and
  `prune_enabled`. The defaults follow the
  `NFR-SEC-008` (90 days) and `NFR-REL-005` (RPO 24h,
  RTO 8h) floors.
- A new decision record that captures the retention and
  deletion contract, the deferred work (per-tenant
  retention floors, cross-region restore, hot-standby
  failover), and the rollback story when a restore
  fails.
- A new product doc
  (`docs/product/backup-and-restore-operations.md`) that
  becomes the living contract for the backup and restore
  domain.
- A new runbook
  (`docs/ops/backup-restore-runbook.md`) that documents
  what an operator does when a restore fails, when a
  backup is stale, and when a retention prune needs to be
  reversed.
- A first bounded backup-and-restore E2E test that
  records a backup, restores it into a scratch
  location, verifies the row count, and asserts the
  audit entry was written.

The slice stops at the local-first, single-host baseline.
Cross-region restore, hot-standby failover, and per-tenant
retention floors remain in the follow-up backlog.

## Affected Users

- Owners and Admins responsible for running the first
  real-environment pilot. They need a bounded,
  confirmation-gated restore path that does not require a
  manual `sqlite3` script.
- Operators on call for the pilot-live environment. They
  need a `backup-restore-runbook.md` entry that explains
  what to do when a backup is stale, when a restore
  fails, and when a retention prune needs to be reversed.
- Compliance and security officers who need an
  audit-bound retention and deletion path that is
  tenant-scoped, role-gated, and reviewable.
- Future implementation agents and engineers extending
  cross-region restore, hot-standby failover, or
  per-tenant retention floors. They need a stable
  contract that they can build on.

## Affected Product Docs

- `docs/product/real-environment-cutover-and-live-operations.md`
  (US-040 contract; this story consumes the
  `BackupSnapshot` metadata and the launch-gate
  `backup_freshness` check).
- `docs/product/observability-and-alerting.md` (US-041
  contract; the `backup.stale` alert and the
  `audit.retention_breach_risk` alert both depend on the
  retention policy this story ships).
- `docs/product/external-metrics-and-tracing.md` (US-042
  contract; the export policy references the retention
  policy indirectly through the audit retention floor).
- `docs/product/audit-log-and-governance.md` (US-026
  contract; the retention and deletion paths emit
  `backup.*` and `data.*` audit entries with the same
  secret-safe payload contract).
- `docs/product/backup-and-restore-operations.md` (new
  product doc that this story seeds as the living
  contract for the backup and restore domain).

## Non-Goals

- Cross-region restore, hot-standby failover, or
  zero-downtime restore orchestration. The slice is
  single-host and bounded.
- Per-tenant retention floors. The slice ships one fixed
  default set; per-tenant tuning is a follow-on story.
- Encrypted-at-rest backups beyond the file-system
  encryption already provided by the storage layer. The
  slice does not introduce application-level encryption.
- Long-term cold-storage tiering. The slice treats all
  backups equally; cold storage is a deployment decision.
- Distributed backup verification. The integrity check
  is local to the worker process; remote verification
  against a third-party service is a deployment
  decision.
- Restoring across SQLite versions. The restore path
  assumes the target SQLite is the same version as the
  source. Version-mismatch recovery is a deployment
  decision.
- Restoring the running application while it is live.
  The bounded restore path requires the application to
  be in `paused` mode; live restore is a deployment
  decision.
