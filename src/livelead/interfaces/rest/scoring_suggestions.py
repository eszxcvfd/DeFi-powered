"""Scoring suggestion REST API (US-039)."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService, make_actor_from_role, make_context
from livelead.application.scoring_suggestions.service import (
    ScoringSuggestionService,
    ScoringSuggestionValidationError,
)
from livelead.domain.audit.enums import AuditAction, AuditOutcome, AuditTargetType
from livelead.domain.audit.model import AuditTarget
from livelead.infrastructure.db.models import ScoringSuggestionSetRow
from livelead.infrastructure.db.repositories.scoring_suggestions import (
    deltas_from_json,
    signals_from_json,
)
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
    require_scoring_editor,
)
from livelead.interfaces.rest.campaigns import _to_detail
from livelead.interfaces.rest.deps import get_db_session
from livelead.interfaces.rest.request_context import capture_request_context

router = APIRouter(tags=["scoring-suggestions"])


class ScoringSuggestionRejectBody(BaseModel):
    review_note: str | None = Field(default=None, max_length=500)


class ScoringWeightDeltaView(BaseModel):
    component: str
    current_weight: float
    proposed_weight: float
    delta: float
    rationale: str


class ScoringSuggestionSignalView(BaseModel):
    kind: str
    summary: str
    count: int
    reason_code: str | None = None


class ScoringSuggestionView(BaseModel):
    id: UUID
    campaign_id: UUID
    status: str
    confidence: float
    summary: str
    caution_notes: list[str]
    assumptions: list[str]
    signals: list[ScoringSuggestionSignalView]
    deltas: list[ScoringWeightDeltaView]
    current_weights: dict[str, float]
    proposed_weights: dict[str, float]
    generated_by: str | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
    review_note: str | None = None
    weight_snapshot_id: UUID | None = None
    created_at: datetime | None = None


class ScoringSuggestionApproveResponse(BaseModel):
    suggestion: ScoringSuggestionView
    campaign: dict


def _to_view(row: ScoringSuggestionSetRow) -> ScoringSuggestionView:
    signals = signals_from_json(row.signals_json)
    deltas = deltas_from_json(row.deltas_json)
    return ScoringSuggestionView(
        id=UUID(row.id),
        campaign_id=UUID(row.campaign_id),
        status=row.status,
        confidence=float(row.confidence or 0),
        summary=row.summary or "",
        caution_notes=json.loads(row.caution_notes_json or "[]"),
        assumptions=json.loads(row.assumptions_json or "[]"),
        signals=[
            ScoringSuggestionSignalView(
                kind=s.kind.value,
                summary=s.summary,
                count=s.count,
                reason_code=s.reason_code,
            )
            for s in signals
        ],
        deltas=[
            ScoringWeightDeltaView(
                component=d.component,
                current_weight=d.current_weight,
                proposed_weight=d.proposed_weight,
                delta=d.delta,
                rationale=d.rationale,
            )
            for d in deltas
        ],
        current_weights=json.loads(row.current_weights_json or "{}"),
        proposed_weights=json.loads(row.proposed_weights_json or "{}"),
        generated_by=row.generated_by,
        decided_by=row.decided_by,
        decided_at=row.decided_at,
        review_note=row.review_note,
        weight_snapshot_id=UUID(row.weight_snapshot_id) if row.weight_snapshot_id else None,
        created_at=row.created_at,
    )


@router.post(
    "/campaigns/{campaign_id}/scoring-suggestions:generate",
    response_model=ScoringSuggestionView,
    status_code=201,
)
async def generate_scoring_suggestions(
    campaign_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_scoring_editor(tenant)
    svc = ScoringSuggestionService(session)
    try:
        row = await svc.generate(
            organization_id=tenant.organization_id,
            campaign_id=campaign_id,
            actor_role=tenant.actor_role,
        )
    except ScoringSuggestionValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    ctx = capture_request_context(request, workflow="scoring_suggestions")
    await AuditService(session).emit(
        organization_id=tenant.organization_id,
        actor=make_actor_from_role(tenant.actor_role),
        action=AuditAction.SCORING_SUGGESTION_GENERATED,
        target=AuditTarget(
            target_type=AuditTargetType.SCORING_SUGGESTION_SET,
            target_id=row.id,
            display=f"scoring_suggestion/{row.id}",
        ),
        outcome=AuditOutcome.SUCCEEDED,
        context=ctx,
        metadata={"campaign_id": str(campaign_id), "confidence": row.confidence},
    )
    await session.commit()
    return _to_view(row)


@router.get(
    "/campaigns/{campaign_id}/scoring-suggestions",
    response_model=list[ScoringSuggestionView],
)
async def list_scoring_suggestions(
    campaign_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ScoringSuggestionService(session)
    try:
        rows = await svc.list_history(tenant.organization_id, campaign_id)
    except ScoringSuggestionValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return [_to_view(r) for r in rows]


@router.post(
    "/campaigns/{campaign_id}/scoring-suggestions/{suggestion_id}:approve",
    response_model=ScoringSuggestionApproveResponse,
)
async def approve_scoring_suggestion(
    campaign_id: UUID,
    suggestion_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_scoring_editor(tenant)
    svc = ScoringSuggestionService(session)
    try:
        row, campaign = await svc.approve(
            organization_id=tenant.organization_id,
            campaign_id=campaign_id,
            suggestion_id=suggestion_id,
            actor_role=tenant.actor_role,
        )
    except ScoringSuggestionValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    parent_name = None
    child_count = 0
    await session.commit()
    detail = _to_detail(campaign, parent_name=parent_name, child_count=child_count)
    return ScoringSuggestionApproveResponse(
        suggestion=_to_view(row),
        campaign=detail.model_dump(mode="json"),
    )


@router.post(
    "/campaigns/{campaign_id}/scoring-suggestions/{suggestion_id}:reject",
    response_model=ScoringSuggestionView,
)
async def reject_scoring_suggestion(
    campaign_id: UUID,
    suggestion_id: UUID,
    body: ScoringSuggestionRejectBody,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_scoring_editor(tenant)
    svc = ScoringSuggestionService(session)
    try:
        row = await svc.reject(
            organization_id=tenant.organization_id,
            campaign_id=campaign_id,
            suggestion_id=suggestion_id,
            actor_role=tenant.actor_role,
            review_note=body.review_note,
        )
    except ScoringSuggestionValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _to_view(row)