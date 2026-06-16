"""Runtime cutover repositories (US-040)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.runtime.enums import (
    BackupVerificationStatus,
    CutoverAction,
    EnvironmentMode,
    LiveIntegration,
    LiveToggleState,
)
from livelead.domain.runtime.models import (
    BackupSnapshot,
    CutoverEvent,
    LiveIntegrationToggle,
    WorkerHeartbeat,
)
from livelead.infrastructure.db.models import (
    BackupSnapshotRow,
    CutoverEventRow,
    LiveIntegrationToggleRow,
    WorkerHeartbeatRow,
)


# ---- Mappers ---------------------------------------------------------------


def row_to_backup_snapshot(row: BackupSnapshotRow) -> BackupSnapshot:
    return BackupSnapshot(
        backup_id=row.backup_id,
        created_at=row.created_at,
        database_path=row.database_path,
        database_size_bytes=int(row.database_size_bytes or 0),
        verification_status=BackupVerificationStatus(row.verification_status),
        notes=row.notes or "",
        recorded_by=row.recorded_by or "",
        verified_at=row.verified_at,
        verified_by=row.verified_by,
    )


def row_to_live_toggle(row: LiveIntegrationToggleRow) -> LiveIntegrationToggle:
    return LiveIntegrationToggle(
        integration=LiveIntegration(row.integration),
        state=LiveToggleState(row.state),
        updated_at=row.updated_at,
        updated_by=row.updated_by or "",
        approval_note=row.approval_note or "",
        previous_state=LiveToggleState(row.previous_state or LiveToggleState.DISABLED.value),
    )


def row_to_cutover_event(row: CutoverEventRow) -> CutoverEvent:
    return CutoverEvent(
        event_id=row.event_id,
        action=CutoverAction(row.action),
        previous_mode=EnvironmentMode(row.previous_mode),
        new_mode=EnvironmentMode(row.new_mode),
        actor=row.actor or "",
        reason=row.reason or "",
        occurred_at=row.occurred_at,
        notes=row.notes or "",
        gate_passed=bool(row.gate_passed),
        gate_summary=row.gate_summary or "",
    )


def row_to_worker_heartbeat(row: WorkerHeartbeatRow) -> WorkerHeartbeat:
    return WorkerHeartbeat(
        worker_id=row.worker_id,
        last_seen=row.last_seen,
        last_task=row.last_task or "",
        detail=row.detail or "",
    )


# ---- Backup snapshots ------------------------------------------------------


class BackupSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, snapshot: BackupSnapshot) -> BackupSnapshot:
        row = BackupSnapshotRow(
            backup_id=snapshot.backup_id,
            created_at=snapshot.created_at,
            database_path=snapshot.database_path,
            database_size_bytes=snapshot.database_size_bytes,
            verification_status=snapshot.verification_status.value,
            notes=snapshot.notes or "",
            recorded_by=snapshot.recorded_by or "",
            verified_at=snapshot.verified_at,
            verified_by=snapshot.verified_by,
            source="operator",
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_backup_snapshot(row)

    async def update_verification(
        self,
        backup_id: str,
        *,
        status: BackupVerificationStatus,
        actor: str,
        verified_at: datetime | None = None,
    ) -> BackupSnapshot | None:
        r = await self._session.execute(
            select(BackupSnapshotRow).where(BackupSnapshotRow.backup_id == backup_id)
        )
        row = r.scalar_one_or_none()
        if row is None:
            return None
        row.verification_status = status.value
        row.verified_by = actor
        row.verified_at = verified_at or datetime.utcnow()
        await self._session.flush()
        return row_to_backup_snapshot(row)

    async def list_recent(self, *, limit: int = 20) -> list[BackupSnapshot]:
        rows = (
            await self._session.execute(
                select(BackupSnapshotRow)
                .order_by(desc(BackupSnapshotRow.created_at))
                .limit(limit)
            )
        ).scalars().all()
        return [row_to_backup_snapshot(r) for r in rows]

    async def latest(self) -> BackupSnapshot | None:
        r = await self._session.execute(
            select(BackupSnapshotRow).order_by(desc(BackupSnapshotRow.created_at)).limit(1)
        )
        row = r.scalar_one_or_none()
        return row_to_backup_snapshot(row) if row else None

    async def count(self) -> int:
        r = await self._session.execute(
            select(func.count(BackupSnapshotRow.backup_id))
        )
        return int(r.scalar_one() or 0)

    async def count_verified_or_recorded(self) -> int:
        r = await self._session.execute(
            select(func.count(BackupSnapshotRow.backup_id)).where(
                BackupSnapshotRow.verification_status.in_(
                    [
                        BackupVerificationStatus.RECORDED.value,
                        BackupVerificationStatus.VERIFIED_RESTORE.value,
                    ]
                )
            )
        )
        return int(r.scalar_one() or 0)


# ---- Live integration toggles ---------------------------------------------


class LiveIntegrationToggleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, organization_id: UUID, integration: LiveIntegration
    ) -> LiveIntegrationToggle | None:
        r = await self._session.execute(
            select(LiveIntegrationToggleRow).where(
                and_(
                    LiveIntegrationToggleRow.organization_id == str(organization_id),
                    LiveIntegrationToggleRow.integration == integration.value,
                )
            )
        )
        row = r.scalar_one_or_none()
        return row_to_live_toggle(row) if row else None

    async def list_for_org(
        self, organization_id: UUID
    ) -> list[LiveIntegrationToggle]:
        r = await self._session.execute(
            select(LiveIntegrationToggleRow).where(
                LiveIntegrationToggleRow.organization_id == str(organization_id)
            )
        )
        return [row_to_live_toggle(row) for row in r.scalars().all()]

    async def upsert(
        self,
        organization_id: UUID,
        integration: LiveIntegration,
        *,
        new_state: LiveToggleState,
        actor: str,
        approval_note: str = "",
    ) -> LiveIntegrationToggle:
        r = await self._session.execute(
            select(LiveIntegrationToggleRow).where(
                and_(
                    LiveIntegrationToggleRow.organization_id == str(organization_id),
                    LiveIntegrationToggleRow.integration == integration.value,
                )
            )
        )
        row = r.scalar_one_or_none()
        if row is None:
            row = LiveIntegrationToggleRow(
                id=str(uuid4()),
                organization_id=str(organization_id),
                integration=integration.value,
                state=new_state.value,
                previous_state=LiveToggleState.DISABLED.value,
                updated_by=actor,
                approval_note=approval_note or "",
                updated_at=datetime.now(UTC),
            )
            self._session.add(row)
        else:
            row.previous_state = row.state
            row.state = new_state.value
            row.updated_by = actor
            row.approval_note = approval_note or ""
            row.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(row)
        return row_to_live_toggle(row)

    async def disable_all_for_org(self, organization_id: UUID, *, actor: str) -> int:
        r = await self._session.execute(
            select(LiveIntegrationToggleRow).where(
                and_(
                    LiveIntegrationToggleRow.organization_id == str(organization_id),
                    LiveIntegrationToggleRow.state == LiveToggleState.ENABLED.value,
                )
            )
        )
        count = 0
        for row in r.scalars().all():
            row.previous_state = row.state
            row.state = LiveToggleState.DISABLED.value
            row.updated_by = actor
            row.approval_note = (row.approval_note or "") + " [rollback:disabled]"
            count += 1
        if count:
            await self._session.flush()
        return count


# ---- Cutover events --------------------------------------------------------


class CutoverEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: CutoverEvent) -> CutoverEvent:
        row = CutoverEventRow(
            event_id=event.event_id,
            organization_id="",  # tenant scope intentionally not bound to a single org
            action=event.action.value,
            previous_mode=event.previous_mode.value,
            new_mode=event.new_mode.value,
            actor=event.actor or "",
            actor_role="",
            reason=event.reason or "",
            notes=event.notes or "",
            gate_passed=event.gate_passed,
            gate_summary=event.gate_summary or "",
            occurred_at=event.occurred_at,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_cutover_event(row)

    async def list_recent(self, *, limit: int = 20) -> list[CutoverEvent]:
        rows = (
            await self._session.execute(
                select(CutoverEventRow)
                .order_by(desc(CutoverEventRow.occurred_at))
                .limit(limit)
            )
        ).scalars().all()
        return [row_to_cutover_event(r) for r in rows]


# ---- Worker heartbeats -----------------------------------------------------


class WorkerHeartbeatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        worker_id: str,
        last_task: str = "",
        detail: str = "",
        organization_id: str = "",
    ) -> WorkerHeartbeat:
        row = WorkerHeartbeatRow(
            id=str(uuid4()),
            worker_id=worker_id,
            last_task=last_task or "",
            detail=detail or "",
            organization_id=organization_id or "",
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_worker_heartbeat(row)

    async def latest(self) -> WorkerHeartbeat | None:
        r = await self._session.execute(
            select(WorkerHeartbeatRow).order_by(desc(WorkerHeartbeatRow.last_seen)).limit(1)
        )
        row = r.scalar_one_or_none()
        return row_to_worker_heartbeat(row) if row else None
