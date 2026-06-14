from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.browser.action_confirmation import (
    BrowserConfirmationState,
    effective_confirmation_state,
)
from livelead.infrastructure.db.models import BrowserActionConfirmationRow


class BrowserActionConfirmationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, confirmation_id: UUID, organization_id: UUID) -> BrowserActionConfirmationRow | None:
        result = await self._session.execute(
            select(BrowserActionConfirmationRow).where(
                BrowserActionConfirmationRow.id == str(confirmation_id),
                BrowserActionConfirmationRow.organization_id == str(organization_id),
            )
        )
        return result.scalar_one_or_none()

    async def get_pending_for_session(
        self, session_id: UUID, organization_id: UUID
    ) -> BrowserActionConfirmationRow | None:
        result = await self._session.execute(
            select(BrowserActionConfirmationRow)
            .where(
                BrowserActionConfirmationRow.session_id == str(session_id),
                BrowserActionConfirmationRow.organization_id == str(organization_id),
                BrowserActionConfirmationRow.state == BrowserConfirmationState.PENDING.value,
            )
            .order_by(BrowserActionConfirmationRow.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        effective = effective_confirmation_state(
            BrowserConfirmationState(row.state),
            expires_at=row.expires_at,
        )
        if effective == BrowserConfirmationState.EXPIRED:
            row.state = BrowserConfirmationState.EXPIRED.value
            await self._session.flush()
            return None
        return row

    async def add(self, row: BrowserActionConfirmationRow) -> BrowserActionConfirmationRow:
        self._session.add(row)
        await self._session.flush()
        return row

    @staticmethod
    def new_row(
        *,
        session_id: UUID,
        organization_id: UUID,
        requested_by: str,
        action_type: str,
        parameters_json: str,
        preview_json: str,
        expires_at: datetime,
    ) -> BrowserActionConfirmationRow:
        return BrowserActionConfirmationRow(
            id=str(uuid4()),
            session_id=str(session_id),
            organization_id=str(organization_id),
            requested_by=requested_by,
            action_type=action_type,
            parameters_json=parameters_json,
            preview_json=preview_json,
            state=BrowserConfirmationState.PENDING.value,
            expires_at=expires_at,
            created_at=datetime.now(UTC),
        )