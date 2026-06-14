from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.engagement.models import EngagementPlan, EngagementTask
from livelead.infrastructure.db.engagement_mappers import notes_to_json, row_to_plan, row_to_task
from livelead.infrastructure.db.models import EngagementPlanRow, EngagementTaskRow


class EngagementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current_plan(self, event_id: UUID) -> EngagementPlan | None:
        result = await self._session.execute(
            select(EngagementPlanRow)
            .where(
                EngagementPlanRow.event_id == str(event_id),
                EngagementPlanRow.superseded_at.is_(None),
            )
            .order_by(EngagementPlanRow.created_at.desc())
            .limit(1)
        )
        row = result.scalars().first()
        return row_to_plan(row) if row else None

    async def list_tasks_for_plan(self, plan_id: UUID) -> list[EngagementTask]:
        result = await self._session.execute(
            select(EngagementTaskRow)
            .where(EngagementTaskRow.plan_id == str(plan_id))
            .order_by(EngagementTaskRow.phase, EngagementTaskRow.created_at)
        )
        return [row_to_task(r) for r in result.scalars().all()]

    async def replace_plan(
        self,
        plan: EngagementPlan,
        tasks: list[EngagementTask],
    ) -> tuple[EngagementPlan, list[EngagementTask]]:
        now = datetime.now(UTC)
        existing = await self._session.execute(
            select(EngagementPlanRow).where(
                EngagementPlanRow.event_id == str(plan.event_id),
                EngagementPlanRow.superseded_at.is_(None),
            )
        )
        for old in existing.scalars().all():
            old.superseded_at = now
            self._session.add(old)

        plan_row = EngagementPlanRow(
            id=str(plan.id),
            event_id=str(plan.event_id),
            campaign_id=str(plan.campaign_id),
            strategy_version=plan.strategy_version,
            generation_notes_json=notes_to_json(plan.generation_notes),
            superseded_at=None,
            created_at=plan.created_at or now,
            updated_at=plan.updated_at or now,
        )
        self._session.add(plan_row)

        for t in tasks:
            task_row = EngagementTaskRow(
                id=str(t.id),
                plan_id=str(plan.id),
                event_id=str(t.event_id),
                phase=t.phase.value,
                title=t.title,
                rationale=t.rationale,
                status=t.status.value,
                assignee=t.assignee,
                deadline=t.deadline,
                notes=t.notes,
                created_at=t.created_at or now,
                updated_at=t.updated_at or now,
            )
            self._session.add(task_row)

        await self._session.flush()
        saved_plan = await self.get_current_plan(plan.event_id)
        assert saved_plan
        saved_tasks = await self.list_tasks_for_plan(saved_plan.id)
        return saved_plan, saved_tasks

    async def get_task(self, task_id: UUID, event_id: UUID) -> EngagementTask | None:
        result = await self._session.execute(
            select(EngagementTaskRow).where(
                EngagementTaskRow.id == str(task_id),
                EngagementTaskRow.event_id == str(event_id),
            )
        )
        row = result.scalars().first()
        return row_to_task(row) if row else None

    async def update_task(
        self,
        task_id: UUID,
        event_id: UUID,
        *,
        status: str | None = None,
        assignee: str | None = None,
        notes: str | None = None,
    ) -> EngagementTask | None:
        result = await self._session.execute(
            select(EngagementTaskRow).where(
                EngagementTaskRow.id == str(task_id),
                EngagementTaskRow.event_id == str(event_id),
            )
        )
        row = result.scalars().first()
        if not row:
            return None
        now = datetime.now(UTC)
        if status is not None:
            row.status = status
        if assignee is not None:
            row.assignee = assignee
        if notes is not None:
            row.notes = notes
        row.updated_at = now
        self._session.add(row)
        await self._session.flush()
        return row_to_task(row)
