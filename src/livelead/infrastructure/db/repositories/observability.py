"""Alert rules and alert events persistence (US-041).

The repository layer is the only place in the application that
talks to the SQLAlchemy rows for `alert_rules` and `alert_events`.
Domain code consumes the pure dataclasses from
`livelead.domain.observability.models`; the interfaces layer wraps
them in Pydantic schemas.

The evaluator is the only writer of `AlertEventRow` and the only
place that updates `resolved_at` / `status` after a firing. The
management endpoints may transition a row to `acknowledged` but
they must not mutate the payload, the dedup key, or the rule id.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, asc, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.observability.enums import (
    AlertChannel,
    AlertEventStatus,
    AlertMetric,
    AlertOperator,
    AlertSeverity,
)
from livelead.domain.observability.models import (
    AlertEvent,
    AlertRule,
)
from livelead.infrastructure.db.models import AlertEventRow, AlertRuleRow

logger = logging.getLogger("livelead.observability_repo")


# ---------------------------------------------------------------------------
# Mappers
# ---------------------------------------------------------------------------


def _channels_from_json(value: str) -> tuple[AlertChannel, ...]:
    if not value:
        return ()
    try:
        data = json.loads(value)
    except (TypeError, ValueError):
        return ()
    if not isinstance(data, list):
        return ()
    out: list[AlertChannel] = []
    for item in data:
        try:
            out.append(AlertChannel(str(item)))
        except ValueError:
            continue
    return tuple(out)


def _channels_to_json(channels: tuple[AlertChannel, ...]) -> str:
    return json.dumps([c.value for c in channels])


def _payload_from_json(value: str) -> dict[str, Any]:
    if not value:
        return {}
    try:
        data = json.loads(value)
    except (TypeError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {"value": data}
    return data


def _payload_to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, default=str)


def row_to_alert_rule(row: AlertRuleRow) -> AlertRule:
    return AlertRule(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        metric=AlertMetric(row.metric),
        operator=AlertOperator(row.operator),
        threshold=float(row.threshold or 0),
        window_seconds=int(row.window_seconds or 0),
        severity=AlertSeverity(row.severity or "warning"),
        cooldown_seconds=int(row.cooldown_seconds or 0),
        channels=_channels_from_json(row.channels_json or "[]"),
        enabled=bool(row.enabled),
        is_system=bool(row.is_system),
        sort_order=int(row.sort_order or 100),
        created_by=row.created_by or "system",
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def row_to_alert_event(row: AlertEventRow) -> AlertEvent:
    return AlertEvent(
        id=row.id,
        organization_id=row.organization_id,
        rule_id=row.rule_id,
        rule_name=row.rule_name,
        metric=AlertMetric(row.metric),
        status=AlertEventStatus(row.status),
        severity=AlertSeverity(row.severity or "warning"),
        fired_at=row.fired_at,
        dedup_key=row.dedup_key,
        payload=_payload_from_json(row.payload_json or "{}"),
        correlation_id=row.correlation_id or "",
        resolved_at=row.resolved_at,
        acknowledged_by=row.acknowledged_by,
        acknowledged_at=row.acknowledged_at,
        resolution_note=row.resolution_note,
    )


# ---------------------------------------------------------------------------
# Alert rules
# ---------------------------------------------------------------------------


class AlertRuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        organization_id: UUID | str,
        name: str,
        metric: AlertMetric,
        operator: AlertOperator,
        threshold: float,
        window_seconds: int,
        severity: AlertSeverity,
        cooldown_seconds: int,
        channels: tuple[AlertChannel, ...],
        enabled: bool,
        is_system: bool,
        sort_order: int,
        created_by: str,
    ) -> AlertRule:
        row = AlertRuleRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            name=name,
            metric=metric.value,
            operator=operator.value,
            threshold=float(threshold),
            window_seconds=int(window_seconds),
            severity=severity.value,
            cooldown_seconds=int(cooldown_seconds),
            channels_json=_channels_to_json(channels),
            enabled=bool(enabled),
            is_system=bool(is_system),
            sort_order=int(sort_order),
            created_by=created_by or "system",
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_alert_rule(row)

    async def update(
        self,
        *,
        rule_id: str,
        threshold: float | None = None,
        window_seconds: int | None = None,
        severity: AlertSeverity | None = None,
        cooldown_seconds: int | None = None,
        channels: tuple[AlertChannel, ...] | None = None,
        enabled: bool | None = None,
    ) -> AlertRule | None:
        values: dict[str, Any] = {}
        if threshold is not None:
            values["threshold"] = float(threshold)
        if window_seconds is not None:
            values["window_seconds"] = int(window_seconds)
        if severity is not None:
            values["severity"] = severity.value
        if cooldown_seconds is not None:
            values["cooldown_seconds"] = int(cooldown_seconds)
        if channels is not None:
            values["channels_json"] = _channels_to_json(channels)
        if enabled is not None:
            values["enabled"] = bool(enabled)
        if not values:
            return await self.get(rule_id)
        await self._session.execute(
            update(AlertRuleRow)
            .where(AlertRuleRow.id == rule_id)
            .values(**values)
        )
        await self._session.flush()
        return await self.get(rule_id)

    async def get(self, rule_id: str) -> AlertRule | None:
        r = await self._session.execute(
            select(AlertRuleRow).where(AlertRuleRow.id == rule_id)
        )
        row = r.scalar_one_or_none()
        return row_to_alert_rule(row) if row else None

    async def get_by_name(
        self, organization_id: UUID | str, name: str
    ) -> AlertRule | None:
        r = await self._session.execute(
            select(AlertRuleRow).where(
                and_(
                    AlertRuleRow.organization_id == str(organization_id),
                    AlertRuleRow.name == name,
                )
            )
        )
        row = r.scalar_one_or_none()
        return row_to_alert_rule(row) if row else None

    async def list_for_org(
        self, organization_id: UUID | str
    ) -> list[AlertRule]:
        r = await self._session.execute(
            select(AlertRuleRow)
            .where(AlertRuleRow.organization_id == str(organization_id))
            .order_by(asc(AlertRuleRow.sort_order), asc(AlertRuleRow.name))
        )
        return [row_to_alert_rule(row) for row in r.scalars().all()]

    async def list_enabled(self) -> list[AlertRule]:
        r = await self._session.execute(
            select(AlertRuleRow)
            .where(AlertRuleRow.enabled.is_(True))
            .order_by(asc(AlertRuleRow.sort_order), asc(AlertRuleRow.name))
        )
        return [row_to_alert_rule(row) for row in r.scalars().all()]

    async def soft_delete(self, rule_id: str) -> bool:
        """Disable a user rule. System rules refuse the call (caller checks)."""
        result = await self._session.execute(
            update(AlertRuleRow)
            .where(AlertRuleRow.id == rule_id)
            .values(enabled=False)
        )
        await self._session.flush()
        return bool(result.rowcount)


# ---------------------------------------------------------------------------
# Alert events
# ---------------------------------------------------------------------------


class AlertEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        organization_id: UUID | str,
        rule_id: str,
        rule_name: str,
        metric: AlertMetric,
        severity: AlertSeverity,
        payload: dict[str, Any],
        dedup_key: str,
        correlation_id: str = "",
        status: AlertEventStatus = AlertEventStatus.FIRING,
        fired_at: datetime | None = None,
    ) -> AlertEvent:
        row = AlertEventRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            rule_id=rule_id,
            rule_name=rule_name,
            metric=metric.value,
            severity=severity.value,
            payload_json=_payload_to_json(payload),
            dedup_key=dedup_key,
            correlation_id=correlation_id or "",
            status=status.value,
            fired_at=fired_at or datetime.utcnow(),
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_alert_event(row)

    async def get(self, event_id: str) -> AlertEvent | None:
        r = await self._session.execute(
            select(AlertEventRow).where(AlertEventRow.id == event_id)
        )
        row = r.scalar_one_or_none()
        return row_to_alert_event(row) if row else None

    async def get_open_for_dedup(self, dedup_key: str) -> AlertEvent | None:
        r = await self._session.execute(
            select(AlertEventRow)
            .where(
                and_(
                    AlertEventRow.dedup_key == dedup_key,
                    AlertEventRow.status.in_(
                        [
                            AlertEventStatus.FIRING.value,
                            AlertEventStatus.ACKNOWLEDGED.value,
                        ]
                    ),
                )
            )
            .order_by(desc(AlertEventRow.fired_at))
        )
        row = r.scalar_one_or_none()
        return row_to_alert_event(row) if row else None

    async def get_open_for_rule(
        self, organization_id: UUID | str, rule_id: str
    ) -> AlertEvent | None:
        """Return the most recent open event for a rule in an organization.

        Used by the evaluator when a signal clears and it must
        transition the open event to ``resolved``. The dedup key
        varies across cooldown buckets, so the evaluator must
        look up by rule id rather than by dedup key for the
        resolution path.
        """

        r = await self._session.execute(
            select(AlertEventRow)
            .where(
                and_(
                    AlertEventRow.organization_id == str(organization_id),
                    AlertEventRow.rule_id == rule_id,
                    AlertEventRow.status.in_(
                        [
                            AlertEventStatus.FIRING.value,
                            AlertEventStatus.ACKNOWLEDGED.value,
                        ]
                    ),
                )
            )
            .order_by(desc(AlertEventRow.fired_at))
        )
        row = r.scalar_one_or_none()
        return row_to_alert_event(row) if row else None

    async def list_for_org(
        self,
        organization_id: UUID | str,
        *,
        status: AlertEventStatus | str | None = None,
        severity: AlertSeverity | str | None = None,
        rule_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AlertEvent], int]:
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        filters = [AlertEventRow.organization_id == str(organization_id)]
        if status is not None:
            status_value = (
                status.value if isinstance(status, AlertEventStatus) else str(status)
            )
            filters.append(AlertEventRow.status == status_value)
        if severity is not None:
            severity_value = (
                severity.value
                if isinstance(severity, AlertSeverity)
                else str(severity)
            )
            filters.append(AlertEventRow.severity == severity_value)
        if rule_id:
            filters.append(AlertEventRow.rule_id == rule_id)
        where = and_(*filters)
        total = (
            await self._session.execute(
                select(func.count(AlertEventRow.id)).where(where)
            )
        ).scalar_one()
        rows = (
            await self._session.execute(
                select(AlertEventRow)
                .where(where)
                .order_by(desc(AlertEventRow.fired_at), desc(AlertEventRow.id))
                .offset(offset)
                .limit(limit)
            )
        ).scalars().all()
        return [row_to_alert_event(r) for r in rows], int(total or 0)

    async def list_open(
        self,
        organization_id: UUID | str,
        *,
        limit: int = 50,
    ) -> list[AlertEvent]:
        rows, _ = await self.list_for_org(
            organization_id,
            status=AlertEventStatus.FIRING,
            limit=limit,
            offset=0,
        )
        return rows

    async def acknowledge(
        self,
        event_id: str,
        *,
        actor: str,
        acknowledged_at: datetime | None = None,
    ) -> AlertEvent | None:
        await self._session.execute(
            update(AlertEventRow)
            .where(
                and_(
                    AlertEventRow.id == event_id,
                    AlertEventRow.status == AlertEventStatus.FIRING.value,
                )
            )
            .values(
                status=AlertEventStatus.ACKNOWLEDGED.value,
                acknowledged_by=actor,
                acknowledged_at=acknowledged_at or datetime.utcnow(),
            )
        )
        await self._session.flush()
        return await self.get(event_id)

    async def resolve(
        self,
        event_id: str,
        *,
        note: str = "",
    ) -> AlertEvent | None:
        await self._session.execute(
            update(AlertEventRow)
            .where(
                and_(
                    AlertEventRow.id == event_id,
                    AlertEventRow.status.in_(
                        [
                            AlertEventStatus.FIRING.value,
                            AlertEventStatus.ACKNOWLEDGED.value,
                        ]
                    ),
                )
            )
            .values(
                status=AlertEventStatus.RESOLVED.value,
                resolved_at=datetime.utcnow(),
                resolution_note=note or None,
            )
        )
        await self._session.flush()
        return await self.get(event_id)

    async def suppress(
        self,
        event_id: str,
    ) -> AlertEvent | None:
        await self._session.execute(
            update(AlertEventRow)
            .where(AlertEventRow.id == event_id)
            .values(status=AlertEventStatus.SUPPRESSED.value)
        )
        await self._session.flush()
        return await self.get(event_id)


__all__ = [
    "AlertEventRepository",
    "AlertRuleRepository",
    "row_to_alert_event",
    "row_to_alert_rule",
]
