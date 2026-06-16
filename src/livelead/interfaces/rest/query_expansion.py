"""Query expansion REST API (US-036)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.application.query_expansion.service import (
    QueryExpansionService,
    QueryExpansionValidationError,
    parse_patch_variants,
)
from livelead.domain.audit.enums import AuditAction, AuditOutcome, AuditTargetType
from livelead.domain.audit.model import AuditTarget
from livelead.infrastructure.db.models import QueryExpansionSetRow
from livelead.infrastructure.db.repositories.query_expansion import variants_from_json
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
    require_scoring_editor,
)
from livelead.interfaces.rest.deps import get_db_session
from livelead.interfaces.rest.request_context import capture_request_context

router = APIRouter(tags=["query-expansion"])


class QueryExpansionVariantBody(BaseModel):
    text: str
    variant_type: str
    source: str
    confidence: float | None = None
    assumption: str | None = None
    user_edited: bool = False
    removed: bool = False


class PatchQueryExpansionBody(BaseModel):
    variants: list[QueryExpansionVariantBody] | None = None
    approve: bool = False


class QueryExpansionView(BaseModel):
    id: UUID
    campaign_id: UUID
    status: str
    generation_mode: str
    version: int
    requires_review: bool
    grouped_variants: dict[str, list[dict]]
    approved_at: datetime | None = None


def _grouped(variants: list) -> dict[str, list[dict]]:
    from livelead.domain.query_expansion.rules import variant_to_dict

    groups: dict[str, list[dict]] = {}
    for v in variants:
        if v.removed:
            continue
        key = v.variant_type.value
        groups.setdefault(key, []).append(variant_to_dict(v))
    return groups


def _to_view(row: QueryExpansionSetRow) -> QueryExpansionView:
    from livelead.domain.query_expansion.models import QueryExpansionGenerationMode
    from livelead.domain.query_expansion.rules import set_requires_review

    variants = variants_from_json(row.variants_json)
    mode = QueryExpansionGenerationMode(row.generation_mode)
    return QueryExpansionView(
        id=UUID(row.id),
        campaign_id=UUID(row.campaign_id),
        status=row.status,
        generation_mode=row.generation_mode,
        version=row.version,
        requires_review=set_requires_review(variants, mode),
        grouped_variants=_grouped(variants),
        approved_at=row.approved_at,
    )


async def _audit(
    request: Request | None,
    session: AsyncSession,
    tenant: TenantContext,
    *,
    action: AuditAction,
    set_id: str,
    campaign_id: str,
    metadata: dict,
) -> None:
    ctx = (
        capture_request_context(request, workflow="query_expansion")
        if request is not None
        else make_context(workflow="query_expansion")
    )
    await AuditService(session).emit(
        organization_id=tenant.organization_id,
        actor=make_actor_from_role(tenant.actor_role),
        action=action,
        target=AuditTarget(
            target_type=AuditTargetType.QUERY_EXPANSION_SET,
            target_id=set_id,
            display=f"query_expansion/{set_id}",
        ),
        outcome=AuditOutcome.SUCCEEDED,
        context=ctx,
        metadata={"campaign_id": campaign_id, **metadata},
    )


@router.post(
    "/campaigns/{campaign_id}/query-expansions:generate",
    response_model=QueryExpansionView,
    status_code=201,
)
async def generate_query_expansion(
    campaign_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_scoring_editor(tenant)
    svc = QueryExpansionService(session)
    try:
        row = await svc.generate(
            organization_id=tenant.organization_id,
            campaign_id=campaign_id,
            actor=tenant.actor_role,
        )
    except QueryExpansionValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await _audit(
        request,
        session,
        tenant,
        action=AuditAction.QUERY_EXPANSION_GENERATED,
        set_id=row.id,
        campaign_id=str(campaign_id),
        metadata={"generation_mode": row.generation_mode, "status": row.status},
    )
    await session.commit()
    return _to_view(row)


@router.get("/campaigns/{campaign_id}/query-expansions", response_model=QueryExpansionView | None)
async def get_query_expansion(
    campaign_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = QueryExpansionService(session)
    row = await svc.get_latest(campaign_id, tenant.organization_id)
    if not row:
        return None
    return _to_view(row)


@router.patch("/campaigns/{campaign_id}/query-expansions", response_model=QueryExpansionView)
async def patch_query_expansion(
    campaign_id: UUID,
    body: PatchQueryExpansionBody,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_scoring_editor(tenant)
    svc = QueryExpansionService(session)
    row = await svc.get_latest(campaign_id, tenant.organization_id)
    if not row or row.campaign_id != str(campaign_id):
        raise HTTPException(status_code=404, detail="no query expansion set for campaign")
    if body.variants is not None:
        variants = parse_patch_variants([v.model_dump() for v in body.variants])
    else:
        variants = variants_from_json(row.variants_json)
    row = await svc.patch_set(row, variants=variants, approve=body.approve, actor=tenant.actor_role)
    action = (
        AuditAction.QUERY_EXPANSION_APPROVED
        if body.approve
        else AuditAction.QUERY_EXPANSION_UPDATED
    )
    await _audit(
        request,
        session,
        tenant,
        action=action,
        set_id=row.id,
        campaign_id=str(campaign_id),
        metadata={"status": row.status, "approve": body.approve},
    )
    await session.commit()
    return _to_view(row)