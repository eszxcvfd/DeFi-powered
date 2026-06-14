from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.browser.debug_artifacts import (
    BrowserArtifactStatus,
    effective_artifact_status,
)
from livelead.infrastructure.db.models import BrowserDebugArtifactRow


class BrowserDebugArtifactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, artifact_id: UUID, organization_id: UUID) -> BrowserDebugArtifactRow | None:
        result = await self._session.execute(
            select(BrowserDebugArtifactRow).where(
                BrowserDebugArtifactRow.id == str(artifact_id),
                BrowserDebugArtifactRow.organization_id == str(organization_id),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_session(self, session_id: UUID, organization_id: UUID) -> list[BrowserDebugArtifactRow]:
        result = await self._session.execute(
            select(BrowserDebugArtifactRow)
            .where(
                BrowserDebugArtifactRow.session_id == str(session_id),
                BrowserDebugArtifactRow.organization_id == str(organization_id),
            )
            .order_by(BrowserDebugArtifactRow.created_at.desc())
        )
        rows = list(result.scalars().all())
        for row in rows:
            if row.status == BrowserArtifactStatus.ACTIVE.value:
                eff = effective_artifact_status(
                    BrowserArtifactStatus(row.status),
                    expires_at=row.expires_at,
                )
                if eff == BrowserArtifactStatus.EXPIRED:
                    row.status = BrowserArtifactStatus.EXPIRED.value
        await self._session.flush()
        return rows

    async def add(self, row: BrowserDebugArtifactRow) -> BrowserDebugArtifactRow:
        self._session.add(row)
        await self._session.flush()
        return row

    @staticmethod
    def new_row(
        *,
        session_id: UUID,
        organization_id: UUID,
        artifact_type: str,
        capture_mode: str,
        status: str,
        storage_path: str,
        content_type: str,
        byte_size: int,
        captured_by: str,
        summary: str,
        expires_at: datetime,
        redacted: bool = False,
    ) -> BrowserDebugArtifactRow:
        return BrowserDebugArtifactRow(
            id=str(uuid4()),
            session_id=str(session_id),
            organization_id=str(organization_id),
            artifact_type=artifact_type,
            capture_mode=capture_mode,
            status=status,
            storage_path=storage_path,
            content_type=content_type,
            byte_size=byte_size,
            captured_by=captured_by,
            summary=summary,
            redacted=redacted,
            expires_at=expires_at,
            created_at=datetime.now(UTC),
        )