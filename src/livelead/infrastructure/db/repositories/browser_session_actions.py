from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.infrastructure.db.models import BrowserSessionActionRow


class BrowserSessionActionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_for_session(self, session_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(BrowserSessionActionRow)
            .where(BrowserSessionActionRow.session_id == str(session_id))
        )
        return int(result.scalar_one() or 0)

    async def add(self, row: BrowserSessionActionRow) -> BrowserSessionActionRow:
        self._session.add(row)
        await self._session.flush()
        return row

    @staticmethod
    def new_row(
        *,
        session_id: UUID,
        organization_id: UUID,
        actor: str,
        action_type: str,
        parameters_json: str,
        lifecycle: str,
        summary: str,
        detail: str | None = None,
        policy_reason: str | None = None,
    ) -> BrowserSessionActionRow:
        now = datetime.now(UTC)
        return BrowserSessionActionRow(
            id=str(uuid4()),
            session_id=str(session_id),
            organization_id=str(organization_id),
            actor=actor,
            action_type=action_type,
            parameters_json=parameters_json,
            lifecycle=lifecycle,
            summary=summary,
            detail=detail,
            policy_reason=policy_reason,
            created_at=now,
            completed_at=now
            if lifecycle in ("completed", "blocked", "failed", "timeout", "needs_user_action")
            else None,
        )
