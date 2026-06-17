"""Metrics export policy persistence (US-042).

The repository layer is the only place in the application that
talks to the SQLAlchemy row for `metrics_export_policies`.
Domain code consumes the pure dataclasses from
`livelead.domain.metrics_export.models`; the interfaces layer
wraps them in Pydantic schemas.

The policy row stores the configuration for every sink
(Prometheus, OpenTelemetry, Sentry), the last export status per
sink, the acceptance metadata, and the per-sink audit-friendly
status markers. The row is unique on `organization_id` so a
workspace has exactly one policy at a time. Secret material is
never stored on the row: the Prometheus scrape token is an
argon2id hash, and the Sentry DSN is a secret-manager reference.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.metrics_export.enums import (
    DEFAULT_OTEL_REDACTION_HEADER_KEYS,
    DEFAULT_OTEL_SAMPLING_RATIO,
    DEFAULT_PROMETHEUS_ALLOWED_CIDRS,
    DEFAULT_SENTRY_ENVIRONMENT,
    DEFAULT_SENTRY_SAMPLE_RATE,
    ExportStatus,
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

logger = logging.getLogger("livelead.metrics_export_repo")


# ---------------------------------------------------------------------------
# Mappers
# ---------------------------------------------------------------------------


def _prometheus_from_json(value: str) -> PrometheusConfig:
    if not value:
        return PrometheusConfig()
    try:
        data = json.loads(value)
    except (TypeError, ValueError):
        return PrometheusConfig()
    if not isinstance(data, dict):
        return PrometheusConfig()
    return PrometheusConfig(
        enabled=bool(data.get("enabled", False)),
        scrape_token_hash=str(data.get("scrape_token_hash", "") or ""),
        allowed_source_cidrs=tuple(
            str(c) for c in data.get("allowed_source_cidrs", DEFAULT_PROMETHEUS_ALLOWED_CIDRS)
        )
        or DEFAULT_PROMETHEUS_ALLOWED_CIDRS,
        retention_note=str(data.get("retention_note", "") or ""),
    )


def _prometheus_to_json(cfg: PrometheusConfig) -> str:
    return json.dumps(
        {
            "enabled": bool(cfg.enabled),
            "scrape_token_hash": str(cfg.scrape_token_hash or ""),
            "allowed_source_cidrs": [str(c) for c in cfg.allowed_source_cidrs],
            "retention_note": str(cfg.retention_note or ""),
        }
    )


def _otel_from_json(value: str) -> OtelConfig:
    if not value:
        return OtelConfig()
    try:
        data = json.loads(value)
    except (TypeError, ValueError):
        return OtelConfig()
    if not isinstance(data, dict):
        return OtelConfig()
    try:
        protocol = OtelProtocol(str(data.get("protocol", OtelProtocol.HTTP_PROTOBUF)))
    except ValueError:
        protocol = OtelProtocol.HTTP_PROTOBUF
    try:
        sampling = float(data.get("sampling_ratio", DEFAULT_OTEL_SAMPLING_RATIO))
    except (TypeError, ValueError):
        sampling = DEFAULT_OTEL_SAMPLING_RATIO
    return OtelConfig(
        enabled=bool(data.get("enabled", False)),
        endpoint=str(data.get("endpoint", "") or ""),
        protocol=protocol,
        sampling_ratio=sampling,
        redaction_header_keys=tuple(
            str(k)
            for k in data.get(
                "redaction_header_keys", DEFAULT_OTEL_REDACTION_HEADER_KEYS
            )
        )
        or DEFAULT_OTEL_REDACTION_HEADER_KEYS,
    )


def _otel_to_json(cfg: OtelConfig) -> str:
    return json.dumps(
        {
            "enabled": bool(cfg.enabled),
            "endpoint": str(cfg.endpoint or ""),
            "protocol": cfg.protocol.value,
            "sampling_ratio": float(cfg.sampling_ratio),
            "redaction_header_keys": [str(k) for k in cfg.redaction_header_keys],
        }
    )


def _sentry_from_json(value: str) -> SentryConfig:
    if not value:
        return SentryConfig()
    try:
        data = json.loads(value)
    except (TypeError, ValueError):
        return SentryConfig()
    if not isinstance(data, dict):
        return SentryConfig()
    try:
        rate = float(data.get("sample_rate", DEFAULT_SENTRY_SAMPLE_RATE))
    except (TypeError, ValueError):
        rate = DEFAULT_SENTRY_SAMPLE_RATE
    return SentryConfig(
        enabled=bool(data.get("enabled", False)),
        dsn_ref=str(data.get("dsn_ref", "") or ""),
        environment=str(data.get("environment", DEFAULT_SENTRY_ENVIRONMENT) or DEFAULT_SENTRY_ENVIRONMENT),
        release=str(data.get("release", "") or ""),
        sample_rate=rate,
    )


def _sentry_to_json(cfg: SentryConfig) -> str:
    return json.dumps(
        {
            "enabled": bool(cfg.enabled),
            "dsn_ref": str(cfg.dsn_ref or ""),
            "environment": str(cfg.environment or DEFAULT_SENTRY_ENVIRONMENT),
            "release": str(cfg.release or ""),
            "sample_rate": float(cfg.sample_rate),
        }
    )


def _status_from_string(value: str | None) -> ExportStatus:
    if not value:
        return ExportStatus.DISABLED
    try:
        return ExportStatus(value)
    except ValueError:
        return ExportStatus.DISABLED


def row_to_metrics_export_policy(row: MetricsExportPolicyRow) -> MetricsExportPolicy:
    return MetricsExportPolicy(
        organization_id=row.organization_id,
        prometheus=_prometheus_from_json(row.prometheus_json or "{}"),
        otel=_otel_from_json(row.otel_json or "{}"),
        sentry=_sentry_from_json(row.sentry_json or "{}"),
        prometheus_last_status=_status_from_string(row.prometheus_last_status),
        prometheus_last_export_at=row.prometheus_last_export_at,
        otel_last_status=_status_from_string(row.otel_last_status),
        otel_last_export_at=row.otel_last_export_at,
        sentry_last_status=_status_from_string(row.sentry_last_status),
        sentry_last_export_at=row.sentry_last_export_at,
        accepted_by=row.accepted_by,
        accepted_at=row.accepted_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class MetricsExportPolicyRepository:
    """Persistence boundary for `metrics_export_policies`.

    The repository deliberately stores the JSON-typed sink
    configuration as TEXT columns; the application layer parses
    them back into typed dataclasses through the helpers above.
    The row is unique on `organization_id`; the read helpers
    return a default policy when no row exists yet.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def get(self, organization_id: UUID | str) -> MetricsExportPolicy | None:
        row = await self._session.execute(
            select(MetricsExportPolicyRow).where(
                MetricsExportPolicyRow.organization_id == str(organization_id)
            )
        )
        row = row.scalar_one_or_none()
        if row is None:
            return None
        return row_to_metrics_export_policy(row)

    async def get_or_default(
        self, organization_id: UUID | str
    ) -> MetricsExportPolicy:
        existing = await self.get(organization_id)
        if existing is not None:
            return existing
        return MetricsExportPolicy(organization_id=str(organization_id))

    async def upsert(
        self,
        *,
        organization_id: UUID | str,
        policy: MetricsExportPolicy,
    ) -> MetricsExportPolicy:
        row = await self._session.execute(
            select(MetricsExportPolicyRow).where(
                MetricsExportPolicyRow.organization_id == str(organization_id)
            )
        )
        row = row.scalar_one_or_none()
        now = datetime.utcnow()
        if row is None:
            row = MetricsExportPolicyRow(
                organization_id=str(organization_id),
                prometheus_json=_prometheus_to_json(policy.prometheus),
                otel_json=_otel_to_json(policy.otel),
                sentry_json=_sentry_to_json(policy.sentry),
                prometheus_last_status=policy.prometheus_last_status.value,
                prometheus_last_export_at=policy.prometheus_last_export_at,
                otel_last_status=policy.otel_last_status.value,
                otel_last_export_at=policy.otel_last_export_at,
                sentry_last_status=policy.sentry_last_status.value,
                sentry_last_export_at=policy.sentry_last_export_at,
                accepted_by=policy.accepted_by,
                accepted_at=policy.accepted_at,
                created_at=now,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.prometheus_json = _prometheus_to_json(policy.prometheus)
            row.otel_json = _otel_to_json(policy.otel)
            row.sentry_json = _sentry_to_json(policy.sentry)
            row.prometheus_last_status = policy.prometheus_last_status.value
            row.prometheus_last_export_at = policy.prometheus_last_export_at
            row.otel_last_status = policy.otel_last_status.value
            row.otel_last_export_at = policy.otel_last_export_at
            row.sentry_last_status = policy.sentry_last_status.value
            row.sentry_last_export_at = policy.sentry_last_export_at
            row.accepted_by = policy.accepted_by
            row.accepted_at = policy.accepted_at
            row.updated_at = now
        await self._session.flush()
        return row_to_metrics_export_policy(row)

    async def record_export(
        self,
        *,
        organization_id: UUID | str,
        sink: MetricsSink,
        status: ExportStatus,
        exported_at: datetime | None = None,
    ) -> None:
        """Record the last export status for a sink without touching the configuration.

        The helper is the single point of truth for the per-sink
        `last_status` and `last_export_at` columns. The exporter
        calls it for every successful or rejected attempt.
        """

        row = await self._session.execute(
            select(MetricsExportPolicyRow).where(
                MetricsExportPolicyRow.organization_id == str(organization_id)
            )
        )
        row = row.scalar_one_or_none()
        if row is None:
            return
        when = exported_at or datetime.utcnow()
        if sink is MetricsSink.PROMETHEUS_EXPOSITION:
            row.prometheus_last_status = status.value
            row.prometheus_last_export_at = when
        elif sink is MetricsSink.OTEL_COLLECTOR:
            row.otel_last_status = status.value
            row.otel_last_export_at = when
        elif sink is MetricsSink.SENTRY_INGEST:
            row.sentry_last_status = status.value
            row.sentry_last_export_at = when
        else:
            raise ValueError(f"EXPORT_POLICY_INVALID:sink_unsupported:{sink}")
        row.updated_at = datetime.utcnow()
        await self._session.flush()


__all__ = ["MetricsExportPolicyRepository", "row_to_metrics_export_policy"]
