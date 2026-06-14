"""Browser profile persistence (US-024)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.browser.profiles import BrowserProfileConsentStatus, BrowserProfileLifecycle
from livelead.infrastructure.db.models import BrowserProfileRow


class BrowserProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: BrowserProfileRow) -> BrowserProfileRow:
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, profile_id: UUID, organization_id: UUID) -> BrowserProfileRow | None:
        r = await self._session.execute(
            select(BrowserProfileRow).where(
                BrowserProfileRow.id == str(profile_id),
                BrowserProfileRow.organization_id == str(organization_id),
            )
        )
        return r.scalar_one_or_none()

    async def list_for_organization(self, organization_id: UUID) -> list[BrowserProfileRow]:
        r = await self._session.execute(
            select(BrowserProfileRow)
            .where(BrowserProfileRow.organization_id == str(organization_id))
            .order_by(BrowserProfileRow.created_at.desc())
        )
        return list(r.scalars().all())

    @staticmethod
    def new_row(
        *,
        organization_id: UUID,
        name: str,
        created_by: str,
        expires_at: datetime | None = None,
        profile_id: UUID | None = None,
    ) -> BrowserProfileRow:
        now = datetime.now(UTC)
        return BrowserProfileRow(
            id=str(profile_id or uuid4()),
            organization_id=str(organization_id),
            name=name.strip() or "Browser profile",
            lifecycle_state=BrowserProfileLifecycle.ACTIVE.value,
            created_by=created_by,
            expires_at=expires_at,
            consent_status=BrowserProfileConsentStatus.NONE.value,
            created_at=now,
            updated_at=now,
        )