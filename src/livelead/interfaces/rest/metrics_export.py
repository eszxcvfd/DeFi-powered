"""Metrics export policy admin API (US-042).

All endpoints are owner/admin only. The surface mirrors the
existing `observability.py` admin endpoints so a future
frontend can compose them into the same settings panel.
"""

from __future__ import annotations

import ipaddress
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService
from livelead.application.metrics_export import (
    ExportPolicyAcceptanceRequired,
    ExportPolicyValidationError,
    MetricsExportService,
    PrometheusExposition,
    verify_scrape_token,
)
from livelead.application.metrics_export.exporter import (
    DefaultTransportFactory,
    MetricsExporter,
)
from livelead.application.observability.signals import SignalProviderFactory
from livelead.domain.metrics_export.enums import (
    MetricsSink,
    OtelProtocol,
)
from livelead.domain.metrics_export.models import (
    MetricsExportPolicy,
    OtelConfig,
    PrometheusConfig,
    SentryConfig,
)
from livelead.infrastructure.db.models import MetricsExportPolicyRow
from livelead.infrastructure.db.repositories.metrics_export import (
    MetricsExportPolicyRepository,
    row_to_metrics_export_policy,
)
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
)
from livelead.interfaces.rest.deps import get_db_session

logger = logging.getLogger("livelead.metrics_export_api")

router = APIRouter(
    prefix="/admin/observability/export-policy",
    tags=["admin-metrics-export"],
)


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------


class PrometheusConfigSchema(BaseModel):
    enabled: bool = False
    has_scrape_token: bool = False
    allowed_source_cidrs: list[str] = Field(default_factory=list)
    retention_note: str = ""


class OtelConfigSchema(BaseModel):
    enabled: bool = False
    endpoint: str = ""
    protocol: str = OtelProtocol.HTTP_PROTOBUF.value
    sampling_ratio: float = 0.1
    redaction_header_keys: list[str] = Field(default_factory=list)


class SentryConfigSchema(BaseModel):
    enabled: bool = False
    has_dsn_ref: bool = False
    environment: str = "pilot_live"
    release: str = ""
    sample_rate: float = 0.2


class SinkStatusSchema(BaseModel):
    status: str
    last_export_at: str | None = None


class ExportPolicySchema(BaseModel):
    organization_id: str
    prometheus: PrometheusConfigSchema
    otel: OtelConfigSchema
    sentry: SentryConfigSchema
    prometheus_status: SinkStatusSchema
    otel_status: SinkStatusSchema
    sentry_status: SinkStatusSchema
    accepted_by: str | None
    accepted_at: str | None
    updated_at: str | None


class ExportPolicyUpdateRequest(BaseModel):
    prometheus: PrometheusConfigSchema | None = None
    otel: OtelConfigSchema | None = None
    sentry: SentryConfigSchema | None = None
    scrape_token: str | None = Field(default=None, max_length=512)
    accepted_by: str | None = Field(default=None, max_length=128)


class TestExportResponse(BaseModel):
    results: dict[str, dict[str, Any]]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _require_owner_or_admin(ctx: TenantContext) -> None:
    role = ctx.role
    if role is None or role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=403,
            detail="owner or admin role required for metrics export policy",
        )


def _prometheus_to_schema(cfg: PrometheusConfig) -> PrometheusConfigSchema:
    return PrometheusConfigSchema(
        enabled=bool(cfg.enabled),
        has_scrape_token=bool(cfg.scrape_token_hash),
        allowed_source_cidrs=[str(c) for c in cfg.allowed_source_cidrs],
        retention_note=str(cfg.retention_note or ""),
    )


def _otel_to_schema(cfg: OtelConfig) -> OtelConfigSchema:
    return OtelConfigSchema(
        enabled=bool(cfg.enabled),
        endpoint=str(cfg.endpoint or ""),
        protocol=cfg.protocol.value,
        sampling_ratio=float(cfg.sampling_ratio),
        redaction_header_keys=[str(k) for k in cfg.redaction_header_keys],
    )


def _sentry_to_schema(cfg: SentryConfig) -> SentryConfigSchema:
    return SentryConfigSchema(
        enabled=bool(cfg.enabled),
        has_dsn_ref=bool(cfg.dsn_ref),
        environment=str(cfg.environment or "pilot_live"),
        release=str(cfg.release or ""),
        sample_rate=float(cfg.sample_rate),
    )


def _policy_to_schema(policy: MetricsExportPolicy) -> ExportPolicySchema:
    return ExportPolicySchema(
        organization_id=policy.organization_id,
        prometheus=_prometheus_to_schema(policy.prometheus),
        otel=_otel_to_schema(policy.otel),
        sentry=_sentry_to_schema(policy.sentry),
        prometheus_status=SinkStatusSchema(
            status=policy.prometheus_last_status.value,
            last_export_at=(
                policy.prometheus_last_export_at.isoformat()
                if policy.prometheus_last_export_at
                else None
            ),
        ),
        otel_status=SinkStatusSchema(
            status=policy.otel_last_status.value,
            last_export_at=(
                policy.otel_last_export_at.isoformat()
                if policy.otel_last_export_at
                else None
            ),
        ),
        sentry_status=SinkStatusSchema(
            status=policy.sentry_last_status.value,
            last_export_at=(
                policy.sentry_last_export_at.isoformat()
                if policy.sentry_last_export_at
                else None
            ),
        ),
        accepted_by=policy.accepted_by,
        accepted_at=(
            policy.accepted_at.isoformat() if policy.accepted_at else None
        ),
        updated_at=(
            policy.updated_at.isoformat() if policy.updated_at else None
        ),
    )


