# Validation

## Required Proof

| Layer | Expectation |
| --- | --- |
| Unit | `BackupRestoreService.schedule_rehearsal` enqueues a worker task through the existing Dramatiq broker and returns a `restore_run_id`. `BackupRestoreService.dry_run_restore` writes to a scratch location and refuses to write to the production database path. `BackupRestoreService.restore_backup` refuses to run without an `accepted_by` and refuses to overwrite the production database while the environment mode is `pilot_live` or `test_like`. `PruneRetentionActor` refuses to run without a `RetentionPolicy.accepted_by` and a `prune_enabled` flag. `DataDeletionService` refuses to run without an `accepted_by` and a `reason`. `SanitizeAlertPayload` from `US-041` strips keys, cookies, raw PII, browser storage state, and full connection strings from every payload before it is persisted. |
| Integration | `GET /admin/backup-snapshots/{id}` returns the snapshot plus the last `backup_restore_runs` row. `GET /admin/backup-restore-runs?status=&backup_id=` returns paginated restore history with sanitized payloads. `POST /admin/backup-snapshots/{id}:restore:dry-run` synchronously restores the backup into a scratch location and reports the result inline. `POST /admin/backup-snapshots/{id}:restore` refuses to run without an `accepted_by` and refuses to overwrite the production database while the environment mode is `pilot_live` or `test_like`. `POST /admin/retention/prune` refuses to run without a `RetentionPolicy.accepted_by` and a `prune_enabled` flag. `POST /admin/data-deletion` refuses to run without an `accepted_by` and a `reason`. Every restore, retention prune, and data-deletion attempt emits a durable audit entry with the same secret-safe payload contract as `US-026` and `US-041`. |
| E2E | An authenticated owner can open the new operator panel, see the most recent `BackupSnapshot` row, click `Dry-run restore`, see the result inline, and acknowledge the result. A bounded restore rehearsal records a backup, restores it into a scratch location, verifies the row count, and asserts the `backup.restore.rehearsed` audit entry was written. A retention prune is rejected when the policy `prune_enabled` flag is `false` and accepted when the flag is `true` and an `accepted_by` is recorded. A data deletion is rejected when the `accepted_by` or the `reason` is missing and accepted when both are present. |
| Security | Direct API calls to the new endpoints with viewer, analyst, sales, and reviewer sessions are rejected with the same error envelope as the existing admin surfaces. Sanitizer tests prove that payloads carrying API keys, cookies, raw PII, browser storage state, and full connection strings are rejected or redacted before persistence. The bounded restore path refuses to overwrite the production database while the environment mode is `pilot_live` or `test_like`. The retention prune refuses to run without a `RetentionPolicy.accepted_by`. The data deletion refuses to run without an `accepted_by` and a `reason`. The migration does not weaken the existing audit retention guarantee from `NFR-SEC-008`. |
| Operational | A runbook entry for the backup and restore domain documents what an operator does when a restore fails, when a backup is stale, and when a retention prune needs to be reversed. The verification script proves that the bounded restore path can restore a backup into a scratch location within the RTO target from `NFR-REL-005`. The retention prune respects the `NFR-SEC-008` audit retention floor. The data-deletion path emits a `data.*` audit entry for every attempt. |
| Platform | The `scripts/verify-us-043.sh` command wires the unit, integration, E2E, security, and operational checks together and is the same command run by `harness-cli story verify` and `harness-cli story verify-all`. The migration is exercised by the verify script so a missing `backup_restore_runs` or `retention_policies` table fails the platform check, not just the data check. |

## Suggested Checks

- Backend unit tests for:
  - `BackupRestoreService.schedule_rehearsal`
  - `BackupRestoreService.dry_run_restore`
  - `BackupRestoreService.restore_backup`
  - `PruneRetentionActor`
  - `DataDeletionService`
  - `SanitizeAlertPayload` reuse for every payload
  - Retention policy validation
  - Acceptance gate for restore, retention, and
    data-deletion
- Backend integration tests for:
  - `GET /admin/backup-snapshots/{id}`
  - `GET /admin/backup-restore-runs`
  - `POST /admin/backup-snapshots/{id}:restore:dry-run`
  - `POST /admin/backup-snapshots/{id}:restore`
  - `POST /admin/retention/prune`
  - `POST /admin/data-deletion`
  - Audit entries for every restore, retention
    prune, and data-deletion attempt
- E2E tests for:
  - Operator panel renders the most recent
    `BackupSnapshot` row, the last
    `backup_restore_runs` row, the retention
    policy, and the `Dry-run restore` button.
  - Bounded restore rehearsal records a backup,
    restores it into a scratch location, verifies
    the row count, and asserts the audit entry.
  - Retention prune is rejected when the
    `prune_enabled` flag is `false`.
  - Data deletion is rejected when the
    `accepted_by` or the `reason` is missing.
- Security tests for:
  - Role enforcement on every new endpoint.
  - Payload sanitization for every new write path.
  - Restore, retention, and data-deletion
    acceptance gates.
- Operational checks for:
  - Restore rehearsal respects the RTO target from
    `NFR-REL-005`.
  - Retention prune respects the audit retention
    floor from `NFR-SEC-008`.
  - The runbook entry exists and references the
    right surfaces.
- Platform proof is the
  `scripts/verify-us-043.sh` command wired into
  `harness-cli story verify` and
  `harness-cli story verify-all`.

## Evidence Hooks

- `tests/unit/test_backup_restore_service.py` —
  service unit tests
- `tests/unit/test_retention_policy.py` — retention
  policy validation
- `tests/unit/test_data_deletion_service.py` —
  data-deletion service
- `tests/integration/test_backup_restore_api.py`
- `tests/integration/test_retention_prune_api.py`
- `tests/integration/test_data_deletion_api.py`
- `tests/security/test_backup_restore_role_gates.py`
- `tests/e2e/backup_restore_rehearsal.py`
- `frontend/e2e/backup-restore-panel.spec.ts`
- `scripts/verify-us-043.sh`
- `docs/ops/backup-restore-runbook.md`
  (operational entry)
- `docs/product/backup-and-restore-operations.md`
  (living product contract)
- `docs/decisions/0021-backup-and-restore-operations-baseline.md`
  (durable decision record)

## Open Questions

- Should the bounded restore path support
  point-in-time recovery against a transaction-log
  backup, or is a full-database restore the only
  supported flow? The first implementation supports
  full-database restore only.
- Should the data-deletion path cascade across
  related records (a lead's activities, a user's
  notifications), or should the caller be
  responsible for the cascade? The first
  implementation marks related records as
  `anonymized` or `redacted` and emits a separate
  audit entry for each cascade step.
- Should the retention prune support a dry-run
  mode that lists the rows it would delete without
  actually deleting them? The first implementation
  refuses to add a dry-run mode; the bounded
  retention path requires an `accepted_by` and the
  prune is the only supported flow.
- Should the bounded restore path require a
  second-owner confirmation, similar to the
  tenant-deletion path? The first implementation
  refuses to add a second-owner confirmation; the
  `accepted_by` is the single acceptance gate.
- Should the bounded restore path support restoring
  into a different schema (for example, a
  per-tenant schema)? The first implementation
  refuses to add per-tenant schemas; the restore
  path restores the entire database.
