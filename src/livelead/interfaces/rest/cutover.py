"""Cutover admin routes (US-040)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService
from livelead.application.runtime.cutover import (
    CutoverError,
    CutoverService,
)
from livelead.application.runtime.readiness import RuntimeReadinessService
from livelead.domain.runtime.enums import EnvironmentMode
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
)
from livelead.interfaces.rest.deps import get_db_session

router = APIRouter(prefix="/admin/cutover", tags=["admin-cutover"])


class CutoverEnterRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    notes: str = Field(default="", max_length=2000)
    admin_pin: str | None = Field(default=None, max_length=200)


class CutoverPauseRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    notes: str = Field(default="", max_length=2000)


class CutoverRollbackRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
    notes: str = Field(default="", max_length=2000)
    target_mode: str = Field(default="test_like")


class CutoverEventView(BaseModel):
    event_id: str
    action: str
    previous_mode: str
    new_mode: str
    actor: str
    reason: str
    notes: str
    occurred_at: str | None
    gate_passed: bool
    gate_summary: str


class CutoverResultView(BaseModel):
    event: CutoverEventView
    previous_mode: str
    new_mode: str
    gate: dict[str, Any]


class CutoverListResponse(BaseModel):
    events: list[CutoverEventView]


def _require_owner_or_admin(ctx: TenantContext) -> None:
    role = ctx.role
    if role is None or role.value not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="owner or admin role required")


def _event_to_view(event) -> CutoverEventView:
    return CutoverEventView(
        event_id=event.event_id,
        action=event.action.value,
        previous_mode=event.previous_mode.value,
        new_mode=event.new_mode.value,
        actor=event.actor,
        reason=event.reason,
        notes=event.notes,
        occurred_at=event.occurred_at.isoformat() if event.occurred_at else None,
        gate_passed=event.gate_passed,
        gate_summary=event.gate_summary,
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


def _build_backup_count_provider(session: AsyncSession):
    from sqlalchemy import func, select
    from livelead.infrastructure.db.models import BackupSnapshotRow
    from livelead.domain.runtime.enums import BackupVerificationStatus

    async def _count() -> int:
        r = await session.execute(
            select(func.count(BackupSnapshotRow.backup_id)).where(
                BackupSnapshotRow.verification_status.in_(
                    [
                        BackupVerificationStatus.RECORDED.value,
                        BackupVerificationStatus.VERIFIED_RESTORE.value,
                    ]
                )
            )
        )
        return int(r.scalar_one() or 0)

    return _count


def _build_service(request: Request, session: AsyncSession) -> CutoverService:
    registry = getattr(request.app.state, "runtime_registry", None)
    if registry is None:
        raise HTTPException(status_code=503, detail="runtime registry not initialised")
    audit = AuditService(session)
    return CutoverService(
        session,
        audit_service=audit,
        settings=request.app.state.settings,
        current_mode_provider=lambda: registry.mode,
        gate_provider=lambda: _build_gate(request, session),
        backup_count_provider=_build_backup_count_provider(session),
        on_mode_change=registry.set_mode,
    )


@router.get("/events", response_model=CutoverListResponse)
async def list_cutover_events(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> CutoverListResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    events = await service.list_events(limit=50)
    return CutoverListResponse(events=[_event_to_view(e) for e in events])


@router.post("/enter-pilot-live", response_model=CutoverResultView)
async def enter_pilot_live(
    payload: CutoverEnterRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> CutoverResultView:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    try:
        result = await service.enter_pilot_live(
            organization_id=ctx.organization_id,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
            reason=payload.reason,
            notes=payload.notes,
            admin_pin=payload.admin_pin,
        )
    except CutoverError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return CutoverResultView(
        event=_event_to_view(result.event),
        previous_mode=result.previous_mode.value,
        new_mode=result.new_mode.value,
        gate=result.gate.to_dict(),
    )


@router.post("/pause", response_model=CutoverResultView)
async def pause_environment(
    payload: CutoverPauseRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> CutoverResultView:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    try:
        result = await service.pause(
            organization_id=ctx.organization_id,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
            reason=payload.reason,
            notes=payload.notes,
        )
    except CutoverError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return CutoverResultView(
        event=_event_to_view(result.event),
        previous_mode=result.previous_mode.value,
        new_mode=result.new_mode.value,
        gate=result.gate.to_dict(),
    )


@router.post("/rollback", response_model=CutoverResultView)
async def rollback_environment(
    payload: CutoverRollbackRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> CutoverResultView:
    _require_owner_or_admin(ctx)
    try:
        target_mode = EnvironmentMode(payload.target_mode)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"target_mode must be one of: test_like, paused, pilot_live",
        ) from exc
    service = _build_service(request, session)
    try:
        result = await service.rollback(
            organization_id=ctx.organization_id,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
            reason=payload.reason,
            notes=payload.notes,
            target_mode=target_mode,
        )
    except CutoverError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return CutoverResultView(
        event=_event_to_view(result.event),
        previous_mode=result.previous_mode.value,
        new_mode=result.new_mode.value,
        gate=result.gate.to_dict(),
    )
