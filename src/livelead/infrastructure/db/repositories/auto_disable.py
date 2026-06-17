"""Connector auto-disable persistence repositories (US-048).

The repositories own every read and write for
``connector_auto_disable_rules`` and
``connector_auto_disable_events``. All methods
take ``organization_id`` first so tenant
isolation is mandatory at the data layer. The
repositories deliberately return pure
dataclasses from
``livelead.domain.auto_disable.models``; the
application service is the only place that
knows the secret-safe payload contract and the
audit entry shape.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.auto_disable.enums import (
    AutoDisableEventStatus,
    AutoDisableTrigger,
)
from livelead.domain.auto_disable.models import (
    ConnectorAutoDisableEvent,
    ConnectorAutoDisableRule,
)
from livelead.infrastructure.db.auto_disable_mappers import (
    row_to_connector_auto_disable_event,
    row_to_connector_auto_disable_rule,
)
from livelead.infrastructure.db.models import (
    ConnectorAutoDisableEventRow,
    ConnectorAutoDisableRuleRow,
)

logger = logging.getLogger("livelead.auto_disable_repo")


def _now() -> datetime:
    return datetime.utcnow()


def _truncate(value: str | None, *, limit: int) -> str | None:
    if value is None:
        return None
    candidate = str(value)
    if len(candidate) <= limit:
        return candidate
    return candidate[: limit - 3] + "..."


# ---------------------------------------------------------------------------
# Rule repository
# ---------------------------------------------------------------------------


class ConnectorAutoDisableRuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def add(
        self,
        *,
        organization_id: UUID | str,
        source_id: UUID | str,
        trigger: AutoDisableTrigger,
        threshold_value: float,
        window_seconds: int,
        consecutive_breaches: int,
        cooldown_seconds: int,
        enabled: bool,
        created_by: str,
    ) -> ConnectorAutoDisableRule:
        now = _now()
        row = ConnectorAutoDisableRuleRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            source_id=str(source_id),
            trigger=trigger.value,
            threshold_value=float(threshold_value),
            window_seconds=int(window_seconds),
            consecutive_breaches=int(consecutive_breaches),
            cooldown_seconds=int(cooldown_seconds),
            enabled=bool(enabled),
            deleted_at=None,
            created_by=str(created_by or "system"),
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_connector_auto_disable_rule(row)

    async def get(
        self, organization_id: UUID | str, rule_id: UUID | str
    ) -> ConnectorAutoDisableRule | None:
        r = await self._session.execute(
            select(ConnectorAutoDisableRuleRow).where(
                and_(
                    ConnectorAutoDisableRuleRow.organization_id
                    == str(organization_id),
                    ConnectorAutoDisableRuleRow.id == str(rule_id),
                    ConnectorAutoDisableRuleRow.deleted_at.is_(None),
                )
            )
        )
        row = r.scalar_one_or_none()
        return (
            row_to_connector_auto_disable_rule(row) if row else None
        )

    async def update(
        self,
        organization_id: UUID | str,
        rule_id: UUID | str,
        *,
        threshold_value: float,
        window_seconds: int,
        consecutive_breaches: int,
        cooldown_seconds: int,
        enabled: bool,
    ) -> ConnectorAutoDisableRule | None:
        r = await self._session.execute(
            select(ConnectorAutoDisableRuleRow).where(
                and_(
                    ConnectorAutoDisableRuleRow.organization_id
                    == str(organization_id),
                    ConnectorAutoDisableRuleRow.id == str(rule_id),
                    ConnectorAutoDisableRuleRow.deleted_at.is_(None),
                )
            )
        )
        row = r.scalar_one_or_none()
        if row is None:
            return None
        row.threshold_value = float(threshold_value)
        row.window_seconds = int(window_seconds)
        row.consecutive_breaches = int(consecutive_breaches)
        row.cooldown_seconds = int(cooldown_seconds)
        row.enabled = bool(enabled)
        row.updated_at = _now()
        await self._session.flush()
        return row_to_connector_auto_disable_rule(row)

    async def soft_delete(
        self, organization_id: UUID | str, rule_id: UUID | str
    ) -> bool:
        r = await self._session.execute(
            select(ConnectorAutoDisableRuleRow).where(
                and_(
                    ConnectorAutoDisableRuleRow.organization_id
                    == str(organization_id),
                    ConnectorAutoDisableRuleRow.id == str(rule_id),
                    ConnectorAutoDisableRuleRow.deleted_at.is_(None),
                )
            )
        )
        row = r.scalar_one_or_none()
        if row is None:
            return False
        row.deleted_at = _now()
        row.enabled = False
        row.updated_at = _now()
        await self._session.flush()
        return True

    async def list_for_org(
        self,
        organization_id: UUID | str,
        *,
        source_id: UUID | str | None = None,
        enabled: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ConnectorAutoDisableRule], int]:
        filters = [
            ConnectorAutoDisableRuleRow.organization_id
            == str(organization_id),
            ConnectorAutoDisableRuleRow.deleted_at.is_(None),
        ]
        if source_id is not None:
            filters.append(
                ConnectorAutoDisableRuleRow.source_id == str(source_id)
            )
        if enabled is not None:
            filters.append(
                ConnectorAutoDisableRuleRow.enabled == bool(enabled)
            )
        where_clause = and_(*filters)
        total_r = await self._session.execute(
            select(func.count(ConnectorAutoDisableRuleRow.id)).where(
                where_clause
            )
        )
        total = int(total_r.scalar_one() or 0)
        rows = (
            await self._session.execute(
                select(ConnectorAutoDisableRuleRow)
                .where(where_clause)
                .order_by(desc(ConnectorAutoDisableRuleRow.created_at))
                .limit(max(1, min(int(limit), 500)))
                .offset(max(0, int(offset)))
            )
        ).scalars().all()
        return [
            row_to_connector_auto_disable_rule(r) for r in rows
        ], total

    async def list_enabled_for_source(
        self, organization_id: UUID | str, source_id: UUID | str
    ) -> list[ConnectorAutoDisableRule]:
        rows = (
            await self._session.execute(
                select(ConnectorAutoDisableRuleRow)
                .where(
                    and_(
                        ConnectorAutoDisableRuleRow.organization_id
                        == str(organization_id),
                        ConnectorAutoDisableRuleRow.source_id
                        == str(source_id),
                        ConnectorAutoDisableRuleRow.deleted_at.is_(None),
                        ConnectorAutoDisableRuleRow.enabled.is_(True),
                    )
                )
                .order_by(ConnectorAutoDisableRuleRow.created_at)
            )
        ).scalars().all()
        return [
            row_to_connector_auto_disable_rule(r) for r in rows
        ]

    async def list_distinct_source_ids(
        self, organization_id: UUID | str
    ) -> list[str]:
        rows = (
            await self._session.execute(
                select(distinct(ConnectorAutoDisableRuleRow.source_id))
                .where(
                    and_(
                        ConnectorAutoDisableRuleRow.organization_id
                        == str(organization_id),
                        ConnectorAutoDisableRuleRow.deleted_at.is_(None),
                        ConnectorAutoDisableRuleRow.enabled.is_(True),
                    )
                )
            )
        ).scalars().all()
        return [str(r) for r in rows]


# ---------------------------------------------------------------------------
# Event repository
# ---------------------------------------------------------------------------


class ConnectorAutoDisableEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def add(
        self,
        *,
        organization_id: UUID | str,
        source_id: UUID | str,
        trigger: AutoDisableTrigger,
        reason: str,
        breach_count: int,
        window_start: datetime,
        window_end: datetime,
        status: AutoDisableEventStatus,
        alert_event_id: str | None = None,
        health_snapshot_id: str | None = None,
        audit_correlation_id: str = "",
        max_reason_length: int = 500,
    ) -> ConnectorAutoDisableEvent:
        row = ConnectorAutoDisableEventRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            source_id=str(source_id),
            trigger=trigger.value,
            reason=_truncate(reason, limit=max_reason_length) or "",
            breach_count=int(breach_count),
            window_start=window_start,
            window_end=window_end,
            status=status.value,
            alert_event_id=alert_event_id,
            health_snapshot_id=health_snapshot_id,
            recovery_actor_id=None,
            recovery_reason=None,
            recovered_at=None,
            audit_correlation_id=audit_correlation_id or "",
            created_at=_now(),
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_connector_auto_disable_event(row)

    async def get(
        self, organization_id: UUID | str, event_id: UUID | str
    ) -> ConnectorAutoDisableEvent | None:
        r = await self._session.execute(
            select(ConnectorAutoDisableEventRow).where(
                and_(
                    ConnectorAutoDisableEventRow.organization_id
                    == str(organization_id),
                    ConnectorAutoDisableEventRow.id == str(event_id),
                )
            )
        )
        row = r.scalar_one_or_none()
        return (
            row_to_connector_auto_disable_event(row) if row else None
        )

    async def list_for_org(
        self,
        organization_id: UUID | str,
        *,
        source_id: UUID | str | None = None,
        status: AutoDisableEventStatus | str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ConnectorAutoDisableEvent], int]:
        filters = [
            ConnectorAutoDisableEventRow.organization_id
            == str(organization_id)
        ]
        if source_id is not None:
            filters.append(
                ConnectorAutoDisableEventRow.source_id == str(source_id)
            )
        if status is not None:
            status_value = (
                status.value
                if isinstance(status, AutoDisableEventStatus)
                else str(status)
            )
            filters.append(
                ConnectorAutoDisableEventRow.status == status_value
            )
        where_clause = and_(*filters)
        total_r = await self._session.execute(
            select(func.count(ConnectorAutoDisableEventRow.id)).where(
                where_clause
            )
        )
        total = int(total_r.scalar_one() or 0)
        rows = (
            await self._session.execute(
                select(ConnectorAutoDisableEventRow)
                .where(where_clause)
                .order_by(desc(ConnectorAutoDisableEventRow.created_at))
                .limit(max(1, min(int(limit), 500)))
                .offset(max(0, int(offset)))
            )
        ).scalars().all()
        return [
            row_to_connector_auto_disable_event(r) for r in rows
        ], total

    async def list_active_for_source(
        self, organization_id: UUID | str, source_id: UUID | str
    ) -> list[ConnectorAutoDisableEvent]:
        rows = (
            await self._session.execute(
                select(ConnectorAutoDisableEventRow)
                .where(
                    and_(
                        ConnectorAutoDisableEventRow.organization_id
                        == str(organization_id),
                        ConnectorAutoDisableEventRow.source_id
                        == str(source_id),
                        ConnectorAutoDisableEventRow.status
                        == AutoDisableEventStatus.ACTIVE.value,
                    )
                )
                .order_by(desc(ConnectorAutoDisableEventRow.created_at))
            )
        ).scalars().all()
        return [
            row_to_connector_auto_disable_event(r) for r in rows
        ]

    async def latest_active_for_source(
        self, organization_id: UUID | str, source_id: UUID | str
    ) -> ConnectorAutoDisableEvent | None:
        rows = (
            await self._session.execute(
                select(ConnectorAutoDisableEventRow)
                .where(
                    and_(
                        ConnectorAutoDisableEventRow.organization_id
                        == str(organization_id),
                        ConnectorAutoDisableEventRow.source_id
                        == str(source_id),
                        ConnectorAutoDisableEventRow.status
                        == AutoDisableEventStatus.ACTIVE.value,
                    )
                )
                .order_by(desc(ConnectorAutoDisableEventRow.created_at))
                .limit(1)
            )
        ).scalars().all()
        if not rows:
            return None
        return row_to_connector_auto_disable_event(rows[0])

    async def recent_for_source(
        self,
        organization_id: UUID | str,
        source_id: UUID | str,
        *,
        limit: int = 50,
    ) -> list[ConnectorAutoDisableEvent]:
        rows = (
            await self._session.execute(
                select(ConnectorAutoDisableEventRow)
                .where(
                    and_(
                        ConnectorAutoDisableEventRow.organization_id
                        == str(organization_id),
                        ConnectorAutoDisableEventRow.source_id
                        == str(source_id),
                    )
                )
                .order_by(desc(ConnectorAutoDisableEventRow.created_at))
                .limit(max(1, min(int(limit), 200)))
            )
        ).scalars().all()
        return [
            row_to_connector_auto_disable_event(r) for r in rows
        ]

    async def transition_status(
        self,
        organization_id: UUID | str,
        event_id: UUID | str,
        *,
        status: AutoDisableEventStatus,
        recovery_actor_id: str | None = None,
        recovery_reason: str | None = None,
        recovered_at: datetime | None = None,
    ) -> ConnectorAutoDisableEvent | None:
        r = await self._session.execute(
            select(ConnectorAutoDisableEventRow).where(
                and_(
                    ConnectorAutoDisableEventRow.organization_id
                    == str(organization_id),
                    ConnectorAutoDisableEventRow.id == str(event_id),
                )
            )
        )
        row = r.scalar_one_or_none()
        if row is None:
            return None
        row.status = status.value
        if recovery_actor_id is not None:
            row.recovery_actor_id = recovery_actor_id
        if recovery_reason is not None:
            row.recovery_reason = _truncate(
                recovery_reason, limit=500
            )
        if recovered_at is not None:
            row.recovered_at = recovered_at
        await self._session.flush()
        return row_to_connector_auto_disable_event(row)


__all__ = [
    "ConnectorAutoDisableEventRepository",
    "ConnectorAutoDisableRuleRepository",
]
