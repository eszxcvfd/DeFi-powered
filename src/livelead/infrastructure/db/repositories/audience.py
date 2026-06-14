from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.audience.models import AudienceHypothesis
from livelead.infrastructure.db.audience_mappers import (
    hypothesis_to_evidence_json,
    row_to_hypothesis,
)
from livelead.infrastructure.db.models import AudienceHypothesisRow


class AudienceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_current(self, event_id: UUID) -> list[AudienceHypothesis]:
        result = await self._session.execute(
            select(AudienceHypothesisRow)
            .where(
                AudienceHypothesisRow.event_id == str(event_id),
                AudienceHypothesisRow.superseded_at.is_(None),
            )
            .order_by(AudienceHypothesisRow.confidence.desc())
        )
        return [row_to_hypothesis(r) for r in result.scalars().all()]

    async def replace_for_event(self, event_id: UUID, hypotheses: list[AudienceHypothesis]) -> list[AudienceHypothesis]:
        now = datetime.now(UTC)
        existing = await self._session.execute(
            select(AudienceHypothesisRow).where(
                AudienceHypothesisRow.event_id == str(event_id),
                AudienceHypothesisRow.superseded_at.is_(None),
            )
        )
        for old in existing.scalars().all():
            old.superseded_at = now
            self._session.add(old)
        for h in hypotheses:
            row = AudienceHypothesisRow(
                id=str(h.id),
                event_id=str(event_id),
                segment_name=h.segment_name,
                fit_type=h.fit_type.value,
                reason=h.reason,
                evidence_json=hypothesis_to_evidence_json(h),
                confidence=h.confidence,
                generated_by=h.generated_by,
                model_version=h.model_version,
                superseded_at=None,
                created_at=h.created_at or now,
            )
            self._session.add(row)
        await self._session.flush()
        return await self.list_current(event_id)