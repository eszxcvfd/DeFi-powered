"""Live integration toggle admin routes (US-040)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService
from livelead.application.runtime.live_toggles import (
    LiveToggleService,
    LiveToggleValidationError,
)
from livelead.application.runtime.readiness import RuntimeReadinessService
from livelead.domain.runtime.enums import LiveIntegration
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
)
from livelead.interfaces.rest.deps import get_db_session

router = APIRouter(prefix="/admin/live-toggles", tags=["admin-live-toggles"])


class LiveToggleView(BaseModel):
    integration: str
    state: str
    previous_state: str
    updated_at: str | None
    updated_by: str
    approval_note: str


class LiveToggleListResponse(BaseModel):
    toggles: list[LiveToggleView]


class LiveToggleEnableRequest(BaseModel):
    approval_note: str = Field(..., min_length=1, max_length=500)


class LiveToggleDisableRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


def _require_owner_or_admin(ctx: TenantContext) -> None:
    role = ctx.role
    if role is None or role.value not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="owner or admin role required")


def _resolve_integration(raw: str) -> LiveIntegration:
    try:
        return LiveIntegration(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=f"unknown integration {raw!r}"
        ) from exc


def _toggle_to_view(toggle) -> LiveToggleView:
    return LiveToggleView(
        integration=toggle.integration.value,
        state=toggle.state.value,
        previous_state=toggle.previous_state.value,
        updated_at=toggle.updated_at.isoformat() if toggle.updated_at else None,
        updated_by=toggle.updated_by,
        approval_note=toggle.approval_note,
    )


async def _build_gate(request: Request, session: AsyncSession):
    registry = request.app.state.runtime_registry
    settings = request.app.state.settings
    service = RuntimeReadinessService(
        session,
        settings=settings,
        environment_mode_provider=lambda: registry.mode,
        backup_max_age_hours=settings.launch_gate_backup_max_age_hours,
        heartbeat_max_age_seconds=settings.launch_gate_worker_heartbeat_max_seconds,
    )
    profile = await service.build_profile()
    return profile.gate


def _build_service(
    request: Request, session: AsyncSession, ctx: TenantContext
) -> LiveToggleService:
    registry = getattr(request.app.state, "runtime_registry", None)
    if registry is None:
        raise HTTPException(status_code=503, detail="runtime registry not initialised")
    audit = AuditService(session)
    return LiveToggleService(
        session,
        audit_service=audit,
        settings=request.app.state.settings,
        environment_mode=registry.mode,
        gate_provider=lambda: _build_gate(request, session),
    )


@router.get("", response_model=LiveToggleListResponse)
async def list_live_toggles(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> LiveToggleListResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session, ctx)
    toggles = await service.list_toggles(ctx.organization_id)
    return LiveToggleListResponse(
        toggles=[_toggle_to_view(t) for t in toggles]
    )


@router.get("/{integration}", response_model=LiveToggleView)
async def get_live_toggle(
    integration: str,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> LiveToggleView:
    _require_owner_or_admin(ctx)
    target = _resolve_integration(integration)
    service = _build_service(request, session, ctx)
    toggle = await service.get_toggle(ctx.organization_id, target)
    return _toggle_to_view(toggle)


@router.post("/{integration}:enable", response_model=LiveToggleView)
async def enable_live_toggle(
    integration: str,
    payload: LiveToggleEnableRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> LiveToggleView:
    _require_owner_or_admin(ctx)
    target = _resolve_integration(integration)
    service = _build_service(request, session, ctx)
    try:
        result = await service.enable(
            organization_id=ctx.organization_id,
            integration=target,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
            approval_note=payload.approval_note,
        )
    except LiveToggleValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return _toggle_to_view(result.toggle)


@router.post("/{integration}:disable", response_model=LiveToggleView)
async def disable_live_toggle(
    integration: str,
    payload: LiveToggleDisableRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> LiveToggleView:
    _require_owner_or_admin(ctx)
    target = _resolve_integration(integration)
    service = _build_service(request, session, ctx)
    try:
        result = await service.disable(
            organization_id=ctx.organization_id,
            integration=target,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
            reason=payload.reason,
        )
    except LiveToggleValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return _toggle_to_view(result.toggle)
