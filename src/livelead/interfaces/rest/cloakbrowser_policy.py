"""Admin CloakBrowser policy API (US-025)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.cloakbrowser.policy_service import CloakBrowserPolicyService
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.admin_connectors import require_admin
from livelead.interfaces.rest.deps import get_db_session

router = APIRouter(prefix="/admin/cloakbrowser-policy", tags=["cloakbrowser-policy"])


class CloakBrowserRequestSchema(BaseModel):
    purpose_rationale: str = Field(min_length=1, max_length=4000)
    pinned_version: str | None = Field(default=None, max_length=64)
    expected_checksum: str | None = Field(default=None, max_length=128)


class CloakBrowserRevokeSchema(BaseModel):
    reason: str = Field(default="revoked", max_length=2000)


class CloakBrowserKillSwitchSchema(BaseModel):
    active: bool = True


def _svc(request: Request, session: AsyncSession) -> CloakBrowserPolicyService:
    return CloakBrowserPolicyService(session, request.app.state.settings)


@router.get("/runtime")
async def get_runtime_policy(
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    s = request.app.state.settings
    await session.commit()
    return {
        "kill_switch_active": bool(s.cloakbrowser_kill_switch),
        "pinned_version": s.cloakbrowser_pinned_version,
        "runtime_version": s.cloakbrowser_runtime_version,
        "checksum_configured": bool(s.cloakbrowser_expected_checksum),
        "runtime_checksum_present": bool(s.cloakbrowser_runtime_checksum),
    }


@router.post("/kill-switch")
async def set_kill_switch(
    body: CloakBrowserKillSwitchSchema,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    if tenant.actor_role not in ("admin", "owner"):
        raise HTTPException(status_code=403, detail="admin role required")
    request.app.state.settings.cloakbrowser_kill_switch = body.active
    await session.commit()
    return {"kill_switch_active": body.active}


@router.get("/sources/{source_id}")
async def get_source_policy(
    source_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    svc = _svc(request, session)
    view = await svc.get_view(source_id, tenant.organization_id)
    if not view:
        raise HTTPException(status_code=404, detail="source not found")
    view["kill_switch_active"] = bool(request.app.state.settings.cloakbrowser_kill_switch)
    await session.commit()
    return view


@router.post("/sources/{source_id}/request")
async def request_cloakbrowser(
    source_id: UUID,
    body: CloakBrowserRequestSchema,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    svc = _svc(request, session)
    try:
        view = await svc.request_enablement(
            tenant.organization_id,
            source_id,
            tenant.actor_role,
            purpose_rationale=body.purpose_rationale,
            pinned_version=body.pinned_version,
            expected_checksum=body.expected_checksum,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    view["kill_switch_active"] = bool(request.app.state.settings.cloakbrowser_kill_switch)
    await session.commit()
    return view


@router.post("/sources/{source_id}/approve-owner-admin")
async def approve_owner_admin(
    source_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    svc = _svc(request, session)
    try:
        view = await svc.approve_owner_admin(tenant.organization_id, source_id, tenant.actor_role)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    view["kill_switch_active"] = bool(request.app.state.settings.cloakbrowser_kill_switch)
    await session.commit()
    return view


@router.post("/sources/{source_id}/approve-compliance")
async def approve_compliance(
    source_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    if tenant.actor_role not in ("compliance", "admin", "owner"):
        raise HTTPException(status_code=403, detail="compliance role required")
    svc = _svc(request, session)
    try:
        view = await svc.approve_compliance(tenant.organization_id, source_id, tenant.actor_role)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    view["kill_switch_active"] = bool(request.app.state.settings.cloakbrowser_kill_switch)
    await session.commit()
    return view


@router.post("/sources/{source_id}/revoke")
async def revoke_cloakbrowser(
    source_id: UUID,
    body: CloakBrowserRevokeSchema,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    svc = _svc(request, session)
    try:
        view = await svc.revoke(
            tenant.organization_id,
            source_id,
            tenant.actor_role,
            reason=body.reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    view["kill_switch_active"] = bool(request.app.state.settings.cloakbrowser_kill_switch)
    await session.commit()
    return view