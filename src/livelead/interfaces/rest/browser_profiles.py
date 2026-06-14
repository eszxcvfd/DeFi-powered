"""Admin browser profile lifecycle API (US-024)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.browser.profiles import BrowserProfileService, ProfileBlocked
from livelead.infrastructure.secrets.vault import SecretVault
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.admin_connectors import require_admin
from livelead.interfaces.rest.deps import get_db_session

router = APIRouter(prefix="/admin/browser-profiles", tags=["browser-profiles"])


def _vault(request: Request) -> SecretVault:
    return SecretVault(request.app.state.settings.secret_master_key)


class CreateBrowserProfileSchema(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    ttl_days: int | None = 30


class ConsentSchema(BaseModel):
    granted: bool = True


class StateMaterialSchema(BaseModel):
    storage_state: dict = Field(default_factory=dict)


class RenewSchema(BaseModel):
    ttl_days: int = 30


@router.post("", status_code=201)
async def create_browser_profile(
    body: CreateBrowserProfileSchema,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    svc = BrowserProfileService(session, _vault(request))
    row = await svc.create(
        tenant.organization_id,
        tenant.actor_role,
        name=body.name,
        ttl_days=body.ttl_days,
    )
    await session.commit()
    return await svc.get_profile(UUID(row.id), tenant.organization_id)


@router.get("")
async def list_browser_profiles(
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    svc = BrowserProfileService(session, _vault(request))
    return await svc.list_profiles(tenant.organization_id)


@router.get("/{profile_id}")
async def get_browser_profile(
    profile_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    svc = BrowserProfileService(session, _vault(request))
    view = await svc.get_profile(profile_id, tenant.organization_id)
    if not view:
        raise HTTPException(status_code=404, detail="profile not found")
    return view


@router.post("/{profile_id}/lock")
async def lock_browser_profile(
    profile_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    svc = BrowserProfileService(session, _vault(request))
    try:
        view = await svc.lock(profile_id, tenant.organization_id, tenant.actor_role)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return view


@router.post("/{profile_id}/renew")
async def renew_browser_profile(
    profile_id: UUID,
    body: RenewSchema,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    svc = BrowserProfileService(session, _vault(request))
    try:
        view = await svc.renew(
            profile_id,
            tenant.organization_id,
            tenant.actor_role,
            ttl_days=body.ttl_days,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return view


@router.post("/{profile_id}/expire")
async def expire_browser_profile(
    profile_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    svc = BrowserProfileService(session, _vault(request))
    try:
        view = await svc.expire(profile_id, tenant.organization_id, tenant.actor_role)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return view


@router.delete("/{profile_id}")
async def delete_browser_profile(
    profile_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    svc = BrowserProfileService(session, _vault(request))
    try:
        view = await svc.delete(profile_id, tenant.organization_id, tenant.actor_role)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return view


@router.post("/{profile_id}/consent")
async def record_profile_consent(
    profile_id: UUID,
    body: ConsentSchema,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    svc = BrowserProfileService(session, _vault(request))
    try:
        view = await svc.record_consent(
            profile_id,
            tenant.organization_id,
            tenant.actor_role,
            granted=body.granted,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return view


@router.post("/{profile_id}/state-material")
async def store_profile_state_material(
    profile_id: UUID,
    body: StateMaterialSchema,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    svc = BrowserProfileService(session, _vault(request))
    try:
        view = await svc.store_state_material(
            profile_id,
            tenant.organization_id,
            tenant.actor_role,
            payload=body.storage_state,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return view


@router.get("/{profile_id}/launch-check")
async def profile_launch_check(
    profile_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_admin(tenant)
    svc = BrowserProfileService(session, _vault(request))
    try:
        await svc.assert_launch_eligible(profile_id, tenant.organization_id)
        return {"eligible": True, "reasons": []}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProfileBlocked as exc:
        return {"eligible": False, "reasons": list(exc.reasons)}