# Exec Plan

## Goal

Add the first bounded backup and restore operations
baseline to LiveLead. The slice turns the
`BackupSnapshot` metadata that `US-040` introduced into a
usable contract: automated restore rehearsal, retention
enforcement, and governed data deletion, all behind
owner/admin role gates and audit entries.

## Scope

In scope:

- New durable `backup_restore_runs` table with the
  minimum fields required to record a restore attempt:
  `started_at`, `completed_at`, `status`, `target_location`,
  `backup_id`, `manifest_hash`, `row_count`, and
  `audit_correlation_id`. Forward-only Alembic migration
  with a documented rollback note in the migration header.
- New durable `retention_policies` table with
  `backup_retention_days`, `audit_retention_days`,
  `prune_enabled`, and `accepted_by` / `accepted_at`. The
  defaults follow the `NFR-SEC-008` (90 days) and
  `NFR-REL-005` (RPO 24h, RTO 8h) floors.
- New `BackupRestoreService` that exposes the bounded
  operations:
  - `schedule_rehearsal` — enqueues a worker task that
    restores the most recent verified backup into a
    scratch location, runs integrity checks, records a
    `backup_restore_runs` row, and emits a
    `backup.restore.rehearsed` audit entry.
  - `dry_run_restore` — synchronously restores a
    backup into a scratch location and reports the
    result inline.
  - `prune_expired_backups` — runs from a periodic
    worker tick, reads the configured retention
    policy, deletes expired `BackupSnapshot` rows, and
    emits a `backup.retention.pruned` audit entry.
  - `delete_data` — a governed REST path that an
    owner or admin can use to delete or anonymize a
    lead, a source observation, or a user. The path
    is tenant-scoped, role-gated, and audit-bound.
- New owner/admin-only REST surface:
  - `GET /admin/backup-snapshots/{id}` — returns the
    snapshot plus the last `backup_restore_runs` row.
  - `GET /admin/backup-restore-runs?status=&backup_id=`
    — paginated restore history with sanitized
    payloads.
  - `POST /admin/backup-snapshots/{id}:restore:dry-run`
    — synchronous dry-run that returns the result
    inline.
  - `POST /admin/backup-snapshots/{id}:restore`
    — bounded, single-action, confirmation-gated real
    restore. Refuses to overwrite the production
    database without an `accepted_by` and an
    `accepted_at` recorded in the policy row.
  - `POST /admin/retention/prune` — bounded,
    confirmation-gated retention prune. Refuses to
    prune without an `accepted_by`.
  - `POST /admin/data-deletion` — bounded,
    confirmation-gated data deletion by tenant,
    user, lead, or source observation.
- A first bounded backup-and-restore E2E test that
  records a backup, restores it into a scratch
  location, verifies the row count, and asserts the
  audit entry was written.
- A new decision record
  (`docs/decisions/0021-backup-and-restore-operations-baseline.md`)
  that captures the retention and deletion contract, the
  deferred work, and the rollback story.
- A new product doc
  (`docs/product/backup-and-restore-operations.md`)
  that becomes the living contract for the backup
  and restore domain.
- A new runbook
  (`docs/ops/backup-restore-runbook.md`) that
  documents what an operator does when a restore
  fails, when a backup is stale, and when a retention
  prune needs to be reversed.
- Reuse of the `SanitizeAlertPayload` helper from
  `US-041` for every payload that flows through the
  restore rehearsal or the data-deletion path.
- Reuse of the audit-emit contract from `US-026` for
  every `backup.*` and `data.*` audit entry.
- Reuse of the launch-gate profile from `US-040` for
  the `backup_freshness` check that the restore
  rehearsal respects.
- Unit, integration, E2E, security, operational, and
  platform checks wired into a `scripts/verify-us-043.sh`
  command that `harness-cli story verify` can run.

Out of scope:

- Cross-region restore, hot-standby failover, or
  zero-downtime restore orchestration. The slice is
  single-host and bounded.
- Per-tenant retention floors. The slice ships one
  fixed default set; per-tenant tuning is a follow-on
  story.
- Encrypted-at-rest backups beyond the file-system
  encryption already provided by the storage layer.
- Long-term cold-storage tiering. The slice treats all
  backups equally; cold storage is a deployment
  decision.
- Distributed backup verification. The integrity
  check is local to the worker process.
- Restoring across SQLite versions. The restore path
  assumes the target SQLite is the same version as
  the source.
- Restoring the running application while it is live.
  The bounded restore path requires the application
  to be in `paused` mode; live restore is a
  deployment decision.
- Replacing the existing `LaunchGateReport` from
  `US-040`. This story consumes it, it does not
  redefine it.
- Replacing the existing `backup.stale` alert from
  `US-041`. This story consumes it, it does not
  redefine it.

## Risk Classification

Risk flags:

- Auth — admin-only restore rehearsal, retention
  prune, and data-deletion paths.
