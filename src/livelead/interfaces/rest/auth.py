"""Auth REST API (US-027).

`/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`, and
`/auth/bootstrap-status` (read-only status that the frontend uses to
decide whether to show the sign-in form or the first-owner onboarding
hint).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from livelead.application.auth import AuthService, LoginOutcome
from livelead.domain.identity import (
    AuthenticatedIdentity,
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    SESSION_TTL_SECONDS,
    Role,
)
from livelead.infrastructure.db.models import UserRow
from livelead.interfaces.auth.tenant_context import (
    DEV_ORGANIZATION_ID,
    TenantContext,
    get_tenant_context,
    is_auth_boundary_open,
)
from livelead.interfaces.rest.deps import get_db_session
from livelead.runtime.settings import parse_settings
from sqlalchemy import func, select

logger = logging.getLogger("livelead.auth_api")

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)
    organization_id: str | None = Field(default=None, max_length=64)


class MeResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    organization_id: str
    role: str
    session_id: str
    expires_at: str


class BootstrapStatusResponse(BaseModel):
    has_users: bool
    default_organization_id: str
    default_email: str


def _serialize(identity: AuthenticatedIdentity) -> dict[str, Any]:
    return identity.to_summary()


def _cookie_settings() -> dict[str, Any]:
    settings = parse_settings()
    return {
        "max_age": SESSION_TTL_SECONDS,
        "httponly": True,
        "samesite": "lax",
        "path": "/",
        "secure": bool(getattr(settings, "auth_cookie_secure", False)),
    }


def _set_session_cookie(response: Response, token: str, expires_at_seconds: int) -> None:
    cfg = _cookie_settings()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=min(cfg["max_age"], max(expires_at_seconds, 60)),
        httponly=cfg["httponly"],
        samesite=cfg["samesite"],
        path=cfg["path"],
        secure=cfg["secure"],
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


@router.get("/bootstrap-status", response_model=BootstrapStatusResponse)
async def bootstrap_status(session: AsyncSession = Depends(get_db_session)) -> BootstrapStatusResponse:
    settings = parse_settings()
    count = (
        await session.execute(select(func.count(UserRow.id)))
    ).scalar_one() or 0
    return BootstrapStatusResponse(
        has_users=bool(int(count) > 0),
        default_organization_id=settings.auth_default_organization_id,
        default_email=settings.auth_default_owner_email,
    )


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    settings = parse_settings()
    org_id_value = body.organization_id or settings.auth_default_organization_id
    try:
        org_id = UUID(org_id_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid organization id") from exc

    rate_limiter = getattr(request.app.state, "auth_rate_limiter", None)
    from livelead.domain.identity import LoginRateLimiter

    limiter = rate_limiter or LoginRateLimiter(
        threshold=settings.auth_rate_limit_threshold,
        window_seconds=float(settings.auth_rate_limit_window_seconds),
        lockout_seconds=float(settings.auth_rate_limit_lockout_seconds),
    )
    auth = AuthService(session, rate_limiter=limiter)
    outcome: LoginOutcome = await auth.login(
        request=request,
        email=body.email,
        password=body.password,
        organization_id=org_id,
    )
    if outcome.success is None or outcome.session_token is None:
        # Same status and body for every failure mode.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=outcome.failure_message or "invalid credentials",
        )

    expires_at = outcome.session_expires_at or outcome.success.expires_at
    expires_in = max(60, int((expires_at.timestamp() - _now_ts())))
    _set_session_cookie(response, outcome.session_token, expires_in)
    return {
        "session": _serialize(outcome.success),
        "expires_in": expires_in,
    }


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    if not tenant.is_authenticated() or tenant.session_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
    from datetime import datetime, UTC
    identity = AuthenticatedIdentity(
        user_id=UUID(tenant.actor_id),
        email=tenant.email,
        display_name=tenant.display_name,
        organization_id=tenant.organization_id,
        role=Role(tenant.actor_role),
        session_id=tenant.session_id,
        expires_at=datetime.now(UTC),
    )
    auth = AuthService(session)
    try:
        outcome = await auth.refresh(request=request, identity=identity)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if outcome.success is None or outcome.session_token is None:
        raise HTTPException(status_code=401, detail="unable to refresh")
    expires_in = max(60, int((outcome.session_expires_at - _now()).total_seconds()))
    _set_session_cookie(response, outcome.session_token, expires_in)
    return {"session": _serialize(outcome.success), "expires_in": expires_in}


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    livelead_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    if tenant.is_authenticated() and tenant.session_id is not None:
        from datetime import datetime, UTC
        identity = AuthenticatedIdentity(
            user_id=UUID(tenant.actor_id),
            email=tenant.email,
            display_name=tenant.display_name,
            organization_id=tenant.organization_id,
            role=Role(tenant.actor_role),
            session_id=tenant.session_id,
            expires_at=datetime.now(UTC),
        )
        try:
            await AuthService(session).logout(request=request, identity=identity)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("logout_failed err=%s", exc)
    _clear_session_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=MeResponse)
async def me(
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
) -> MeResponse:
    if tenant.is_authenticated() and tenant.session_id is not None:
        return MeResponse(
            user_id=tenant.actor_id,
            email=tenant.email,
            display_name=tenant.display_name,
            organization_id=str(tenant.organization_id),
            role=tenant.actor_role,
            session_id=str(tenant.session_id),
            expires_at="",
        )
    # Dev-header fallback: only surface a synthetic session if the caller
    # explicitly opted into the dev boundary by setting the X-Actor-Role
    # header. This keeps the existing e2e tests working without weakening
    # the new session requirement for real callers.
    x_actor_role = request.headers.get("x-actor-role")
    if (
        is_auth_boundary_open()
        and x_actor_role
        and tenant.actor_role
    ):
        return MeResponse(
            user_id=f"dev:{tenant.actor_role}",
            email=f"dev-{tenant.actor_role}@example.com",
            display_name=f"Dev {tenant.actor_role}",
            organization_id=str(tenant.organization_id),
            role=tenant.actor_role,
            session_id="00000000-0000-4000-8000-000000000099",
            expires_at="",
        )
    raise HTTPException(status_code=401, detail="authentication required")


def _now():
    from datetime import UTC, datetime

    return datetime.now(UTC)


def _now_ts() -> float:
    return _now().timestamp()


__all__ = ["router"]
