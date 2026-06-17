"""Connector auto-disable and policy recovery (US-048) REST API.

Exposes the bounded connector auto-disable
surface for owner/admin roles. The bounded
surface is read-only with respect to product
state except for the bounded
`POST
/admin/connectors/auto-disable/events/{id}/recover`
endpoint, the
`POST
/admin/connectors/{source_id}/auto-disable/evaluate`
endpoint, and the rule CRUD endpoints; the
surface never mutates a source outside the
bounded evaluation and recovery paths.

Routes:

- ``GET
  /admin/connectors/auto-disable/rules`` —
  paginated rule list (owner/admin only).
- ``POST
  /admin/connectors/auto-disable/rules`` —
  create a rule (owner/admin only).
- ``GET
  /admin/connectors/auto-disable/rules/{id}`` —
  single rule (owner/admin only).
- ``PATCH
  /admin/connectors/auto-disable/rules/{id}`` —
  update a rule (owner/admin only).
- ``DELETE
  /admin/connectors/auto-disable/rules/{id}`` —
  soft-delete a rule (owner/admin only).
- ``GET
  /admin/connectors/auto-disable/events`` —
  paginated event history (owner/admin only).
- ``POST
  /admin/connectors/auto-disable/events/{id}/recover`` —
  recovery action (owner/admin only).
- ``POST
  /admin/connectors/{source_id}/auto-disable/evaluate`` —
  bounded evaluation cycle (owner/admin only).

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

from livelead.application.auto_disable import (
    AutoDisableError,
    AutoDisableEventNotFound,
    AutoDisableInvalidPayload,
    AutoDisableInvalidTrigger,
    AutoDisableInvalidWindow,
    AutoDisableRecoveryRejected,
    AutoDisableRuleNotFound,
    AutoDisableService,
    AutoDisableSourceNotFound,
)
from livelead.domain.auto_disable.enums import (
    AutoDisableEventStatus,
    AutoDisableTrigger,
)
from livelead.domain.auto_disable.models import (
    AutoDisableEvaluationResult,
    ConnectorAutoDisableEvent,
    ConnectorAutoDisableRule,
)
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
)
from livelead.interfaces.rest.deps import get_db_session
from livelead.runtime.settings import parse_settings

logger = logging.getLogger("livelead.auto_disable_api")

router = APIRouter(
    tags=["admin-connector-auto-disable"],
)


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------


class AutoDisableTriggerView(BaseModel):
    value: str
    label: str


class AutoDisableRuleView(BaseModel):
    id: str
    organization_id: str
    source_id: str
    trigger: str
    threshold_value: float
    window_seconds: int
    consecutive_breaches: int
    cooldown_seconds: int
    enabled: bool
    created_by: str
    created_at: str | None
    updated_at: str | None


class AutoDisableRuleListResponse(BaseModel):
    items: list[AutoDisableRuleView]
    total: int
    limit: int
    offset: int


class AutoDisableEventView(BaseModel):
    id: str
    organization_id: str
    source_id: str
    trigger: str
    reason: str
    breach_count: int
    window_start: str | None
    window_end: str | None
    status: str
    alert_event_id: str | None
    health_snapshot_id: str | None
    recovery_actor_id: str | None
    recovery_reason: str | None
    recovered_at: str | None
    audit_correlation_id: str
    created_at: str | None


class AutoDisableEventListResponse(BaseModel):
    items: list[AutoDisableEventView]
    total: int
    limit: int
    offset: int


class AutoDisableEvaluationResultView(BaseModel):
    should_disable: bool
    trigger: str | None
    reason: str | None
    breach_count: int
    window_start: str | None
    window_end: str | None
    alert_event_id: str | None
    health_snapshot_id: str | None
    rule_id: str | None


class CreateRuleRequest(BaseModel):
    source_id: str = Field(..., min_length=1, max_length=64)
    trigger: str = Field(..., min_length=1, max_length=32)
    threshold_value: float = Field(..., ge=0.0)
    window_seconds: int | None = Field(default=None, ge=60, le=24 * 3600)
    consecutive_breaches: int | None = Field(default=None, ge=1, le=100)
    cooldown_seconds: int | None = Field(default=None, ge=0, le=24 * 3600)
    enabled: bool = True


class UpdateRuleRequest(BaseModel):
    threshold_value: float | None = Field(default=None, ge=0.0)
    window_seconds: int | None = Field(default=None, ge=60, le=24 * 3600)
    consecutive_breaches: int | None = Field(default=None, ge=1, le=100)
    cooldown_seconds: int | None = Field(default=None, ge=0, le=24 * 3600)
    enabled: bool | None = None


class RecoverEventRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class TriggerChoicesResponse(BaseModel):
    triggers: list[AutoDisableTriggerView]
    event_statuses: list[AutoDisableTriggerView]


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
            detail="owner or admin role required for connector auto-disable",
        )


def _rule_to_view(
    rule: ConnectorAutoDisableRule,
) -> AutoDisableRuleView:
    return AutoDisableRuleView(
        id=rule.id,
        organization_id=rule.organization_id,
        source_id=rule.source_id,
        trigger=rule.trigger.value,
        threshold_value=float(rule.threshold_value),
        window_seconds=int(rule.window_seconds),
        consecutive_breaches=int(rule.consecutive_breaches),
        cooldown_seconds=int(rule.cooldown_seconds),
        enabled=bool(rule.enabled),
        created_by=rule.created_by,
        created_at=(
            rule.created_at.isoformat() if rule.created_at else None
        ),
        updated_at=(
            rule.updated_at.isoformat() if rule.updated_at else None
        ),
    )


def _event_to_view(
    event: ConnectorAutoDisableEvent,
) -> AutoDisableEventView:
    return AutoDisableEventView(
        id=event.id,
        organization_id=event.organization_id,
        source_id=event.source_id,
        trigger=event.trigger.value,
        reason=event.reason,
        breach_count=int(event.breach_count),
        window_start=(
            event.window_start.isoformat()
            if event.window_start
            else None
        ),
        window_end=(
            event.window_end.isoformat() if event.window_end else None
        ),
        status=event.status.value,
        alert_event_id=event.alert_event_id,
        health_snapshot_id=event.health_snapshot_id,
        recovery_actor_id=event.recovery_actor_id,
        recovery_reason=event.recovery_reason,
        recovered_at=(
            event.recovered_at.isoformat()
            if event.recovered_at
            else None
        ),
        audit_correlation_id=event.audit_correlation_id,
        created_at=(
            event.created_at.isoformat() if event.created_at else None
        ),
    )


def _result_to_view(
    result: AutoDisableEvaluationResult,
) -> AutoDisableEvaluationResultView:
    return AutoDisableEvaluationResultView(
        should_disable=bool(result.should_disable),
        trigger=result.trigger.value if result.trigger else None,
        reason=result.reason,
        breach_count=int(result.breach_count),
        window_start=(
            result.window_start.isoformat()
            if result.window_start
            else None
        ),
        window_end=(
            result.window_end.isoformat() if result.window_end else None
        ),
        alert_event_id=result.alert_event_id,
        health_snapshot_id=result.health_snapshot_id,
        rule_id=result.rule_id,
    )


def _build_service(session: AsyncSession) -> AutoDisableService:
    settings = parse_settings()
    return AutoDisableService(
        session,
        environment_mode=settings.environment_mode,
    )


# ----------------------------------------------------------------------
# Choice endpoints
# ----------------------------------------------------------------------


@router.get(
    "/admin/connectors/auto-disable/choices",
    response_model=TriggerChoicesResponse,
)
async def list_choices(
    ctx: TenantContext = Depends(get_tenant_context),
) -> TriggerChoicesResponse:
    """Return the closed `AutoDisableTrigger` and
    `AutoDisableEventStatus` enums so the
    frontend can render a bounded selector
    without hardcoding the values.
    """

    _require_owner_or_admin(ctx)
    triggers = [
        AutoDisableTriggerView(
            value=trigger.value,
            label=trigger.value.replace("_", " ").title(),
        )
        for trigger in AutoDisableTrigger
    ]
    statuses = [
        AutoDisableTriggerView(
            value=status.value,
            label=status.value.replace("_", " ").title(),
        )
        for status in AutoDisableEventStatus
    ]
    return TriggerChoicesResponse(
        triggers=triggers, event_statuses=statuses
    )


# ----------------------------------------------------------------------
# Rule endpoints
# ----------------------------------------------------------------------


@router.get(
    "/admin/connectors/auto-disable/rules",
    response_model=AutoDisableRuleListResponse,
)
async def list_auto_disable_rules(
    source_id: str | None = Query(default=None, max_length=64),
    enabled: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AutoDisableRuleListResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    parsed_source = UUID(source_id) if source_id else None
    items, total = await service.list_rules(
        ctx.organization_id,
        source_id=parsed_source,
        enabled=enabled,
        limit=limit,
        offset=offset,
    )
    await session.commit()
    return AutoDisableRuleListResponse(
        items=[_rule_to_view(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/admin/connectors/auto-disable/rules",
    response_model=AutoDisableRuleView,
    status_code=201,
)
async def create_auto_disable_rule(
    payload: CreateRuleRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AutoDisableRuleView:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    try:
        source_uuid = UUID(payload.source_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="invalid source_id"
        ) from exc
    try:
        rule = await service.create_rule(
            organization_id=ctx.organization_id,
            source_id=source_uuid,
            trigger=payload.trigger,
            threshold_value=payload.threshold_value,
            window_seconds=payload.window_seconds,
            consecutive_breaches=payload.consecutive_breaches,
            cooldown_seconds=payload.cooldown_seconds,
            enabled=payload.enabled,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except AutoDisableSourceNotFound as exc:
        raise HTTPException(
            status_code=404, detail="AUTO_DISABLE_SOURCE_NOT_FOUND"
        ) from exc
    except AutoDisableInvalidTrigger as exc:
        raise HTTPException(
            status_code=400, detail="AUTO_DISABLE_RULE_INVALID"
        ) from exc
    except AutoDisableInvalidWindow as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc
    except AutoDisableError as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc
    await session.commit()
    return _rule_to_view(rule)


@router.get(
    "/admin/connectors/auto-disable/rules/{rule_id}",
    response_model=AutoDisableRuleView,
)
async def get_auto_disable_rule(
    rule_id: UUID,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AutoDisableRuleView:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    rule = await service.get_rule(ctx.organization_id, rule_id)
    if rule is None:
        raise HTTPException(
            status_code=404, detail="AUTO_DISABLE_RULE_NOT_FOUND"
        )
    await session.commit()
    return _rule_to_view(rule)


@router.patch(
    "/admin/connectors/auto-disable/rules/{rule_id}",
    response_model=AutoDisableRuleView,
)
async def update_auto_disable_rule(
    rule_id: UUID,
    payload: UpdateRuleRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AutoDisableRuleView:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    try:
        rule = await service.update_rule(
            organization_id=ctx.organization_id,
            rule_id=rule_id,
            threshold_value=payload.threshold_value,
            window_seconds=payload.window_seconds,
            consecutive_breaches=payload.consecutive_breaches,
            cooldown_seconds=payload.cooldown_seconds,
            enabled=payload.enabled,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except AutoDisableRuleNotFound as exc:
        raise HTTPException(
            status_code=404, detail="AUTO_DISABLE_RULE_NOT_FOUND"
        ) from exc
    except AutoDisableInvalidWindow as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc
    except AutoDisableError as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc
    if rule is None:
        raise HTTPException(
            status_code=404, detail="AUTO_DISABLE_RULE_NOT_FOUND"
        )
    await session.commit()
    return _rule_to_view(rule)


@router.delete(
    "/admin/connectors/auto-disable/rules/{rule_id}",
    status_code=204,
)
async def delete_auto_disable_rule(
    rule_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    try:
        await service.delete_rule(
            organization_id=ctx.organization_id,
            rule_id=rule_id,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except AutoDisableRuleNotFound as exc:
        raise HTTPException(
            status_code=404, detail="AUTO_DISABLE_RULE_NOT_FOUND"
        ) from exc
    await session.commit()


# ----------------------------------------------------------------------
# Event endpoints
# ----------------------------------------------------------------------


@router.get(
    "/admin/connectors/auto-disable/events",
    response_model=AutoDisableEventListResponse,
)
async def list_auto_disable_events(
    source_id: str | None = Query(default=None, max_length=64),
    status: str | None = Query(default=None, max_length=16),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AutoDisableEventListResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    parsed_source = UUID(source_id) if source_id else None
    parsed_status = (
        AutoDisableEventStatus(status) if status else None
    )
    items, total = await service.list_events(
        ctx.organization_id,
        source_id=parsed_source,
        status=parsed_status,
        limit=limit,
        offset=offset,
    )
    await session.commit()
    return AutoDisableEventListResponse(
        items=[_event_to_view(e) for e in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/admin/connectors/auto-disable/events/{event_id}/recover",
    response_model=AutoDisableEventView,
)
async def recover_auto_disable_event(
    event_id: UUID,
    payload: RecoverEventRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AutoDisableEventView:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    try:
        event = await service.recover_source(
            organization_id=ctx.organization_id,
            event_id=event_id,
            reason=payload.reason,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except AutoDisableEventNotFound as exc:
        raise HTTPException(
            status_code=404, detail="AUTO_DISABLE_EVENT_NOT_FOUND"
        ) from exc
    except AutoDisableRecoveryRejected as exc:
        raise HTTPException(
            status_code=409, detail=str(exc)
        ) from exc
    except AutoDisableInvalidPayload as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc
    except AutoDisableError as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc
    await session.commit()
    return _event_to_view(event)


# ----------------------------------------------------------------------
# Evaluation endpoint
# ----------------------------------------------------------------------


@router.post(
    "/admin/connectors/{source_id}/auto-disable/evaluate",
    response_model=AutoDisableEvaluationResultView,
)
async def evaluate_auto_disable(
    source_id: UUID,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AutoDisableEvaluationResultView:
    _require_owner_or_admin(ctx)
    service = _build_service(session)
    try:
        result = await service.evaluate_source(
            organization_id=ctx.organization_id,
            source_id=source_id,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=_user_agent(request),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except AutoDisableSourceNotFound as exc:
        raise HTTPException(
            status_code=404, detail="AUTO_DISABLE_SOURCE_NOT_FOUND"
        ) from exc
    except AutoDisableError as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc
    await session.commit()
    return _result_to_view(result)


__all__ = ["router"]
