import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.discovery.schedule_recurrence import (
    compute_next_run,
    parse_recurrence,
    recurrence_to_json,
)
from livelead.domain.discovery.schedule_state import ScheduleEnabledState
from livelead.infrastructure.db.models import DiscoveryScheduleRow


class DiscoveryScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, schedule_id: UUID, organization_id: UUID) -> DiscoveryScheduleRow | None:
        result = await self._session.execute(
            select(DiscoveryScheduleRow).where(
                DiscoveryScheduleRow.id == str(schedule_id),
                DiscoveryScheduleRow.organization_id == str(organization_id),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_campaign(
        self, campaign_id: UUID, organization_id: UUID
    ) -> list[DiscoveryScheduleRow]:
        result = await self._session.execute(
            select(DiscoveryScheduleRow)
            .where(
                DiscoveryScheduleRow.campaign_id == str(campaign_id),
                DiscoveryScheduleRow.organization_id == str(organization_id),
            )
            .order_by(DiscoveryScheduleRow.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        *,
        organization_id: UUID,
        campaign_id: UUID,
        recurrence: dict,
        source_ids: list[str],
        template: dict,
        created_by: str,
    ) -> DiscoveryScheduleRow:
        spec = parse_recurrence(recurrence)
        now = datetime.now(UTC)
        next_run = compute_next_run(spec, after=now)
        row = DiscoveryScheduleRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            campaign_id=str(campaign_id),
            enabled_state=ScheduleEnabledState.ENABLED.value,
            recurrence_json=json.dumps(recurrence_to_json(spec)),
            source_ids_json=json.dumps(source_ids),
            template_json=json.dumps(template),
            next_run_at=next_run,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def update_recurrence(self, row: DiscoveryScheduleRow, recurrence: dict) -> DiscoveryScheduleRow:
        spec = parse_recurrence(recurrence)
        row.recurrence_json = json.dumps(recurrence_to_json(spec))
        row.next_run_at = compute_next_run(spec, after=datetime.now(UTC))
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return row

    async def set_enabled_state(self, row: DiscoveryScheduleRow, state: ScheduleEnabledState) -> DiscoveryScheduleRow:
        row.enabled_state = state.value
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return row

    async def set_source_ids(self, row: DiscoveryScheduleRow, source_ids: list[str]) -> DiscoveryScheduleRow:
        row.source_ids_json = json.dumps(source_ids)
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return row

    async def record_dispatch(
        self,
        row: DiscoveryScheduleRow,
        *,
        outcome: str,
        job_id: str | None,
    ) -> None:
        row.last_dispatch_outcome = outcome
        row.last_dispatched_job_id = job_id
        row.updated_at = datetime.now(UTC)
        await self._session.flush()