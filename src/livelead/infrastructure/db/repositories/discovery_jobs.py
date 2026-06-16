import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.discovery.lifecycle import can_cancel
from livelead.domain.discovery.models import DiscoveryJobStatus
from livelead.infrastructure.db.models import DiscoveryJobRow


class DiscoveryJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, job_id: UUID, organization_id: UUID) -> DiscoveryJobRow | None:
        result = await self._session.execute(
            select(DiscoveryJobRow).where(
                DiscoveryJobRow.id == str(job_id),
                DiscoveryJobRow.organization_id == str(organization_id),
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        organization_id: UUID,
        campaign_id: UUID,
        criteria_snapshot: dict,
        source_ids: list[str],
        created_by: str,
        discovery_schedule_id: str | None = None,
    ) -> DiscoveryJobRow:
        now = datetime.now(UTC)
        progress = {
            "percent": 0,
            "sources": {
                sid: {"status": "pending", "items_found": 0, "pages_processed": 0}
                for sid in source_ids
            },
            "events": [{"type": "job.queued", "at": now.isoformat()}],
        }
        row = DiscoveryJobRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            campaign_id=str(campaign_id),
            status=DiscoveryJobStatus.QUEUED.value,
            criteria_snapshot_json=json.dumps(criteria_snapshot),
            progress_json=json.dumps(progress),
            discovery_schedule_id=discovery_schedule_id,
            created_by=created_by,
            created_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def request_cancel(self, row: DiscoveryJobRow) -> DiscoveryJobRow:
        status = DiscoveryJobStatus(row.status)
        if not can_cancel(status):
            return row
        row.cancel_requested = True
        await self._session.flush()
        return row
