from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService, make_actor_from_role
from livelead.application.content.service import ContentService
from livelead.domain.audit.enums import (
    AuditAction,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditTarget
from livelead.domain.content.handoff import may_handoff_content
from livelead.domain.content.review import is_ready_for_later_use
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.content_schemas import (
    ContentContextPreviewSchema,
    ContentDraftDetailSchema,
    ContentDraftPatchSchema,
    ContentGenerateRequestSchema,
    ContentGenerateResponseSchema,
    ContentGenerationSettingsSchema,
    ContentHandoffActionSchema,
    ContentHandoffRecordSchema,
    ContentReviewActionSchema,
    ContentReviewDecisionSchema,
    ContentRiskFlagSchema,
    ContentSubmitReviewSchema,
)
from livelead.interfaces.rest.deps import get_db_session
from livelead.interfaces.rest.request_context import capture_request_context

router = APIRouter(tags=["content"])


async def _record_audit(
    session: AsyncSession,
    tenant: TenantContext,
    request: Request,
    *,
    action: AuditAction,
    target_id: str,
    target_display: str,
    outcome: AuditOutcome,
    workflow: str,
    metadata: dict | None = None,
) -> None:
    try:
        await AuditService(session).emit(
            organization_id=tenant.organization_id,
            actor=make_actor_from_role(tenant.actor_role),
            action=action,
            target=AuditTarget(
                target_type=AuditTargetType.CONTENT_DRAFT,
                target_id=target_id,
                display=target_display,
            ),
            outcome=outcome,
            context=capture_request_context(request, workflow=workflow),
            metadata=metadata,
        )
    except Exception:
        # Audit must never block the originating workflow.
        pass


def _draft_detail(
    d, history: list | None = None, handoff_history: list | None = None
) -> ContentDraftDetailSchema:
    assert d.metadata
    status = d.review_status
    handoffs = handoff_history or []
    latest = handoffs[0] if handoffs else None
    return ContentDraftDetailSchema(
        id=d.id,
        event_id=d.event_id,
        variant_index=d.variant_index,
        review_status=status.value,
        body_revision=d.body_revision,
        reviewer_assignee=d.reviewer_assignee,
        ready_for_use=is_ready_for_later_use(status),
        usage_status=d.usage_status.value,
        handoff_available=may_handoff_content(status),
        latest_handoff_at=latest.created_at if latest else None,
        latest_handoff_actor=latest.actor if latest else "",
        settings=ContentGenerationSettingsSchema(
            content_type=d.settings.content_type.value,
            platform=d.settings.platform.value,
            language=d.settings.language,
            tone=d.settings.tone,
            length=d.settings.length,
            market_context=d.settings.market_context,
            cta=d.settings.cta,
            variant_count=d.settings.variant_count,
        ),
        body_text=d.body_text,
        risk_flags=[
            ContentRiskFlagSchema(code=f.code.value, message=f.message, severity=f.severity)
            for f in d.risk_flags
        ],
        provider=d.metadata.provider,
        model=d.metadata.model,
        prompt_template_version=d.metadata.prompt_template_version,
        input_context_summary=d.metadata.input_context_summary,
        last_editor=d.metadata.last_editor if d.metadata else "system",
        generated_at=d.metadata.generated_at if d.metadata else None,
        updated_at=d.updated_at,
        review_history=[
            ContentReviewDecisionSchema(
                id=h.id,
                action=h.action,
                from_status=h.from_status,
                to_status=h.to_status,
                actor=h.actor,
                note=h.note,
                body_revision=h.body_revision,
                created_at=h.created_at,
            )
            for h in (history or [])
        ],
        handoff_history=[
            ContentHandoffRecordSchema(
                id=h.id,
                action=h.action,
                actor=h.actor,
                export_format=h.export_format,
                body_revision=h.body_revision,
                created_at=h.created_at,
            )
            for h in handoffs
        ],
    )


def _preview_schema(p) -> ContentContextPreviewSchema:
    return ContentContextPreviewSchema(
        event_title=p.event_title,
        event_description=p.event_description,
        campaign_focus=p.campaign_focus,
        score_summary=p.score_summary,
        audience_summary=p.audience_summary,
        plan_task_count=p.plan_task_count,
        notes=list(p.notes),
    )


async def _detail_with_history(svc: ContentService, d) -> ContentDraftDetailSchema:
    hist = await svc.list_review_history(d.id)
    handoff = await svc.list_handoff_history(d.id)
    return _draft_detail(d, hist, handoff)


@router.post("/content/generate", response_model=ContentGenerateResponseSchema)
async def generate_content(
    body: ContentGenerateRequestSchema,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ContentService(session)
    settings = ContentService.settings_from_payload(body.settings.model_dump())
    preview, drafts, errors = await svc.generate(body.event_id, tenant.organization_id, settings)
    if errors:
        code = 404 if "not found" in errors[0] else 400
        raise HTTPException(status_code=code, detail=errors[0])
    assert preview
    await session.commit()
    return ContentGenerateResponseSchema(
        context=_preview_schema(preview),
        drafts=[_draft_detail(d) for d in drafts],
    )


@router.get("/events/{event_id}/content/context", response_model=ContentContextPreviewSchema)
async def content_context(
    event_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    preview = await ContentService(session).preview_context(event_id, tenant.organization_id)
    if not preview:
        raise HTTPException(status_code=404, detail="event not found")
    await session.commit()
    return _preview_schema(preview)


@router.get("/events/{event_id}/content/drafts", response_model=list[ContentDraftDetailSchema])
async def list_content_drafts(
    event_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ContentService(session)
    drafts = await svc.list_drafts(event_id, tenant.organization_id)
    if drafts is None:
        raise HTTPException(status_code=404, detail="event not found")
    out = []
    for d in drafts:
        out.append(await _detail_with_history(svc, d))
    await session.commit()
    return out


@router.patch(
    "/events/{event_id}/content/drafts/{draft_id}", response_model=ContentDraftDetailSchema
)
async def patch_content_draft(
    event_id: UUID,
    draft_id: UUID,
    body: ContentDraftPatchSchema,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ContentService(session)
    updated = await svc.update_draft(
        event_id,
        draft_id,
        tenant.organization_id,
        body.body_text,
        editor=body.editor,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="draft not found")
    await session.commit()
    return await _detail_with_history(svc, updated)


@router.post(
    "/events/{event_id}/content/drafts/{draft_id}/submit-for-review",
    response_model=ContentDraftDetailSchema,
)
async def submit_for_review(
    event_id: UUID,
    draft_id: UUID,
    body: ContentSubmitReviewSchema,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ContentService(session)
    try:
        updated = await svc.submit_for_review(
            event_id,
            draft_id,
            tenant.organization_id,
            actor=tenant.actor_role,
            assignee=body.assignee,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid review transition") from None
    if not updated:
        raise HTTPException(status_code=404, detail="draft not found")
    await _record_audit(
        session,
        tenant,
        request,
        action=AuditAction.CONTENT_SUBMITTED_FOR_REVIEW,
        target_id=str(draft_id),
        target_display=f"draft {draft_id}",
        outcome=AuditOutcome.SUCCEEDED,
        workflow="content.review.submit",
        metadata={"event_id": str(event_id), "assignee": body.assignee},
    )
    await session.commit()
    return await _detail_with_history(svc, updated)


@router.post("/content/{draft_id}/approve", response_model=ContentDraftDetailSchema)
async def approve_content(
    draft_id: UUID,
    body: ContentReviewActionSchema,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ContentService(session)
    try:
        updated = await svc.approve_draft(
            body.event_id,
            draft_id,
            tenant.organization_id,
            actor=body.actor,
            actor_role=tenant.actor_role,
            note=body.note,
        )
    except PermissionError:
        await _record_audit(
            session,
            tenant,
            request,
            action=AuditAction.CONTENT_APPROVED,
            target_id=str(draft_id),
            target_display=f"draft {draft_id}",
            outcome=AuditOutcome.DENIED,
            workflow="content.review.approve",
            metadata={"event_id": str(body.event_id), "reason": "role cannot approve"},
        )
        raise HTTPException(status_code=403, detail="role cannot approve content") from None
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid review transition") from None
    if not updated:
        raise HTTPException(status_code=404, detail="draft not found")
    await _record_audit(
        session,
        tenant,
        request,
        action=AuditAction.CONTENT_APPROVED,
        target_id=str(draft_id),
        target_display=f"draft {draft_id}",
        outcome=AuditOutcome.SUCCEEDED,
        workflow="content.review.approve",
        metadata={"event_id": str(body.event_id), "actor": body.actor},
    )
    await session.commit()
    return await _detail_with_history(svc, updated)


@router.post("/content/{draft_id}/reject", response_model=ContentDraftDetailSchema)
async def reject_content(
    draft_id: UUID,
    body: ContentReviewActionSchema,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ContentService(session)
    try:
        updated = await svc.reject_draft(
            body.event_id,
            draft_id,
            tenant.organization_id,
            actor=body.actor,
            actor_role=tenant.actor_role,
            note=body.note,
        )
    except PermissionError:
        await _record_audit(
            session,
            tenant,
            request,
            action=AuditAction.CONTENT_REJECTED,
            target_id=str(draft_id),
            target_display=f"draft {draft_id}",
            outcome=AuditOutcome.DENIED,
            workflow="content.review.reject",
            metadata={"event_id": str(body.event_id), "reason": "role cannot reject"},
        )
        raise HTTPException(status_code=403, detail="role cannot reject content") from None
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid review transition") from None
    if not updated:
        raise HTTPException(status_code=404, detail="draft not found")
    await _record_audit(
        session,
        tenant,
        request,
        action=AuditAction.CONTENT_REJECTED,
        target_id=str(draft_id),
        target_display=f"draft {draft_id}",
        outcome=AuditOutcome.SUCCEEDED,
        workflow="content.review.reject",
        metadata={"event_id": str(body.event_id), "actor": body.actor},
    )
    await session.commit()
    return await _detail_with_history(svc, updated)


@router.post("/content/{draft_id}/record-copy", response_model=ContentDraftDetailSchema)
async def record_content_copy(
    draft_id: UUID,
    body: ContentHandoffActionSchema,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ContentService(session)
    try:
        updated = await svc.record_copy_handoff(
            body.event_id,
            draft_id,
            tenant.organization_id,
            actor=body.actor,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="content not approved for handoff") from None
    if not updated:
        raise HTTPException(status_code=404, detail="draft not found")
    await session.commit()
    return await _detail_with_history(svc, updated)


@router.get("/content/{draft_id}/export")
async def export_content(
    draft_id: UUID,
    event_id: UUID = Query(...),
    format: str = Query("markdown", alias="format"),
    actor: str = Query("analyst"),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ContentService(session)
    try:
        result = await svc.export_approved(
            event_id,
            draft_id,
            tenant.organization_id,
            fmt=format,
            actor=actor,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    if not result:
        raise HTTPException(status_code=404, detail="draft not found")
    media_type, filename, body_text = result
    await session.commit()
    return Response(
        content=body_text,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/content/{draft_id}/mark-used", response_model=ContentDraftDetailSchema)
async def mark_content_used(
    draft_id: UUID,
    body: ContentHandoffActionSchema,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ContentService(session)
    try:
        updated = await svc.mark_used(
            body.event_id,
            draft_id,
            tenant.organization_id,
            actor=body.actor,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    if not updated:
        raise HTTPException(status_code=404, detail="draft not found")
    await session.commit()
    return await _detail_with_history(svc, updated)
