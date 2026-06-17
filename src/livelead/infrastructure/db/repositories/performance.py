"""Performance snapshot and browser session sample
repositories (US-044).

The repository layer is the only place in the
application that talks to the SQLAlchemy rows for
`performance_snapshots` and `browser_session_samples`.
Domain code consumes the pure dataclasses from
`livelead.domain.performance.models`; the interfaces
layer wraps them in Pydantic schemas.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.performance.enums import (
    PerformanceScenario,
)
from livelead.domain.performance.models import (
    BrowserSessionSample,
    PerformanceSnapshot,
)
from livelead.infrastructure.db.models import (
    BrowserSessionSampleRow,
    PerformanceSnapshotRow,
)

logger = logging.getLogger("livelead.performance_repo")


# ---------------------------------------------------------------------------
# Mappers
# ---------------------------------------------------------------------------


def _scenario_from_string(value: str | None) -> PerformanceScenario:
    if not value:
        return PerformanceScenario.API_READ_LATENCY
    try:
        return PerformanceScenario(value)
    except ValueError:
        return PerformanceScenario.API_READ_LATENCY


def row_to_performance_snapshot(row: PerformanceSnapshotRow) -> PerformanceSnapshot:
    return PerformanceSnapshot(
        id=row.id,
        organization_id=row.organization_id,
        scenario=_scenario_from_string(row.scenario),
        started_at=row.started_at,
        completed_at=row.completed_at,
        p50_ms=float(row.p50_ms or 0),
        p95_ms=float(row.p95_ms or 0),
        p99_ms=float(row.p99_ms or 0),
        rps=float(row.rps or 0),
        error_rate=float(row.error_rate or 0),
        concurrent_users=int(row.concurrent_users or 0),
        audit_correlation_id=row.audit_correlation_id or "",
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def row_to_browser_session_sample(
    row: BrowserSessionSampleRow,
) -> BrowserSessionSample:
    return BrowserSessionSample(
        id=row.id,
        organization_id=row.organization_id,
        session_id=row.session_id,
        profile_id=row.profile_id,
        memory_rss_mb=int(row.memory_rss_mb or 0),
        cpu_pct=int(row.cpu_pct or 0),
        budget_pct=int(row.budget_pct or 0),
        audited_at=row.audited_at,
        breach=bool(row.breach),
        created_at=row.created_at,
    )


# ---------------------------------------------------------------------------
# Performance snapshot repository
# ---------------------------------------------------------------------------


class PerformanceSnapshotRepository:
    """Persistence boundary for `performance_snapshots`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def add(
        self,
        *,
        organization_id: UUID | str,
        scenario: PerformanceScenario,
        started_at: datetime,
        audit_correlation_id: str = "",
    ) -> PerformanceSnapshot:
        row = PerformanceSnapshotRow(
            organization_id=str(organization_id),
            scenario=scenario.value,
            started_at=started_at,
            p50_ms=0.0,
            p95_ms=0.0,
            p99_ms=0.0,
            rps=0.0,
            error_rate=0.0,
            concurrent_users=0,
            audit_correlation_id=audit_correlation_id,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_performance_snapshot(row)

    async def complete(
        self,
        snapshot_id: str,
        *,
        completed_at: datetime | None = None,
        p50_ms: float = 0.0,
        p95_ms: float = 0.0,
        p99_ms: float = 0.0,
        rps: float = 0.0,
        error_rate: float = 0.0,
        concurrent_users: int = 0,
    ) -> PerformanceSnapshot | None:
        r = await self._session.execute(
            select(PerformanceSnapshotRow).where(
                PerformanceSnapshotRow.id == snapshot_id
            )
        )
        row = r.scalar_one_or_none()
        if row is None:
            return None
        row.completed_at = completed_at or datetime.utcnow()
        row.p50_ms = float(p50_ms)
        row.p95_ms = float(p95_ms)
        row.p99_ms = float(p99_ms)
        row.rps = float(rps)
        row.error_rate = float(error_rate)
        row.concurrent_users = int(concurrent_users)
        row.updated_at = datetime.utcnow()
        await self._session.flush()
        return row_to_performance_snapshot(row)

    async def list_for_org(
        self,
        organization_id: UUID | str,
        *,
        scenario: PerformanceScenario | str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PerformanceSnapshot], int]:
        filters = [PerformanceSnapshotRow.organization_id == str(organization_id)]
        if scenario is not None:
            scenario_value = (
                scenario.value
                if isinstance(scenario, PerformanceScenario)
                else str(scenario)
            )
            filters.append(PerformanceSnapshotRow.scenario == scenario_value)
        where_clause = and_(*filters)
        total_r = await self._session.execute(
            select(func.count(PerformanceSnapshotRow.id)).where(where_clause)
        )
        total = int(total_r.scalar_one() or 0)
        rows = (
            await self._session.execute(
                select(PerformanceSnapshotRow)
                .where(where_clause)
                .order_by(desc(PerformanceSnapshotRow.started_at))
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()
        return [row_to_performance_snapshot(r) for r in rows], total

    async def latest_for_scenario(
        self,
        organization_id: UUID | str,
        scenario: PerformanceScenario,
    ) -> PerformanceSnapshot | None:
        r = await self._session.execute(
            select(PerformanceSnapshotRow)
            .where(
                and_(
                    PerformanceSnapshotRow.organization_id == str(organization_id),
                    PerformanceSnapshotRow.scenario == scenario.value,
                )
            )
            .order_by(desc(PerformanceSnapshotRow.started_at))
            .limit(1)
        )
        row = r.scalar_one_or_none()
        return row_to_performance_snapshot(row) if row else None


# ---------------------------------------------------------------------------
# Browser session sample repository
# ---------------------------------------------------------------------------


class BrowserSessionSampleRepository:
    """Persistence boundary for `browser_session_samples`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def add(
        self,
        *,
        organization_id: UUID | str,
        session_id: str,
        profile_id: str,
        memory_rss_mb: int,
        cpu_pct: int,
        budget_pct: int,
        breach: bool,
        audited_at: datetime | None = None,
    ) -> BrowserSessionSample:
        row = BrowserSessionSampleRow(
            organization_id=str(organization_id),
            session_id=session_id,
            profile_id=profile_id,
            memory_rss_mb=int(memory_rss_mb),
            cpu_pct=int(cpu_pct),
            budget_pct=int(budget_pct),
            audited_at=audited_at or datetime.utcnow(),
            breach=bool(breach),
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_browser_session_sample(row)

    async def latest_for_session(
        self,
        organization_id: UUID | str,
        session_id: str,
    ) -> BrowserSessionSample | None:
        r = await self._session.execute(
            select(BrowserSessionSampleRow)
            .where(
                and_(
                    BrowserSessionSampleRow.organization_id == str(organization_id),
                    BrowserSessionSampleRow.session_id == session_id,
                )
            )
            .order_by(desc(BrowserSessionSampleRow.audited_at))
            .limit(1)
        )
        row = r.scalar_one_or_none()
        return row_to_browser_session_sample(row) if row else None

    async def rolling_average_budget_pct(
        self,
        organization_id: UUID | str,
        *,
        window_seconds: int = 120,
    ) -> float:
        """Compute the rolling average `budget_pct` over the
        configured window. The bounded SLO evaluator reads
        the result to detect a sustained breach."""

        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(seconds=int(window_seconds))
        r = await self._session.execute(
            select(func.avg(BrowserSessionSampleRow.budget_pct)).where(
                and_(
                    BrowserSessionSampleRow.organization_id == str(organization_id),
                    BrowserSessionSampleRow.audited_at >= cutoff,
                )
            )
        )
        avg = r.scalar_one()
        return float(avg or 0.0)


__all__ = [
    "BrowserSessionSampleRepository",
    "PerformanceSnapshotRepository",
    "row_to_browser_session_sample",
    "row_to_performance_snapshot",
]
