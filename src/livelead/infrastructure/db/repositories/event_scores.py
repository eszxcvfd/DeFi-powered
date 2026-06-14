"""Event score persistence — append-friendly history via superseded_at."""

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.scoring.calculator import ScoreResult
from livelead.domain.scoring.models import EventScore
from livelead.infrastructure.db.event_mappers import row_to_score, score_result_to_json_payload
from livelead.infrastructure.db.models import EventScoreRow

logger = logging.getLogger("livelead.scoring")


class EventScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current(self, event_id: UUID, campaign_id: UUID) -> EventScore | None:
        result = await self._session.execute(
            select(EventScoreRow)
            .where(
                EventScoreRow.event_id == str(event_id),
                EventScoreRow.campaign_id == str(campaign_id),
                EventScoreRow.superseded_at.is_(None),
            )
            .order_by(EventScoreRow.calculated_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row_to_score(row) if row else None

    async def get_current_for_events(
        self, event_ids: list[UUID], campaign_id: UUID
    ) -> dict[UUID, EventScore]:
        if not event_ids:
            return {}
        ids = [str(e) for e in event_ids]
        result = await self._session.execute(
            select(EventScoreRow).where(
                EventScoreRow.event_id.in_(ids),
                EventScoreRow.campaign_id == str(campaign_id),
                EventScoreRow.superseded_at.is_(None),
            )
        )
        out: dict[UUID, EventScore] = {}
        for row in result.scalars().all():
            eid = UUID(row.event_id)
            if eid not in out:
                out[eid] = row_to_score(row)
        return out

    async def append_score(
        self,
        event_id: UUID,
        campaign_id: UUID,
        result: ScoreResult,
    ) -> EventScore:
        now = datetime.now(UTC)
        existing = await self._session.execute(
            select(EventScoreRow).where(
                EventScoreRow.event_id == str(event_id),
                EventScoreRow.campaign_id == str(campaign_id),
                EventScoreRow.superseded_at.is_(None),
            )
        )
        for old in existing.scalars().all():
            old.superseded_at = now
            self._session.add(old)

        w_json, c_json, e_json = score_result_to_json_payload(result)
        row = EventScoreRow(
            id=str(uuid4()),
            event_id=str(event_id),
            campaign_id=str(campaign_id),
            total_score=result.total_score,
            priority_level=result.priority_level.value,
            scoring_version=result.scoring_version,
            calculated_at=now,
            weights_snapshot_json=w_json,
            components_json=c_json,
            explanation_json=e_json,
            superseded_at=None,
        )
        self._session.add(row)
        await self._session.flush()
        logger.info(
            "event_score_calculated event_id=%s campaign_id=%s total=%s priority=%s version=%s",
            event_id,
            campaign_id,
            result.total_score,
            result.priority_level.value,
            result.scoring_version,
        )
        return row_to_score(row)