- Authorization — owner/admin role gate for every new
  endpoint; tenant scope for the retention policy and
  the data-deletion path.
- Data model — new `backup_restore_runs` table, new
  `retention_policies` table, forward-only migration.
- Audit/security — every restore, retention prune,
  and data-deletion entry must carry a
  secret-safe payload and an audit entry; data
  deletion is irreversible and the slice refuses to
  run without an `accepted_by` and an `accepted_at`.
- External systems — the slice is local-first and
  single-host, but the restore path is a deployment
  decision and the slice must not commit to a
  particular object storage provider.
- Public contracts — new REST endpoints, new error
  codes, new operator panel widget; consumed by the
  same admin surfaces that already speak to the
  backup and runtime-readiness endpoints from
  `US-040`.
- Existing behavior — `US-040` `BackupSnapshot`,
  `US-041` `backup.stale` alert, and `US-026` audit
  log are adjacent; this story extends them, it does
  not redefine them.
- Weak proof — backup and restore is exactly the
  area where "we added tests" is not the same as "we
  can restore within the RTO window"; this story
  adds a dedicated rehearsal test that runs the full
  cycle and asserts the audit entry was written.
- Multi-domain — touches audit (`US-026`),
  observability (`US-041`), runtime readiness
  (`US-040`), and notification (`US-029`).

Hard gates:

- Any restore, retention prune, or data-deletion
  path that mutates product state without an
  `accepted_by` and an `accepted_at` recorded in the
  policy row.
- Any path that overwrites the production database
  while the application is in `pilot_live` or
  `test_like` mode.
- Any path that leaks a secret, a cookie, browser
  storage state, raw PII, or a full connection
  string through the restore rehearsal or the
  data-deletion entry.
- Any change that weakens the `SanitizeAlertPayload`
  contract from `US-041` or the audit retention
  guarantee from `NFR-SEC-008`.
- Any change that bypasses the existing
  `LaunchGateReport` from `US-040` or the
  `backup.stale` alert from `US-041`.

## Work Phases

1. Discovery — read `SPEC.md` §10.2 and §10.4, the
   `US-040` story packet, the `US-041` story packet,
   the `US-026` audit log contract, the `US-029`
   notification contract, and the
   `pilot-live-rollback-runbook.md` entry. Confirm
   the seams that the slice consumes are stable and
   reusable.
2. Design — define `BackupRestoreRun`, `RetentionPolicy`,
   `BackupRestoreService`, `RestoreRehearsalActor`,
   `PruneRetentionActor`, `DataDeletionService`, and
   `BuildRetentionPolicy` services. Lock the
   sanitization contract to the existing
   `SanitizeAlertPayload` helper from `US-041` and
   refuse any restore or deletion entry that fails
   the filter.
3. Validation planning — design a per-path test
   harness that runs a deterministic backup through
   the restore rehearsal, asserts the
   `backup_restore_runs` row, and asserts the
   `backup.restore.rehearsed` audit entry. Add a
   `POST /admin/backup-snapshots/{id}:restore:dry-run`
   smoke test that an admin can run from the
   operator panel.
4. Implementation — add the migrations, the domain
   models, the restore rehearsal actor, the retention
   prune actor, the data-deletion service, the admin
   endpoints, and the operator panel widget. Reuse
   the existing `SanitizeAlertPayload` helper; do
   not introduce a parallel redaction helper.
5. Verification — run unit, integration, E2E,
   security, operational, and platform checks
   defined in `validation.md`. Run the full
   rehearsal cycle and assert the bounded RTO target
   from `NFR-REL-005`.
6. Harness update — add the new product doc, the
   decision record, the durable story status, the
   `scripts/verify-us-043.sh` command, and a final
   trace. Capture any friction in the
   `harness_friction` field.

## Stop Conditions

Pause for human confirmation if:

- The story starts requiring a specific object
  storage provider (S3, GCS, Azure Blob) to meet the
  acceptance criteria. This slice is local-first and
  vendor-agnostic by design.
- Product direction becomes ambiguous between
  "local-first single-host baseline" and "ship a
  full vendor integration this cycle".
- Validation would need to weaken the
  `SanitizeAlertPayload` contract, the audit
  retention guarantee, or the existing
  `LaunchGateReport` from `US-040` to fit schedule.
- A new retention floor is needed that cannot be
  justified from `NFR-REL-005` or `NFR-SEC-008`; the
  floor must be deferred or added to the spec in the
  same story with explicit acceptance criteria.
- A later story wants to subscribe a paid external
  consumer (S3, GCS, Azure Blob) before this slice
  is implemented; in that case, the integration
  must wait until the local-first baseline is in
  place.
- The bounded restore path needs to overwrite the
  production database while the application is in
  `pilot_live` or `test_like` mode. The slice
  requires the application to be in `paused` mode
  before a real restore runs.
