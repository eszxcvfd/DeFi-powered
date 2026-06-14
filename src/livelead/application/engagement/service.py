import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audience.service import AudienceService
from livelead.domain.engagement.generator import PlanGenerationContext, generate_engagement_plan
from livelead.domain.engagement.models import EngagementPlanState
from livelead.domain.engagement.transitions import can_transition, parse_task_status
from livelead.infrastructure.db.repositories.campaigns import CampaignRepository
from livelead.infrastructure.db.repositories.engagement import EngagementRepository
from livelead.infrastructure.db.repositories.event_scores import EventScoreRepository
from livelead.infrastructure.db.repositories.events import EventRepository

logger = logging.getLogger("livelead.engagement")


class EngagementService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = EventRepository(session)
        self._campaigns = CampaignRepository(session)
        self._scores = EventScoreRepository(session)
        self._engagement = EngagementRepository(session)

    async def get_plan_state(self, event_id: UUID, organization_id: UUID) -> EngagementPlanState:
        event = await self._events.get(event_id, organization_id)
        if not event:
            return EngagementPlanState(state="missing", generation_notes=("Event not found.",))

        plan = await self._engagement.get_current_plan(event_id)
        if not plan:
            return EngagementPlanState(state="missing", generation_notes=("No engagement plan yet.",))

        tasks = await self._engagement.list_tasks_for_plan(plan.id)
        return EngagementPlanState(state="ready", plan=plan, tasks=tuple(tasks))

    async def create_or_refresh_plan(self, event_id: UUID, organization_id: UUID) -> EngagementPlanState:
        event = await self._events.get(event_id, organization_id)
        if not event:
            return EngagementPlanState(state="blocked", generation_notes=("Event not found.",))

        campaign = await self._campaigns.get(event.campaign_id, organization_id)
        if not campaign:
            return EngagementPlanState(state="blocked", generation_notes=("Campaign context missing.",))

        score = await self._scores.get_current(event_id, event.campaign_id)
        if not score:
            return EngagementPlanState(
                state="blocked",
                generation_notes=("Score the event before creating an engagement plan.",),
            )

        audience = await AudienceService(self._session).get_or_generate(event_id, organization_id)
        ctx = PlanGenerationContext(
            event=event,
            campaign=campaign,
            score=score,
            hypotheses=tuple(audience.hypotheses),
        )
        generated = generate_engagement_plan(ctx)
        if generated.state != "ready" or not generated.plan:
            return generated

        plan, tasks = await self._engagement.replace_plan(generated.plan, list(generated.tasks))
        logger.info(
            "engagement_plan_created event_id=%s plan_id=%s tasks=%s version=%s",
            event_id,
            plan.id,
            len(tasks),
            plan.strategy_version,
        )
        return EngagementPlanState(state="ready", plan=plan, tasks=tuple(tasks))

    async def update_task(
        self,
        event_id: UUID,
        task_id: UUID,
        organization_id: UUID,
        *,
        status: str | None = None,
        assignee: str | None = None,
        notes: str | None = None,
    ) -> EngagementPlanState | None:
        if not await self._events.get(event_id, organization_id):
            return None

        task = await self._engagement.get_task(task_id, event_id)
        if not task:
            return None

        new_status = parse_task_status(status) if status else None
        if new_status and not can_transition(task.status, new_status):
            raise ValueError("invalid task status transition")

        updated = await self._engagement.update_task(
            task_id,
            event_id,
            status=new_status.value if new_status else None,
            assignee=assignee,
            notes=notes,
        )
        if updated and new_status:
            logger.info(
                "engagement_task_updated event_id=%s task_id=%s status=%s",
                event_id,
                task_id,
                new_status.value,
            )
        return await self.get_plan_state(event_id, organization_id)