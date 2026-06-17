"""Backup restore and retention repositories (US-043).

The repository layer is the only place in the
application that talks to the SQLAlchemy rows for
`backup_restore_runs` and `retention_policies`. Domain
code consumes the pure dataclasses from
`livelead.domain.backup.models`; the interfaces layer
wraps them in Pydantic schemas.

The repositories deliberately store the `error` column
as nullable TEXT so a failed restore can record the
error message without leaking secret material. The
sanitization contract is enforced by the application
service through the `SanitizeAlertPayload` helper
from `US-041`.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.backup.enums import RestoreMode, RestoreRunStatus
from livelead.domain.backup.models import (
    BackupRestoreRun,
    RetentionPolicy,
)
from livelead.infrastructure.db.models import (
    BackupRestoreRunRow,
    RetentionPolicyRow,
)

logger = logging.getLogger("livelead.backup_restore_repo")


# ---------------------------------------------------------------------------
# Mappers
# ---------------------------------------------------------------------------


def _status_from_string(value: str | None) -> RestoreRunStatus:
    if not value:
        return RestoreRunStatus.PENDING
    try:
        return RestoreRunStatus(value)
    except ValueError:
        return RestoreRunStatus.FAILED


def _mode_from_string(value: str | None) -> RestoreMode:
    if not value:
        return RestoreMode.DRY_RUN
    try:
        return RestoreMode(value)
    except ValueError:
        return RestoreMode.DRY_RUN


def row_to_backup_restore_run(row: BackupRestoreRunRow) -> BackupRestoreRun:
    return BackupRestoreRun(
        id=row.id,
        organization_id=row.organization_id,
        backup_id=row.backup_id,
        started_at=row.started_at,
        completed_at=row.completed_at,
        status=_status_from_string(row.status),
        mode=_mode_from_string(row.mode),
        target_location=row.target_location or "",
        manifest_hash=row.manifest_hash or "",
        row_count=int(row.row_count or 0),
        audit_correlation_id=row.audit_correlation_id or "",
        error=row.error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def row_to_retention_policy(row: RetentionPolicyRow) -> RetentionPolicy:
    return RetentionPolicy(
        organization_id=row.organization_id,
        backup_retention_days=int(row.backup_retention_days or 30),
        audit_retention_days=int(row.audit_retention_days or 90),
        prune_enabled=bool(row.prune_enabled),
        accepted_by=row.accepted_by,
        accepted_at=row.accepted_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
)


# ---------------------------------------------------------------------------
# Backup restore run repository
# ---------------------------------------------------------------------------


class BackupRestoreRunRepository:
    """Persistence boundary for `backup_restore_runs`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def add(
        self,
        *,
        organization_id: UUID | str,
        backup_id: str,
        started_at: datetime,
        mode: RestoreMode,
        target_location: str,
        audit_correlation_id: str = "",
    ) -> BackupRestoreRun:
        row = BackupRestoreRunRow(
            organization_id=str(organization_id),
            backup_id=backup_id,
            started_at=started_at,
            status=RestoreRunStatus.PENDING.value,
            mode=mode.value,
            target_location=target_location,
            manifest_hash="",
            row_count=0,
            audit_correlation_id=audit_correlation_id,
            error=None,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_backup_restore_run(row)

    async def get(self, run_id: str) -> BackupRestoreRun | None:
        r = await self._session.execute(
            select(BackupRestoreRunRow).where(BackupRestoreRunRow.id == run_id)
        )
        row = r.scalar_one_or_none()
        return row_to_backup_restore_run(row) if row else None

    async def list_for_org(
        self,
        organization_id: UUID | str,
        *,
        status: RestoreRunStatus | str | None = None,
        backup_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BackupRestoreRun], int]:
        filters = [BackupRestoreRunRow.organization_id == str(organization_id)]
        if status is not None:
            status_value = status.value if isinstance(status, RestoreRunStatus) else str(status)
            filters.append(BackupRestoreRunRow.status == status_value)
        if backup_id is not None:
            filters.append(BackupRestoreRunRow.backup_id == backup_id)
        where_clause = and_(*filters)
        total_r = await self._session.execute(
            select(func.count(BackupRestoreRunRow.id)).where(where_clause)
        )
        total = int(total_r.scalar_one() or 0)
        rows = (
            await self._session.execute(
                select(BackupRestoreRunRow)
                .where(where_clause)
                .order_by(desc(BackupRestoreRunRow.started_at))
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()
        return [row_to_backup_restore_run(r) for r in rows], total

    async def latest_for_backup(
        self, organization_id: UUID | str, backup_id: str
    ) -> BackupRestoreRun | None:
        r = await self._session.execute(
            select(BackupRestoreRunRow)
            .where(
                and_(
                    BackupRestoreRunRow.organization_id == str(organization_id),
                    BackupRestoreRunRow.backup_id == backup_id,
                )
            )
            .order_by(desc(BackupRestoreRunRow.started_at))
            .limit(1)
        )
        row = r.scalar_one_or_none()
        return row_to_backup_restore_run(row) if row else None

    async def complete(
        self,
        run_id: str,
        *,
        status: RestoreRunStatus,
        completed_at: datetime | None = None,
        manifest_hash: str = "",
        row_count: int = 0,
        error: str | None = None,
    ) -> BackupRestoreRun | None:
        r = await self._session.execute(
            select(BackupRestoreRunRow).where(BackupRestoreRunRow.id == run_id)
        )
        row = r.scalar_one_or_none()
        if row is None:
            return None
        row.status = status.value
        row.completed_at = completed_at or datetime.utcnow()
        row.manifest_hash = manifest_hash
        row.row_count = int(row_count)
        row.error = error
        row.updated_at = datetime.utcnow()
        await self._session.flush()
        return row_to_backup_restore_run(row)


# ---------------------------------------------------------------------------
# Retention policy repository
# ---------------------------------------------------------------------------


class RetentionPolicyRepository:
    """Persistence boundary for `retention_policies`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def get(self, organization_id: UUID | str) -> RetentionPolicy | None:
        r = await self._session.execute(
            select(RetentionPolicyRow).where(
                RetentionPolicyRow.organization_id == str(organization_id)
            )
        )
        row = r.scalar_one_or_none()
        return row_to_retention_policy(row) if row else None

    async def get_or_default(
        self, organization_id: UUID | str
    ) -> RetentionPolicy:
        existing = await self.get(organization_id)
        if existing is not None:
            return existing
        return RetentionPolicy(organization_id=str(organization_id))

    async def upsert(
        self,
        *,
        organization_id: UUID | str,
        policy: RetentionPolicy,
    ) -> RetentionPolicy:
        row = await self._session.execute(
            select(RetentionPolicyRow).where(
                RetentionPolicyRow.organization_id == str(organization_id)
            )
        )
        row = row.scalar_one_or_none()
        now = datetime.utcnow()
        if row is None:
            row = RetentionPolicyRow(
                organization_id=str(organization_id),
                backup_retention_days=int(policy.backup_retention_days),
                audit_retention_days=int(policy.audit_retention_days),
                prune_enabled=bool(policy.prune_enabled),
                accepted_by=policy.accepted_by,
                accepted_at=policy.accepted_at,
                created_at=now,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.backup_retention_days = int(policy.backup_retention_days)
            row.audit_retention_days = int(policy.audit_retention_days)
            row.prune_enabled = bool(policy.prune_enabled)
            row.accepted_by = policy.accepted_by
            row.accepted_at = policy.accepted_at
            row.updated_at = now
        await self._session.flush()
        return row_to_retention_policy(row)


__all__ = [
    "BackupRestoreRunRepository",
    "RetentionPolicyRepository",
    "row_to_backup_restore_run",
    "row_to_retention_policy",
]
