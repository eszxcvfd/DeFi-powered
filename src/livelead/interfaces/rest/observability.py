"""Observability and alerting admin API (US-041).

All endpoints are owner/admin only. The surface mirrors the
existing admin endpoints in `live_toggles.py` and `cutover.py` so
a future frontend can compose them into the same settings panel.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService
from livelead.application.observability import (
    AlertEventListView,
    AlertEventNotFound,
    AlertRuleListView,
    AlertRuleNotFound,
    AlertRuleValidationError,
    AlertService,
)
from livelead.application.runtime.readiness import RuntimeReadinessService
from livelead.domain.observability.enums import (
    AlertChannel,
    AlertEventStatus,
    AlertMetric,
    AlertOperator,
    AlertSeverity,
)
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
)
from livelead.interfaces.rest.deps import get_db_session

logger = logging.getLogger("livelead.observability_api")

router = APIRouter(prefix="/admin/observability", tags=["admin-observability"])


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------


class AlertRuleSchema(BaseModel):
    id: str
    organization_id: str
    name: str
    metric: str
    operator: str
    threshold: float
    window_seconds: int
    severity: str
    cooldown_seconds: int
    channels: list[str]
    enabled: bool
    is_system: bool
    sort_order: int
    created_by: str
    created_at: str | None
    updated_at: str | None


class AlertRuleListResponse(BaseModel):
    items: list[AlertRuleSchema]


class AlertRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=96)
    metric: str = Field(..., min_length=1, max_length=64)
    operator: str = Field(..., min_length=1, max_length=8)
    threshold: float
    window_seconds: int = Field(default=0, ge=0, le=7 * 86_400)
    severity: str = Field(default="warning", min_length=1, max_length=16)
    cooldown_seconds: int = Field(default=600, ge=0, le=30 * 86_400)
    channels: list[str] = Field(default_factory=list)
    enabled: bool = True


class AlertRuleUpdateRequest(BaseModel):
    threshold: float | None = None
    window_seconds: int | None = Field(default=None, ge=0, le=7 * 86_400)
    severity: str | None = None
    cooldown_seconds: int | None = Field(default=None, ge=0, le=30 * 86_400)
    channels: list[str] | None = None
    enabled: bool | None = None


class AlertEventSchema(BaseModel):
    id: str
    organization_id: str
    rule_id: str
    rule_name: str
    metric: str
    status: str
    severity: str
    fired_at: str
    resolved_at: str | None
    acknowledged_by: str | None
    acknowledged_at: str | None
    resolution_note: str | None
    correlation_id: str
    dedup_key: str
    payload: dict[str, Any]
    payload_redacted: bool = False


class AlertEventListResponse(BaseModel):
    items: list[AlertEventSchema]
    total: int
    limit: int
    offset: int


class AlertEventAckRequest(BaseModel):
    note: str = Field(default="", max_length=500)


class GateCheckSchema(BaseModel):
    name: str
    detail: str


class OperatorSummarySchema(BaseModel):
    environment_mode: str
    gate_passed: bool
    gate_blocking: list[GateCheckSchema]
    gate_warnings: list[GateCheckSchema]
    backup_freshness: str
    backup_age_hours: float | None
    worker_heartbeat_age_seconds: float | None
    open_alerts_by_severity: dict[str, int]
    recent_alerts: list[AlertEventSchema]
    rules_total: int
    rules_enabled: int


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _require_owner_or_admin(ctx: TenantContext) -> None:
    role = ctx.role
    if role is None or role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=403, detail="owner or admin role required for observability"
        )


def _rule_view(rule) -> AlertRuleSchema:
    return AlertRuleSchema(
        id=rule.id,
        organization_id=rule.organization_id,
        name=rule.name,
        metric=rule.metric.value,
        operator=rule.operator.value,
        threshold=float(rule.threshold),
        window_seconds=int(rule.window_seconds),
        severity=rule.severity.value,
        cooldown_seconds=int(rule.cooldown_seconds),
        channels=[c.value for c in rule.channels],
        enabled=bool(rule.enabled),
        is_system=bool(rule.is_system),
        sort_order=int(rule.sort_order),
        created_by=rule.created_by,
        created_at=rule.created_at.isoformat() if rule.created_at else None,
        updated_at=rule.updated_at.isoformat() if rule.updated_at else None,
    )


def _event_view(event, *, redacted: bool = True) -> AlertEventSchema:
    return AlertEventSchema(
        id=event.id,
        organization_id=event.organization_id,
        rule_id=event.rule_id,
        rule_name=event.rule_name,
        metric=event.metric.value,
        status=event.status.value,
        severity=event.severity.value,
        fired_at=event.fired_at.isoformat(),
        resolved_at=event.resolved_at.isoformat() if event.resolved_at else None,
        acknowledged_by=event.acknowledged_by,
        acknowledged_at=(
            event.acknowledged_at.isoformat() if event.acknowledged_at else None
        ),
        resolution_note=event.resolution_note,
        correlation_id=event.correlation_id,
        dedup_key=event.dedup_key,
        payload=event.payload,
        payload_redacted=redacted,
    )


def _build_service(
    request: Request, session: AsyncSession
) -> AlertService:
    audit = AuditService(session)
    return AlertService(session, audit_service=audit)


def _parse_metric(value: str) -> AlertMetric:
    try:
        return AlertMetric(value)
    except ValueError as exc:
        raise AlertRuleValidationError(
            f"ALERT_RULE_INVALID:metric_unsupported:{value}"
        ) from exc


def _parse_operator(value: str) -> AlertOperator:
    try:
        return AlertOperator(value)
    except ValueError as exc:
        raise AlertRuleValidationError(
            f"ALERT_RULE_INVALID:operator_unsupported:{value}"
        ) from exc


def _parse_severity(value: str) -> AlertSeverity:
    try:
        return AlertSeverity(value)
    except ValueError as exc:
        # Bubble up as a validation error with the canonical prefix.
        raise AlertRuleValidationError(
            f"ALERT_RULE_INVALID:severity_unsupported:{value}"
        ) from exc


def _parse_channels(values: list[str]) -> list[AlertChannel]:
    out: list[AlertChannel] = []
    for raw in values:
        try:
            out.append(AlertChannel(raw))
        except ValueError as exc:
            raise AlertRuleValidationError(
                f"ALERT_RULE_INVALID:channel_unsupported:{raw}"
            ) from exc
    return out


# ----------------------------------------------------------------------
# Operator summary
# ----------------------------------------------------------------------


@router.get("/summary", response_model=OperatorSummarySchema)
async def operator_summary(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> OperatorSummarySchema:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    registry = request.app.state.runtime_registry
    settings = request.app.state.settings
    runtime_service = RuntimeReadinessService(
        session,
        settings=settings,
        environment_mode_provider=lambda: registry.mode,
        backup_max_age_hours=settings.launch_gate_backup_max_age_hours,
        heartbeat_max_age_seconds=settings.launch_gate_worker_heartbeat_max_seconds,
    )
    summary = await service.build_operator_summary(
        organization_id=ctx.organization_id,
        settings=settings,
        runtime_service=runtime_service,
    )
    await session.commit()
    return OperatorSummarySchema(
        environment_mode=summary.environment_mode,
        gate_passed=summary.gate_passed,
        gate_blocking=[GateCheckSchema(**c) for c in summary.gate_blocking],
        gate_warnings=[GateCheckSchema(**c) for c in summary.gate_warnings],
        backup_freshness=summary.backup_freshness,
        backup_age_hours=summary.backup_age_hours,
        worker_heartbeat_age_seconds=summary.worker_heartbeat_age_seconds,
        open_alerts_by_severity=summary.open_alerts_by_severity,
        recent_alerts=[_event_view(e) for e in summary.recent_alerts],
        rules_total=summary.rules_total,
        rules_enabled=summary.rules_enabled,
    )


# ----------------------------------------------------------------------
# Alert rules
# ----------------------------------------------------------------------


@router.get("/alert-rules", response_model=AlertRuleListResponse)
async def list_alert_rules(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AlertRuleListResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    view: AlertRuleListView = await service.list_rules(ctx.organization_id)
    await session.commit()
    return AlertRuleListResponse(items=[_rule_view(r) for r in view.items])


@router.post(
    "/alert-rules",
    response_model=AlertRuleSchema,
    status_code=201,
)
async def create_alert_rule(
    payload: AlertRuleCreateRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AlertRuleSchema:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    try:
        rule = await service.create_rule(
            organization_id=ctx.organization_id,
            name=payload.name,
            metric=_parse_metric(payload.metric),
            operator=_parse_operator(payload.operator),
            threshold=float(payload.threshold),
            window_seconds=int(payload.window_seconds),
            severity=_parse_severity(payload.severity),
            cooldown_seconds=int(payload.cooldown_seconds),
            channels=_parse_channels(payload.channels),
            enabled=bool(payload.enabled),
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except AlertRuleValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _rule_view(rule)


@router.patch("/alert-rules/{rule_id}", response_model=AlertRuleSchema)
async def update_alert_rule(
    rule_id: str,
    payload: AlertRuleUpdateRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AlertRuleSchema:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    severity = _parse_severity(payload.severity) if payload.severity else None
    channels = (
        _parse_channels(payload.channels) if payload.channels is not None else None
    )
    try:
        rule = await service.update_rule(
            organization_id=ctx.organization_id,
            rule_id=rule_id,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
            threshold=payload.threshold,
            window_seconds=payload.window_seconds,
            severity=severity,
            cooldown_seconds=payload.cooldown_seconds,
            channels=channels,
            enabled=payload.enabled,
        )
    except AlertRuleNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AlertRuleValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _rule_view(rule)


@router.delete("/alert-rules/{rule_id}", status_code=204)
async def delete_alert_rule(
    rule_id: str,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    try:
        await service.delete_rule(
            organization_id=ctx.organization_id,
            rule_id=rule_id,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except AlertRuleNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AlertRuleValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()


# ----------------------------------------------------------------------
# Alert events
# ----------------------------------------------------------------------


@router.get("/alert-events", response_model=AlertEventListResponse)
async def list_alert_events(
    status: str | None = Query(default=None, max_length=16),
    severity: str | None = Query(default=None, max_length=16),
    rule_id: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    request: Request = None,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AlertEventListResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    parsed_status = (
        AlertEventStatus(status) if status else None
    )
    parsed_sev = AlertSeverity(severity) if severity else None
    view: AlertEventListView = await service.list_events(
        ctx.organization_id,
        status=parsed_status,
        severity=parsed_sev,
        rule_id=rule_id,
        limit=limit,
        offset=offset,
    )
    await session.commit()
    return AlertEventListResponse(
        items=[_event_view(e) for e in view.items],
        total=view.total,
        limit=view.limit,
        offset=view.offset,
    )


@router.post(
    "/alert-events/{event_id}/acknowledge",
    response_model=AlertEventSchema,
)
async def acknowledge_alert_event(
    event_id: str,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AlertEventSchema:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    try:
        event = await service.acknowledge_event(
            organization_id=ctx.organization_id,
            event_id=event_id,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
        )
    except AlertEventNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return _event_view(event)
