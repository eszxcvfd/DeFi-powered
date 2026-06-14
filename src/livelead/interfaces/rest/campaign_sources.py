from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.sources.policy import evaluate_source_policy
from livelead.infrastructure.db.models import CampaignRow, SourceRow
from livelead.infrastructure.db.repositories.sources import SourceRepository
from livelead.infrastructure.db.source_mappers import row_to_source
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.deps import get_db_session

router = APIRouter(prefix="/campaigns", tags=["campaign-sources"])


class CampaignSourcesSchema(BaseModel):
    source_ids: list[UUID]


class RunnableSourceSchema(BaseModel):
    id: UUID
    name: str
    domain: str
    connector_type: str
    runnable: bool
    denied_reasons: list[str]
    preferred_over_browser: bool


def _view(s) -> RunnableSourceSchema:
    d = evaluate_source_policy(s)
    return RunnableSourceSchema(
        id=s.id,
        name=s.name,
        domain=s.domain,
        connector_type=s.connector_type.value,
        runnable=d.runnable,
        denied_reasons=list(d.reasons),
        preferred_over_browser=d.preferred_over_browser,
    )


@router.get("/runnable-sources", response_model=list[RunnableSourceSchema])
async def runnable_catalog(
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    repo = SourceRepository(session)
    sources = await repo.list_for_organization(tenant.organization_id)
    sources = sorted(
        sources,
        key=lambda s: (0 if evaluate_source_policy(s).preferred_over_browser else 1, s.domain),
    )
    return [_view(s) for s in sources]


@router.get("/{campaign_id}/sources", response_model=list[RunnableSourceSchema])
async def list_campaign_sources(
    campaign_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    camp = await session.execute(
        select(CampaignRow).where(
            CampaignRow.id == str(campaign_id),
            CampaignRow.organization_id == str(tenant.organization_id),
        )
    )
    if not camp.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="campaign not found")
    repo = SourceRepository(session)
    ids = await repo.list_campaign_source_ids(campaign_id, tenant.organization_id)
    if not ids:
        return await runnable_catalog(tenant, session)
    result = await session.execute(
        select(SourceRow).where(
            SourceRow.organization_id == str(tenant.organization_id),
            SourceRow.id.in_([str(i) for i in ids]),
        )
    )
    return [_view(row_to_source(row)) for row in result.scalars().all()]


@router.put("/{campaign_id}/sources", response_model=list[RunnableSourceSchema])
async def set_campaign_sources(
    campaign_id: UUID,
    body: CampaignSourcesSchema,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    camp = await session.execute(
        select(CampaignRow).where(
            CampaignRow.id == str(campaign_id),
            CampaignRow.organization_id == str(tenant.organization_id),
        )
    )
    if not camp.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="campaign not found")
    repo = SourceRepository(session)
    for sid in body.source_ids:
        row = await repo.get(sid, tenant.organization_id)
        if not row:
            raise HTTPException(status_code=404, detail=f"source {sid} not found")
        d = evaluate_source_policy(row_to_source(row))
        if not d.runnable:
            raise HTTPException(
                status_code=409,
                detail={"message": "source not runnable", "reasons": list(d.reasons), "source_id": str(sid)},
            )
    await repo.set_campaign_sources(campaign_id, tenant.organization_id, body.source_ids)
    await session.commit()
    return await list_campaign_sources(campaign_id, tenant, session)