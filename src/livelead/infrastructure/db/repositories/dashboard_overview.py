"""Dashboard overview read queries (US-014)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.leads.models import LeadStage
from livelead.domain.scoring.models import PriorityLevel
from livelead.infrastructure.db.models import (
    EventRow,
    EventScoreRow,
    GeneratedContentDraftRow,
    LeadActivityRow,
    LeadRow,
)


class DashboardOverviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_events_discovered(
        self, organization_id: UUID, start: datetime, end_exclusive: datetime
    ) -> tuple[int, datetime | None]:
        q = select(func.count(), func.max(EventRow.observed_at)).where(
            EventRow.organization_id == str(organization_id),
            EventRow.observed_at >= start,
            EventRow.observed_at < end_exclusive,
        )
        row = (await self._session.execute(q)).one()
        return int(row[0] or 0), row[1]

    async def count_prioritized_events(
        self, organization_id: UUID, start: datetime, end_exclusive: datetime
    ) -> tuple[int, datetime | None]:
        priority_levels = (
            PriorityLevel.VERY_HIGH.value,
            PriorityLevel.HIGH.value,
            PriorityLevel.WATCH.value,
        )
        q = (
            select(func.count(), func.max(EventScoreRow.calculated_at))
            .select_from(EventScoreRow)
            .join(EventRow, EventRow.id == EventScoreRow.event_id)
            .where(
                EventRow.organization_id == str(organization_id),
                EventScoreRow.superseded_at.is_(None),
                EventScoreRow.priority_level.in_(priority_levels),
                EventScoreRow.calculated_at >= start,
                EventScoreRow.calculated_at < end_exclusive,
            )
        )
        row = (await self._session.execute(q)).one()
        return int(row[0] or 0), row[1]

    async def count_events_watched_or_engaged(
        self, organization_id: UUID, start: datetime, end_exclusive: datetime
    ) -> tuple[int, datetime | None]:
        """Leads linked to events with watched+ stage, created in window."""
        engaged_stages = [
            s.value for s in LeadStage if s not in (LeadStage.NEWLY_DISCOVERED, LeadStage.NOT_FIT)
        ]
        q = select(func.count(), func.max(LeadRow.created_at)).where(
            LeadRow.organization_id == str(organization_id),
            LeadRow.event_id.is_not(None),
            LeadRow.stage.in_(engaged_stages),
            LeadRow.created_at >= start,
            LeadRow.created_at < end_exclusive,
        )
        row = (await self._session.execute(q)).one()
        return int(row[0] or 0), row[1]

    async def count_new_leads(
        self, organization_id: UUID, start: datetime, end_exclusive: datetime
    ) -> tuple[int, datetime | None]:
        q = select(func.count(), func.max(LeadRow.created_at)).where(
            LeadRow.organization_id == str(organization_id),
            LeadRow.created_at >= start,
            LeadRow.created_at < end_exclusive,
        )
        row = (await self._session.execute(q)).one()
        return int(row[0] or 0), row[1]

    async def count_content_created(
        self, organization_id: UUID, start: datetime, end_exclusive: datetime
    ) -> tuple[int, datetime | None]:
        q = (
            select(func.count(), func.max(GeneratedContentDraftRow.generated_at))
            .select_from(GeneratedContentDraftRow)
            .join(EventRow, EventRow.id == GeneratedContentDraftRow.event_id)
            .where(
                EventRow.organization_id == str(organization_id),
                GeneratedContentDraftRow.generated_at >= start,
                GeneratedContentDraftRow.generated_at < end_exclusive,
            )
        )
        row = (await self._session.execute(q)).one()
        return int(row[0] or 0), row[1]

    async def count_content_approved(
        self, organization_id: UUID, start: datetime, end_exclusive: datetime
    ) -> tuple[int, datetime | None]:
        q = (
            select(func.count(), func.max(GeneratedContentDraftRow.updated_at))
            .select_from(GeneratedContentDraftRow)
            .join(EventRow, EventRow.id == GeneratedContentDraftRow.event_id)
            .where(
                EventRow.organization_id == str(organization_id),
                GeneratedContentDraftRow.lifecycle == "approved",
                GeneratedContentDraftRow.updated_at >= start,
                GeneratedContentDraftRow.updated_at < end_exclusive,
            )
        )
        row = (await self._session.execute(q)).one()
        return int(row[0] or 0), row[1]

    async def count_content_used(
        self, organization_id: UUID, start: datetime, end_exclusive: datetime
    ) -> tuple[int, datetime | None]:
        q = (
            select(func.count(), func.max(GeneratedContentDraftRow.updated_at))
            .select_from(GeneratedContentDraftRow)
            .join(EventRow, EventRow.id == GeneratedContentDraftRow.event_id)
            .where(
                EventRow.organization_id == str(organization_id),
                GeneratedContentDraftRow.usage_status == "used",
                GeneratedContentDraftRow.updated_at >= start,
                GeneratedContentDraftRow.updated_at < end_exclusive,
            )
        )
        row = (await self._session.execute(q)).one()
        return int(row[0] or 0), row[1]

    async def count_outcome_entries(
        self,
        organization_id: UUID,
        outcome_type: str,
        start: datetime,
        end_exclusive: datetime,
    ) -> tuple[int, datetime | None]:
        occurred = func.coalesce(LeadActivityRow.occurred_at, LeadActivityRow.created_at)
        q = (
            select(func.count(), func.max(occurred))
            .select_from(LeadActivityRow)
            .join(LeadRow, LeadRow.id == LeadActivityRow.lead_id)
            .where(
                LeadRow.organization_id == str(organization_id),
                LeadActivityRow.kind == "outcome_recorded",
                LeadActivityRow.outcome_type == outcome_type,
                occurred >= start,
                occurred < end_exclusive,
            )
        )
        row = (await self._session.execute(q)).one()
        return int(row[0] or 0), row[1]

    async def org_has_any_events(self, organization_id: UUID) -> bool:
        q = select(func.count()).where(EventRow.organization_id == str(organization_id))
        return int((await self._session.execute(q)).scalar_one()) > 0

    async def org_has_any_scores(self, organization_id: UUID) -> bool:
        q = (
            select(func.count())
            .select_from(EventScoreRow)
            .join(EventRow, EventRow.id == EventScoreRow.event_id)
            .where(EventRow.organization_id == str(organization_id))
        )
        return int((await self._session.execute(q)).scalar_one()) > 0

    async def org_has_any_leads(self, organization_id: UUID) -> bool:
        q = select(func.count()).where(LeadRow.organization_id == str(organization_id))
        return int((await self._session.execute(q)).scalar_one()) > 0

    async def org_has_any_content(self, organization_id: UUID) -> bool:
        q = (
            select(func.count())
            .select_from(GeneratedContentDraftRow)
            .join(EventRow, EventRow.id == GeneratedContentDraftRow.event_id)
            .where(EventRow.organization_id == str(organization_id))
        )
        return int((await self._session.execute(q)).scalar_one()) > 0

    async def org_has_outcome_activity(self, organization_id: UUID, outcome_type: str) -> bool:
        q = (
            select(func.count())
            .select_from(LeadActivityRow)
            .join(LeadRow, LeadRow.id == LeadActivityRow.lead_id)
            .where(
                LeadRow.organization_id == str(organization_id),
                LeadActivityRow.kind == "outcome_recorded",
                LeadActivityRow.outcome_type == outcome_type,
            )
        )
        return int((await self._session.execute(q)).scalar_one()) > 0
