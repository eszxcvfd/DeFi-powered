"""Discovery copilot persistence (US-037)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.infrastructure.db.models import DiscoveryCopilotResponseRow


class DiscoveryCopilotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        organization_id: UUID,
        campaign_id: UUID,
        question: str,
        response: dict,
        provider_id: str,
        model_id: str,
        confidence: float,
        created_by: str,
    ) -> DiscoveryCopilotResponseRow:
        row = DiscoveryCopilotResponseRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            campaign_id=str(campaign_id),
            question=question,
            response_json=json.dumps(response),
            provider_id=provider_id,
            model_id=model_id,
            confidence=confidence,
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, response_id: UUID, organization_id: UUID) -> DiscoveryCopilotResponseRow | None:
        result = await self._session.execute(
            select(DiscoveryCopilotResponseRow).where(
                DiscoveryCopilotResponseRow.id == str(response_id),
                DiscoveryCopilotResponseRow.organization_id == str(organization_id),
            )
        )
        return result.scalar_one_or_none()

    async def list_recent_for_campaign(
        self, campaign_id: UUID, organization_id: UUID, *, limit: int = 10
    ) -> list[DiscoveryCopilotResponseRow]:
        result = await self._session.execute(
            select(DiscoveryCopilotResponseRow)
            .where(
                DiscoveryCopilotResponseRow.campaign_id == str(campaign_id),
                DiscoveryCopilotResponseRow.organization_id == str(organization_id),
            )
            .order_by(DiscoveryCopilotResponseRow.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_accepted(
        self,
        row: DiscoveryCopilotResponseRow,
        *,
        accepted_by: str,
        query_expansion_set_id: str | None,
    ) -> DiscoveryCopilotResponseRow:
        row.accepted_at = datetime.now(UTC)
        row.accepted_by = accepted_by
        row.query_expansion_set_id = query_expansion_set_id
        await self._session.flush()
        return row