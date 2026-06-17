"""Webhook delivery and event fan-out (US-049) REST API.

Exposes the bounded governed webhook surface
for owner/admin roles. The bounded surface is
read-only with respect to product state except
for the bounded `POST
/admin/webhooks/subscriptions/{id}/test`
endpoint, the `POST
/admin/webhooks/subscriptions/{id}/rotate-secret`
endpoint, the `POST
/admin/webhooks/deliveries/{id}/retry`
endpoint, and the rule CRUD endpoints; the
surface never mutates product state outside the
bounded delivery and recovery paths.

Routes:

- ``GET /admin/webhooks/subscriptions`` —
  paginated subscription list (owner/admin
  only).
- ``POST /admin/webhooks/subscriptions`` —
  create a subscription (owner/admin only).
- ``GET
  /admin/webhooks/subscriptions/{id}`` —
  single subscription (owner/admin only).
- ``PATCH
  /admin/webhooks/subscriptions/{id}`` —
  update a subscription (owner/admin only).
- ``DELETE
  /admin/webhooks/subscriptions/{id}`` —
  soft-delete a subscription (owner/admin only).
- ``POST
  /admin/webhooks/subscriptions/{id}/rotate-secret``
  — rotate the signing secret (owner/admin only).
- ``POST
  /admin/webhooks/subscriptions/{id}/test`` —
  bounded test send (owner/admin only).
- ``GET /admin/webhooks/deliveries`` —
  paginated delivery history (owner/admin only).
- ``POST
  /admin/webhooks/deliveries/{id}/retry`` —
  retry a failed or dead-letter delivery
  (owner/admin only).

All new error responses follow the existing
error envelope (``code``, ``message``,
``request_id``, ``details``).
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.webhooks import (
    WebhookDeliveryNotFound,
    WebhookDeliveryService,
    WebhookEnvironmentPaused,
    WebhookError,
    WebhookInvalidEventType,
    WebhookInvalidTargetUrl,
    WebhookSubscriptionNotFound,
)
from livelead.domain.webhooks.enums import (
    WebhookDeliveryStatus,
    WebhookEventType,
)
from livelead.domain.webhooks.models import (
    WebhookDelivery,
    WebhookDeliveryThresholds,
    WebhookSubscription,
)
from livelead.infrastructure.secrets.vault import SecretVault
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
)
from livelead.interfaces.rest.deps import get_db_session
from livelead.runtime.settings import parse_settings

logger = logging.getLogger("livelead.webhook_api")

router = APIRouter(tags=["admin-webhooks"])


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------


class WebhookEventTypeView(BaseModel):
    value: str
    label: str


class WebhookDeliveryStatusView(BaseModel):
    value: str
    label: str


class WebhookChoices(BaseModel):
    event_types: list[WebhookEventTypeView]
    delivery_statuses: list[WebhookDeliveryStatusView]


class WebhookSubscriptionView(BaseModel):
    id: str
    organization_id: str
    name: str
    target_url: str
    secret_id: str
    event_types: list[str]
    enabled: bool
    created_by: str
    created_at: str | None
    updated_at: str | None
    last_rotated_at: str | None
    last_success_at: str | None
    last_failure_at: str | None


class WebhookSubscriptionListResponse(BaseModel):
    items: list[WebhookSubscriptionView]
    total: int
    limit: int
    offset: int


class WebhookDeliveryView(BaseModel):
    id: str
    organization_id: str
    subscription_id: str
    event_id: str | None
    event_type: str
    target_url: str
    payload_hash: str
    status: str
    attempt_count: int
    next_attempt_at: str | None
    last_attempt_at: str | None
    last_response_code: int | None
    last_response_message: str | None
    delivered_at: str | None
    created_at: str | None


class WebhookDeliveryListResponse(BaseModel):
    items: list[WebhookDeliveryView]
    total: int
    limit: int
    offset: int


class CreateSubscriptionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    target_url: str = Field(..., min_length=1, max_length=2048)
    event_types: list[str] = Field(..., min_length=1, max_length=16)
    enabled: bool = True


class UpdateSubscriptionRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    target_url: str | None = Field(default=None, min_length=1, max_length=2048)
    event_types: list[str] | None = Field(default=None, min_length=1, max_length=16)
    enabled: bool | None = None


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
            detail="owner or admin role required for webhooks",
        )


def _subscription_to_view(
    sub: WebhookSubscription,
) -> WebhookSubscriptionView:
    return WebhookSubscriptionView(
        id=sub.id,
        organization_id=sub.organization_id,
        name=sub.name,
        target_url=sub.target_url,
        secret_id=sub.secret_id,
        event_types=list(sub.event_types),
        enabled=bool(sub.enabled),
        created_by=sub.created_by,
        created_at=(
            sub.created_at.isoformat() if sub.created_at else None
        ),
        updated_at=(
            sub.updated_at.isoformat() if sub.updated_at else None
        ),
        last_rotated_at=(
            sub.last_rotated_at.isoformat()
            if sub.last_rotated_at
            else None
        ),
        last_success_at=(
            sub.last_success_at.isoformat()
            if sub.last_success_at
            else None
        ),
        last_failure_at=(
            sub.last_failure_at.isoformat()
            if sub.last_failure_at
            else None
        ),
    )


def _delivery_to_view(
    delivery: WebhookDelivery,
) -> WebhookDeliveryView:
    return WebhookDeliveryView(
        id=delivery.id,
        organization_id=delivery.organization_id,
        subscription_id=delivery.subscription_id,
        event_id=delivery.event_id,
        event_type=delivery.event_type.value,
        target_url=delivery.target_url,
        payload_hash=delivery.payload_hash,
        status=delivery.status.value,
        attempt_count=int(delivery.attempt_count),
        next_attempt_at=(
            delivery.next_attempt_at.isoformat()
            if delivery.next_attempt_at
            else None
        ),
        last_attempt_at=(
            delivery.last_attempt_at.isoformat()
            if delivery.last_attempt_at
            else None
        ),
        last_response_code=delivery.last_response_code,
        last_response_message=delivery.last_response_message,
        delivered_at=(
            delivery.delivered_at.isoformat()
            if delivery.delivered_at
            else None
        ),
        created_at=(
            delivery.created_at.isoformat()
            if delivery.created_at
            else None
        ),
    )


def _build_service(session: AsyncSession) -> WebhookDeliveryService:
    settings = parse_settings()
    vault = SecretVault(settings.secret_master_key)
    return WebhookDeliveryService(
        session,
        vault=vault,
        environment_mode=settings.environment_mode,
        thresholds=WebhookDeliveryThresholds(),
    )


# ----------------------------------------------------------------------
# Choice endpoints
# ----------------------------------------------------------------------


@router.get(
    "/admin/webhooks/choices",
    response_model=WebhookChoices,
)
async def list_choices(
    ctx: TenantContext = Depends(get_tenant_context),
) -> WebhookChoices:
    """Return the closed `WebhookEventType` and
    `WebhookDeliveryStatus` enums so the
    frontend can render a bounded selector
    without hardcoding the values.
    """

    _require_owner_or_admin(ctx)
    event_types = [
        WebhookEventTypeView(
            value=event.value,
            label=event.value.replace("_", " ").title(),
        )
        for event in WebhookEventType
    ]
    delivery_statuses = [
        WebhookDeliveryStatusView(
            value=status.value,
            label=status.value.replace("_", " ").title(),
        )
        for status in WebhookDeliveryStatus
    ]
    return WebhookChoices(
        event_types=event_types,
        delivery_statuses=delivery_statuses,
    )


# ----------------------------------------------------------------------
# Subscription endpoints
# ----------------------------------------------------------------------


@router.get(
    "/admin/webhooks/subscriptions",
    response_model=WebhookSubscriptionListResponse,
)
async def list_webhook_subscriptions(
    enabled: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> WebhookSubscriptionListResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    items, total = await service.list_subscriptions(
        ctx.organization_id,
        enabled=enabled,
        limit=limit,
        offset=offset,
    )
    await session.commit()
    return WebhookSubscriptionListResponse(
        items=[_subscription_to_view(s) for s in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/admin/webhooks/subscriptions",
    response_model=WebhookSubscriptionView,
    status_code=201,
)
async def create_webhook_subscription(
    payload: CreateSubscriptionRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> WebhookSubscriptionView:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    try:
        sub = await service.create_subscription(
            organization_id=ctx.organization_id,
            name=payload.name,
            target_url=payload.target_url,
            event_types=payload.event_types,
            enabled=payload.enabled,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except WebhookInvalidTargetUrl as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WebhookInvalidEventType as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WebhookError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _subscription_to_view(sub)


@router.get(
    "/admin/webhooks/subscriptions/{subscription_id}",
    response_model=WebhookSubscriptionView,
)
async def get_webhook_subscription(
    subscription_id: UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> WebhookSubscriptionView:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    sub = await service.get_subscription(
        ctx.organization_id, subscription_id
    )
    if sub is None:
        raise HTTPException(
            status_code=404,
            detail="WEBHOOK_SUBSCRIPTION_NOT_FOUND",
        )
    await session.commit()
    return _subscription_to_view(sub)


@router.patch(
    "/admin/webhooks/subscriptions/{subscription_id}",
    response_model=WebhookSubscriptionView,
)
async def update_webhook_subscription(
    subscription_id: UUID,
    payload: UpdateSubscriptionRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> WebhookSubscriptionView:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    try:
        sub = await service.update_subscription(
            organization_id=ctx.organization_id,
            subscription_id=subscription_id,
            name=payload.name,
            target_url=payload.target_url,
            event_types=payload.event_types,
            enabled=payload.enabled,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except WebhookSubscriptionNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail="WEBHOOK_SUBSCRIPTION_NOT_FOUND",
        ) from exc
    except WebhookInvalidTargetUrl as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WebhookInvalidEventType as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WebhookError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _subscription_to_view(sub)


@router.delete(
    "/admin/webhooks/subscriptions/{subscription_id}",
    status_code=204,
)
async def delete_webhook_subscription(
    subscription_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    try:
        await service.soft_delete_subscription(
            organization_id=ctx.organization_id,
            subscription_id=subscription_id,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except WebhookSubscriptionNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail="WEBHOOK_SUBSCRIPTION_NOT_FOUND",
        ) from exc
    await session.commit()


@router.post(
    "/admin/webhooks/subscriptions/{subscription_id}/rotate-secret",
    response_model=WebhookSubscriptionView,
)
async def rotate_webhook_secret(
    subscription_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> WebhookSubscriptionView:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    try:
        sub = await service.rotate_secret(
            organization_id=ctx.organization_id,
            subscription_id=subscription_id,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except WebhookSubscriptionNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail="WEBHOOK_SUBSCRIPTION_NOT_FOUND",
        ) from exc
    except WebhookEnvironmentPaused as exc:
        raise HTTPException(
            status_code=409, detail=str(exc)
        ) from exc
    except WebhookError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _subscription_to_view(sub)


@router.post(
    "/admin/webhooks/subscriptions/{subscription_id}/test",
    response_model=WebhookDeliveryView,
)
async def test_webhook_subscription(
    subscription_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> WebhookDeliveryView:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    try:
        delivery = await service.test_send(
            organization_id=ctx.organization_id,
            subscription_id=subscription_id,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except WebhookSubscriptionNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail="WEBHOOK_SUBSCRIPTION_NOT_FOUND",
        ) from exc
    except WebhookInvalidTargetUrl as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WebhookError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _delivery_to_view(delivery)


# ----------------------------------------------------------------------
# Delivery endpoints
# ----------------------------------------------------------------------


@router.get(
    "/admin/webhooks/deliveries",
    response_model=WebhookDeliveryListResponse,
)
async def list_webhook_deliveries(
    subscription_id: str | None = Query(default=None, max_length=64),
    status: str | None = Query(default=None, max_length=16),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> WebhookDeliveryListResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    parsed_sub = UUID(subscription_id) if subscription_id else None
    parsed_status = (
        WebhookDeliveryStatus(status) if status else None
    )
    items, total = await service.list_deliveries(
        ctx.organization_id,
        subscription_id=parsed_sub,
        status=parsed_status,
        limit=limit,
        offset=offset,
    )
    await session.commit()
    return WebhookDeliveryListResponse(
        items=[_delivery_to_view(d) for d in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/admin/webhooks/deliveries/{delivery_id}/retry",
    response_model=WebhookDeliveryView,
)
async def retry_webhook_delivery(
    delivery_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> WebhookDeliveryView:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    try:
        delivery = await service.retry_delivery(
            organization_id=ctx.organization_id,
            delivery_id=delivery_id,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except WebhookDeliveryNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail="WEBHOOK_DELIVERY_NOT_FOUND",
        ) from exc
    except WebhookError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _delivery_to_view(delivery)


__all__ = ["router"]
