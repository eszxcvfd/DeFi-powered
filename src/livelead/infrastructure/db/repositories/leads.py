from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.leads.models import LeadActivityEntry, LeadRecord, LeadStage
from livelead.infrastructure.db.lead_mappers import row_to_activity, row_to_lead
from livelead.infrastructure.db.models import LeadActivityRow, LeadRow


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_org(
        self,
        organization_id: UUID,
        *,
        owner: str | None = None,
        campaign_id: UUID | None = None,
        discovery_source: str | None = None,
        due_before: date | None = None,
    ) -> list[LeadRecord]:
        q = select(LeadRow).where(LeadRow.organization_id == str(organization_id))
        if owner:
            q = q.where(LeadRow.owner == owner)
        if campaign_id:
            q = q.where(LeadRow.campaign_id == str(campaign_id))
        if discovery_source:
            q = q.where(LeadRow.discovery_source == discovery_source)
        if due_before:
            q = q.where(LeadRow.follow_up_date.is_not(None), LeadRow.follow_up_date <= due_before.isoformat())
        q = q.order_by(LeadRow.updated_at.desc())
        result = await self._session.execute(q)
        return [row_to_lead(r) for r in result.scalars().all()]

    async def list_all_for_org(self, organization_id: UUID) -> list[LeadRecord]:
        result = await self._session.execute(
            select(LeadRow).where(LeadRow.organization_id == str(organization_id))
        )
        return [row_to_lead(r) for r in result.scalars().all()]

    async def get(self, lead_id: UUID, organization_id: UUID) -> LeadRecord | None:
        result = await self._session.execute(
            select(LeadRow).where(LeadRow.id == str(lead_id), LeadRow.organization_id == str(organization_id))
        )
        row = result.scalars().first()
        return row_to_lead(row) if row else None

    async def list_by_event(self, event_id: UUID, organization_id: UUID) -> list[LeadRecord]:
        result = await self._session.execute(
            select(LeadRow).where(
                LeadRow.event_id == str(event_id),
                LeadRow.organization_id == str(organization_id),
            )
        )
        return [row_to_lead(r) for r in result.scalars().all()]

    async def insert(self, row: LeadRow) -> LeadRecord:
        self._session.add(row)
        await self._session.flush()
        return row_to_lead(row)

    async def save_fields(self, lead_id: UUID, organization_id: UUID, **fields: object) -> LeadRecord | None:
        result = await self._session.execute(
            select(LeadRow).where(LeadRow.id == str(lead_id), LeadRow.organization_id == str(organization_id))
        )
        row = result.scalars().first()
        if not row:
            return None
        for key, val in fields.items():
            if hasattr(row, key):
                setattr(row, key, val)
        row.updated_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()
        return row_to_lead(row)


class LeadActivityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_lead(self, lead_id: UUID, *, limit: int = 50) -> list[LeadActivityEntry]:
        result = await self._session.execute(
            select(LeadActivityRow)
            .where(LeadActivityRow.lead_id == str(lead_id))
            .order_by(LeadActivityRow.created_at.desc())
            .limit(limit)
        )
        return [row_to_activity(r) for r in result.scalars().all()]

    async def append(
        self,
        *,
        lead_id: UUID,
        kind: str,
        actor: str,
        body: str = "",
        from_stage: str = "",
        to_stage: str = "",
    ) -> LeadActivityEntry:
        now = datetime.now(UTC)
        row = LeadActivityRow(
            id=str(uuid4()),
            lead_id=str(lead_id),
            kind=kind,
            actor=actor,
            body=body,
            from_stage=from_stage,
            to_stage=to_stage,
            created_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_activity(row)


def new_lead_row(**kwargs: object) -> LeadRow:
    now = datetime.now(UTC)
    defaults: dict = {
        "id": str(uuid4()),
        "stage": LeadStage.NEWLY_DISCOVERED.value,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return LeadRow(**defaults)  # type: ignore[arg-type]