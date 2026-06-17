"""Row mappers for the connector auto-disable tables (US-048)."""

from __future__ import annotations

from livelead.domain.auto_disable.enums import (
    AutoDisableEventStatus,
    AutoDisableTrigger,
)
from livelead.domain.auto_disable.models import (
    ConnectorAutoDisableEvent,
    ConnectorAutoDisableRule,
)
from livelead.infrastructure.db.models import (
    ConnectorAutoDisableEventRow,
    ConnectorAutoDisableRuleRow,
)


def _trigger_from_string(value: str | None) -> AutoDisableTrigger:
    if not value:
        return AutoDisableTrigger.HEALTH_UNHEALTHY
    try:
        return AutoDisableTrigger(value)
    except ValueError:
        return AutoDisableTrigger.HEALTH_UNHEALTHY


def _event_status_from_string(
    value: str | None,
) -> AutoDisableEventStatus:
    if not value:
        return AutoDisableEventStatus.ACTIVE
    try:
        return AutoDisableEventStatus(value)
    except ValueError:
        return AutoDisableEventStatus.ACTIVE


def row_to_connector_auto_disable_rule(
    row: ConnectorAutoDisableRuleRow,
) -> ConnectorAutoDisableRule:
    return ConnectorAutoDisableRule(
        id=row.id,
        organization_id=row.organization_id,
        source_id=row.source_id,
        trigger=_trigger_from_string(row.trigger),
        threshold_value=float(row.threshold_value or 0.0),
        window_seconds=int(row.window_seconds or 0),
        consecutive_breaches=int(row.consecutive_breaches or 0),
        cooldown_seconds=int(row.cooldown_seconds or 0),
        enabled=bool(row.enabled),
        created_by=row.created_by or "system",
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def row_to_connector_auto_disable_event(
    row: ConnectorAutoDisableEventRow,
) -> ConnectorAutoDisableEvent:
    return ConnectorAutoDisableEvent(
        id=row.id,
        organization_id=row.organization_id,
        source_id=row.source_id,
        trigger=_trigger_from_string(row.trigger),
        reason=row.reason or "",
        breach_count=int(row.breach_count or 0),
        window_start=row.window_start,
        window_end=row.window_end,
        status=_event_status_from_string(row.status),
        alert_event_id=row.alert_event_id,
        health_snapshot_id=row.health_snapshot_id,
        recovery_actor_id=row.recovery_actor_id,
        recovery_reason=row.recovery_reason,
        recovered_at=row.recovered_at,
        audit_correlation_id=row.audit_correlation_id or "",
        created_at=row.created_at,
    )


__all__ = [
    "row_to_connector_auto_disable_event",
    "row_to_connector_auto_disable_rule",
]
