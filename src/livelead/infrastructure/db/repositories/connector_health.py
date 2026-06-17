"""Connector health surface persistence repositories (US-046).

The repository owns every read and write for
``connector_health_snapshots`` and
``connector_health_errors``. All methods take
``organization_id`` first so tenant isolation is
mandatory at the data layer. The repository
deliberately returns pure dataclasses from
``livelead.domain.connector_health.models``; the
application service is the only place that knows
the secret-safe payload contract and the audit
entry shape.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from livelead.infrastructure.db.connector_health_mappers import (
    row_to_connector_health_error,
    row_to_connector_health_snapshot,
)
from livelead.infrastructure.db.models import (
    ConnectorHealthErrorRow,
    ConnectorHealthSnapshotRow,
)

logger = logging.getLogger("livelead.connector_health_repo")


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
# Snapshot repository
# ---------------------------------------------------------------------------


class ConnectorHealthSnapshotRepository:
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
        connector_type: ConnectorType,
        window_start: datetime,
        window_end: datetime,
        total_runs: int,
        success_count: int,
        failure_count: int,
        success_rate: float,
        p50_latency_ms: float,
        p95_latency_ms: float,
        captcha_count: int,
        captcha_rate: float,
        last_run_at: datetime | None,
        last_error_code: str | None,
        last_error_message: str | None,
        status: ConnectorHealthStatus,
        audit_correlation_id: str = "",
        max_error_message_length: int = 500,
    ) -> ConnectorHealthSnapshot:
        now = _now()
        row = ConnectorHealthSnapshotRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            source_id=str(source_id),
            connector_type=connector_type.value,
            window_start=window_start,
            window_end=window_end,
            total_runs=int(total_runs),
            success_count=int(success_count),
            failure_count=int(failure_count),
            success_rate=float(success_rate),
            p50_latency_ms=float(p50_latency_ms),
            p95_latency_ms=float(p95_latency_ms),
            captcha_count=int(captcha_count),
            captcha_rate=float(captcha_rate),
            last_run_at=last_run_at,
            last_error_code=_truncate(last_error_code, limit=64),
            last_error_message=_truncate(
                last_error_message, limit=max_error_message_length
            ),
            status=status.value,
            audit_correlation_id=audit_correlation_id or "",
            computed_at=now,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_connector_health_snapshot(row)

    async def list_for_org(
        self,
        organization_id: UUID | str,
        *,
        source_id: UUID | str | None = None,
        status: ConnectorHealthStatus | str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ConnectorHealthSnapshot], int]:
        filters = [
            ConnectorHealthSnapshotRow.organization_id
            == str(organization_id)
        ]
        if source_id is not None:
            filters.append(
                ConnectorHealthSnapshotRow.source_id == str(source_id)
            )
        if status is not None:
            status_value = (
                status.value
                if isinstance(status, ConnectorHealthStatus)
                else str(status)
            )
            filters.append(
                ConnectorHealthSnapshotRow.status == status_value
            )
        where_clause = and_(*filters)
        total_r = await self._session.execute(
            select(func.count(ConnectorHealthSnapshotRow.id)).where(
                where_clause
            )
        )
        total = int(total_r.scalar_one() or 0)
        rows = (
            await self._session.execute(
                select(ConnectorHealthSnapshotRow)
                .where(where_clause)
                .order_by(desc(ConnectorHealthSnapshotRow.computed_at))
                .limit(max(1, min(int(limit), 500)))
                .offset(max(0, int(offset)))
            )
        ).scalars().all()
        return [row_to_connector_health_snapshot(r) for r in rows], total

    async def latest_for_source(
        self,
        organization_id: UUID | str,
        source_id: UUID | str,
    ) -> ConnectorHealthSnapshot | None:
        r = await self._session.execute(
            select(ConnectorHealthSnapshotRow)
            .where(
                and_(
                    ConnectorHealthSnapshotRow.organization_id
                    == str(organization_id),
                    ConnectorHealthSnapshotRow.source_id
                    == str(source_id),
                )
            )
            .order_by(desc(ConnectorHealthSnapshotRow.computed_at))
            .limit(1)
        )
        row = r.scalar_one_or_none()
        return (
            row_to_connector_health_snapshot(row) if row else None
        )

    async def latest_for_org(
        self,
        organization_id: UUID | str,
    ) -> list[ConnectorHealthSnapshot]:
        """Return the latest snapshot per source for the
        bounded summary endpoint. The bounded path
        reads the most recent snapshot for each
        source; a missing source returns no entry.
        """

        from sqlalchemy import distinct

        result = await self._session.execute(
            select(ConnectorHealthSnapshotRow)
            .where(
                ConnectorHealthSnapshotRow.organization_id
                == str(organization_id)
            )
            .order_by(
                ConnectorHealthSnapshotRow.source_id,
                desc(ConnectorHealthSnapshotRow.computed_at),
            )
        )
        latest_by_source: dict[str, ConnectorHealthSnapshot] = {}
        for row in result.scalars().all():
            if row.source_id not in latest_by_source:
                latest_by_source[row.source_id] = (
                    row_to_connector_health_snapshot(row)
                )
        return list(latest_by_source.values())


# ---------------------------------------------------------------------------
# Error rollup repository
# ---------------------------------------------------------------------------


class ConnectorHealthErrorRepository:
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
        error_code: str,
        error_message: str,
        first_seen_at: datetime,
        last_seen_at: datetime,
        occurrence_count: int = 1,
        audit_correlation_id: str = "",
        max_error_message_length: int = 500,
    ) -> ConnectorHealthError:
        row = ConnectorHealthErrorRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            source_id=str(source_id),
            error_code=error_code[:64],
            error_message=_truncate(
                error_message, limit=max_error_message_length
            )
            or "",
            first_seen_at=first_seen_at,
            last_seen_at=last_seen_at,
            occurrence_count=int(occurrence_count),
            audit_correlation_id=audit_correlation_id or "",
            created_at=_now(),
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_connector_health_error(row)

    async def list_for_source(
        self,
        organization_id: UUID | str,
        source_id: UUID | str,
        *,
        limit: int = 20,
    ) -> list[ConnectorHealthError]:
        result = await self._session.execute(
            select(ConnectorHealthErrorRow)
            .where(
                and_(
                    ConnectorHealthErrorRow.organization_id
                    == str(organization_id),
                    ConnectorHealthErrorRow.source_id == str(source_id),
                )
            )
            .order_by(desc(ConnectorHealthErrorRow.last_seen_at))
            .limit(max(1, min(int(limit), 200)))
        )
        return [
            row_to_connector_health_error(r)
            for r in result.scalars().all()
        ]


__all__ = [
    "ConnectorHealthErrorRepository",
    "ConnectorHealthSnapshotRepository",
]
