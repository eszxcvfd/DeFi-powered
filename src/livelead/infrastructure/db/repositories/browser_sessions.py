from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.browser.models import BrowserSessionRecord, BrowserSessionState
from livelead.infrastructure.db.browser_session_mappers import row_to_record
from livelead.infrastructure.db.models import BrowserSessionRow


class BrowserSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, session_id: UUID, organization_id: UUID) -> BrowserSessionRow | None:
        result = await self._session.execute(
            select(BrowserSessionRow).where(
                BrowserSessionRow.id == str(session_id),
                BrowserSessionRow.organization_id == str(organization_id),
            )
        )
        return result.scalar_one_or_none()

    async def add(self, row: BrowserSessionRow) -> BrowserSessionRecord:
        self._session.add(row)
        await self._session.flush()
        return row_to_record(row)

    async def apply_runtime(
        self,
        row: BrowserSessionRow,
        *,
        state: BrowserSessionState | None = None,
        current_url: str | None = None,
        latest_action_summary: str | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        worker_id: str | None = None,
        stop_requested: bool | None = None,
        error_summary: str | None = None,
    ) -> BrowserSessionRecord:
        if state is not None:
            row.status = state.value
        if current_url is not None:
            row.current_url = current_url
        if latest_action_summary is not None:
            row.latest_action_summary = latest_action_summary
        if started_at is not None:
            row.started_at = started_at
        if ended_at is not None:
            row.ended_at = ended_at
        if worker_id is not None:
            row.worker_id = worker_id
        if stop_requested is not None:
            row.stop_requested = stop_requested
        if error_summary is not None:
            row.error_summary = error_summary
        await self._session.flush()
        return row_to_record(row)

    async def mark_stop_requested(self, row: BrowserSessionRow) -> BrowserSessionRecord:
        row.stop_requested = True
        row.status = BrowserSessionState.STOPPING.value
        await self._session.flush()
        return row_to_record(row)

    @staticmethod
    def touch_started(row: BrowserSessionRow) -> None:
        if not row.started_at:
            row.started_at = datetime.now(UTC)
