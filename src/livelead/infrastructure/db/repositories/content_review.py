from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.content.models import ContentReviewDecision, ContentReviewStatus
from livelead.infrastructure.db.content_mappers import row_to_decision
from livelead.infrastructure.db.models import ContentReviewDecisionRow, GeneratedContentDraftRow


class ContentReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_draft(self, draft_id: UUID) -> list[ContentReviewDecision]:
        result = await self._session.execute(
            select(ContentReviewDecisionRow)
            .where(ContentReviewDecisionRow.draft_id == str(draft_id))
            .order_by(ContentReviewDecisionRow.created_at.desc())
        )
        return [row_to_decision(r) for r in result.scalars().all()]

    async def append_decision(
        self,
        *,
        draft_id: UUID,
        event_id: UUID,
        action: str,
        from_status: ContentReviewStatus,
        to_status: ContentReviewStatus,
        actor: str,
        note: str,
        body_revision: int,
    ) -> ContentReviewDecision:
        now = datetime.now(UTC)
        row = ContentReviewDecisionRow(
            id=str(uuid4()),
            draft_id=str(draft_id),
            event_id=str(event_id),
            action=action,
            from_status=from_status.value,
            to_status=to_status.value,
            actor=actor,
            note=note,
            body_revision=body_revision,
            created_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_decision(row)

    async def set_review_status(
        self,
        draft_id: UUID,
        event_id: UUID,
        status: ContentReviewStatus,
        *,
        reviewer_assignee: str | None = None,
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
        row.lifecycle = status.value
        if reviewer_assignee is not None:
            row.reviewer_assignee = reviewer_assignee
        row.updated_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()
        return True