"""Integration tests for the alert evaluator (US-041)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete

from livelead.application.audit.audit_service import AuditService
from livelead.application.observability import (
    AlertEvaluator,
    AlertService,
    SignalProviderFactory,
)
from livelead.infrastructure.db.models import BackupSnapshotRow
from livelead.infrastructure.db.repositories.observability import (
    AlertEventRepository,
)
from livelead.infrastructure.observability.worker_heartbeat import (
    record_heartbeat_async,
)
from livelead.infrastructure.db.session import (
    create_engine,
    create_session_factory,
)
from livelead.runtime.settings import parse_settings

ORG_ID = "00000000-0000-4000-8000-000000000001"


async def _make_evaluator(session):
    audit = AuditService(session)
    service = AlertService(session, audit_service=audit)
    factory = SignalProviderFactory()
    return AlertEvaluator(
        session,
        audit_service=audit,
        alert_service=service,
        signal_factory=factory,
    ), service


async def _ensure_fresh_heartbeat():
    """Insert a fresh worker heartbeat so the seed rules don't fire on noise.

    The `worker.heartbeat.missing` seed rule fires whenever the
    worker_heartbeats table is empty; the other seed rules stay
    silent when there are no discovery jobs / browser sessions.
    A fresh heartbeat keeps the test focused on the rule the
    test creates.
    """

    settings = parse_settings()
    engine = create_engine(settings)
    sf = create_session_factory(engine)
    await record_heartbeat_async(sf, last_task="test")
    await engine.dispose()


async def _create_rule(service, metric, threshold=0.0, window=0, cooldown=600):
    return await service.create_rule(
        organization_id=ORG_ID,
        name=f"test.evaluator.{uuid4().hex[:8]}",
        metric=metric,
        operator="gt",
        threshold=threshold,
        window_seconds=window,
        severity="warning",
        cooldown_seconds=cooldown,
        channels=["in_app"],
        enabled=True,
        actor="test",
        actor_role="owner",
    )


@pytest.mark.asyncio
async def test_evaluator_fires_event_for_stale_backup(migrated_session):
    await migrated_session.execute(delete(BackupSnapshotRow))
    await migrated_session.commit()
    evaluator, service = await _make_evaluator(migrated_session)
    rule = await _create_rule(service, "backup.age_hours", threshold=0.0)
    outcome = await evaluator.evaluate_organization(ORG_ID)
    await migrated_session.commit()
    assert outcome.events_fired >= 1
    events, _ = await AlertEventRepository(migrated_session).list_for_org(
        ORG_ID, rule_id=rule.id, limit=10
    )
    assert any(e.status.value == "firing" for e in events)


@pytest.mark.asyncio
async def test_evaluator_suppresses_duplicate_firing_in_cooldown(migrated_session):
    await migrated_session.execute(delete(BackupSnapshotRow))
    await migrated_session.commit()
    evaluator, service = await _make_evaluator(migrated_session)
    rule = await _create_rule(
        service, "backup.age_hours", threshold=0.0, cooldown=600
    )
    outcome1 = await evaluator.evaluate_organization(ORG_ID)
    await migrated_session.commit()
    outcome2 = await evaluator.evaluate_organization(ORG_ID)
    await migrated_session.commit()
    assert outcome1.events_fired >= 1
    assert outcome2.events_suppressed >= 1
    events, _ = await AlertEventRepository(migrated_session).list_for_org(
        ORG_ID, rule_id=rule.id, limit=10
    )
    firing = [e for e in events if e.status.value == "firing"]
    suppressed = [e for e in events if e.status.value == "suppressed"]
    assert len(firing) == 1
    assert len(suppressed) >= 1


@pytest.mark.asyncio
async def test_evaluator_resolves_open_event_when_signal_clears(migrated_session):
    await _ensure_fresh_heartbeat()
    evaluator, service = await _make_evaluator(migrated_session)
    rule = await _create_rule(service, "backup.age_hours", threshold=10.0)

    # First, signal is healthy — no event expected.
    await migrated_session.execute(delete(BackupSnapshotRow))
    migrated_session.add(
        BackupSnapshotRow(
            backup_id="fresh-1",
            created_at=datetime.utcnow(),
            database_path="/tmp/test.sqlite3",
            database_size_bytes=1024,
            verification_status="recorded",
            source="test",
        )
    )
    await migrated_session.commit()
    outcome = await evaluator.evaluate_organization(ORG_ID)
    await migrated_session.commit()
    assert outcome.events_fired == 0
    assert outcome.events_resolved == 0

    # Stale backup → firing.
    await migrated_session.execute(delete(BackupSnapshotRow))
    migrated_session.add(
        BackupSnapshotRow(
            backup_id="stale-1",
            created_at=datetime.utcnow() - timedelta(hours=72),
            database_path="/tmp/test.sqlite3",
            database_size_bytes=1024,
            verification_status="recorded",
            source="test",
        )
    )
    await migrated_session.commit()
    outcome = await evaluator.evaluate_organization(ORG_ID)
    await migrated_session.commit()
    assert outcome.events_fired >= 1

    # Fresh backup → resolves the open event.
    await migrated_session.execute(delete(BackupSnapshotRow))
    migrated_session.add(
        BackupSnapshotRow(
            backup_id="fresh-2",
            created_at=datetime.utcnow(),
            database_path="/tmp/test.sqlite3",
            database_size_bytes=1024,
            verification_status="recorded",
            source="test",
        )
    )
    await migrated_session.commit()
    outcome = await evaluator.evaluate_organization(ORG_ID)
    await migrated_session.commit()
    assert outcome.events_resolved >= 1
    events, _ = await AlertEventRepository(migrated_session).list_for_org(
        ORG_ID, rule_id=rule.id, limit=10
    )
    assert all(e.status.value in ("resolved", "suppressed") for e in events)


@pytest.mark.asyncio
async def test_evaluator_does_not_fire_when_metric_below_threshold(migrated_session):
    # Set up clean state so the seed rules are quiet.
    await _ensure_fresh_heartbeat()
    await migrated_session.execute(delete(BackupSnapshotRow))
    migrated_session.add(
        BackupSnapshotRow(
            backup_id="fresh-baseline",
            created_at=datetime.utcnow(),
            database_path="/tmp/test.sqlite3",
            database_size_bytes=1024,
            verification_status="recorded",
            source="test",
        )
    )
    await migrated_session.commit()

    evaluator, service = await _make_evaluator(migrated_session)
    rule = await _create_rule(
        service, "worker.heartbeat.age_seconds", threshold=3600.0
    )
    outcome = await evaluator.evaluate_organization(ORG_ID)
    await migrated_session.commit()
    assert outcome.events_fired == 0
    events, _ = await AlertEventRepository(migrated_session).list_for_org(
        ORG_ID, rule_id=rule.id, limit=10
    )
    assert all(e.status.value != "firing" for e in events)
