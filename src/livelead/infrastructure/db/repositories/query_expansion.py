"""Query expansion persistence (US-036)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.query_expansion.models import (
    QueryExpansionGenerationMode,
    QueryExpansionSetStatus,
    QueryExpansionVariant,
    QueryVariantSource,
    QueryVariantType,
)
from livelead.infrastructure.db.models import QueryExpansionSetRow


def _variant_from_dict(data: dict) -> QueryExpansionVariant:
    return QueryExpansionVariant(
        text=str(data.get("text", "")),
        variant_type=QueryVariantType(data.get("variant_type", QueryVariantType.SYNONYM.value)),
        source=QueryVariantSource(data.get("source", QueryVariantSource.RULE.value)),
        confidence=data.get("confidence"),
        assumption=data.get("assumption"),
        user_edited=bool(data.get("user_edited", False)),
        removed=bool(data.get("removed", False)),
    )


def variants_from_json(raw: str) -> list[QueryExpansionVariant]:
    data = json.loads(raw or "[]")
    if not isinstance(data, list):
        return []
    return [_variant_from_dict(x) for x in data if isinstance(x, dict)]


def variants_to_json(variants: list[QueryExpansionVariant]) -> str:
    from livelead.domain.query_expansion.rules import variant_to_dict

    return json.dumps([variant_to_dict(v) for v in variants])


class QueryExpansionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, set_id: UUID, organization_id: UUID) -> QueryExpansionSetRow | None:
        result = await self._session.execute(
            select(QueryExpansionSetRow).where(
                QueryExpansionSetRow.id == str(set_id),
                QueryExpansionSetRow.organization_id == str(organization_id),
            )
        )
        return result.scalar_one_or_none()

    async def latest_for_campaign(
        self, campaign_id: UUID, organization_id: UUID
    ) -> QueryExpansionSetRow | None:
        result = await self._session.execute(
            select(QueryExpansionSetRow)
            .where(
                QueryExpansionSetRow.campaign_id == str(campaign_id),
                QueryExpansionSetRow.organization_id == str(organization_id),
            )
            .order_by(QueryExpansionSetRow.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def latest_approved_for_campaign(
        self, campaign_id: UUID, organization_id: UUID
    ) -> QueryExpansionSetRow | None:
        result = await self._session.execute(
            select(QueryExpansionSetRow)
            .where(
                QueryExpansionSetRow.campaign_id == str(campaign_id),
                QueryExpansionSetRow.organization_id == str(organization_id),
                QueryExpansionSetRow.status == QueryExpansionSetStatus.APPROVED.value,
            )
            .order_by(QueryExpansionSetRow.approved_at.desc().nullslast(), QueryExpansionSetRow.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def supersede_approved_sets(self, campaign_id: UUID, organization_id: UUID) -> None:
        result = await self._session.execute(
            select(QueryExpansionSetRow).where(
                QueryExpansionSetRow.campaign_id == str(campaign_id),
                QueryExpansionSetRow.organization_id == str(organization_id),
                QueryExpansionSetRow.status == QueryExpansionSetStatus.APPROVED.value,
            )
        )
        for row in result.scalars().all():
            row.status = QueryExpansionSetStatus.SUPERSEDED.value

    async def create_draft(
        self,
        *,
        organization_id: UUID,
        campaign_id: UUID,
        generation_mode: QueryExpansionGenerationMode,
        variants: list[QueryExpansionVariant],
        created_by: str,
        status: QueryExpansionSetStatus,
    ) -> QueryExpansionSetRow:
        row = QueryExpansionSetRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            campaign_id=str(campaign_id),
            status=status.value,
            generation_mode=generation_mode.value,
            variants_json=variants_to_json(variants),
            version=1,
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def update_variants(
        self,
        row: QueryExpansionSetRow,
        *,
        variants: list[QueryExpansionVariant],
        status: QueryExpansionSetStatus,
        approved_by: str | None = None,
    ) -> QueryExpansionSetRow:
        row.variants_json = variants_to_json(variants)
        row.status = status.value
        if status == QueryExpansionSetStatus.APPROVED:
            row.approved_at = datetime.now(UTC)
            row.approved_by = approved_by
        await self._session.flush()
        return row