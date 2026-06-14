"""Ensure a single E2E parent campaign; attach Playwright children under it."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.campaigns.lineage import E2E_ROOT_NAME, E2E_ROOT_SOURCE
from livelead.domain.campaigns.models import Campaign
from livelead.infrastructure.db.mappers import row_to_campaign
from livelead.infrastructure.db.models import CampaignRow


async def get_or_create_e2e_root(session: AsyncSession, organization_id: UUID) -> Campaign:
    org = str(organization_id)
    result = await session.execute(
        select(CampaignRow).where(
            CampaignRow.organization_id == org,
            CampaignRow.creation_source == E2E_ROOT_SOURCE,
            CampaignRow.parent_campaign_id.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    if row:
        return row_to_campaign(row)
    now = datetime.now(UTC)
    row = CampaignRow(
        id=str(uuid4()),
        organization_id=org,
        name=E2E_ROOT_NAME,
        description="Parent container for Playwright / automated test campaigns. Children are test runs.",
        target_industry="Automation",
        product_or_service_focus="",
        market_regions_json="[]",
        languages_json="[]",
        timezone="UTC",
        icp_json="{}",
        scoring_weights_json="{}",
        status="draft",
        parent_campaign_id=None,
        created_by_actor="system",
        creation_source=E2E_ROOT_SOURCE,
        automation_run_id=None,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.flush()
    return row_to_campaign(row)


async def resolve_parent_for_create(
    session: AsyncSession,
    organization_id: UUID,
    creation_source: str,
    explicit_parent: UUID | None,
) -> UUID | None:
    if explicit_parent:
        return explicit_parent
    if creation_source == "playwright":
        root = await get_or_create_e2e_root(session, organization_id)
        return root.id
    return None
