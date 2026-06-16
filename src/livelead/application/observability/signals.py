"""Signal providers for the alert evaluator (US-041).

Each provider knows how to read a single metric from the durable
tables that already exist. The evaluator asks the
`SignalProviderFactory` for the right provider by metric name, the
provider returns a `SignalSample`, and the evaluator applies the
rule's operator and threshold.

Signal providers are pure functions of the database state: no
in-memory state, no caching. The evaluator's cooldown window and
dedup key handle rate limiting; a missed tick only costs a missed
notification, not a stale value.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Protocol

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.infrastructure.db.models import (
    AuditEntryRow,
    DiscoveryJobRow,
    WorkerHeartbeatRow,
)
from livelead.infrastructure.db.repositories.runtime import (
    BackupSnapshotRepository,
    WorkerHeartbeatRepository,
)

logger = logging.getLogger("livelead.observability_signals")


@dataclass(frozen=True, slots=True)
class SignalSample:
    """The result of reading a single metric.

    `value` is the numeric measurement the evaluator applies the
    rule's operator to. `window_seconds` is the rolling window
    used to compute the value (0 means point-in-time). `details`
    is a small, secret-safe dictionary that the evaluator can
    attach to the resulting alert event payload.
    """

    value: float
    window_seconds: int = 0
    details: dict[str, Any] | None = None


class SignalProvider(Protocol):
    """Read a single metric from the durable tables."""

    metric_name: str

    async def read(
        self,
        session: AsyncSession,
        *,
        organization_id: str,
        window_seconds: int,
    ) -> SignalSample: ...


# ---------------------------------------------------------------------------
# backup.age_hours
# ---------------------------------------------------------------------------


class BackupAgeHoursProvider:
    metric_name = "backup.age_hours"

    async def read(
        self,
        session: AsyncSession,
        *,
        organization_id: str,
        window_seconds: int,
    ) -> SignalSample:
        repo = BackupSnapshotRepository(session)
        latest = await repo.latest()
        if latest is None:
            return SignalSample(value=float("inf"), window_seconds=0, details={"reason": "no_backup"})
        age_hours = latest.age_seconds() / 3600.0
        return SignalSample(
            value=age_hours,
            window_seconds=0,
            details={
                "backup_id": latest.backup_id,
                "verification_status": latest.verification_status.value,
                "age_seconds": latest.age_seconds(),
            },
        )


# ---------------------------------------------------------------------------
# worker.heartbeat.age_seconds
# ---------------------------------------------------------------------------


class WorkerHeartbeatAgeProvider:
    metric_name = "worker.heartbeat.age_seconds"

    async def read(
        self,
        session: AsyncSession,
        *,
        organization_id: str,
        window_seconds: int,
    ) -> SignalSample:
        repo = WorkerHeartbeatRepository(session)
        latest = await repo.latest()
        if latest is None:
            return SignalSample(value=float("inf"), window_seconds=0, details={"reason": "no_heartbeat"})
        return SignalSample(
            value=latest.age_seconds,
            window_seconds=0,
            details={
                "worker_id": latest.worker_id,
                "last_task": latest.last_task,
            },
        )


# ---------------------------------------------------------------------------
# connector.failure_rate
# ---------------------------------------------------------------------------


class ConnectorFailureRateProvider:
    metric_name = "connector.failure_rate"

    async def read(
        self,
        session: AsyncSession,
        *,
        organization_id: str,
        window_seconds: int,
    ) -> SignalSample:
        window = max(int(window_seconds or 1800), 60)
        since = datetime.utcnow() - timedelta(seconds=window)
        completed = await session.execute(
            select(func.count(DiscoveryJobRow.id)).where(
                and_(
                    DiscoveryJobRow.organization_id == str(organization_id),
                    DiscoveryJobRow.completed_at.is_not(None),
                    DiscoveryJobRow.completed_at >= since,
                )
            )
        )
        failed = await session.execute(
            select(func.count(DiscoveryJobRow.id)).where(
                and_(
                    DiscoveryJobRow.organization_id == str(organization_id),
                    DiscoveryJobRow.completed_at.is_not(None),
                    DiscoveryJobRow.completed_at >= since,
                    DiscoveryJobRow.status == "failed",
                )
            )
        )
        total = int(completed.scalar_one() or 0)
        failed_n = int(failed.scalar_one() or 0)
        rate = (failed_n / total) if total else 0.0
        return SignalSample(
            value=float(rate),
            window_seconds=window,
            details={
                "total_jobs": total,
                "failed_jobs": failed_n,
            },
        )


# ---------------------------------------------------------------------------
# discovery.needs_user_action_rate
# ---------------------------------------------------------------------------


class DiscoveryNeedsUserActionRateProvider:
    metric_name = "discovery.needs_user_action_rate"

    async def read(
        self,
        session: AsyncSession,
        *,
        organization_id: str,
        window_seconds: int,
    ) -> SignalSample:
        window = max(int(window_seconds or 3600), 60)
        since = datetime.utcnow() - timedelta(seconds=window)
        completed = await session.execute(
            select(func.count(DiscoveryJobRow.id)).where(
                and_(
                    DiscoveryJobRow.organization_id == str(organization_id),
                    DiscoveryJobRow.completed_at.is_not(None),
                    DiscoveryJobRow.completed_at >= since,
                )
            )
        )
        nua = await session.execute(
            select(func.count(DiscoveryJobRow.id)).where(
                and_(
                    DiscoveryJobRow.organization_id == str(organization_id),
                    DiscoveryJobRow.completed_at.is_not(None),
                    DiscoveryJobRow.completed_at >= since,
                    DiscoveryJobRow.status == "needs_user_action",
                )
            )
        )
        total = int(completed.scalar_one() or 0)
        nua_n = int(nua.scalar_one() or 0)
        rate = (nua_n / total) if total else 0.0
        return SignalSample(
            value=float(rate),
            window_seconds=window,
            details={
                "total_jobs": total,
                "needs_user_action_jobs": nua_n,
            },
        )


# ---------------------------------------------------------------------------
# browser.crash_loop
# ---------------------------------------------------------------------------


class BrowserCrashLoopProvider:
    """Counts the number of audit-recorded browser crashes in the window.

    The first slice treats every `BROWSER_LAUNCH_DENIED` or
    `BROWSER_CONFIRMATION_*` audit entry whose `metadata_json`
    mentions a crash as a crash event. A future story can attach a
    dedicated `browser.crashed` action; for now the heuristic is
    good enough to alert on a sustained crash loop without
    redesigning the audit log.
    """

    metric_name = "browser.crash_loop"

    async def read(
        self,
        session: AsyncSession,
        *,
        organization_id: str,
        window_seconds: int,
    ) -> SignalSample:
        window = max(int(window_seconds or 600), 60)
        since = datetime.utcnow() - timedelta(seconds=window)
        rows = await session.execute(
            select(func.count(AuditEntryRow.id)).where(
                and_(
                    AuditEntryRow.organization_id == str(organization_id),
                    AuditEntryRow.action.like("browser.%"),
                    AuditEntryRow.occurred_at >= since,
                )
            )
        )
        count = int(rows.scalar_one() or 0)
        return SignalSample(
            value=float(count),
            window_seconds=window,
            details={"crash_events": count},
        )


# ---------------------------------------------------------------------------
# audit.retention_breach_risk
# ---------------------------------------------------------------------------


class AuditRetentionBreachRiskProvider:
    metric_name = "audit.retention_breach_risk"

    async def read(
        self,
        session: AsyncSession,
        *,
        organization_id: str,
        window_seconds: int,
    ) -> SignalSample:
        r = await session.execute(
            select(func.min(AuditEntryRow.occurred_at)).where(
                AuditEntryRow.organization_id == str(organization_id)
            )
        )
        oldest = r.scalar_one()
        if oldest is None:
            return SignalSample(value=0.0, window_seconds=0, details={"oldest": None})
        age_seconds = (datetime.utcnow() - oldest).total_seconds()
        age_days = max(age_seconds / 86400.0, 0.0)
        return SignalSample(
            value=age_days,
            window_seconds=0,
            details={"oldest_audit_age_days": age_days},
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class SignalProviderFactory:
    """Maps metric names to the corresponding provider.

    The factory is constructed once per process and shared across
    ticks. It is intentionally not a singleton; tests can pass a
    factory that returns mock providers.
    """

    def __init__(self) -> None:
        self._providers: dict[str, SignalProvider] = {
            p.metric_name: p
            for p in (
                BackupAgeHoursProvider(),
                WorkerHeartbeatAgeProvider(),
                ConnectorFailureRateProvider(),
                DiscoveryNeedsUserActionRateProvider(),
                BrowserCrashLoopProvider(),
                AuditRetentionBreachRiskProvider(),
            )
        }

    def get(self, metric_name: str) -> SignalProvider | None:
        return self._providers.get(metric_name)

    def supported_metrics(self) -> set[str]:
        return set(self._providers.keys())


__all__ = [
    "AuditRetentionBreachRiskProvider",
    "BackupAgeHoursProvider",
    "BrowserCrashLoopProvider",
    "ConnectorFailureRateProvider",
    "DiscoveryNeedsUserActionRateProvider",
    "SignalProvider",
    "SignalProviderFactory",
    "SignalSample",
    "WorkerHeartbeatAgeProvider",
]
