"""Health, readiness, and runtime-readiness surfaces (US-040)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.queries.health import get_health_status
from livelead.application.runtime.readiness import RuntimeReadinessService
from livelead.domain.runtime.enums import EnvironmentMode
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
)
from livelead.interfaces.rest.deps import get_db_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    """Legacy health endpoint preserved for existing callers.

    New consumers should use `/health/live` and `/health/ready`.
    """
    settings = request.app.state.settings
    sqlite_ok = getattr(request.app.state, "sqlite_ok", True)
    redis_ok = getattr(request.app.state, "redis_ok", False)
    return await get_health_status(settings, sqlite_ok=sqlite_ok, redis_ok=redis_ok)


class HealthLiveSchema(BaseModel):
    status: str
    service: str
    version: str


@router.get("/health/live")
async def health_live(request: Request) -> HealthLiveSchema:
    """Process liveness — returns `ok` whenever the API process can answer.

    Liveness never depends on dependencies, backup state, or runtime mode.
    It exists so an orchestrator can decide whether the process needs to be
    restarted (US-040).
    """
    return HealthLiveSchema(
        status="ok",
        service="livelead-api",
        version=getattr(request.app.state, "api_version", "0.1.0"),
    )


class HealthReadySchema(BaseModel):
    status: str
    blocking: list[dict[str, str]]
    warnings: list[dict[str, str]]
    environment_mode: str


@router.get("/health/ready")
async def health_ready(request: Request) -> HealthReadySchema:
    """Process readiness — fail-closed on blocking launch-gate checks.

    Returns `ok` when the launch gate is satisfied for the current
    `EnvironmentMode`. In `test_like` mode the gate is reported
    (warnings only) so operators can see what would block live
    entry. The endpoint never returns secret material, full
    connection strings, or backup encryption keys.
    """
    registry = getattr(request.app.state, "runtime_registry", None)
    if registry is None:
        return HealthReadySchema(
            status="unavailable",
            blocking=[{"name": "runtime.registry", "detail": "registry not initialised"}],
            warnings=[],
            environment_mode="test_like",
        )
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        service = RuntimeReadinessService(
            session,
            settings=request.app.state.settings,
            environment_mode_provider=lambda: registry.mode,
            backup_max_age_hours=request.app.state.settings.launch_gate_backup_max_age_hours,
            heartbeat_max_age_seconds=request.app.state.settings.launch_gate_worker_heartbeat_max_seconds,
        )
        profile = await service.build_profile()
    blocking = [
        {"name": c.name, "detail": c.detail} for c in profile.gate.blocking_checks
    ]
    warnings = [
        {"name": c.name, "detail": c.detail} for c in profile.gate.warning_checks
    ]
    overall = "ok" if profile.gate.passed else "degraded"
    if profile.gate.environment_mode == EnvironmentMode.PILOT_LIVE and not profile.gate.passed:
        overall = "unavailable"
    return HealthReadySchema(
        status=overall,
        blocking=blocking,
        warnings=warnings,
        environment_mode=profile.gate.environment_mode.value,
    )


class RuntimeReadinessSchema(BaseModel):
    mode: str
    gate: dict[str, Any]
    toggles: list[dict[str, Any]]
    last_backup: dict[str, Any] | None
    backup_freshness: str
    worker_heartbeat: dict[str, Any] | None
    auth_allow_dev_headers: bool
    auth_cookie_secure: bool
    secret_master_key_is_default: bool
    tls_terminated: bool
    redis_reachable: bool
    sqlite_writable: bool


def _require_owner_or_admin(ctx: TenantContext) -> None:
    role = ctx.role
    if role is None or role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=403, detail="owner or admin role required for runtime readiness"
        )


@router.get("/admin/runtime-readiness")
async def runtime_readiness(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> RuntimeReadinessSchema:
    """Full runtime-readiness view for owners and admins (US-040)."""
    _require_owner_or_admin(ctx)
    registry = getattr(request.app.state, "runtime_registry", None)
    if registry is None:
        raise HTTPException(status_code=503, detail="runtime registry not initialised")
    service = RuntimeReadinessService(
        session,
        settings=request.app.state.settings,
        environment_mode_provider=lambda: registry.mode,
        backup_max_age_hours=request.app.state.settings.launch_gate_backup_max_age_hours,
        heartbeat_max_age_seconds=request.app.state.settings.launch_gate_worker_heartbeat_max_seconds,
    )
    profile = await service.build_profile(organization_id=ctx.organization_id)
    return RuntimeReadinessSchema(**profile.to_dict())
