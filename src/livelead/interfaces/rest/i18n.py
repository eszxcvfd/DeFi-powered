"""Internationalization and timezone REST API (US-047).

Exposes the bounded i18n and timezone surface
for the current user and for owner/admin
organization management. The endpoints are
read or write surfaces that own:

- `GET /me/locale` — current-user locale and
  timezone (any authenticated user).
- `PATCH /me/locale` — current-user locale and
  timezone upsert (any authenticated user).
- `GET /admin/organizations/{id}/locale` —
  organization default locale and timezone
  (owner/admin only).
- `PATCH /admin/organizations/{id}/locale` —
  organization default locale and timezone
  upsert (owner/admin only).

All API datetime fields stay in UTC ISO-8601
in the wire format. Locale and timezone
resolution happens at the API boundary through
the `I18nService` so the existing REST contract
is not redefined.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.i18n import (
    I18nInvalidTimezone,
    I18nService,
    I18nServiceError,
    I18nUnsupportedLocale,
)
from livelead.domain.identity.roles import is_governance
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
)
from livelead.interfaces.rest.deps import get_db_session

logger = logging.getLogger("livelead.i18n_api")

router = APIRouter(tags=["i18n"])

# Nested routers so the per-user and
# per-organization surfaces do not collide with
# the existing admin surface paths.
me_router = APIRouter(prefix="/me", tags=["i18n-me"])
admin_router = APIRouter(
    prefix="/admin/organizations", tags=["i18n-admin"]
)


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------


class UserLocaleResponse(BaseModel):
    user_id: str
    organization_id: str
    locale: str
    timezone: str
    resolved_locale: str
    resolved_timezone: str
    locale_source: str
    timezone_source: str


class UserLocaleUpdateRequest(BaseModel):
    locale: str | None = Field(default=None, max_length=16)
    timezone: str | None = Field(default=None, max_length=64)


class OrganizationLocaleResponse(BaseModel):
    organization_id: str
    default_locale: str
    default_timezone: str


class OrganizationLocaleUpdateRequest(BaseModel):
    default_locale: str | None = Field(default=None, max_length=16)
    default_timezone: str | None = Field(default=None, max_length=64)


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
    if role is None or not is_governance(role):
        raise HTTPException(
            status_code=403,
            detail="owner or admin role required for organization locale",
        )


def _build_service(
    session: AsyncSession,
) -> I18nService:
    from livelead.application.audit.audit_service import AuditService

    return I18nService(
        session, audit_service=AuditService(session)
    )


# ----------------------------------------------------------------------
# Per-user endpoints
# ----------------------------------------------------------------------


@me_router.get("/locale", response_model=UserLocaleResponse)
async def get_my_locale(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> UserLocaleResponse:
    service = _build_service(session)
    user_id = ctx.actor_id or str(ctx.organization_id)
    view = await service.get_user_locale(user_id, ctx.organization_id)
    return UserLocaleResponse(
        user_id=str(view.user_id),
        organization_id=str(view.organization_id),
        locale=view.locale,
        timezone=view.timezone,
        resolved_locale=view.resolved_locale,
        resolved_timezone=view.resolved_timezone,
        locale_source=view.locale_source,
        timezone_source=view.timezone_source,
    )


@me_router.patch("/locale", response_model=UserLocaleResponse)
async def patch_my_locale(
    payload: UserLocaleUpdateRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> UserLocaleResponse:
    service = _build_service(session)
    user_id = ctx.actor_id or str(ctx.organization_id)
    try:
        view = await service.update_user_locale(
            user_id=user_id,
            organization_id=ctx.organization_id,
            locale=payload.locale,
            timezone=payload.timezone,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except I18nUnsupportedLocale as exc:
        await session.commit()
        raise HTTPException(
            status_code=400, detail=exc.rejection_code
        ) from exc
    except I18nInvalidTimezone as exc:
        await session.commit()
        raise HTTPException(
            status_code=400, detail=exc.rejection_code
        ) from exc
    await session.commit()
    return UserLocaleResponse(
        user_id=str(view.user_id),
        organization_id=str(view.organization_id),
        locale=view.locale,
        timezone=view.timezone,
        resolved_locale=view.resolved_locale,
        resolved_timezone=view.resolved_timezone,
        locale_source=view.locale_source,
        timezone_source=view.timezone_source,
    )


# ----------------------------------------------------------------------
# Per-organization endpoints
# ----------------------------------------------------------------------


@admin_router.get(
    "/{organization_id}/locale",
    response_model=OrganizationLocaleResponse,
)
async def get_organization_locale(
    organization_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> OrganizationLocaleResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    view = await service.get_organization_locale(organization_id)
    if view is None:
        raise HTTPException(status_code=404, detail="organization not found")
    return OrganizationLocaleResponse(
        organization_id=str(view.organization_id),
        default_locale=view.default_locale,
        default_timezone=view.default_timezone,
    )


@admin_router.patch(
    "/{organization_id}/locale",
    response_model=OrganizationLocaleResponse,
)
async def patch_organization_locale(
    organization_id: str,
    payload: OrganizationLocaleUpdateRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> OrganizationLocaleResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    try:
        view = await service.update_organization_locale(
            organization_id=organization_id,
            default_locale=payload.default_locale,
            default_timezone=payload.default_timezone,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except I18nUnsupportedLocale as exc:
        await session.commit()
        raise HTTPException(
            status_code=400, detail=exc.rejection_code
        ) from exc
    except I18nInvalidTimezone as exc:
        await session.commit()
        raise HTTPException(
            status_code=400, detail=exc.rejection_code
        ) from exc
    except I18nServiceError as exc:
        await session.commit()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return OrganizationLocaleResponse(
        organization_id=str(view.organization_id),
        default_locale=view.default_locale,
        default_timezone=view.default_timezone,
    )


__all__ = [
    "admin_router",
    "me_router",
    "router",
]
