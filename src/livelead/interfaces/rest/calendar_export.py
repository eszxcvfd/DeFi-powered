"""Event calendar export (ICS) REST API (US-045).

Exposes the bounded calendar export surface for the
current user. The tokenized endpoint is the only
endpoint that accepts a token instead of a session.

Routes:

- ``GET /events/{id}.ics`` — single event ICS (current user).
- ``GET /watchlist/events.ics`` — current user watchlist ICS.
- ``GET /events.ics?campaign_id=&region=...`` — current event filter ICS.
- ``POST /calendar-export-tokens`` — mint a bounded export token.
- ``GET /calendar-export-tokens`` — list the user's active and revoked tokens.
- ``DELETE /calendar-export-tokens/{id}`` — revoke a token.
- ``GET /calendar-export/{token}.ics`` — tokenized ICS feed.

The current-user endpoints require an authenticated
session. The tokenized endpoint resolves the user
from the token row, not from the session, so a
desktop or mobile calendar client can subscribe to
the feed without sharing a session.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.calendar_export import (
    CalendarExportError,
    CalendarExportForbidden,
    CalendarExportInvalidScope,
    CalendarExportNotFound,
    CalendarExportService,
    CalendarExportTokenExpired,
    CalendarExportTokenRevoked,
)
from livelead.domain.calendar_export.enums import (
    CalendarScope,
)
from livelead.domain.calendar_export.models import (
    CalendarExportFilter,
)
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.deps import get_db_session
from livelead.runtime.settings import parse_settings

logger = logging.getLogger("livelead.calendar_export_api")

router = APIRouter(tags=["calendar-export"])


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------


class MintTokenRequest(BaseModel):
    scope: str = Field(..., min_length=1, max_length=32)
    target_id: str | None = Field(default=None, max_length=64)
    filter_json: dict[str, Any] | None = None
    expires_at: str | None = Field(default=None, max_length=64)


class MintTokenResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    scope: str
    target_id: str | None
    filter_json: dict[str, Any] | None
    expires_at: str | None
    revoked_at: str | None
    last_used_at: str | None
    use_count: int
    created_at: str | None
    updated_at: str | None
    plaintext: str


class CalendarTokenView(BaseModel):
    id: str
    organization_id: str
    user_id: str
    scope: str
    target_id: str | None
    filter_json: dict[str, Any] | None
    expires_at: str | None
    revoked_at: str | None
    last_used_at: str | None
    use_count: int
    created_at: str | None
    updated_at: str | None


class CalendarTokenListResponse(BaseModel):
    items: list[CalendarTokenView]
    total: int


class CalendarExportAuditView(BaseModel):
    id: str
    organization_id: str
    user_id: str | None
    token_id: str | None
    scope: str
    event_id: str | None
    event_count: int
    result: str
    ip_address: str
    user_agent: str
    request_id: str
    created_at: str | None


class CalendarExportAuditListResponse(BaseModel):
    items: list[CalendarExportAuditView]
    total: int


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


def _identity_from_tenant(tenant: TenantContext) -> tuple[UUID, str]:
    if (
        not tenant.is_authenticated()
        or not tenant.actor_id
        or tenant.role is None
    ):
        raise HTTPException(
            status_code=401, detail="authentication required"
        )
    return UUID(tenant.actor_id), tenant.role.value


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="invalid expires_at"
        ) from exc


def _token_to_view(token) -> CalendarTokenView:
    return CalendarTokenView(
        id=token.id,
        organization_id=token.organization_id,
        user_id=token.user_id,
        scope=token.scope.value,
        target_id=token.target_id,
        filter_json=token.filter_json,
        expires_at=(
            token.expires_at.isoformat() if token.expires_at else None
        ),
        revoked_at=(
            token.revoked_at.isoformat() if token.revoked_at else None
        ),
        last_used_at=(
            token.last_used_at.isoformat() if token.last_used_at else None
        ),
        use_count=int(token.use_count or 0),
        created_at=(
            token.created_at.isoformat() if token.created_at else None
        ),
        updated_at=(
            token.updated_at.isoformat() if token.updated_at else None
        ),
    )


def _audit_to_view(audit) -> CalendarExportAuditView:
    return CalendarExportAuditView(
        id=audit.id,
        organization_id=audit.organization_id,
        user_id=audit.user_id,
        token_id=audit.token_id,
        scope=audit.scope.value,
        event_id=audit.event_id,
        event_count=int(audit.event_count or 0),
        result=audit.result.value,
        ip_address=audit.ip_address,
        user_agent=audit.user_agent,
        request_id=audit.request_id,
        created_at=(
            audit.created_at.isoformat() if audit.created_at else None
        ),
    )


def _build_service(
    session: AsyncSession,
) -> CalendarExportService:
    settings = parse_settings()
    return CalendarExportService(
        session,
        environment_mode=settings.environment_mode,
    )


def _ics_response(
    *,
    body: str,
    organization_id: str,
    scope: str,
    count: int,
) -> PlainTextResponse:
    filename = (
        f"livelead-{scope}-{organization_id}.ics"
    )
    return PlainTextResponse(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "X-LiveLead-Scope": scope,
            "X-LiveLead-Event-Count": str(count),
        },
    )


# ----------------------------------------------------------------------
# Current-user ICS endpoints
# ----------------------------------------------------------------------


@router.get("/events/{event_id}.ics")
async def get_event_ics(
    event_id: str,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> PlainTextResponse:
    # FastAPI captures `event_id` greedily; the literal
    # `.ics` suffix stays in the parameter when the
    # request hits a real UUID-shaped value. Strip the
    # suffix so the handler can parse the UUID.
    candidate = event_id
    if candidate.endswith(".ics"):
        candidate = candidate[: -len(".ics")]
    try:
        parsed_event_id = UUID(candidate)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="invalid event id"
        ) from exc
    user_id, role = _identity_from_tenant(tenant)
    service = _build_service(session)
    try:
        body, count = await service.build_event_ics(
            organization_id=tenant.organization_id,
            requester_id=user_id,
            event_id=parsed_event_id,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=str(user_id),
            actor_role=role,
        )
    except CalendarExportNotFound as exc:
        raise HTTPException(status_code=404, detail="EVENT_NOT_FOUND") from exc
    except CalendarExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _ics_response(
        body=body,
        organization_id=str(tenant.organization_id),
        scope=CalendarScope.EVENT.value,
        count=count,
    )


@router.get("/watchlist/events.ics")
async def get_watchlist_ics(
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> PlainTextResponse:
    user_id, role = _identity_from_tenant(tenant)
    service = _build_service(session)
    body, count = await service.build_watchlist_ics(
        organization_id=tenant.organization_id,
        user_id=user_id,
        request_id=_request_id(request),
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
        actor=str(user_id),
        actor_role=role,
    )
    await session.commit()
    return _ics_response(
        body=body,
        organization_id=str(tenant.organization_id),
        scope=CalendarScope.WATCHLIST.value,
        count=count,
    )


@router.get("/events.ics")
async def get_events_ics(
    campaign_id: str | None = Query(default=None, max_length=64),
    industry: str | None = Query(default=None, max_length=64),
    region: str | None = Query(default=None, max_length=64),
    label: str | None = Query(default=None, max_length=64),
    request: Request = None,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> PlainTextResponse:
    user_id, role = _identity_from_tenant(tenant)
    service = _build_service(session)
    filter_obj = CalendarExportFilter(
        campaign_id=campaign_id,
        industry=industry,
        region=region,
        label=label or "",
    )
    body, count = await service.build_filter_ics(
        organization_id=tenant.organization_id,
        requester_id=user_id,
        filter_obj=filter_obj,
        request_id=_request_id(request),
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
        actor=str(user_id),
        actor_role=role,
    )
    await session.commit()
    return _ics_response(
        body=body,
        organization_id=str(tenant.organization_id),
        scope=CalendarScope.EVENT_FILTER.value,
        count=count,
    )


# ----------------------------------------------------------------------
# Token management
# ----------------------------------------------------------------------


@router.post(
    "/calendar-export-tokens",
    response_model=MintTokenResponse,
)
async def mint_calendar_token(
    payload: MintTokenRequest,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> MintTokenResponse:
    user_id, role = _identity_from_tenant(tenant)
    service = _build_service(session)
    try:
        token, plaintext = await service.mint_token(
            organization_id=tenant.organization_id,
            user_id=user_id,
            scope=payload.scope,
            target_id=payload.target_id,
            filter_json=payload.filter_json,
            expires_at=_parse_iso(payload.expires_at),
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=str(user_id),
            actor_role=role,
        )
    except CalendarExportInvalidScope as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except CalendarExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    view = _token_to_view(token).model_dump()
    view["plaintext"] = plaintext
    return MintTokenResponse(**view)


@router.get(
    "/calendar-export-tokens",
    response_model=CalendarTokenListResponse,
)
async def list_calendar_tokens(
    include_revoked: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> CalendarTokenListResponse:
    user_id, _ = _identity_from_tenant(tenant)
    service = _build_service(session)
    items = await service.list_tokens(
        tenant.organization_id,
        user_id,
        include_revoked=include_revoked,
        limit=limit,
    )
    await session.commit()
    return CalendarTokenListResponse(
        items=[_token_to_view(item) for item in items],
        total=len(items),
    )


@router.delete(
    "/calendar-export-tokens/{token_id}",
    response_model=CalendarTokenView,
)
async def revoke_calendar_token(
    token_id: UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> CalendarTokenView:
    user_id, role = _identity_from_tenant(tenant)
    service = _build_service(session)
    try:
        revoked = await service.revoke_token(
            organization_id=tenant.organization_id,
            user_id=user_id,
            token_id=token_id,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=str(user_id),
            actor_role=role,
        )
    except CalendarExportNotFound as exc:
        raise HTTPException(
            status_code=404, detail="CALENDAR_TOKEN_NOT_FOUND"
        ) from exc
    await session.commit()
    return _token_to_view(revoked)


@router.get(
    "/calendar-export-tokens/audits",
    response_model=CalendarExportAuditListResponse,
)
async def list_calendar_export_audits(
    limit: int = Query(default=50, ge=1, le=500),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> CalendarExportAuditListResponse:
    user_id, _ = _identity_from_tenant(tenant)
    service = _build_service(session)
    items = await service.list_audits(
        tenant.organization_id, user_id, limit=limit
    )
    await session.commit()
    return CalendarExportAuditListResponse(
        items=[_audit_to_view(item) for item in items],
        total=len(items),
    )


# ----------------------------------------------------------------------
# Tokenized ICS endpoint
# ----------------------------------------------------------------------


@router.get("/calendar-export/{token}.ics")
async def get_tokenized_ics(
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> PlainTextResponse:
    if token.endswith(".ics"):
        token = token[: -len(".ics")]
    # The tokenized endpoint resolves the user and
    # the organization from the token row, not from
    # the session. The first pass hashes the
    # presented plaintext and finds the row across
    # all organizations; the second pass uses the
    # resolved organization for the inner dispatch.
    from sqlalchemy import select

    from livelead.application.calendar_export.tokens import (
        hash_calendar_token,
    )
    from livelead.infrastructure.db.models import (
        CalendarExportTokenRow,
    )

    token_hash = hash_calendar_token(token)
    row = (
        await session.execute(
            select(CalendarExportTokenRow).where(
                CalendarExportTokenRow.token_hash == token_hash
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=404, detail="CALENDAR_TOKEN_NOT_FOUND"
        )
    organization_id = row.organization_id
    service = _build_service(session)
    try:
        body, count, scope = await service.build_tokenized_ics(
            organization_id=organization_id,
            plaintext=token,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
        )
    except CalendarExportNotFound as exc:
        raise HTTPException(
            status_code=404, detail="CALENDAR_TOKEN_NOT_FOUND"
        ) from exc
    except CalendarExportTokenRevoked as exc:
        raise HTTPException(
            status_code=410, detail="CALENDAR_TOKEN_REVOKED"
        ) from exc
    except CalendarExportTokenExpired as exc:
        raise HTTPException(
            status_code=410, detail="CALENDAR_TOKEN_EXPIRED"
        ) from exc
    await session.commit()
    return _ics_response(
        body=body,
        organization_id=organization_id,
        scope=scope.value,
        count=count,
    )


__all__ = ["router"]
