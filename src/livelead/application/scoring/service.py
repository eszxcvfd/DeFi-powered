"""Score calculation orchestration."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.scoring.calculator import ScoreResult, calculate_event_score
from livelead.domain.scoring.models import EventScore
from livelead.infrastructure.db.repositories.campaigns import CampaignRepository
from livelead.infrastructure.db.repositories.event_scores import EventScoreRepository
from livelead.infrastructure.db.repositories.events import EventRepository

logger = logging.getLogger("livelead.scoring")


class ScoringService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = EventRepository(session)
        self._campaigns = CampaignRepository(session)
        self._scores = EventScoreRepository(session)

    async def score_event(
        self,
        event_id: UUID,
        organization_id: UUID,
        *,
        campaign_id: UUID | None = None,
    ) -> EventScore | None:
        event = await self._events.get(event_id, organization_id)
        if not event:
            return None
        cid = campaign_id or event.campaign_id
        campaign = await self._campaigns.get(cid, organization_id)
        if not campaign:
            return None
        if event.campaign_id != cid:
            return None
        result: ScoreResult = calculate_event_score(event, campaign)
        return await self._scores.append_score(event_id, cid, result)

    async def rescore_event(self, event_id: UUID, organization_id: UUID) -> EventScore | None:
        logger.info("event_rescore_requested event_id=%s", event_id)
        return await self.score_event(event_id, organization_id)