def _build_service(
    request: Request, session: AsyncSession
) -> MetricsExportService:
    audit = AuditService(session)
    return MetricsExportService(session, audit_service=audit)


def _parse_prometheus(payload: PrometheusConfigSchema) -> PrometheusConfig:
    return PrometheusConfig(
        enabled=bool(payload.enabled),
        scrape_token_hash="",
        allowed_source_cidrs=tuple(str(c) for c in payload.allowed_source_cidrs),
        retention_note=str(payload.retention_note or ""),
    )


def _parse_otel(payload: OtelConfigSchema) -> OtelConfig:
    try:
        protocol = OtelProtocol(str(payload.protocol))
    except ValueError as exc:
        raise ExportPolicyValidationError(
            f"EXPORT_POLICY_INVALID:otel_protocol_unsupported:{payload.protocol}"
        ) from exc
    return OtelConfig(
        enabled=bool(payload.enabled),
        endpoint=str(payload.endpoint or ""),
        protocol=protocol,
        sampling_ratio=float(payload.sampling_ratio),
        redaction_header_keys=tuple(str(k) for k in payload.redaction_header_keys),
    )


def _parse_sentry(payload: SentryConfigSchema) -> SentryConfig:
    return SentryConfig(
        enabled=bool(payload.enabled),
        dsn_ref="",
        environment=str(payload.environment or "pilot_live"),
        release=str(payload.release or ""),
        sample_rate=float(payload.sample_rate),
    )


def _client_ip_in_cidrs(client_host: str, cidrs: list[str]) -> bool:
    if not client_host or not cidrs:
        return False
    try:
        ip = ipaddress.ip_address(client_host)
    except ValueError:
        return False
    for cidr in cidrs:
        try:
            if ip in ipaddress.ip_network(str(cidr), strict=False):
                return True
        except ValueError:
            continue
    return False


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------


@router.get("", response_model=ExportPolicySchema)
async def get_export_policy(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> ExportPolicySchema:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    policy = await service.get_policy(ctx.organization_id)
    await session.commit()
    return _policy_to_schema(policy)


@router.put("", response_model=ExportPolicySchema)
async def put_export_policy(
    payload: ExportPolicyUpdateRequest,
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> ExportPolicySchema:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    prom = _parse_prometheus(payload.prometheus) if payload.prometheus else None
    otel = _parse_otel(payload.otel) if payload.otel else None
    sentry = _parse_sentry(payload.sentry) if payload.sentry else None
    if payload.scrape_token and prom is None:
        raise HTTPException(
            status_code=400,
            detail="EXPORT_POLICY_INVALID:scrape_token_requires_prometheus_config",
        )
    try:
        policy = await service.update_policy(
            organization_id=ctx.organization_id,
            actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
            actor_role=ctx.actor_role,
            prometheus=prom,
            otel=otel,
            sentry=sentry,
            scrape_token_plaintext=payload.scrape_token,
            accepted_by=payload.accepted_by,
        )
    except ExportPolicyAcceptanceRequired as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ExportPolicyValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return _policy_to_schema(policy)


@router.post("/test", response_model=TestExportResponse)
async def test_export_policy(
    request: Request,
    ctx: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> TestExportResponse:
    _require_owner_or_admin(ctx)
    service = _build_service(request, session)
    results = await service.test_policy(
        organization_id=ctx.organization_id,
        actor=ctx.actor_id or ctx.display_name or ctx.actor_role,
        actor_role=ctx.actor_role,
    )
    await session.commit()
    return TestExportResponse(
        results={sink.value: result.to_dict() for sink, result in results.items()}
    )


# ----------------------------------------------------------------------
# Prometheus scrape endpoint
# ----------------------------------------------------------------------


prom_router = APIRouter(tags=["metrics"])


@prom_router.get("/metrics")
async def scrape_metrics(
    request: Request,
    x_scrape_token: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """Prometheus exposition endpoint.

    The endpoint is owner/admin only by default. It can be
    opened to a scrape target through the policy's
    `scrape_token_hash` and `allowed_source_cidrs`. A
    non-allowlisted source returns 403; a missing or invalid
    token returns 401; a disabled sink returns 404.
    """

    row = await session.execute(select(MetricsExportPolicyRow).limit(1))
    row = row.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="METRICS_DISABLED")
    policy = row_to_metrics_export_policy(row)
    if not policy.prometheus.enabled:
        raise HTTPException(status_code=404, detail="METRICS_DISABLED")
    client_host = request.client.host if request.client else ""
    if not _client_ip_in_cidrs(client_host, list(policy.prometheus.allowed_source_cidrs)):
        raise HTTPException(status_code=403, detail="METRICS_SOURCE_NOT_ALLOWED")
    if not x_scrape_token or not verify_scrape_token(
        x_scrape_token, policy.prometheus.scrape_token_hash
    ):
        raise HTTPException(status_code=401, detail="METRICS_SCRAPE_TOKEN_INVALID")
    transport = DefaultTransportFactory().build(
        MetricsSink.PROMETHEUS_EXPOSITION, policy
    )
    exporter = MetricsExporter(
        session=session,
        signal_factory=SignalProviderFactory(),
    )
    samples = await exporter.collect_samples(organization_id=policy.organization_id)
    await transport.export(organization_id=policy.organization_id, samples=samples)
    body = getattr(transport, "last_text_body", "")
    return PlainTextResponse(content=body, media_type="text/plain; version=0.0.4")


__all__ = ["prom_router", "router"]
