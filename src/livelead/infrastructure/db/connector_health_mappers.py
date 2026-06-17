"""Row mappers for the connector health surface tables (US-046)."""

from __future__ import annotations

from livelead.domain.connector_health.enums import (
    ConnectorHealthStatus,
)
from livelead.domain.connector_health.models import (
    ConnectorHealthError,
    ConnectorHealthSnapshot,
)
from livelead.domain.sources.models import (
    ConnectorType,
)
from livelead.infrastructure.db.models import (
    ConnectorHealthErrorRow,
    ConnectorHealthSnapshotRow,
)


def _status_from_string(value: str | None) -> ConnectorHealthStatus:
    if not value:
        return ConnectorHealthStatus.UNKNOWN
    try:
        return ConnectorHealthStatus(value)
    except ValueError:
        return ConnectorHealthStatus.UNKNOWN


def _connector_type_from_string(value: str | None) -> ConnectorType:
    if not value:
        return ConnectorType.OFFICIAL_API
    try:
        return ConnectorType(value)
    except ValueError:
        return ConnectorType.OFFICIAL_API


def row_to_connector_health_snapshot(
    row: ConnectorHealthSnapshotRow,
) -> ConnectorHealthSnapshot:
    return ConnectorHealthSnapshot(
        id=row.id,
        organization_id=row.organization_id,
        source_id=row.source_id,
        connector_type=_connector_type_from_string(row.connector_type),
        window_start=row.window_start,
        window_end=row.window_end,
        total_runs=int(row.total_runs or 0),
        success_count=int(row.success_count or 0),
        failure_count=int(row.failure_count or 0),
        success_rate=float(row.success_rate or 0.0),
        p50_latency_ms=float(row.p50_latency_ms or 0.0),
        p95_latency_ms=float(row.p95_latency_ms or 0.0),
        captcha_count=int(row.captcha_count or 0),
        captcha_rate=float(row.captcha_rate or 0.0),
        last_run_at=row.last_run_at,
        last_error_code=row.last_error_code,
        last_error_message=row.last_error_message,
        status=_status_from_string(row.status),
        audit_correlation_id=row.audit_correlation_id or "",
        computed_at=row.computed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def row_to_connector_health_error(
    row: ConnectorHealthErrorRow,
) -> ConnectorHealthError:
    return ConnectorHealthError(
        id=row.id,
        organization_id=row.organization_id,
        source_id=row.source_id,
        error_code=row.error_code,
        error_message=row.error_message,
        first_seen_at=row.first_seen_at,
        last_seen_at=row.last_seen_at,
        occurrence_count=int(row.occurrence_count or 0),
        audit_correlation_id=row.audit_correlation_id or "",
        created_at=row.created_at,
    )


__all__ = [
    "row_to_connector_health_error",
    "row_to_connector_health_snapshot",
]
