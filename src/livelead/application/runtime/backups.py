"""Backup-snapshot application service (US-040).

Records backup metadata, lists recent snapshots, and supports
verification transitions. The service does not perform the actual
filesystem copy — operators (or a backup script) record a snapshot
after the copy has succeeded, then mark verification outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

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
from livelead.domain.runtime.enums import (
    BackupFreshness,
    BackupVerificationStatus,
)
from livelead.domain.runtime.models import BackupSnapshot
from livelead.infrastructure.db.repositories.runtime import BackupSnapshotRepository


class BackupServiceError(ValueError):
    """Raised when a backup operation is rejected."""


@dataclass(frozen=True, slots=True)
class BackupSummary:
    snapshot: BackupSnapshot
    freshness: BackupFreshness


class BackupService:
    def __init__(
        self,
        session,
        *,
        audit_service: AuditService,
        backup_max_age_hours: float,
    ) -> None:
        self._session = session
        self._audit = audit_service
        self._max_age_hours = float(backup_max_age_hours)
        self._repo = BackupSnapshotRepository(session)

    async def record_snapshot(
        self,
        *,
        organization_id: UUID,
        backup_id: str,
        database_path: str,
        notes: str = "",
        actor: str = "",
        actor_role: str = "",
    ) -> BackupSnapshot:
        if not backup_id or not backup_id.strip():
            raise BackupServiceError("backup_id is required")
        if not database_path or not database_path.strip():
            raise BackupServiceError("database_path is required")
        size = _safe_size(database_path)
        snapshot = BackupSnapshot(
            backup_id=backup_id,
            created_at=datetime.now(UTC),
            database_path=database_path,
            database_size_bytes=size,
            verification_status=BackupVerificationStatus.RECORDED,
            notes=notes or "",
            recorded_by=actor or "",
        )
        stored = await self._repo.add(snapshot)
        await self._audit.emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor_role, actor_id=actor or actor_role),
            action=AuditAction.BACKUP_SNAPSHOT_RECORDED,
            target=AuditTarget(
                target_type=AuditTargetType.BACKUP_SNAPSHOT,
                target_id=stored.backup_id,
                display=f"backup:{stored.backup_id}",
            ),
            outcome=AuditOutcome.SUCCEEDED,
            context=make_context(workflow="backup"),
            metadata={
                "backup_id": stored.backup_id,
                "verification_status": stored.verification_status.value,
                "database_size_bytes": stored.database_size_bytes,
            },
        )
        return stored

    async def verify_snapshot(
        self,
        *,
        organization_id: UUID,
        backup_id: str,
        status: BackupVerificationStatus,
        actor: str = "",
        actor_role: str = "",
    ) -> BackupSnapshot:
        updated = await self._repo.update_verification(
            backup_id, status=status, actor=actor or actor_role
        )
        if updated is None:
            raise BackupServiceError(f"unknown backup_id={backup_id}")
        action = (
            AuditAction.BACKUP_SNAPSHOT_VERIFIED
            if status == BackupVerificationStatus.VERIFIED_RESTORE
            else AuditAction.BACKUP_SNAPSHOT_FAILED
        )
        outcome = (
            AuditOutcome.SUCCEEDED
            if status == BackupVerificationStatus.VERIFIED_RESTORE
            else AuditOutcome.FAILED
        )
        await self._audit.emit(
            organization_id=organization_id,
            actor=make_actor_from_role(actor_role, actor_id=actor or actor_role),
            action=action,
            target=AuditTarget(
                target_type=AuditTargetType.BACKUP_SNAPSHOT,
                target_id=updated.backup_id,
                display=f"backup:{updated.backup_id}",
            ),
            outcome=outcome,
            context=make_context(workflow="backup"),
            metadata={
                "backup_id": updated.backup_id,
                "verification_status": updated.verification_status.value,
            },
        )
        return updated

    async def list_recent(self, *, limit: int = 20) -> list[BackupSummary]:
        snapshots = await self._repo.list_recent(limit=limit)
        return [
            BackupSummary(
                snapshot=s,
                freshness=s.freshness(max_age_hours=self._max_age_hours),
            )
            for s in snapshots
        ]

    async def latest_summary(self) -> BackupSummary | None:
        snapshot = await self._repo.latest()
        if snapshot is None:
            return None
        return BackupSummary(
            snapshot=snapshot,
            freshness=snapshot.freshness(max_age_hours=self._max_age_hours),
        )

    async def fresh_snapshot_count(self) -> int:
        return await self._repo.count_verified_or_recorded()

    async def total_snapshot_count(self) -> int:
        return await self._repo.count()


def _safe_size(path: str) -> int:
    try:
        p = Path(path)
        if p.is_file():
            return p.stat().st_size
    except OSError:
        return 0
    return 0
