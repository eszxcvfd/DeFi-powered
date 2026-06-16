"""Unit tests for the alert evaluator signal providers (US-041)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.observability.signals import (
    AuditRetentionBreachRiskProvider,
    BackupAgeHoursProvider,
    BrowserCrashLoopProvider,
    ConnectorFailureRateProvider,
    DiscoveryNeedsUserActionRateProvider,
    SignalProviderFactory,
    WorkerHeartbeatAgeProvider,
)
from livelead.infrastructure.db.models import (
    AlertRuleRow,
    AuditEntryRow,
    DiscoveryJobRow,
    WorkerHeartbeatRow,
)
from livelead.infrastructure.db.session import (
    create_engine,
    create_session_factory,
)
from livelead.infrastructure.observability.worker_heartbeat import (
    record_heartbeat_async,
)
from livelead.infrastructure.db.models import BackupSnapshotRow
from livelead.infrastructure.db.repositories.runtime import (
    BackupSnapshotRepository,
    WorkerHeartbeatRepository,
)
from livelead.runtime.settings import parse_settings


@pytest_asyncio.fixture
async def session():
    settings = parse_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    async with factory() as sess:
        yield sess
    await engine.dispose()


def test_factory_supports_seed_metrics() -> None:
    factory = SignalProviderFactory()
    assert factory.get("backup.age_hours") is not None
    assert factory.get("worker.heartbeat.age_seconds") is not None
    assert factory.get("connector.failure_rate") is not None
    assert factory.get("discovery.needs_user_action_rate") is not None
    assert factory.get("browser.crash_loop") is not None
    assert factory.get("audit.retention_breach_risk") is not None
    assert factory.get("not.a.metric") is None


@pytest.mark.asyncio
async def test_backup_age_hours_returns_inf_when_no_snapshot(session: AsyncSession) -> None:
    repo = BackupSnapshotRepository(session)
    latest = await repo.latest()
    # wipe to make this test deterministic
    if latest is not None:
        from sqlalchemy import delete

        await session.execute(delete(BackupSnapshotRow))
        await session.commit()
    sample = await BackupAgeHoursProvider().read(
        session, organization_id="00000000-0000-4000-8000-000000000001", window_seconds=0
    )
    assert sample.value == float("inf")
    assert sample.details == {"reason": "no_backup"}


@pytest.mark.asyncio
async def test_worker_heartbeat_age_returns_inf_when_no_heartbeat(session: AsyncSession) -> None:
    from sqlalchemy import delete

    await session.execute(delete(WorkerHeartbeatRow))
    await session.commit()
    sample = await WorkerHeartbeatAgeProvider().read(
        session, organization_id="00000000-0000-4000-8000-000000000001", window_seconds=0
    )
    assert sample.value == float("inf")
    assert sample.details == {"reason": "no_heartbeat"}


@pytest.mark.asyncio
async def test_connector_failure_rate_zero_when_no_jobs(session: AsyncSession) -> None:
    from sqlalchemy import delete

    await session.execute(delete(DiscoveryJobRow))
    await session.commit()
    sample = await ConnectorFailureRateProvider().read(
        session, organization_id="00000000-0000-4000-8000-000000000001", window_seconds=600
    )
    assert sample.value == 0.0
    assert sample.details == {"total_jobs": 0, "failed_jobs": 0}


@pytest.mark.asyncio
async def test_connector_failure_rate_counts_failures(session: AsyncSession) -> None:
    from sqlalchemy import delete

    org_id = "00000000-0000-4000-8000-000000000001"
    await session.execute(delete(DiscoveryJobRow))
    now = datetime.utcnow()
    for i in range(4):
        await session.execute(
            DiscoveryJobRow.__table__.insert().values(
                id=str(uuid4()),
                organization_id=org_id,
                campaign_id=str(uuid4()),
                status="succeeded",
                completed_at=now - timedelta(seconds=10),
            )
        )
    for i in range(6):
        await session.execute(
            DiscoveryJobRow.__table__.insert().values(
                id=str(uuid4()),
                organization_id=org_id,
                campaign_id=str(uuid4()),
                status="failed",
                completed_at=now - timedelta(seconds=10),
            )
        )
    await session.commit()
    sample = await ConnectorFailureRateProvider().read(
        session, organization_id=org_id, window_seconds=600
    )
    assert sample.value == pytest.approx(0.6, abs=1e-9)
    assert sample.details == {"total_jobs": 10, "failed_jobs": 6}


@pytest.mark.asyncio
async def test_discovery_needs_user_action_rate(session: AsyncSession) -> None:
    from sqlalchemy import delete

    org_id = "00000000-0000-4000-8000-000000000001"
    await session.execute(delete(DiscoveryJobRow))
    now = datetime.utcnow()
    for i in range(7):
        await session.execute(
            DiscoveryJobRow.__table__.insert().values(
                id=str(uuid4()),
                organization_id=org_id,
                campaign_id=str(uuid4()),
                status="succeeded",
                completed_at=now - timedelta(seconds=10),
            )
        )
    for i in range(3):
        await session.execute(
            DiscoveryJobRow.__table__.insert().values(
                id=str(uuid4()),
                organization_id=org_id,
                campaign_id=str(uuid4()),
                status="needs_user_action",
                completed_at=now - timedelta(seconds=10),
            )
        )
    await session.commit()
    sample = await DiscoveryNeedsUserActionRateProvider().read(
        session, organization_id=org_id, window_seconds=600
    )
    assert sample.value == pytest.approx(0.3, abs=1e-9)
    assert sample.details == {"total_jobs": 10, "needs_user_action_jobs": 3}


@pytest.mark.asyncio
async def test_browser_crash_loop_counts_browser_audit_rows(session: AsyncSession) -> None:
    from sqlalchemy import delete

    org_id = "00000000-0000-4000-8000-000000000001"
    await session.execute(delete(AuditEntryRow))
    now = datetime.utcnow()
    for _ in range(3):
        await session.execute(
            AuditEntryRow.__table__.insert().values(
                id=str(uuid4()),
                organization_id=org_id,
                actor_id="user-1",
                actor_type="human",
                actor_role="analyst",
                action="browser.action.confirmation.cancelled",
                action_family="browser",
                target_type="browser_session",
                target_id="session-1",
                target_display="session-1",
                outcome="succeeded",
                occurred_at=now,
            )
        )
    await session.commit()
    sample = await BrowserCrashLoopProvider().read(
        session, organization_id=org_id, window_seconds=600
    )
    assert sample.value == 3.0


@pytest.mark.asyncio
async def test_audit_retention_breach_risk_zero_when_no_audit(session: AsyncSession) -> None:
    from sqlalchemy import delete

    await session.execute(delete(AuditEntryRow))
    await session.commit()
    sample = await AuditRetentionBreachRiskProvider().read(
        session, organization_id="00000000-0000-4000-8000-000000000001", window_seconds=0
    )
    assert sample.value == 0.0
    assert sample.details == {"oldest": None}
