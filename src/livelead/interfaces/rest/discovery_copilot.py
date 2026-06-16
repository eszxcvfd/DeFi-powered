"""Discovery copilot REST API (US-037)."""

from __future__ import annotations

import json
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
from livelead.domain.discovery_copilot.schema import CopilotSchemaError
from livelead.application.ai_feedback.service import AiFeedbackService, resolve_feedback_actor_key
from livelead.application.discovery_copilot.service import (
    DiscoveryCopilotService,
    DiscoveryCopilotValidationError,
)
from livelead.domain.ai_feedback.models import AiFeedbackTargetType
from livelead.domain.audit.enums import AuditAction, AuditOutcome, AuditTargetType
from livelead.domain.audit.model import AuditTarget
from livelead.infrastructure.db.models import DiscoveryCopilotResponseRow
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
    require_scoring_editor,
)
from livelead.interfaces.rest.deps import get_db_session
from livelead.interfaces.rest.events_schemas import ViewerFeedbackSchema
from livelead.interfaces.rest.request_context import capture_request_context

router = APIRouter(tags=["discovery-copilot"])


class DiscoveryCopilotRespondBody(BaseModel):
    question: str = Field(..., min_length=8, max_length=2000)


class DiscoveryCopilotAcceptBody(BaseModel):
    response_id: UUID


class DiscoveryCopilotResponseView(BaseModel):
    id: UUID
    campaign_id: UUID
    question: str
    confidence: float
    provider_id: str
    model_id: str
    structured: dict
    accepted_at: datetime | None = None
    query_expansion_set_id: UUID | None = None
    created_at: datetime
    viewer_feedback: ViewerFeedbackSchema | None = None


class AcceptCopilotView(BaseModel):
    copilot_response_id: UUID
    query_expansion_set_id: UUID
    expansion_status: str


def _feedback_from_projection(proj) -> ViewerFeedbackSchema | None:
    if proj is None:
        return None
    return ViewerFeedbackSchema(
        state=proj.state,
        reason_code=proj.reason_code,
        note=proj.note,
        updated_at=proj.updated_at,
    )


def _to_view(row: DiscoveryCopilotResponseRow, viewer_feedback: ViewerFeedbackSchema | None = None) -> DiscoveryCopilotResponseView:
    structured = json.loads(row.response_json or "{}")
    return DiscoveryCopilotResponseView(
        id=UUID(row.id),
        campaign_id=UUID(row.campaign_id),
        question=row.question,
        confidence=row.confidence,
        provider_id=row.provider_id,
        model_id=row.model_id,
        structured=structured,
        accepted_at=row.accepted_at,
        query_expansion_set_id=UUID(row.query_expansion_set_id)
        if row.query_expansion_set_id
        else None,
        created_at=row.created_at,
        viewer_feedback=viewer_feedback,
    )


async def _audit(
    request: Request | None,
    session: AsyncSession,
    tenant: TenantContext,
    *,
    action: AuditAction,
    response_id: str,
    campaign_id: str,
    metadata: dict,
) -> None:
    ctx = (
        capture_request_context(request, workflow="discovery_copilot")
        if request is not None
        else make_context(workflow="discovery_copilot")
    )
    await AuditService(session).emit(
        organization_id=tenant.organization_id,
        actor=make_actor_from_role(tenant.actor_role),
        action=action,
        target=AuditTarget(
            target_type=AuditTargetType.DISCOVERY_COPILOT_RESPONSE,
            target_id=response_id,
            display=f"discovery_copilot/{response_id}",
        ),
        outcome=AuditOutcome.SUCCEEDED,
        context=ctx,
        metadata={"campaign_id": campaign_id, **metadata},
    )


@router.post(
    "/campaigns/{campaign_id}/discovery-copilot:respond",
    response_model=DiscoveryCopilotResponseView,
    status_code=201,
)
async def discovery_copilot_respond(
    campaign_id: UUID,
    body: DiscoveryCopilotRespondBody,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_scoring_editor(tenant)
    svc = DiscoveryCopilotService(session)
    try:
        row = await svc.respond(
            organization_id=tenant.organization_id,
            campaign_id=campaign_id,
            question=body.question,
            actor=tenant.actor_role,
        )
    except DiscoveryCopilotValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except CopilotSchemaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    await _audit(
        request,
        session,
        tenant,
        action=AuditAction.DISCOVERY_COPILOT_RESPONDED,
        response_id=row.id,
        campaign_id=str(campaign_id),
        metadata={"confidence": row.confidence, "provider_id": row.provider_id},
    )
    await session.commit()
    actor_key = resolve_feedback_actor_key(actor_id=tenant.actor_id, actor_role=tenant.actor_role)
    fb = await AiFeedbackService(session).get_viewer_projection(
        tenant.organization_id,
        actor_key,
        AiFeedbackTargetType.DISCOVERY_COPILOT_RESPONSE,
        UUID(row.id),
    )
    return _to_view(row, _feedback_from_projection(fb))


@router.get(
    "/campaigns/{campaign_id}/discovery-copilot/responses",
    response_model=list[DiscoveryCopilotResponseView],
)
async def list_discovery_copilot_responses(
    campaign_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = DiscoveryCopilotService(session)
    rows = await svc.list_recent(campaign_id, tenant.organization_id)
    actor_key = resolve_feedback_actor_key(actor_id=tenant.actor_id, actor_role=tenant.actor_role)
    fb_svc = AiFeedbackService(session)
    fb_map = await fb_svc.project_for_viewer(
        tenant.organization_id,
        actor_key,
        AiFeedbackTargetType.DISCOVERY_COPILOT_RESPONSE,
        [UUID(r.id) for r in rows],
    )
    return [_to_view(r, _feedback_from_projection(fb_map.get(UUID(r.id)))) for r in rows]


@router.post(
    "/campaigns/{campaign_id}/discovery-copilot:accept",
    response_model=AcceptCopilotView,
)
async def discovery_copilot_accept(
    campaign_id: UUID,
    body: DiscoveryCopilotAcceptBody,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_scoring_editor(tenant)
    svc = DiscoveryCopilotService(session)
    try:
        copilot_row, expansion_row = await svc.accept_into_query_expansion(
            response_id=body.response_id,
            organization_id=tenant.organization_id,
            campaign_id=campaign_id,
            actor=tenant.actor_role,
        )
    except DiscoveryCopilotValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _audit(
        request,
        session,
        tenant,
        action=AuditAction.DISCOVERY_COPILOT_ACCEPTED,
        response_id=copilot_row.id,
        campaign_id=str(campaign_id),
        metadata={"query_expansion_set_id": expansion_row.id},
    )
    await session.commit()
    return AcceptCopilotView(
        copilot_response_id=UUID(copilot_row.id),
        query_expansion_set_id=UUID(expansion_row.id),
        expansion_status=expansion_row.status,
    )