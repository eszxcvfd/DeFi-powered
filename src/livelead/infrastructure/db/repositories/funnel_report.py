"""Funnel report read queries (US-016)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.infrastructure.db.models import EventRow, LeadActivityRow, LeadRow


class FunnelReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_events_in_window(
        self, organization_id: UUID, start: datetime, end_exclusive: datetime
    ) -> tuple[int, datetime | None]:
        q = select(func.count(), func.max(EventRow.observed_at)).where(
            EventRow.organization_id == str(organization_id),
            EventRow.observed_at >= start,
            EventRow.observed_at < end_exclusive,
        )
        row = (await self._session.execute(q)).one()
        return int(row[0] or 0), row[1]

    async def count_leads_in_window(
        self, organization_id: UUID, start: datetime, end_exclusive: datetime
    ) -> tuple[int, datetime | None]:
        q = select(func.count(), func.max(LeadRow.created_at)).where(
            LeadRow.organization_id == str(organization_id),
            LeadRow.created_at >= start,
            LeadRow.created_at < end_exclusive,
        )
        row = (await self._session.execute(q)).one()
        return int(row[0] or 0), row[1]

    async def count_manual_leads_in_window(
        self, organization_id: UUID, start: datetime, end_exclusive: datetime
    ) -> int:
        q = select(func.count()).where(
            LeadRow.organization_id == str(organization_id),
            LeadRow.event_id.is_(None),
            LeadRow.created_at >= start,
            LeadRow.created_at < end_exclusive,
        )
        return int((await self._session.execute(q)).scalar_one() or 0)

    async def count_distinct_leads_with_outcome(
        self,
        organization_id: UUID,
        outcome_type: str,
        start: datetime,
        end_exclusive: datetime,
    ) -> tuple[int, datetime | None]:
        occurred = func.coalesce(LeadActivityRow.occurred_at, LeadActivityRow.created_at)
        q = (
            select(func.count(func.distinct(LeadActivityRow.lead_id)), func.max(occurred))
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
