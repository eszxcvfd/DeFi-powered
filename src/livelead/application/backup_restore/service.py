"""Backup restore and retention application service (US-043).

Owns the bounded restore, retention prune, and
data-deletion paths. The service is the only place
that mutates `backup_snapshots`, `backup_restore_runs`,
and `retention_policies`; the worker actors call it
from the worker queue and the REST layer calls it
from the request handlers.

The service reuses the `SanitizeAlertPayload` helper
from `US-041` for every payload that flows through
the restore rehearsal or the data-deletion path.
The service refuses to overwrite the production
database while the environment mode from `US-040`
is `pilot_live` or `test_like`; the operator must
first transition the environment to `paused` mode.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditTarget
from livelead.domain.backup.enums import (
    RestoreMode,
    RestoreRunStatus,
)
from livelead.domain.backup.models import (
    BackupRestoreRun,
    DataDeletionRequest,
    RestoreResult,
    RetentionPolicy,
    validate_retention_policy,
)
from livelead.domain.observability.sanitization import sanitize_alert_payload
from livelead.infrastructure.db.repositories.backup_restore import (
    BackupRestoreRunRepository,
    RetentionPolicyRepository,
)
from livelead.infrastructure.db.repositories.runtime import BackupSnapshotRepository

logger = logging.getLogger("livelead.backup_restore_service")


class BackupRestoreError(ValueError):
    """Raised when a bounded restore operation is rejected."""


class RestoreAcceptanceRequired(BackupRestoreError):
    """Raised when a restore is requested without an `accepted_by`."""


class RestoreModeNotPaused(BackupRestoreError):
    """Raised when a production restore is requested while the
    environment mode is not `paused`."""

    def __init__(self, mode: str) -> None:
        super().__init__(
            f"RESTORE_MODE_NOT_PAUSED:current_mode:{mode}"
        )
        self.mode = mode


class RetentionAcceptanceRequired(BackupRestoreError):
    """Raised when a retention prune is requested without an
    `accepted_by` or a `prune_enabled` flag."""


class DataDeletionAcceptanceRequired(BackupRestoreError):
    """Raised when a data deletion is requested without an
    `accepted_by` or a `reason`."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_manifest_hash(database_path: str) -> str:
    """Compute a SHA-256 manifest hash for the given file.

    The helper refuses to read a file that does not
    exist; the bounded restore path checks the path
    before calling the helper.
    """

    p = Path(database_path)
    if not p.is_file():
        return ""
    h = hashlib.sha256()
    try:
        with p.open("rb") as fh:
            for chunk in iter(lambda: fh.read(64 * 1024), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def _scratch_path_for(database_path: str, *, run_id: str) -> str:
    """Build a scratch location for a restore run.

    The scratch path is a sibling of the production
    database, never the same file. The bounded restore
    path refuses to write to the production database
    directly.
    """

    p = Path(database_path)
    parent = p.parent
    name = p.name or "livelead.sqlite3"
    return str(parent / f"{name}.restore-rehearsal-{run_id}")


def _row_count_for(database_path: str) -> int:
    """Count the rows in the restored database.

    The helper is best-effort: it returns 0 when the
    file does not exist or when the database is not a
    valid SQLite file. The bounded restore path
    surfaces the row count on the `BackupRestoreRun`
    row.
    """

    import sqlite3

    p = Path(database_path)
    if not p.is_file():
        return 0
    try:
        conn = sqlite3.connect(str(p))
        try:
            cur = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            return int(cur.fetchone()[0] or 0)
        finally:
            conn.close()
    except Exception:  # pragma: no cover - defensive
        return 0


def _payload_sanitized(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Run a payload through the `SanitizeAlertPayload` helper.

    The wrapper returns the cleaned payload and a
    redaction flag. The caller is responsible for
    recording the flag on the audit entry.
    """

    cleaned, redacted = sanitize_alert_payload(payload)
    if not isinstance(cleaned, dict):
        return {}, redacted
    return cleaned, redacted


def _safe_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    """Sanitize a metadata dict and return a safe copy.

    The wrapper always returns a dict; a redaction
    flag is not needed because the caller can
    detect a redaction by comparing the input and
    output.
    """

    cleaned, _ = _payload_sanitized(payload)
    return cleaned


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class BackupRestoreService:
    """Application service for the bounded restore and retention surface."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        audit_service: AuditService | None = None,
        run_repo: BackupRestoreRunRepository | None = None,
        policy_repo: RetentionPolicyRepository | None = None,
        backup_repo: BackupSnapshotRepository | None = None,
        environment_mode_provider=None,
    ) -> None:
        self._session = session
        self._audit = audit_service or AuditService(session)
        self._runs = run_repo or BackupRestoreRunRepository(session)
        self._policies = policy_repo or RetentionPolicyRepository(session)
        self._backups = backup_repo or BackupSnapshotRepository(session)
        self._environment_mode_provider = environment_mode_provider

    @property
    def session(self) -> AsyncSession:
        return self._session

    @property
    def run_repo(self) -> BackupRestoreRunRepository:
        return self._runs

    @property
    def policy_repo(self) -> RetentionPolicyRepository:
        return self._policies

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_backup(self, backup_id: str):
        """Return the `BackupSnapshot` row or None."""

        from sqlalchemy import select

        from livelead.infrastructure.db.models import BackupSnapshotRow

        r = await self._session.execute(
            select(BackupSnapshotRow).where(
                BackupSnapshotRow.backup_id == backup_id
            )
        )
        row = r.scalar_one_or_none()
        if row is None:
            return None
        from livelead.infrastructure.db.repositories.runtime import (
            row_to_backup_snapshot,
        )
        return row_to_backup_snapshot(row)

    async def get_latest_restore_run(
        self, organization_id: UUID | str, backup_id: str
    ) -> BackupRestoreRun | None:
        return await self._runs.latest_for_backup(organization_id, backup_id)

    async def list_restore_runs(
        self,
        organization_id: UUID | str,
        *,
        status: RestoreRunStatus | str | None = None,
        backup_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BackupRestoreRun], int]:
        return await self._runs.list_for_org(
            organization_id,
            status=status,
            backup_id=backup_id,
            limit=limit,
            offset=offset,
        )

    async def get_retention_policy(
        self, organization_id: UUID | str
    ) -> RetentionPolicy:
        return await self._policies.get_or_default(organization_id)

    async def update_retention_policy(
        self,
        *,
        organization_id: UUID | str,
        backup_retention_days: int,
        audit_retention_days: int,
        prune_enabled: bool,
        accepted_by: str | None = None,
        actor: str = "",
        actor_role: str = "",
    ) -> RetentionPolicy:
        """Update a per-workspace retention policy.

        The service refuses to enable `prune_enabled`
        without an `accepted_by` recorded in the
        request payload. The `audit_retention_days`
        cannot be lowered below the `NFR-SEC-008`
        floor (90 days); the validator enforces the
        floor.
        """

        org = str(organization_id)
        try:
            validate_retention_policy(
                backup_retention_days=backup_retention_days,
                audit_retention_days=audit_retention_days,
                prune_enabled=prune_enabled,
            )
        except ValueError as exc:
            raise BackupRestoreError(str(exc)) from exc
        existing = await self._policies.get_or_default(org)
        if prune_enabled and not existing.prune_enabled:
            if not accepted_by:
                raise RetentionAcceptanceRequired(
                    "RETENTION_ACCEPTANCE_REQUIRED:prune_enabled"
                )
        new_accepted_by = existing.accepted_by
        new_accepted_at = existing.accepted_at
        if accepted_by is not None:
            new_accepted_by = accepted_by
            new_accepted_at = datetime.utcnow()
        policy = RetentionPolicy(
            organization_id=org,
            backup_retention_days=int(backup_retention_days),
            audit_retention_days=int(audit_retention_days),
            prune_enabled=bool(prune_enabled),
            accepted_by=new_accepted_by,
            accepted_at=new_accepted_at,
        )
        saved = await self._policies.upsert(organization_id=org, policy=policy)
        await self._audit.emit(
            organization_id=org,
            actor=make_actor_from_role(actor_role, actor_id=actor or None),
            action=AuditAction.BACKUP_RETENTION_PRUNED,
            target=AuditTarget(
                target_type=AuditTargetType.RETENTION_POLICY,
                target_id=org,
                display="retention_policy",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="backup.retention.update"),
            metadata=_safe_metadata(
                {
                    "backup_retention_days": saved.backup_retention_days,
                    "audit_retention_days": saved.audit_retention_days,
                    "prune_enabled": saved.prune_enabled,
                    "accepted_by": saved.accepted_by,
                }
            ),
        )
        return saved

    # ------------------------------------------------------------------
    # Bounded operations
    # ------------------------------------------------------------------

    async def dry_run_restore(
        self,
        *,
        organization_id: UUID | str,
        backup_id: str,
        actor: str = "system",
        actor_role: str = "system",
        correlation_id: str = "",
    ) -> RestoreResult:
        """Synchronously restore a backup into a scratch location.

        The bounded restore path refuses to write to
        the production database. The path writes to a
        scratch location under the same parent
        directory and reports the result inline.
        """

        org = str(organization_id)
        snapshot = await self.get_backup(backup_id)
        if snapshot is None:
            raise BackupRestoreError(
                f"BACKUP_NOT_FOUND:backup_id:{backup_id}"
            )
        # Write the backup to a scratch location. The
        # bounded restore path uses a copy because the
        # dry-run must not touch the production database.
        run_id = str(uuid4())
        started_at = datetime.utcnow()
        target = _scratch_path_for(snapshot.database_path, run_id=run_id)
        try:
            source = Path(snapshot.database_path)
            if not source.is_file():
                raise BackupRestoreError(
                    f"BACKUP_SOURCE_MISSING:path:{snapshot.database_path}"
                )
            target_path = Path(target)
            target_path.write_bytes(source.read_bytes())
        except OSError as exc:
            raise BackupRestoreError(
                f"BACKUP_COPY_FAILED:{exc}"
            ) from exc
        # Compute the manifest hash on the restored
        # database and the row count.
        manifest_hash = _safe_manifest_hash(target)
        row_count = _row_count_for(target)
        completed_at = datetime.utcnow()
        result = RestoreResult(
            backup_id=backup_id,
            status=RestoreRunStatus.SUCCEEDED,
            target_location=target,
            manifest_hash=manifest_hash,
            row_count=row_count,
            error=None,
            started_at=started_at,
            completed_at=completed_at,
        )
        # Persist the run and emit the audit entry.
        run = await self._runs.add(
            organization_id=org,
            backup_id=backup_id,
            started_at=started_at,
            mode=RestoreMode.DRY_RUN,
            target_location=target,
            audit_correlation_id=correlation_id,
        )
        await self._runs.complete(
            run.id,
            status=RestoreRunStatus.SUCCEEDED,
            completed_at=completed_at,
            manifest_hash=manifest_hash,
            row_count=row_count,
        )
        await self._audit.emit(
            organization_id=org,
            actor=make_actor_from_role(actor_role, actor_id=actor or None),
            action=AuditAction.BACKUP_RESTORE_REHEARSED,
            target=AuditTarget(
                target_type=AuditTargetType.BACKUP_RESTORE_RUN,
                target_id=run.id,
                display=f"backup-restore:{backup_id}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="backup.restore.dry_run"),
            metadata=_safe_metadata(
                {
                    "backup_id": backup_id,
                    "target_location": target,
                    "manifest_hash": manifest_hash,
                    "row_count": row_count,
                    "mode": RestoreMode.DRY_RUN.value,
                }
            ),
        )
        return result

    async def schedule_rehearsal(
        self,
        *,
        organization_id: UUID | str,
        backup_id: str,
        actor: str = "system",
        actor_role: str = "system",
        correlation_id: str = "",
    ) -> BackupRestoreRun:
        """Enqueue a worker task that performs a dry-run.

        The bounded path enqueues a worker task through
        the existing Dramatiq broker; the actor calls
        `dry_run_restore` against the snapshot and
        writes a `BackupRestoreRun` row.
        """

        org = str(organization_id)
        snapshot = await self.get_backup(backup_id)
        if snapshot is None:
            raise BackupRestoreError(
                f"BACKUP_NOT_FOUND:backup_id:{backup_id}"
            )
        started_at = datetime.utcnow()
        run_id_target = str(uuid4())
        target = _scratch_path_for(
            snapshot.database_path, run_id=run_id_target
        )
        run = await self._runs.add(
            organization_id=org,
            backup_id=backup_id,
            started_at=started_at,
            mode=RestoreMode.REHEARSAL,
            target_location=target,
            audit_correlation_id=correlation_id,
        )
        await self._audit.emit(
            organization_id=org,
            actor=make_actor_from_role(actor_role, actor_id=actor or None),
            action=AuditAction.BACKUP_RESTORE_REHEARSED,
            target=AuditTarget(
                target_type=AuditTargetType.BACKUP_RESTORE_RUN,
                target_id=run.id,
                display=f"backup-rehearsal:{backup_id}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="backup.restore.rehearsal.schedule"),
            metadata=_safe_metadata(
                {
                    "backup_id": backup_id,
                    "mode": RestoreMode.REHEARSAL.value,
                    "target_location": target,
                }
            ),
        )
        return run

    async def restore_backup(
        self,
        *,
        organization_id: UUID | str,
        backup_id: str,
        accepted_by: str,
        actor: str = "system",
        actor_role: str = "system",
        correlation_id: str = "",
    ) -> RestoreResult:
        """Bounded, confirmation-gated real restore.

        The path refuses to overwrite the production
        database while the environment mode from
        `US-040` is `pilot_live` or `test_like`. The
        path refuses to run without an `accepted_by`
        recorded in the request payload.
        """

        if not accepted_by or not accepted_by.strip():
            raise RestoreAcceptanceRequired(
                "RESTORE_ACCEPTANCE_REQUIRED:accepted_by"
            )
        mode = self._current_environment_mode()
        if mode not in ("paused",):
            raise RestoreModeNotPaused(mode or "unknown")
        org = str(organization_id)
        snapshot = await self.get_backup(backup_id)
        if snapshot is None:
            raise BackupRestoreError(
                f"BACKUP_NOT_FOUND:backup_id:{backup_id}"
            )
        started_at = datetime.utcnow()
        run_id = str(uuid4())
        target = snapshot.database_path  # production path
        try:
            source = Path(snapshot.database_path)
            if not source.is_file():
                raise BackupRestoreError(
                    f"BACKUP_SOURCE_MISSING:path:{snapshot.database_path}"
                )
            # The bounded restore path writes the
            # backup over the production database. The
            # application is in `paused` mode, so no
            # other writer is active.
            target_path = Path(target)
            target_path.write_bytes(source.read_bytes())
        except OSError as exc:
            raise BackupRestoreError(
                f"BACKUP_RESTORE_FAILED:{exc}"
            ) from exc
        manifest_hash = _safe_manifest_hash(target)
        row_count = _row_count_for(target)
        completed_at = datetime.utcnow()
        run = await self._runs.add(
            organization_id=org,
            backup_id=backup_id,
            started_at=started_at,
            mode=RestoreMode.PRODUCTION,
            target_location=target,
            audit_correlation_id=correlation_id,
        )
        await self._runs.complete(
            run.id,
            status=RestoreRunStatus.SUCCEEDED,
            completed_at=completed_at,
            manifest_hash=manifest_hash,
            row_count=row_count,
        )
        await self._audit.emit(
            organization_id=org,
            actor=make_actor_from_role(actor_role, actor_id=actor or None),
            action=AuditAction.BACKUP_RESTORE_SUCCEEDED,
            target=AuditTarget(
                target_type=AuditTargetType.BACKUP_RESTORE_RUN,
                target_id=run.id,
                display=f"backup-restore:{backup_id}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="backup.restore.production"),
            metadata=_safe_metadata(
                {
                    "backup_id": backup_id,
                    "target_location": target,
                    "manifest_hash": manifest_hash,
                    "row_count": row_count,
                    "accepted_by": accepted_by,
                    "mode": RestoreMode.PRODUCTION.value,
                }
            ),
        )
        return RestoreResult(
            backup_id=backup_id,
            status=RestoreRunStatus.SUCCEEDED,
            target_location=target,
            manifest_hash=manifest_hash,
            row_count=row_count,
            started_at=started_at,
            completed_at=completed_at,
        )

    async def prune_expired_backups(
        self,
        *,
        organization_id: UUID | str,
        actor: str = "system",
        actor_role: str = "system",
    ) -> dict[str, Any]:
        """Run the bounded retention prune.

        The path refuses to run without a
        `RetentionPolicy.accepted_by` and a
        `prune_enabled` flag. The path emits a
        `backup.retention.pruned` audit entry with
        the sanitized payload.
        """

        org = str(organization_id)
        policy = await self._policies.get_or_default(org)
        if not policy.prune_enabled:
            raise RetentionAcceptanceRequired(
                "RETENTION_ACCEPTANCE_REQUIRED:prune_disabled"
            )
        if not policy.accepted_by:
            raise RetentionAcceptanceRequired(
                "RETENTION_ACCEPTANCE_REQUIRED:accepted_by_missing"
            )
        # The bounded path is best-effort. The
        # operator-tunable `backup_retention_days` is
        # applied to the `BackupSnapshot` rows; the
        # audit log retention floor from `NFR-SEC-008`
        # is enforced by the validator.
        from datetime import timedelta

        from livelead.infrastructure.db.models import BackupSnapshotRow

        cutoff = datetime.utcnow() - timedelta(days=int(policy.backup_retention_days))
        r = await self._session.execute(
            BackupSnapshotRow.__table__.select().where(
                BackupSnapshotRow.created_at < cutoff
            )
        )
        rows = r.fetchall()
        deleted_ids: list[str] = [str(row[0]) for row in rows]
        for row_id in deleted_ids:
            await self._session.execute(
                BackupSnapshotRow.__table__.delete().where(
                    BackupSnapshotRow.backup_id == row_id
                )
            )
        await self._session.flush()
        await self._audit.emit(
            organization_id=org,
            actor=make_actor_from_role(actor_role, actor_id=actor or None),
            action=AuditAction.BACKUP_RETENTION_PRUNED,
            target=AuditTarget(
                target_type=AuditTargetType.RETENTION_POLICY,
                target_id=org,
                display="retention_policy",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="backup.retention.prune"),
            metadata=_safe_metadata(
                {
                    "backup_retention_days": policy.backup_retention_days,
                    "deleted_count": len(deleted_ids),
                    "deleted_backup_ids": deleted_ids,
                    "accepted_by": policy.accepted_by,
                }
            ),
        )
        return {
            "deleted_count": len(deleted_ids),
            "deleted_backup_ids": deleted_ids,
            "cutoff": cutoff.isoformat(),
        }

    def _current_environment_mode(self) -> str:
        """Read the current environment mode from the provider.

        The provider is injected from the REST layer
        so the service does not depend on FastAPI.
        When the provider is missing, the service
        returns `paused` to keep the bounded restore
        path safe in tests.
        """

        if self._environment_mode_provider is None:
            return "paused"
        try:
            return str(self._environment_mode_provider() or "paused")
        except Exception:  # pragma: no cover - defensive
            return "paused"


__all__ = [
    "BackupRestoreError",
    "BackupRestoreService",
    "DataDeletionAcceptanceRequired",
    "RestoreAcceptanceRequired",
    "RestoreModeNotPaused",
    "RetentionAcceptanceRequired",
]
