import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.audience.generator import GenerationContext, generate_audience_analysis
from livelead.domain.audience.models import AUDIENCE_STRATEGY_VERSION, AudienceAnalysisState
from livelead.infrastructure.db.repositories.audience import AudienceRepository
from livelead.infrastructure.db.repositories.campaigns import CampaignRepository
from livelead.infrastructure.db.repositories.events import EventRepository

logger = logging.getLogger("livelead.audience")


class AudienceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = EventRepository(session)
        self._campaigns = CampaignRepository(session)
        self._audience = AudienceRepository(session)

    async def get_or_generate(self, event_id: UUID, organization_id: UUID, *, refresh: bool = False) -> AudienceAnalysisState:
        event = await self._events.get(event_id, organization_id)
        if not event:
            return AudienceAnalysisState(state="pending", generation_notes=("Event not found.",))

        current = await self._audience.list_current(event_id)
        if current and not refresh:
            stale = any(h.model_version != AUDIENCE_STRATEGY_VERSION for h in current)
            if not stale:
                return AudienceAnalysisState(
                    state="ready",
                    hypotheses=tuple(current),
                    strategy_version=current[0].model_version if current else AUDIENCE_STRATEGY_VERSION,
                )

        campaign = await self._campaigns.get(event.campaign_id, organization_id)
        if not campaign:
            return AudienceAnalysisState(state="empty", generation_notes=("Campaign context missing.",))

        obs = await self._events.list_observations(event_id)
        ctx = GenerationContext(event=event, campaign=campaign, observations=tuple(obs))
        analysis = generate_audience_analysis(ctx)

        if analysis.state == "ready" and analysis.hypotheses:
            await self._audience.replace_for_event(event_id, list(analysis.hypotheses))
            logger.info(
                "audience_generated event_id=%s count=%s version=%s",
                event_id,
                len(analysis.hypotheses),
                analysis.strategy_version,
            )
        elif refresh:
            await self._audience.replace_for_event(event_id, [])

        return analysis