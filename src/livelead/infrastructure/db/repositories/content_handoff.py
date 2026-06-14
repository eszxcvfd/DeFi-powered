from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.content.models import ContentHandoffRecord, ContentUsageStatus
from livelead.infrastructure.db.content_mappers import row_to_handoff
from livelead.infrastructure.db.models import ContentHandoffRecordRow, GeneratedContentDraftRow


class ContentHandoffRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_draft(self, draft_id: UUID) -> list[ContentHandoffRecord]:
        result = await self._session.execute(
            select(ContentHandoffRecordRow)
            .where(ContentHandoffRecordRow.draft_id == str(draft_id))
            .order_by(ContentHandoffRecordRow.created_at.desc())
        )
        return [row_to_handoff(r) for r in result.scalars().all()]

    async def append(
        self,
        *,
        draft_id: UUID,
        event_id: UUID,
        action: str,
        actor: str,
        export_format: str = "",
        body_revision: int,
    ) -> ContentHandoffRecord:
        now = datetime.now(UTC)
        row = ContentHandoffRecordRow(
            id=str(uuid4()),
            draft_id=str(draft_id),
            event_id=str(event_id),
            action=action,
            actor=actor,
            export_format=export_format or "",
            body_revision=body_revision,
            created_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_handoff(row)

    async def set_usage_status(
        self,
        draft_id: UUID,
        event_id: UUID,
        status: ContentUsageStatus,
    ) -> bool:
        result = await self._session.execute(
            select(GeneratedContentDraftRow).where(
                GeneratedContentDraftRow.id == str(draft_id),
                GeneratedContentDraftRow.event_id == str(event_id),
            )
        )
        row = result.scalars().first()
        if not row:
            return False
        row.usage_status = status.value
        row.updated_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()
        return True

    async def get_usage_status(self, draft_id: UUID, event_id: UUID) -> ContentUsageStatus | None:
        result = await self._session.execute(
            select(GeneratedContentDraftRow).where(
                GeneratedContentDraftRow.id == str(draft_id),
                GeneratedContentDraftRow.event_id == str(event_id),
            )
        )
        row = result.scalars().first()
        if not row:
            return None
        raw = getattr(row, "usage_status", None) or ContentUsageStatus.NOT_USED.value
        return ContentUsageStatus(raw)