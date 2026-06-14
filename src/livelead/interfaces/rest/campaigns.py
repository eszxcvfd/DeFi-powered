from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.campaigns.e2e_lineage import resolve_parent_for_create
from livelead.application.campaigns.list_tree import build_campaign_forest, flatten_forest
from livelead.application.campaigns.parse import parse_create_body, parse_patch_body
from livelead.domain.campaigns.lineage import display_source_label
from livelead.infrastructure.db.models import CampaignRow
from livelead.infrastructure.db.repositories.campaigns import CampaignRepository
from livelead.interfaces.auth.creation_context import CreationContext, get_creation_context
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
    require_scoring_editor,
)
from livelead.interfaces.rest.campaigns_schemas import (
    CampaignCreateSchema,
    CampaignDetailSchema,
    CampaignPatchSchema,
    CampaignSummarySchema,
    DateRangeSchema,
    IcpCriteriaSchema,
)
from livelead.interfaces.rest.deps import get_db_session

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _summary_from_node(node) -> CampaignSummarySchema:
    c = node.campaign
    return CampaignSummarySchema(
        id=c.id,
        name=c.name,
        target_industry=c.target_industry,
        status=c.status.value,
        updated_at=c.updated_at,
        parent_campaign_id=node.parent_campaign_id,
        parent_name=node.parent_name,
        created_by_actor=node.created_by_actor,
        creation_source=node.creation_source,
        creation_source_label=node.creation_source_label,
        automation_run_id=node.automation_run_id,
        child_count=node.child_count,
        depth=node.depth,
    )


def _to_detail(
    campaign, *, parent_name: str | None = None, child_count: int = 0
) -> CampaignDetailSchema:
    return CampaignDetailSchema(
        id=campaign.id,
        organization_id=campaign.organization_id,
        name=campaign.name,
        description=campaign.description,
        target_industry=campaign.target_industry,
        product_or_service_focus=campaign.product_or_service_focus,
        market_regions=list(campaign.market_regions),
        languages=list(campaign.languages),
        timezone=campaign.timezone,
        date_range=DateRangeSchema(
            start=campaign.date_range.start,
            end=campaign.date_range.end,
        ),
        positive_keywords=list(campaign.positive_keywords),
        exclude_keywords=list(campaign.exclude_keywords),
        icp=IcpCriteriaSchema(
            industry=campaign.icp.industry,
            organization_type=campaign.icp.organization_type,
            company_size=campaign.icp.company_size,
            role_or_title_targets=list(campaign.icp.role_or_title_targets),
            country_or_region=campaign.icp.country_or_region,
            pain_points=list(campaign.icp.pain_points),
            use_cases=list(campaign.icp.use_cases),
            positive_keywords=list(campaign.icp.positive_keywords),
            excluded_keywords=list(campaign.icp.excluded_keywords),
        ),
        scoring_weights=dict(campaign.scoring_weights.weights),
        status=campaign.status.value,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        parent_campaign_id=campaign.parent_campaign_id,
        parent_name=parent_name,
        created_by_actor=campaign.created_by_actor,
        creation_source=campaign.creation_source,
        creation_source_label=display_source_label(campaign.creation_source),
        automation_run_id=campaign.automation_run_id,
        child_count=child_count,
    )


@router.get("", response_model=list[CampaignSummarySchema])
async def list_campaigns(
    flat: bool = Query(default=True, description="Return tree order with depth for UI indentation"),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    repo = CampaignRepository(session)
    campaigns = await repo.list_for_organization(tenant.organization_id)
    forest = build_campaign_forest(campaigns)
    nodes = flatten_forest(forest) if flat else [n for n in flatten_forest(forest)]
    await session.commit()
    return [_summary_from_node(n) for n in nodes]


@router.post("", response_model=CampaignDetailSchema, status_code=201)
async def create_campaign(
    body: CampaignCreateSchema,
    tenant: TenantContext = Depends(get_tenant_context),
    creation: CreationContext = Depends(get_creation_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_scoring_editor(tenant)
    parsed, errors = parse_create_body(body.model_dump())
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    assert parsed is not None
    parent_id = await resolve_parent_for_create(
        session,
        tenant.organization_id,
        creation.creation_source,
        body.parent_campaign_id,
    )
    repo = CampaignRepository(session)
    row = CampaignRepository.new_row_from_payload(
        tenant.organization_id,
        {
            "name": parsed.name,
            "description": parsed.description,
            "target_industry": parsed.target_industry,
            "product_or_service_focus": parsed.product_or_service_focus,
            "market_regions": parsed.market_regions,
            "languages": parsed.languages,
            "timezone": parsed.timezone,
            "date_range": parsed.date_range,
            "positive_keywords": parsed.positive_keywords,
            "exclude_keywords": parsed.exclude_keywords,
            "icp": parsed.icp,
            "scoring_weights": parsed.scoring_weights,
            "status": parsed.status,
        },
        parent_campaign_id=parent_id,
        created_by_actor=creation.created_by_actor,
        creation_source=creation.creation_source,
        automation_run_id=creation.automation_run_id,
    )
    campaign = await repo.add(row)
    parent_name = None
    if parent_id:
        parent = await repo.get(parent_id, tenant.organization_id)
        parent_name = parent.name if parent else None
    await session.commit()
    return _to_detail(campaign, parent_name=parent_name, child_count=0)


@router.get("/{campaign_id}", response_model=CampaignDetailSchema)
async def get_campaign(
    campaign_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    repo = CampaignRepository(session)
    campaign = await repo.get(campaign_id, tenant.organization_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="campaign not found")
    parent_name = None
    if campaign.parent_campaign_id:
        parent = await repo.get(campaign.parent_campaign_id, tenant.organization_id)
        parent_name = parent.name if parent else None
    all_c = await repo.list_for_organization(tenant.organization_id)
    child_count = sum(1 for c in all_c if c.parent_campaign_id == campaign_id)
    return _to_detail(campaign, parent_name=parent_name, child_count=child_count)


@router.patch("/{campaign_id}", response_model=CampaignDetailSchema)
async def patch_campaign(
    campaign_id: UUID,
    body: CampaignPatchSchema,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_scoring_editor(tenant)
    patch, errors = parse_patch_body(body.model_dump(exclude_unset=True))
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    result = await session.execute(
        select(CampaignRow).where(
            CampaignRow.id == str(campaign_id),
            CampaignRow.organization_id == str(tenant.organization_id),
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="campaign not found")
    repo = CampaignRepository(session)
    await repo.apply_patch(row, patch or {})
    await session.commit()
    return await get_campaign(campaign_id, tenant, session)
