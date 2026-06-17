"""Backup and restore operations admin API (US-043).

All endpoints are owner/admin only. The surface mirrors
the existing `backups.py` admin endpoints so a future
frontend can compose them into the same settings panel.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService
from livelead.application.backup_restore import (
    BackupRestoreError,
    BackupRestoreService,
    DataDeletionAcceptanceRequired,
    DataDeletionService,
    RestoreAcceptanceRequired,
    RestoreModeNotPaused,
    RetentionAcceptanceRequired,
)
from livelead.domain.backup.enums import (
    DataDeletionTarget,
    RestoreRunStatus,
)
from livelead.domain.backup.models import (
    BackupRestoreRun,
    RetentionPolicy,
)
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
)
from livelead.interfaces.rest.deps import get_db_session

logger = logging.getLogger("livelead.backup_restore_api")

router = APIRouter(
    prefix="/admin",
    tags=["admin-backup-restore"],
)


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------


class BackupSnapshotView(BaseModel):
    backup_id: str
    created_at: str | None
    database_path: str
    database_size_bytes: int
    verification_status: str
    notes: str
    recorded_by: str
    verified_at: str | None
    verified_by: str | None


class BackupRestoreRunView(BaseModel):
    id: str
    organization_id: str
    backup_id: str
    started_at: str | None
    completed_at: str | None
    status: str
    mode: str
    target_location: str
    manifest_hash: str
    row_count: int
    audit_correlation_id: str
    error: str | None = None


class BackupDetailResponse(BaseModel):
    snapshot: BackupSnapshotView
    latest_restore_run: BackupRestoreRunView | None = None


class BackupRestoreRunListResponse(BaseModel):
    items: list[BackupRestoreRunView]
    total: int
    limit: int
    offset: int


class DryRunRestoreRequest(BaseModel):
    accepted_by: str | None = Field(default=None, max_length=128)


class DryRunRestoreResponse(BaseModel):
    backup_id: str
    status: str
    target_location: str
    manifest_hash: str
    row_count: int
    error: str | None = None
    started_at: str | None
    completed_at: str | None


class RestoreBackupRequest(BaseModel):
    accepted_by: str = Field(..., min_length=1, max_length=128)


class RestoreBackupResponse(BaseModel):
    backup_id: str
    status: str
    target_location: str
    manifest_hash: str
    row_count: int
    started_at: str | None
    completed_at: str | None


class ScheduleRehearsalRequest(BaseModel):
    backup_id: str = Field(..., min_length=1, max_length=96)


class ScheduleRehearsalResponse(BaseModel):
    restore_run_id: str
    backup_id: str
    mode: str
    target_location: str
    status: str


class RetentionPolicySchema(BaseModel):
    organization_id: str
    backup_retention_days: int
    audit_retention_days: int
    prune_enabled: bool
    accepted_by: str | None
    accepted_at: str | None
    updated_at: str | None


class RetentionPolicyUpdateRequest(BaseModel):
    backup_retention_days: int | None = Field(default=None, ge=1, le=3650)
    audit_retention_days: int | None = Field(default=None, ge=0)
    prune_enabled: bool | None = None
    accepted_by: str | None = Field(default=None, max_length=128)


class RetentionPruneRequest(BaseModel):
    accepted_by: str = Field(..., min_length=1, max_length=128)


class RetentionPruneResponse(BaseModel):
    deleted_count: int
    deleted_backup_ids: list[str]
    cutoff: str


class DataDeletionRequestSchema(BaseModel):
    target: str = Field(..., min_length=1, max_length=32)
    target_id: str = Field(..., min_length=1, max_length=96)
    accepted_by: str = Field(..., min_length=1, max_length=128)
    reason: str = Field(..., min_length=1, max_length=500)


class DataDeletionResponse(BaseModel):
    target: str
    target_id: str
    status: str
    anonymized_at: str | None = None
    disabled_at: str | None = None
    redacted_at: str | None = None


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _require_owner_or_admin(ctx: TenantContext) -> None:
    role = ctx.role
    if role is None or role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=403,
            detail="owner or admin role required for backup and restore",
        )


def _snapshot_to_view(snapshot) -> BackupSnapshotView:
    return BackupSnapshotView(
        backup_id=snapshot.backup_id,
        created_at=(
            snapshot.created_at.isoformat() if snapshot.created_at else None
        ),
        database_path=snapshot.database_path,
        database_size_bytes=int(snapshot.database_size_bytes or 0),
        verification_status=str(snapshot.verification_status.value),
        notes=str(snapshot.notes or ""),
        recorded_by=str(snapshot.recorded_by or ""),
        verified_at=(
            snapshot.verified_at.isoformat() if snapshot.verified_at else None
        ),
        verified_by=str(snapshot.verified_by or ""),
    )


def _run_to_view(run: BackupRestoreRun) -> BackupRestoreRunView:
    return BackupRestoreRunView(
        id=run.id,
        organization_id=run.organization_id,
        backup_id=run.backup_id,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=(
            run.completed_at.isoformat() if run.completed_at else None
        ),
        status=run.status.value,
        mode=run.mode.value,
        target_location=run.target_location,
        manifest_hash=run.manifest_hash,
        row_count=int(run.row_count),
        audit_correlation_id=run.audit_correlation_id,
        error=run.error,
    )


def _policy_to_schema(policy: RetentionPolicy) -> RetentionPolicySchema:
    return RetentionPolicySchema(
        organization_id=policy.organization_id,
        backup_retention_days=int(policy.backup_retention_days),
        audit_retention_days=int(policy.audit_retention_days),
        prune_enabled=bool(policy.prune_enabled),
        accepted_by=policy.accepted_by,
        accepted_at=(
            policy.accepted_at.isoformat() if policy.accepted_at else None
        ),
        updated_at=(
            policy.updated_at.isoformat() if policy.updated_at else None
        ),
    )


def _build_service(
    request: Request, session: AsyncSession
) -> BackupRestoreService:
    audit = AuditService(session)
    environment_mode_provider = None
    registry = getattr(request.app.state, "runtime_registry", None)
    if registry is not None and hasattr(registry, "mode"):
        environment_mode_provider = lambda: registry.mode.value
    return BackupRestoreService(
        session,
        audit_service=audit,
        environment_mode_provider=environment_mode_provider,
    )


def _build_deletion_service(
    session: AsyncSession,
) -> DataDeletionService:
    audit = AuditService(session)
    return DataDeletionService(session, audit_service=audit)


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------


@router.get(
    "/backup-snapshots/{backup_id}",
    response_model=BackupDetailResponse,
)
async def get_backup_snapshot(
    backup_id: str,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> BackupDetailResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    snapshot = await service.get_backup(backup_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="BACKUP_NOT_FOUND")
    latest = await service.get_latest_restore_run(
        ctx.organization_id, backup_id
    )
    await session.commit()
    return BackupDetailResponse(
        snapshot=_snapshot_to_view(snapshot),
        latest_restore_run=(
            _run_to_view(latest) if latest is not None else None
        ),
    )


@router.get(
    "/backup-restore-runs",
    response_model=BackupRestoreRunListResponse,
)
async def list_backup_restore_runs(
    status: str | None = Query(default=None, max_length=32),
    backup_id: str | None = Query(default=None, max_length=96),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    request: Request = None,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> BackupRestoreRunListResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    parsed_status = (
        RestoreRunStatus(status) if status else None
    )
    items, total = await service.list_restore_runs(
        ctx.organization_id,
        status=parsed_status,
        backup_id=backup_id,
        limit=limit,
        offset=offset,
    )
    await session.commit()
    return BackupRestoreRunListResponse(
        items=[_run_to_view(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/backup-snapshots/{backup_id}:restore:dry-run",
    response_model=DryRunRestoreResponse,
)
async def dry_run_restore_backup(
    backup_id: str,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> DryRunRestoreResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    try:
        result = await service.dry_run_restore(
            organization_id=ctx.organization_id,
            backup_id=backup_id,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except BackupRestoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return DryRunRestoreResponse(
        backup_id=result.backup_id,
        status=result.status.value,
        target_location=result.target_location,
        manifest_hash=result.manifest_hash,
        row_count=int(result.row_count),
        error=result.error,
        started_at=(
            result.started_at.isoformat() if result.started_at else None
        ),
        completed_at=(
            result.completed_at.isoformat() if result.completed_at else None
        ),
    )


@router.post(
    "/backup-snapshots/{backup_id}:restore",
    response_model=RestoreBackupResponse,
)
async def restore_backup(
    backup_id: str,
    payload: RestoreBackupRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> RestoreBackupResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    try:
        result = await service.restore_backup(
            organization_id=ctx.organization_id,
            backup_id=backup_id,
            accepted_by=payload.accepted_by,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except RestoreAcceptanceRequired as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RestoreModeNotPaused as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BackupRestoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return RestoreBackupResponse(
        backup_id=result.backup_id,
        status=result.status.value,
        target_location=result.target_location,
        manifest_hash=result.manifest_hash,
        row_count=int(result.row_count),
        started_at=(
            result.started_at.isoformat() if result.started_at else None
        ),
        completed_at=(
            result.completed_at.isoformat() if result.completed_at else None
        ),
    )


@router.post(
    "/backup-snapshots/{backup_id}:rehearsal",
    response_model=ScheduleRehearsalResponse,
)
async def schedule_backup_rehearsal(
    backup_id: str,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> ScheduleRehearsalResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    try:
        run = await service.schedule_rehearsal(
            organization_id=ctx.organization_id,
            backup_id=backup_id,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except BackupRestoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return ScheduleRehearsalResponse(
        restore_run_id=run.id,
        backup_id=run.backup_id,
        mode=run.mode.value,
        target_location=run.target_location,
        status=run.status.value,
    )


@router.get(
    "/retention/policy",
    response_model=RetentionPolicySchema,
)
async def get_retention_policy(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> RetentionPolicySchema:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    policy = await service.get_retention_policy(ctx.organization_id)
    await session.commit()
    return _policy_to_schema(policy)


@router.put(
    "/retention/policy",
    response_model=RetentionPolicySchema,
)
async def put_retention_policy(
    payload: RetentionPolicyUpdateRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> RetentionPolicySchema:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    current = await service.get_retention_policy(ctx.organization_id)
    try:
        policy = await service.update_retention_policy(
            organization_id=ctx.organization_id,
            backup_retention_days=(
                payload.backup_retention_days
                if payload.backup_retention_days is not None
                else current.backup_retention_days
            ),
            audit_retention_days=(
                payload.audit_retention_days
                if payload.audit_retention_days is not None
                else current.audit_retention_days
            ),
            prune_enabled=(
                payload.prune_enabled
                if payload.prune_enabled is not None
                else current.prune_enabled
            ),
            accepted_by=payload.accepted_by,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except RetentionAcceptanceRequired as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BackupRestoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _policy_to_schema(policy)


@router.post(
    "/retention/prune",
    response_model=RetentionPruneResponse,
)
async def retention_prune(
    payload: RetentionPruneRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> RetentionPruneResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    try:
        result = await service.prune_expired_backups(
            organization_id=ctx.organization_id,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except RetentionAcceptanceRequired as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BackupRestoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return RetentionPruneResponse(
        deleted_count=int(result["deleted_count"]),
        deleted_backup_ids=list(result["deleted_backup_ids"]),
        cutoff=str(result["cutoff"]),
    )


@router.post(
    "/data-deletion",
    response_model=DataDeletionResponse,
)
async def data_deletion(
    payload: DataDeletionRequestSchema,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> DataDeletionResponse:
    _require_owner_or_admin(ctx)
    service = _build_deletion_service(session)
    try:
        result = await service.delete_data(
            organization_id=ctx.organization_id,
            target=payload.target,
            target_id=payload.target_id,
            accepted_by=payload.accepted_by,
            reason=payload.reason,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except DataDeletionAcceptanceRequired as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except BackupRestoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return DataDeletionResponse(
        target=str(result["target"]),
        target_id=str(result["target_id"]),
        status=str(result["status"]),
        anonymized_at=result.get("anonymized_at"),
        disabled_at=result.get("disabled_at"),
        redacted_at=result.get("redacted_at"),
    )


__all__ = ["router"]
