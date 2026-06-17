"""Performance baseline and SLO admin API (US-044).

All endpoints are owner/admin only. The surface
mirrors the existing `observability.py` admin
endpoints so a future frontend can compose them
into the same settings panel.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService
from livelead.application.performance import (
    BrowserSessionBudgetEnforcer,
    PerformanceBaselineService,
    PerformanceError,
)
from livelead.domain.performance.enums import (
    DEFAULT_API_READ_LATENCY_P95_MS,
    DEFAULT_BROWSER_SESSION_BUDGET_PCT,
    DEFAULT_CONCURRENCY_USERS_CAP,
    DEFAULT_DISCOVERY_FIRST_PROGRESS_P95_MS,
    DEFAULT_EVENT_LIST_PAGINATION_P95_MS,
    PerformanceScenario,
)
from livelead.domain.performance.models import (
    PerformanceSnapshot,
    PerformanceSummaryEntry,
)
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
)
from livelead.interfaces.rest.deps import get_db_session

logger = logging.getLogger("livelead.performance_api")

router = APIRouter(
    prefix="/admin/performance",
    tags=["admin-performance"],
)


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------


class PerformanceSnapshotView(BaseModel):
    id: str
    organization_id: str
    scenario: str
    started_at: str | None
    completed_at: str | None
    p50_ms: float
    p95_ms: float
    p99_ms: float
    rps: float
    error_rate: float
    concurrent_users: int
    audit_correlation_id: str


class PerformanceSummaryEntryView(BaseModel):
    scenario: str
    metric: str
    snapshot: PerformanceSnapshotView | None = None
    budget_p95_ms: float
    window_seconds: int
    breach: bool


class PerformanceSummaryResponse(BaseModel):
    entries: list[PerformanceSummaryEntryView]


class PerformanceSnapshotListResponse(BaseModel):
    items: list[PerformanceSnapshotView]
    total: int
    limit: int
    offset: int


class RunScenarioRequest(BaseModel):
    scenario: str = Field(..., min_length=1, max_length=64)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _require_owner_or_admin(ctx: TenantContext) -> None:
    role = ctx.role
    if role is None or role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=403,
            detail="owner or admin role required for performance baseline",
        )


def _snapshot_to_view(snapshot: PerformanceSnapshot) -> PerformanceSnapshotView:
    return PerformanceSnapshotView(
        id=snapshot.id,
        organization_id=snapshot.organization_id,
        scenario=snapshot.scenario.value,
        started_at=(
            snapshot.started_at.isoformat() if snapshot.started_at else None
        ),
        completed_at=(
            snapshot.completed_at.isoformat() if snapshot.completed_at else None
        ),
        p50_ms=float(snapshot.p50_ms),
        p95_ms=float(snapshot.p95_ms),
        p99_ms=float(snapshot.p99_ms),
        rps=float(snapshot.rps),
        error_rate=float(snapshot.error_rate),
        concurrent_users=int(snapshot.concurrent_users),
        audit_correlation_id=snapshot.audit_correlation_id,
    )


def _entry_to_view(entry: PerformanceSummaryEntry) -> PerformanceSummaryEntryView:
    return PerformanceSummaryEntryView(
        scenario=entry.scenario.value,
        metric=entry.metric.value,
        snapshot=(
            _snapshot_to_view(entry.snapshot) if entry.snapshot else None
        ),
        budget_p95_ms=float(entry.budget_p95_ms),
        window_seconds=int(entry.window_seconds),
        breach=bool(entry.breach),
    )


def _build_service(session: AsyncSession) -> PerformanceBaselineService:
    audit = AuditService(session)
    return PerformanceBaselineService(session, audit_service=audit)


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------


@router.get("/summary", response_model=PerformanceSummaryResponse)
async def performance_summary(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> PerformanceSummaryResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    entries = await service.build_summary(ctx.organization_id)
    await session.commit()
    return PerformanceSummaryResponse(
        entries=[_entry_to_view(e) for e in entries]
    )


@router.get("/snapshots", response_model=PerformanceSnapshotListResponse)
async def list_performance_snapshots(
    scenario: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    request: Request = None,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> PerformanceSnapshotListResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    parsed_scenario = (
        PerformanceScenario(scenario) if scenario else None
    )
    items, total = await service.list_snapshots(
        ctx.organization_id,
        scenario=parsed_scenario,
        limit=limit,
        offset=offset,
    )
    await session.commit()
    return PerformanceSnapshotListResponse(
        items=[_snapshot_to_view(s) for s in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/scenarios:run",
    response_model=PerformanceSnapshotView,
)
async def run_performance_scenario(
    payload: RunScenarioRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> PerformanceSnapshotView:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    try:
        snapshot = await service.run_scenario(
            organization_id=ctx.organization_id,
            scenario=payload.scenario,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except PerformanceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _snapshot_to_view(snapshot)


__all__ = ["router"]
