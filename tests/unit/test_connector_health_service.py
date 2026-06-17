"""Unit tests for the connector health service (US-046)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.connector_health import (
    ConnectorHealthError,
    ConnectorHealthInvalidWindow,
    ConnectorHealthService,
    ConnectorHealthSourceNotFound,
)
from livelead.domain.connector_health.enums import (
    ConnectorHealthStatus,
)
from livelead.domain.connector_health.models import (
    ConnectorHealthThresholds,
)
from livelead.domain.runtime.enums import EnvironmentMode
from livelead.infrastructure.db.models import (
    AuditEntryRow,
    ConnectorHealthErrorRow,
    ConnectorHealthSnapshotRow,
    SourceRow,
)


ORG_ID = "00000000-0000-4000-8000-000000000001"
USER_ID = "00000000-0000-4000-8000-000000000002"


def _build_service(
    session: AsyncSession,
    *,
    environment_mode: EnvironmentMode | str = EnvironmentMode.PILOT_LIVE,
    thresholds: ConnectorHealthThresholds | None = None,
) -> ConnectorHealthService:
    return ConnectorHealthService(
        session,
        environment_mode=environment_mode,
        thresholds=thresholds or ConnectorHealthThresholds(),
    )


async def _seed_source(
    session: AsyncSession,
    *,
    source_id: str | None = None,
    domain: str = "example.com",
) -> str:
    if source_id is None:
        source_id = str(uuid4())
    session.add(
        SourceRow(
            id=source_id,
            organization_id=ORG_ID,
            name="Example",
            domain=domain,
            connector_type="rss",
            automation_engine="none",
            authentication_mode="none",
            enabled=True,
            approved=True,
        )
    )
    await session.flush()
    return source_id


async def _seed_audit(
    session: AsyncSession,
    *,
    action: str,
    occurred_at: datetime,
    source_id: str,
    metadata: dict | None = None,
) -> None:
    row_id = str(uuid4())
    session.add(
        AuditEntryRow(
            id=row_id,
            organization_id=ORG_ID,
            actor_id="system",
            actor_type="system",
            actor_role="system",
            action=action,
            action_family=action.split(".")[0],
            target_type="system",
            target_id=system_marker(),
            target_display="",
            outcome="succeeded",
            occurred_at=occurred_at,
            request_id="",
            session_id="",
            correlation_id="",
            client_ip="",
            user_agent="",
            workflow="",
            metadata_json=json.dumps(
                {"source_id": source_id, **(metadata or {})}
            ),
            metadata_redacted=False,
        )
    )
    await session.flush()


def system_marker() -> str:
    return "system"


# ----------------------------------------------------------------------
# Compute
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_snapshot_persists_row_and_audit(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(5):
        await _seed_audit(
            session,
            action="discovery.run.completed",
            occurred_at=now - timedelta(minutes=10 + i),
            source_id=source_id,
            metadata={"duration_ms": 100 + i * 10},
        )
    service = _build_service(session)
    snapshot = await service.compute_snapshot(
        organization_id=ORG_ID,
        source_id=source_id,
        actor=USER_ID,
        actor_role="owner",
    )
    assert snapshot.id
    assert snapshot.source_id == source_id
    assert snapshot.total_runs == 5
    assert snapshot.success_count == 5
    assert snapshot.failure_count == 0
    assert snapshot.status is ConnectorHealthStatus.HEALTHY
    rows = (
        await session.execute(
            select(ConnectorHealthSnapshotRow).where(
                ConnectorHealthSnapshotRow.id == snapshot.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    audit_rows = (
        await session.execute(
            select(AuditEntryRow).where(
                AuditEntryRow.target_id == snapshot.id
            )
        )
    ).scalars().all()
    assert len(audit_rows) == 1
    assert audit_rows[0].action == "connector.health.snapshot.computed"


@pytest.mark.asyncio
async def test_compute_snapshot_with_failures_emits_health_status(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(8):
        await _seed_audit(
            session,
            action="discovery.run.completed",
            occurred_at=now - timedelta(minutes=10 + i),
            source_id=source_id,
            metadata={"duration_ms": 100 + i},
        )
    for i in range(5):
        await _seed_audit(
            session,
            action="discovery.run.failed",
            occurred_at=now - timedelta(minutes=2 + i),
            source_id=source_id,
            metadata={
                "error_code": "rate_limited",
                "error_message": "rate limit exceeded",
            },
        )
    service = _build_service(session)
    snapshot = await service.compute_snapshot(
        organization_id=ORG_ID,
        source_id=source_id,
    )
    assert snapshot.total_runs == 13
    assert snapshot.success_count == 8
    assert snapshot.failure_count == 5
    assert snapshot.last_error_code == "rate_limited"
    assert snapshot.status in {
        ConnectorHealthStatus.DEGRADED,
        ConnectorHealthStatus.UNHEALTHY,
    }


@pytest.mark.asyncio
async def test_compute_snapshot_records_error_rollup(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    await _seed_audit(
        session,
        action="discovery.run.failed",
        occurred_at=now - timedelta(minutes=5),
        source_id=source_id,
        metadata={
            "error_code": "rate_limited",
            "error_message": "rate limit exceeded",
        },
    )
    service = _build_service(session)
    await service.compute_snapshot(
        organization_id=ORG_ID,
        source_id=source_id,
    )
    rows = (
        await session.execute(
            select(ConnectorHealthErrorRow).where(
                ConnectorHealthErrorRow.source_id == source_id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].error_code == "rate_limited"


@pytest.mark.asyncio
async def test_compute_snapshot_skips_rows_outside_window(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    # Audit row outside the bounded window.
    await _seed_audit(
        session,
        action="discovery.run.completed",
        occurred_at=now - timedelta(hours=48),
        source_id=source_id,
        metadata={"duration_ms": 100},
    )
    # Audit row inside the bounded window.
    await _seed_audit(
        session,
        action="discovery.run.completed",
        occurred_at=now - timedelta(minutes=5),
        source_id=source_id,
        metadata={"duration_ms": 200},
    )
    service = _build_service(session)
    snapshot = await service.compute_snapshot(
        organization_id=ORG_ID,
        source_id=source_id,
        window_seconds=3600,
    )
    assert snapshot.total_runs == 1


@pytest.mark.asyncio
async def test_compute_snapshot_rejects_unknown_source(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    with pytest.raises(ConnectorHealthSourceNotFound):
        await service.compute_snapshot(
            organization_id=ORG_ID,
            source_id=str(uuid4()),
        )


@pytest.mark.asyncio
async def test_compute_snapshot_clamps_window_to_mode_bound(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    service = _build_service(
        session, environment_mode=EnvironmentMode.TEST_LIKE
    )
    snapshot = await service.compute_snapshot(
        organization_id=ORG_ID,
        source_id=source_id,
        window_seconds=24 * 3600,
    )
    # The bounded path clips the window to the
    # `test_like` bound (1 hour).
    duration = snapshot.window_end - snapshot.window_start
    assert duration.total_seconds() <= 3600


@pytest.mark.asyncio
async def test_compute_snapshot_returns_unknown_for_no_signals(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    service = _build_service(session)
    snapshot = await service.compute_snapshot(
        organization_id=ORG_ID,
        source_id=source_id,
    )
    assert snapshot.total_runs == 0
    assert snapshot.status is ConnectorHealthStatus.UNKNOWN


# ----------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_summary_emits_audit_entry(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    service = _build_service(session)
    entries = await service.build_summary(
        organization_id=ORG_ID,
        actor=USER_ID,
        actor_role="owner",
    )
    assert len(entries) == 1
    assert entries[0].source_id == source_id
    rows = (
        await session.execute(
            select(AuditEntryRow).where(
                AuditEntryRow.action
                == "connector.health.summary.requested"
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].action_family == "connector"


# ----------------------------------------------------------------------
# Recent errors
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_recent_errors_returns_rollup(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(3):
        await _seed_audit(
            session,
            action="discovery.run.failed",
            occurred_at=now - timedelta(minutes=5 + i),
            source_id=source_id,
            metadata={
                "error_code": "rate_limited",
                "error_message": f"failure {i}",
            },
        )
    service = _build_service(session)
    # First compute to populate the error rollup.
    await service.compute_snapshot(
        organization_id=ORG_ID, source_id=source_id
    )
    errors = await service.list_recent_errors(
        organization_id=ORG_ID,
        source_id=source_id,
        actor=USER_ID,
        actor_role="owner",
    )
    assert len(errors) == 1
    assert errors[0].error_code == "rate_limited"


@pytest.mark.asyncio
async def test_list_recent_errors_rejects_unknown_source(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    with pytest.raises(ConnectorHealthSourceNotFound):
        await service.list_recent_errors(
            organization_id=ORG_ID,
            source_id=str(uuid4()),
        )
