"""Backup-snapshot admin routes (US-040)."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService
from livelead.application.runtime.backups import (
    BackupService,
    BackupServiceError,
)
from livelead.domain.runtime.enums import BackupVerificationStatus
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
)
from livelead.interfaces.rest.deps import get_db_session

router = APIRouter(prefix="/admin/backup-snapshots", tags=["admin-backup-snapshots"])


class BackupRecordRequest(BaseModel):
    backup_id: str | None = Field(default=None, max_length=96)
    database_path: str = Field(..., min_length=1, max_length=1024)
    notes: str = Field(default="", max_length=2000)


class BackupVerifyRequest(BaseModel):
    status: str = Field(..., min_length=1, max_length=32)


class BackupView(BaseModel):
    backup_id: str
    created_at: str | None
    database_path: str
    database_size_bytes: int
    verification_status: str
    notes: str
    recorded_by: str
    verified_at: str | None
    verified_by: str | None
    freshness: str
    age_seconds: float


class BackupListResponse(BaseModel):
    snapshots: list[BackupView]
    latest: BackupView | None
    fresh_count: int
    total_count: int


def _require_owner_or_admin(ctx: TenantContext) -> None:
    role = ctx.role
    if role is None or role.value not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="owner or admin role required")


def _snapshot_to_view(snapshot, freshness: str) -> BackupView:
    return BackupView(
        backup_id=snapshot.backup_id,
        created_at=snapshot.created_at.isoformat() if snapshot.created_at else None,
        database_path=snapshot.database_path,
        database_size_bytes=snapshot.database_size_bytes,
        verification_status=snapshot.verification_status.value,
        notes=snapshot.notes,
        recorded_by=snapshot.recorded_by,
        verified_at=snapshot.verified_at.isoformat() if snapshot.verified_at else None,
        verified_by=snapshot.verified_by,
        freshness=freshness,
        age_seconds=snapshot.age_seconds(),
    )


def _build_service(request: Request, session: AsyncSession) -> BackupService:
    audit = AuditService(session)
    return BackupService(
        session,
        audit_service=audit,
        backup_max_age_hours=request.app.state.settings.launch_gate_backup_max_age_hours,
    )


@router.get("", response_model=BackupListResponse)
async def list_backup_snapshots(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> BackupListResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    summaries = await service.list_recent(limit=50)
    latest_summary = await service.latest_summary()
    fresh = await service.fresh_snapshot_count()
    total = await service.total_snapshot_count()
    return BackupListResponse(
        snapshots=[
            _snapshot_to_view(s.snapshot, s.freshness.value) for s in summaries
        ],
        latest=(
            _snapshot_to_view(latest_summary.snapshot, latest_summary.freshness.value)
            if latest_summary
            else None
        ),
        fresh_count=fresh,
        total_count=total,
    )


@router.post(":record", response_model=BackupView, status_code=201)
async def record_backup_snapshot(
    payload: BackupRecordRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> BackupView:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    backup_id = (payload.backup_id or "").strip() or f"backup-{uuid4().hex[:12]}"
    try:
        snapshot = await service.record_snapshot(
            organization_id=ctx.organization_id,
            backup_id=backup_id,
            database_path=payload.database_path,
            notes=payload.notes,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except BackupServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    summary = await service.latest_summary()
    freshness = summary.freshness.value if summary else "unknown"
    return _snapshot_to_view(snapshot, freshness)


@router.post("/{backup_id}:verify", response_model=BackupView)
async def verify_backup_snapshot(
    backup_id: str,
    payload: BackupVerifyRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> BackupView:
    _require_owner_or_admin(ctx)
    try:
        status = BackupVerificationStatus(payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"unknown status {payload.status!r}") from exc
    service = _build_service(request, session)
    try:
        snapshot = await service.verify_snapshot(
            organization_id=ctx.organization_id,
            backup_id=backup_id,
            status=status,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except BackupServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    summary = await service.latest_summary()
    freshness = summary.freshness.value if summary and summary.snapshot.backup_id == backup_id else "unknown"
    return _snapshot_to_view(snapshot, freshness)
