"""AI feedback REST API (US-038)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.ai_feedback.service import (
    AiFeedbackService,
    AiFeedbackValidationError,
    resolve_feedback_actor_key,
)
from livelead.domain.ai_feedback.models import AiFeedbackProjection
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context, require_scoring_editor
from livelead.interfaces.rest.deps import get_db_session

router = APIRouter(tags=["ai-feedback"])


class AiFeedbackUpsertBody(BaseModel):
    state: str = Field(..., min_length=3, max_length=32)
    reason_code: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=500)


class ViewerFeedbackView(BaseModel):
    state: str
    reason_code: str | None = None
    note: str | None = None
    updated_at: datetime | None = None


def _projection_to_view(proj: AiFeedbackProjection) -> ViewerFeedbackView:
    return ViewerFeedbackView(
        state=proj.state,
        reason_code=proj.reason_code,
        note=proj.note,
        updated_at=proj.updated_at,
    )


@router.put(
    "/discovery-copilot-responses/{response_id}/feedback",
    response_model=ViewerFeedbackView,
)
async def upsert_discovery_copilot_feedback(
    response_id: UUID,
    body: AiFeedbackUpsertBody,
    _request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_scoring_editor(tenant)
    actor_key = resolve_feedback_actor_key(actor_id=tenant.actor_id, actor_role=tenant.actor_role)
    svc = AiFeedbackService(session)
    try:
        proj = await svc.record_discovery_copilot_feedback(
            organization_id=tenant.organization_id,
            response_id=response_id,
            actor_key=actor_key,
            actor_role=tenant.actor_role,
            state=body.state,
            reason_code=body.reason_code,
            note=body.note,
        )
    except AiFeedbackValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _projection_to_view(proj)


@router.put(
    "/audience-hypotheses/{hypothesis_id}/feedback",
    response_model=ViewerFeedbackView,
)
async def upsert_audience_hypothesis_feedback(
    hypothesis_id: UUID,
    body: AiFeedbackUpsertBody,
    _request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_scoring_editor(tenant)
    actor_key = resolve_feedback_actor_key(actor_id=tenant.actor_id, actor_role=tenant.actor_role)
    svc = AiFeedbackService(session)
    try:
        proj = await svc.record_audience_hypothesis_feedback(
            organization_id=tenant.organization_id,
            hypothesis_id=hypothesis_id,
            actor_key=actor_key,
            actor_role=tenant.actor_role,
            state=body.state,
            reason_code=body.reason_code,
            note=body.note,
        )
    except AiFeedbackValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _projection_to_view(proj)