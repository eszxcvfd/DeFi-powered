"""Tests for the connector health audit sanitizer contract (US-046)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.connector_health import (
    ConnectorHealthService,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditTargetType,
)
from livelead.domain.connector_health.enums import (
    ConnectorHealthStatus,
)
from livelead.domain.runtime.enums import EnvironmentMode
from livelead.infrastructure.db.models import (
    AuditEntryRow,
    SourceRow,
)


ORG_ID = "00000000-0000-4000-8000-000000000001"


async def _seed_source(
    session: AsyncSession,
    *,
    source_id: str,
    domain: str = "example.com",
) -> None:
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


async def _seed_audit(
    session: AsyncSession,
    *,
    action: str,
    occurred_at: datetime,
    source_id: str,
    metadata: dict | None = None,
) -> None:
    session.add(
        AuditEntryRow(
            id="00000000-0000-4000-8000-0000000999"
            f"{abs(hash((action, occurred_at.isoformat(), source_id))) % 1000:03d}",
            organization_id=ORG_ID,
            actor_id="system",
            actor_type="system",
            actor_role="system",
            action=action,
            action_family=action.split(".")[0],
            target_type="system",
            target_id="system",
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


def _build_service(session: AsyncSession) -> ConnectorHealthService:
    return ConnectorHealthService(
        session, environment_mode=EnvironmentMode.PILOT_LIVE
    )


@pytest.mark.asyncio
async def test_compute_snapshot_emits_secret_safe_audit_metadata(
    session: AsyncSession,
) -> None:
    source_id = "src-secret-test-1"
    await _seed_source(session, source_id=source_id)
    now = datetime.now(UTC).replace(tzinfo=None)
    # Seed an audit row that contains a secret in
    # the metadata. The bounded path runs the
    # audit payload through the
    # `SanitizeAlertPayload` helper from `US-041`
    # so the secret never reaches the audit
    # entry's `metadata_json`.
    await _seed_audit(
        session,
        action="discovery.run.completed",
        occurred_at=now - timedelta(minutes=10),
        source_id=source_id,
        metadata={"duration_ms": 120, "api_key": "sk-secret"},
    )
    service = _build_service(session)
    snapshot = await service.compute_snapshot(
        organization_id=ORG_ID,
        source_id=source_id,
    )
    assert snapshot.id
    rows = (
        await session.execute(
            AuditEntryRow.__table__.select().where(
                AuditEntryRow.action
                == AuditAction.CONNECTOR_HEALTH_SNAPSHOT_COMPUTED.value
            )
        )
    ).fetchall()
    assert rows
    for row in rows:
        metadata = row.metadata_json or ""
        assert "sk-secret" not in metadata
        assert "api_key" not in metadata or "REDACTED" in metadata


@pytest.mark.asyncio
async def test_compute_snapshot_uses_existing_target_type(
    session: AsyncSession,
) -> None:
    source_id = "src-target-type-1"
    await _seed_source(session, source_id=source_id)
    service = _build_service(session)
    await service.compute_snapshot(
        organization_id=ORG_ID,
        source_id=source_id,
    )
    rows = (
        await session.execute(
            AuditEntryRow.__table__.select().where(
                AuditEntryRow.action
                == AuditAction.CONNECTOR_HEALTH_SNAPSHOT_COMPUTED.value
            )
        )
    ).fetchall()
    assert rows
    for row in rows:
        assert row.target_type == (
            AuditTargetType.CONNECTOR_HEALTH_SNAPSHOT.value
        )


@pytest.mark.asyncio
async def test_compute_snapshot_emits_snapshot_row_with_status(
    session: AsyncSession,
) -> None:
    source_id = "src-snapshot-status-1"
    await _seed_source(session, source_id=source_id)
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(9):
        await _seed_audit(
            session,
            action="discovery.run.completed",
            occurred_at=now - timedelta(minutes=10 + i),
            source_id=source_id,
            metadata={"duration_ms": 100 + i * 5},
        )
    await _seed_audit(
        session,
        action="discovery.run.failed",
        occurred_at=now - timedelta(minutes=2),
        source_id=source_id,
        metadata={"error_code": "timeout", "error_message": "request timed out"},
    )
    service = _build_service(session)
    snapshot = await service.compute_snapshot(
        organization_id=ORG_ID,
        source_id=source_id,
    )
    assert snapshot.status in {
        ConnectorHealthStatus.DEGRADED,
        ConnectorHealthStatus.UNHEALTHY,
        ConnectorHealthStatus.HEALTHY,
        ConnectorHealthStatus.UNKNOWN,
    }
    assert snapshot.total_runs == 10
    assert snapshot.success_count == 9
    assert snapshot.failure_count == 1
    assert snapshot.last_error_code == "timeout"
