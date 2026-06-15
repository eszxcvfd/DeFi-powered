"""Supervised browser session API (US-020)."""

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService, make_actor_from_role
from livelead.application.browser.debug_artifacts import BrowserDebugArtifactService
from livelead.application.browser.profiles import BrowserProfileService, ProfileBlocked
from livelead.application.browser.service import (
    BrowserSessionService,
    InvalidLaunchContext,
    session_status_view,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditTarget
from livelead.infrastructure.secrets.vault import SecretVault
from livelead.domain.browser.actions import BrowserActionType
from livelead.domain.browser.policy import BrowserLaunchDenied
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.deps import get_db_session
from livelead.interfaces.rest.request_context import capture_request_context

router = APIRouter(prefix="/browser-sessions", tags=["browser-sessions"])


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
                target_type=AuditTargetType.BROWSER_CONFIRMATION,
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


class BrowserSessionCreateSchema(BaseModel):
    event_id: UUID | None = None
    source_id: UUID | None = None
    initial_url: str | None = None
    browser_profile_id: UUID | None = None


class BrowserActionRequestSchema(BaseModel):
    action_type: str
    parameters: dict = {}


class BrowserActionResultSchema(BaseModel):
    action_type: str
    lifecycle: str
    summary: str
    detail: str | None = None
    policy_reason: str | None = None
    current_url: str | None = None
    text_preview: str | None = None
    confirmation_id: str | None = None
    confirmation_state: str | None = None
    preview: dict | None = None
    expires_at: str | None = None
    requested_by: str | None = None


class BrowserSessionViewSchema(BaseModel):
    id: UUID
    state: str
    engine: str
    current_url: str
    runtime_seconds: int
    latest_action_summary: str
    isolation: dict
    target: dict
    stop_requested: bool
    terminal: bool
    error_summary: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    created_at: str
    debug_enabled: bool = False
    latest_artifact_summary: str = ""


class BrowserDebugToggleSchema(BaseModel):
    enabled: bool = True


class BrowserArtifactViewSchema(BaseModel):
    id: str
    session_id: str
    artifact_type: str
    capture_mode: str
    status: str
    content_type: str
    byte_size: int
    captured_by: str
    summary: str
    redacted: bool
    expires_at: str
    created_at: str | None = None
    policy_reason: str | None = None


def _view(record) -> BrowserSessionViewSchema:
    payload = session_status_view(record)
    return BrowserSessionViewSchema(
        id=UUID(payload["id"]), **{k: v for k, v in payload.items() if k != "id"}
    )


@router.post("", response_model=BrowserSessionViewSchema, status_code=201)
async def create_browser_session(
    body: BrowserSessionCreateSchema,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    if tenant.actor_role not in ("analyst", "admin", "owner"):
        raise HTTPException(status_code=403, detail="role cannot open browser sessions")
    svc = BrowserSessionService(session, request.app.state.settings)
    profile_svc = BrowserProfileService(session, SecretVault(request.app.state.settings.secret_master_key))
    isolation_key: str | None = None
    profile_boundary: str | None = None
    storage_state: dict | None = None
    try:
        if body.browser_profile_id:
            prow, isolation_key, profile_boundary = await profile_svc.assert_launch_eligible(
                body.browser_profile_id, tenant.organization_id
            )
            storage_state = profile_svc.load_storage_state_for_runtime(prow)
        if body.event_id:
            await svc.provision_playwright_from_evidence(
                tenant.organization_id, body.event_id, tenant.actor_role
            )
            record = await svc.create_for_event(
                tenant.organization_id,
                tenant.actor_role,
                event_id=body.event_id,
                source_id=body.source_id,
            )
        elif body.source_id and body.initial_url:
            record = await svc.create_for_source(
                tenant.organization_id,
                tenant.actor_role,
                source_id=body.source_id,
                initial_url=body.initial_url,
                browser_profile_id=body.browser_profile_id,
                isolation_key=isolation_key,
                profile_boundary=profile_boundary,
                storage_state=storage_state,
            )
            if body.browser_profile_id:
                await profile_svc.touch_last_used(body.browser_profile_id, tenant.organization_id)
        else:
            raise HTTPException(
                status_code=400,
                detail="provide event_id or (source_id and initial_url)",
            )
    except ProfileBlocked as exc:
        await _record_audit(
            session,
            tenant,
            request,
            action=AuditAction.BROWSER_LAUNCH_DENIED,
            target_id=str(body.browser_profile_id or ""),
            target_display="browser-profile",
            outcome=AuditOutcome.DENIED,
            workflow="browser.launch",
            metadata={"reasons": list(exc.reasons)},
        )
        raise HTTPException(
            status_code=409, detail={"profile_blocked": list(exc.reasons)}
        ) from exc
    except InvalidLaunchContext as exc:
        raise HTTPException(status_code=400, detail={"launch_errors": list(exc.errors)}) from exc
    except BrowserLaunchDenied as exc:
        await _record_audit(
            session,
            tenant,
            request,
            action=AuditAction.BROWSER_LAUNCH_DENIED,
            target_id=str(body.source_id or body.event_id or "unknown"),
            target_display="browser-session",
            outcome=AuditOutcome.DENIED,
            workflow="browser.launch",
            metadata={"reasons": list(exc.reasons)},
        )
        raise HTTPException(status_code=409, detail={"policy_denied": list(exc.reasons)}) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return _view(record)


@router.get("/{session_id}", response_model=BrowserSessionViewSchema)
async def get_browser_session(
    session_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = BrowserSessionService(session)
    record = await svc.get_status(session_id, tenant.organization_id)
    if not record:
        raise HTTPException(status_code=404, detail="session not found")
    await session.commit()
    return _view(record)


@router.post("/{session_id}/actions", response_model=BrowserActionResultSchema)
async def execute_browser_action(
    session_id: UUID,
    body: BrowserActionRequestSchema,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    if tenant.actor_role not in ("analyst", "admin", "owner"):
        raise HTTPException(status_code=403, detail="role cannot run browser actions")
    raw_type = body.action_type.lower().strip()
    try:
        action_type = BrowserActionType(raw_type)
    except ValueError:
        if raw_type == "submit_form":
            action_type = BrowserActionType.SUBMIT_FORM
        else:
            raise HTTPException(status_code=400, detail="unsupported action_type") from None
    svc = BrowserSessionService(session)
    try:
        result = await svc.execute_action(
            session_id,
            tenant.organization_id,
            tenant.actor_role,
            action_type=action_type,
            parameters=body.parameters or {},
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return BrowserActionResultSchema(**result)


@router.post("/{session_id}/stop", response_model=BrowserSessionViewSchema)
async def stop_browser_session(
    session_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    if tenant.actor_role not in ("analyst", "admin", "owner"):
        raise HTTPException(status_code=403, detail="role cannot stop browser sessions")
    svc = BrowserSessionService(session)
    try:
        record = await svc.stop(session_id, tenant.organization_id, tenant.actor_role)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return _view(record)


@router.post("/{session_id}/confirmations/{confirmation_id}/confirm", response_model=BrowserActionResultSchema)
async def confirm_browser_action(
    session_id: UUID,
    confirmation_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    _ = session_id
    if tenant.actor_role not in ("analyst", "admin", "owner"):
        raise HTTPException(status_code=403, detail="role cannot confirm browser actions")
    svc = BrowserSessionService(session)
    try:
        result = await svc.confirm_browser_action(
            confirmation_id,
            tenant.organization_id,
            tenant.actor_role,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await _record_audit(
        session,
        tenant,
        request,
        action=AuditAction.BROWSER_CONFIRMATION_CONFIRMED,
        target_id=str(confirmation_id),
        target_display=f"confirmation {confirmation_id}",
        outcome=AuditOutcome.SUCCEEDED,
        workflow="browser.confirmation.confirm",
        metadata={"lifecycle": result.get("lifecycle", "")},
    )
    await session.commit()
    return BrowserActionResultSchema(**result)


@router.post("/{session_id}/confirmations/{confirmation_id}/cancel", response_model=BrowserActionResultSchema)
async def cancel_browser_action(
    session_id: UUID,
    confirmation_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    _ = session_id
    if tenant.actor_role not in ("analyst", "admin", "owner"):
        raise HTTPException(status_code=403, detail="role cannot cancel browser actions")
    svc = BrowserSessionService(session)
    try:
        result = await svc.cancel_browser_action(
            confirmation_id,
            tenant.organization_id,
            tenant.actor_role,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await _record_audit(
        session,
        tenant,
        request,
        action=AuditAction.BROWSER_CONFIRMATION_CANCELLED,
        target_id=str(confirmation_id),
        target_display=f"confirmation {confirmation_id}",
        outcome=AuditOutcome.SUCCEEDED,
        workflow="browser.confirmation.cancel",
        metadata={"lifecycle": result.get("lifecycle", "")},
    )
    await session.commit()
    return BrowserActionResultSchema(**result)


@router.post("/{session_id}/debug", response_model=dict)
async def set_browser_session_debug(
    session_id: UUID,
    body: BrowserDebugToggleSchema,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    if tenant.actor_role not in ("analyst", "admin", "owner"):
        raise HTTPException(status_code=403, detail="role cannot configure browser debug")
    svc = BrowserDebugArtifactService(session, request.app.state.settings)
    try:
        out = await svc.set_debug_enabled(
            session_id,
            tenant.organization_id,
            tenant.actor_role,
            enabled=body.enabled,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return out


@router.post("/{session_id}/artifacts/screenshot", response_model=BrowserArtifactViewSchema)
async def capture_browser_screenshot(
    session_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    if tenant.actor_role not in ("analyst", "admin", "owner"):
        raise HTTPException(status_code=403, detail="role cannot capture screenshots")
    svc = BrowserDebugArtifactService(session, request.app.state.settings)
    try:
        out = await svc.capture_screenshot(session_id, tenant.organization_id, tenant.actor_role)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    if out.get("status") in ("blocked", "failed"):
        return BrowserArtifactViewSchema(
            id="",
            session_id=str(session_id),
            artifact_type="screenshot",
            capture_mode="manual",
            status=out["status"],
            content_type="",
            byte_size=0,
            captured_by=tenant.actor_role,
            summary=out.get("summary", ""),
            redacted=False,
            expires_at="",
            policy_reason=out.get("policy_reason"),
        )
    return BrowserArtifactViewSchema(**out)


@router.get("/{session_id}/artifacts", response_model=list[BrowserArtifactViewSchema])
async def list_browser_artifacts(
    session_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = BrowserDebugArtifactService(session, request.app.state.settings)
    rows = await svc.list_artifacts(session_id, tenant.organization_id)
    await session.commit()
    return [BrowserArtifactViewSchema(**r) for r in rows]


@router.get("/{session_id}/artifacts/{artifact_id}/download")
async def download_browser_artifact(
    session_id: UUID,
    artifact_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    _ = session_id
    svc = BrowserDebugArtifactService(session, request.app.state.settings)
    try:
        body, content_type, _kind = await svc.read_artifact_bytes(
            artifact_id, tenant.organization_id, tenant.actor_role
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    await session.commit()
    return Response(content=body, media_type=content_type)


@router.get("/{session_id}/stream")
async def stream_browser_session(
    session_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
):
    factory = request.app.state.session_factory

    async def event_gen():
        last_state = None
        for _ in range(80):
            async with factory() as sess:
                svc = BrowserSessionService(sess, request.app.state.settings)
                record = await svc.get_status(session_id, tenant.organization_id)
                if not record:
                    yield 'data: {"type":"browser.error","detail":"not_found"}\n\n'
                    break
                view = session_status_view(record)
                state = view["state"]
                if state != last_state:
                    if last_state is None and state in ("starting", "running", "queued"):
                        yield f"data: {json.dumps({'type': 'browser.session_started', 'state': state})}\n\n"
                    last_state = state
                yield f"data: {json.dumps({'type': 'browser.status', **view})}\n\n"
                if view["terminal"]:
                    yield f"data: {json.dumps({'type': 'browser.session_closed', 'state': state})}\n\n"
                    break
            await asyncio.sleep(0.2)
        yield 'data: {"type":"stream.end"}\n\n'

    return StreamingResponse(event_gen(), media_type="text/event-stream")
