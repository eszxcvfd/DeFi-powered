"""Connector health surface (ICS) REST API (US-046).

Exposes the bounded connector health surface for
owner/admin roles. The bounded surface is
read-only with respect to product state; the only
mutations are the bounded per-source
`POST /admin/connectors/health/snapshots:compute`
endpoint and the matching audit entries.

Routes:

- ``GET /admin/connectors/health/summary`` — per-source
  health summary (owner/admin only).
- ``GET /admin/connectors/health/snapshots`` — paginated
  snapshot history (owner/admin only).
- ``POST /admin/connectors/health/snapshots:compute`` —
  bounded, confirmation-gated per-source computation
  (owner/admin only).
- ``GET /admin/connectors/{source_id}/health/errors`` —
  recent error rollup for the source detail surface
  (owner/admin only).

The current-user endpoints require an
authenticated session with `owner` or `admin`
role. The bounded surface never reads signals
outside the closed window enforced by the
`EnvironmentMode` from `US-040`.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.connector_health import (
    ConnectorHealthError,
    ConnectorHealthInvalidWindow,
    ConnectorHealthService,
    ConnectorHealthSourceNotFound,
)
from livelead.domain.connector_health.enums import (
    ConnectorHealthStatus,
)
from livelead.domain.connector_health.models import (
    ConnectorHealthError as DomainConnectorHealthError,
    ConnectorHealthSnapshot,
    ConnectorHealthSummaryEntry,
)
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
)
from livelead.interfaces.rest.deps import get_db_session
from livelead.runtime.settings import parse_settings

logger = logging.getLogger("livelead.connector_health_api")

router = APIRouter(
    prefix="/admin/connectors/health",
    tags=["admin-connector-health"],
)


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------


class ConnectorHealthSnapshotView(BaseModel):
    id: str
    organization_id: str
    source_id: str
    connector_type: str
    window_start: str | None
    window_end: str | None
    total_runs: int
    success_count: int
    failure_count: int
    success_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    captcha_count: int
    captcha_rate: float
    last_run_at: str | None
    last_error_code: str | None
    last_error_message: str | None
    status: str
    audit_correlation_id: str
    computed_at: str | None
    created_at: str | None
    updated_at: str | None


class ConnectorHealthSummaryEntryView(BaseModel):
    source_id: str
    source_name: str
    connector_type: str
    snapshot: ConnectorHealthSnapshotView | None
    healthy_min_success_rate: float
    degraded_min_success_rate: float
    healthy_max_captcha_rate: float
    degraded_max_captcha_rate: float
    breach: bool


class ConnectorHealthSummaryResponse(BaseModel):
    entries: list[ConnectorHealthSummaryEntryView]


class ConnectorHealthSnapshotListResponse(BaseModel):
    items: list[ConnectorHealthSnapshotView]
    total: int
    limit: int
    offset: int


class ConnectorHealthErrorView(BaseModel):
    id: str
    organization_id: str
    source_id: str
    error_code: str
    error_message: str
    first_seen_at: str | None
    last_seen_at: str | None
    occurrence_count: int
    audit_correlation_id: str
    created_at: str | None


class ConnectorHealthErrorListResponse(BaseModel):
    items: list[ConnectorHealthErrorView]
    total: int


class ComputeSnapshotRequest(BaseModel):
    source_id: str = Field(..., min_length=1, max_length=64)
    window_seconds: int | None = Field(default=None, ge=60, le=24 * 3600)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _request_id(request: Request) -> str:
    return (
        request.headers.get("x-request-id")
        or request.headers.get("X-Request-ID")
        or ""
    )


def _client_ip(request: Request) -> str:
    if request.client is None:
        return ""
    return str(request.client.host or "")


def _user_agent(request: Request) -> str:
    return str(request.headers.get("user-agent") or "")[:256]


def _require_owner_or_admin(ctx: TenantContext) -> None:
    role = ctx.role
    if role is None or role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=403,
            detail="owner or admin role required for connector health",
        )


def _snapshot_to_view(
    snapshot: ConnectorHealthSnapshot,
) -> ConnectorHealthSnapshotView:
    return ConnectorHealthSnapshotView(
        id=snapshot.id,
        organization_id=snapshot.organization_id,
        source_id=snapshot.source_id,
        connector_type=snapshot.connector_type.value,
        window_start=(
            snapshot.window_start.isoformat()
            if snapshot.window_start
            else None
        ),
        window_end=(
            snapshot.window_end.isoformat() if snapshot.window_end else None
        ),
        total_runs=int(snapshot.total_runs),
        success_count=int(snapshot.success_count),
        failure_count=int(snapshot.failure_count),
        success_rate=float(snapshot.success_rate),
        p50_latency_ms=float(snapshot.p50_latency_ms),
        p95_latency_ms=float(snapshot.p95_latency_ms),
        captcha_count=int(snapshot.captcha_count),
        captcha_rate=float(snapshot.captcha_rate),
        last_run_at=(
            snapshot.last_run_at.isoformat()
            if snapshot.last_run_at
            else None
        ),
        last_error_code=snapshot.last_error_code,
        last_error_message=snapshot.last_error_message,
        status=snapshot.status.value,
        audit_correlation_id=snapshot.audit_correlation_id,
        computed_at=(
            snapshot.computed_at.isoformat()
            if snapshot.computed_at
            else None
        ),
        created_at=(
            snapshot.created_at.isoformat()
            if snapshot.created_at
            else None
        ),
        updated_at=(
            snapshot.updated_at.isoformat()
            if snapshot.updated_at
            else None
        ),
    )


def _entry_to_view(
    entry: ConnectorHealthSummaryEntry,
) -> ConnectorHealthSummaryEntryView:
    return ConnectorHealthSummaryEntryView(
        source_id=entry.source_id,
        source_name=entry.source_name,
        connector_type=entry.connector_type.value,
        snapshot=(
            _snapshot_to_view(entry.snapshot)
            if entry.snapshot
            else None
        ),
        healthy_min_success_rate=float(entry.healthy_min_success_rate),
        degraded_min_success_rate=float(entry.degraded_min_success_rate),
        healthy_max_captcha_rate=float(entry.healthy_max_captcha_rate),
        degraded_max_captcha_rate=float(entry.degraded_max_captcha_rate),
        breach=bool(entry.breach),
    )


def _error_to_view(
    error: DomainConnectorHealthError,
) -> ConnectorHealthErrorView:
    return ConnectorHealthErrorView(
        id=error.id,
        organization_id=error.organization_id,
        source_id=error.source_id,
        error_code=error.error_code,
        error_message=error.error_message,
        first_seen_at=(
            error.first_seen_at.isoformat()
            if error.first_seen_at
            else None
        ),
        last_seen_at=(
            error.last_seen_at.isoformat()
            if error.last_seen_at
            else None
        ),
        occurrence_count=int(error.occurrence_count),
        audit_correlation_id=error.audit_correlation_id,
        created_at=(
            error.created_at.isoformat() if error.created_at else None
        ),
    )


def _build_service(
    session: AsyncSession,
) -> ConnectorHealthService:
    settings = parse_settings()
    return ConnectorHealthService(
        session,
        environment_mode=settings.environment_mode,
    )


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------


@router.get("/summary", response_model=ConnectorHealthSummaryResponse)
async def connector_health_summary(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> ConnectorHealthSummaryResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    entries = await service.build_summary(
        ctx.organization_id,
        request_id=_request_id(request),
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
        actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
        actor_role=ctx.actor_role,
    )
    await session.commit()
    return ConnectorHealthSummaryResponse(
        entries=[_entry_to_view(e) for e in entries]
    )


@router.get(
    "/snapshots",
    response_model=ConnectorHealthSnapshotListResponse,
)
async def list_connector_health_snapshots(
    source_id: str | None = Query(default=None, max_length=64),
    status: str | None = Query(default=None, max_length=16),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    request: Request = None,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> ConnectorHealthSnapshotListResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    parsed_source = (
        UUID(source_id) if source_id else None
    )
    parsed_status = (
        ConnectorHealthStatus(status) if status else None
    )
    items, total = await service.list_snapshots(
        ctx.organization_id,
        source_id=parsed_source,
        status=parsed_status,
        limit=limit,
        offset=offset,
    )
    await session.commit()
    return ConnectorHealthSnapshotListResponse(
        items=[_snapshot_to_view(s) for s in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/snapshots:compute",
    response_model=ConnectorHealthSnapshotView,
)
async def compute_connector_health_snapshot(
    payload: ComputeSnapshotRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> ConnectorHealthSnapshotView:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    try:
        source_uuid = UUID(payload.source_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="invalid source_id"
        ) from exc
    try:
        snapshot = await service.compute_snapshot(
            organization_id=ctx.organization_id,
            source_id=source_uuid,
            window_seconds=payload.window_seconds,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except ConnectorHealthSourceNotFound as exc:
        raise HTTPException(
            status_code=404, detail="CONNECTOR_HEALTH_SOURCE_NOT_FOUND"
        ) from exc
    except ConnectorHealthInvalidWindow as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc
    except ConnectorHealthError as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc
    await session.commit()
    return _snapshot_to_view(snapshot)


@router.get(
    "/{source_id}/errors",
    response_model=ConnectorHealthErrorListResponse,
)
async def list_connector_health_errors(
    source_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    request: Request = None,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> ConnectorHealthErrorListResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    try:
        items = await service.list_recent_errors(
            ctx.organization_id,
            source_id,
            limit=limit,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except ConnectorHealthSourceNotFound as exc:
        raise HTTPException(
            status_code=404, detail="CONNECTOR_HEALTH_SOURCE_NOT_FOUND"
        ) from exc
    await session.commit()
    return ConnectorHealthErrorListResponse(
        items=[_error_to_view(item) for item in items],
        total=len(items),
    )


__all__ = ["router"]
