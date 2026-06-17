"""Unit tests for the connector auto-disable service (US-048).

The service is the only place that mutates
`connector_auto_disable_rules` and
`connector_auto_disable_events` and emits the
`connector.auto_disable.*` audit entries. The
tests prove the bounded trigger evaluation,
the bounded `cooldown_seconds` window, the
bounded `consecutive_breaches` counter, the
source-side `evaluate_source_for_discovery`
helper, the human-confirmed recovery flow,
and the audit capture all work end-to-end
against the in-memory SQLite test fixture.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.auto_disable import (
    AutoDisableError,
    AutoDisableEventNotFound,
    AutoDisableInvalidWindow,
    AutoDisableRecoveryRejected,
    AutoDisableRuleNotFound,
    AutoDisableService,
    AutoDisableSourceNotFound,
)
from livelead.domain.auto_disable.enums import (
    AutoDisableEventStatus,
    AutoDisableTrigger,
)
from livelead.domain.auto_disable.models import (
    AutoDisableThresholds,
)
from livelead.domain.connector_health.enums import (
    ConnectorHealthStatus,
)
from livelead.domain.observability.enums import (
    AlertEventStatus,
    AlertMetric,
    AlertSeverity,
)
from livelead.domain.runtime.enums import EnvironmentMode
from livelead.infrastructure.db.models import (
    AlertEventRow,
    AuditEntryRow,
    ConnectorAutoDisableEventRow,
    ConnectorAutoDisableRuleRow,
    ConnectorHealthSnapshotRow,
    SourceRow,
)

ORG_ID = "00000000-0000-4000-8000-000000000001"
USER_ID = "00000000-0000-4000-8000-000000000002"


def _build_service(
    session: AsyncSession,
    *,
    environment_mode: EnvironmentMode | str = EnvironmentMode.PILOT_LIVE,
) -> AutoDisableService:
    return AutoDisableService(
        session,
        environment_mode=environment_mode,
        thresholds=AutoDisableThresholds(),
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


async def _seed_snapshot(
    session: AsyncSession,
    *,
    source_id: str,
    status: ConnectorHealthStatus,
    success_rate: float = 1.0,
    captcha_rate: float = 0.0,
    computed_at: datetime | None = None,
) -> str:
    if computed_at is None:
        computed_at = datetime.now(UTC).replace(tzinfo=None)
    snapshot_id = str(uuid4())
    session.add(
        ConnectorHealthSnapshotRow(
            id=snapshot_id,
            organization_id=ORG_ID,
            source_id=source_id,
            connector_type="rss",
            window_start=computed_at - timedelta(hours=1),
            window_end=computed_at,
            total_runs=10,
            success_count=10,
            failure_count=0,
            success_rate=success_rate,
            p50_latency_ms=100.0,
            p95_latency_ms=200.0,
            captcha_count=0,
            captcha_rate=captcha_rate,
            last_run_at=computed_at,
            last_error_code=None,
            last_error_message=None,
            status=status.value,
            audit_correlation_id="",
            computed_at=computed_at,
            created_at=computed_at,
            updated_at=computed_at,
        )
    )
    await session.flush()
    return snapshot_id


async def _seed_alert(
    session: AsyncSession,
    *,
    source_id: str,
    metric: AlertMetric,
    severity: AlertSeverity,
    fired_at: datetime,
    status: AlertEventStatus = AlertEventStatus.FIRING,
) -> None:
    dedup_key = f"k_{uuid4()}"
    session.add(
        AlertEventRow(
            id=str(uuid4()),
            organization_id=ORG_ID,
            rule_id=str(uuid4()),
            rule_name="seed",
            metric=metric.value,
            severity=severity.value,
            payload_json=json.dumps(
                {"source_id": source_id, "value": 1.0}
            ),
            dedup_key=dedup_key,
            correlation_id="",
            status=status.value,
            fired_at=fired_at,
        )
    )
    await session.flush()


# ----------------------------------------------------------------------
# Rule CRUD
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_rule_persists_row_and_audit(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    service = _build_service(session)
    rule = await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
        consecutive_breaches=3,
        actor=USER_ID,
        actor_role="owner",
    )
    assert rule.id
    assert rule.source_id == source_id
    rows = (
        await session.execute(
            select(ConnectorAutoDisableRuleRow).where(
                ConnectorAutoDisableRuleRow.id == rule.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    audit = (
        await session.execute(
            select(AuditEntryRow).where(
                AuditEntryRow.action
                == "connector.auto_disable.rule.created"
            )
        )
    ).scalars().all()
    assert len(audit) == 1
    assert audit[0].target_id == rule.id


@pytest.mark.asyncio
async def test_create_rule_rejects_unknown_source(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    with pytest.raises(AutoDisableSourceNotFound):
        await service.create_rule(
            organization_id=ORG_ID,
            source_id=str(uuid4()),
            trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
            threshold_value=0.0,
        )


@pytest.mark.asyncio
async def test_create_rule_rejects_invalid_trigger(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    service = _build_service(session)
    with pytest.raises(AutoDisableError):
        await service.create_rule(
            organization_id=ORG_ID,
            source_id=source_id,
            trigger="not-a-real-trigger",
            threshold_value=0.0,
        )


@pytest.mark.asyncio
async def test_create_rule_clamps_window_to_mode_bound(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    service = _build_service(
        session, environment_mode=EnvironmentMode.TEST_LIKE
    )
    rule = await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
        window_seconds=24 * 3600,
    )
    # Bounded path clips to `test_like` max (1h).
    assert rule.window_seconds <= 3600


@pytest.mark.asyncio
async def test_update_rule_emits_audit_with_diff(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    service = _build_service(session)
    rule = await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
        consecutive_breaches=3,
    )
    updated = await service.update_rule(
        organization_id=ORG_ID,
        rule_id=rule.id,
        threshold_value=0.5,
        consecutive_breaches=5,
    )
    assert updated.threshold_value == pytest.approx(0.5)
    assert updated.consecutive_breaches == 5
    audit = (
        await session.execute(
            select(AuditEntryRow).where(
                AuditEntryRow.action
                == "connector.auto_disable.rule.updated"
            )
        )
    ).scalars().all()
    assert len(audit) == 1


@pytest.mark.asyncio
async def test_update_rule_rejects_unknown_rule(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    with pytest.raises(AutoDisableRuleNotFound):
        await service.update_rule(
            organization_id=ORG_ID,
            rule_id=str(uuid4()),
            threshold_value=0.0,
        )


@pytest.mark.asyncio
async def test_delete_rule_soft_deletes(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    service = _build_service(session)
    rule = await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
    )
    await service.delete_rule(
        organization_id=ORG_ID, rule_id=rule.id
    )
    # The rule is soft-deleted; list_for_org
    # excludes deleted rows.
    rules, _ = await service.list_rules(ORG_ID)
    assert all(r.id != rule.id for r in rules)


# ----------------------------------------------------------------------
# Evaluation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_source_fires_and_flips_enabled(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(3):
        await _seed_snapshot(
            session,
            source_id=source_id,
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=3 - i),
        )
    service = _build_service(session)
    rule = await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
        consecutive_breaches=3,
        window_seconds=1800,
    )
    result = await service.evaluate_source(
        organization_id=ORG_ID, source_id=source_id
    )
    assert result.should_disable is True
    assert result.trigger is AutoDisableTrigger.HEALTH_UNHEALTHY
    events = (
        await session.execute(
            select(ConnectorAutoDisableEventRow)
        )
    ).scalars().all()
    assert len(events) == 1
    assert events[0].status == AutoDisableEventStatus.ACTIVE.value
    source = (
        await session.execute(
            select(SourceRow).where(SourceRow.id == source_id)
        )
    ).scalar_one()
    assert source.enabled is False
    assert source.auto_disabled_by_event_id == events[0].id
    # Audit entry was written.
    audit = (
        await session.execute(
            select(AuditEntryRow).where(
                AuditEntryRow.action
                == "connector.auto_disable.triggered"
            )
        )
    ).scalars().all()
    assert len(audit) == 1


@pytest.mark.asyncio
async def test_evaluate_source_does_not_fire_below_threshold(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    await _seed_snapshot(
        session,
        source_id=source_id,
        status=ConnectorHealthStatus.HEALTHY,
        computed_at=now - timedelta(minutes=1),
    )
    service = _build_service(session)
    await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
        consecutive_breaches=3,
    )
    result = await service.evaluate_source(
        organization_id=ORG_ID, source_id=source_id
    )
    assert result.should_disable is False


@pytest.mark.asyncio
async def test_evaluate_source_respects_cooldown(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(3):
        await _seed_snapshot(
            session,
            source_id=source_id,
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=3 - i),
        )
    service = _build_service(session)
    rule = await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
        consecutive_breaches=3,
        cooldown_seconds=900,
    )
    # First evaluation fires.
    first = await service.evaluate_source(
        organization_id=ORG_ID, source_id=source_id
    )
    assert first.should_disable is True
    # Second evaluation is in cooldown.
    second = await service.evaluate_source(
        organization_id=ORG_ID, source_id=source_id
    )
    assert second.should_disable is False


@pytest.mark.asyncio
async def test_evaluate_source_fires_error_spike(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(3):
        await _seed_alert(
            session,
            source_id=source_id,
            metric=AlertMetric.CONNECTOR_FAILURE_RATE,
            severity=AlertSeverity.CRITICAL,
            fired_at=now - timedelta(minutes=3 - i),
        )
    service = _build_service(session)
    await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.ERROR_SPIKE,
        threshold_value=3.0,
        consecutive_breaches=3,
        window_seconds=1800,
    )
    result = await service.evaluate_source(
        organization_id=ORG_ID, source_id=source_id
    )
    assert result.should_disable is True
    assert result.trigger is AutoDisableTrigger.ERROR_SPIKE


@pytest.mark.asyncio
async def test_evaluate_source_fires_needs_user_action_storm(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(3):
        await _seed_alert(
            session,
            source_id=source_id,
            metric=AlertMetric.DISCOVERY_NEEDS_USER_ACTION_RATE,
            severity=AlertSeverity.WARNING,
            fired_at=now - timedelta(minutes=3 - i),
        )
    service = _build_service(session)
    await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.NEEDS_USER_ACTION_STORM,
        threshold_value=3.0,
        consecutive_breaches=3,
        window_seconds=1800,
    )
    result = await service.evaluate_source(
        organization_id=ORG_ID, source_id=source_id
    )
    assert result.should_disable is True
    assert result.trigger is AutoDisableTrigger.NEEDS_USER_ACTION_STORM


@pytest.mark.asyncio
async def test_evaluate_source_rejects_unknown_source(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    with pytest.raises(AutoDisableSourceNotFound):
        await service.evaluate_source(
            organization_id=ORG_ID, source_id=str(uuid4())
        )


# ----------------------------------------------------------------------
# Discovery helper
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_source_for_discovery_returns_allowed(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    service = _build_service(session)
    decision = await service.evaluate_source_for_discovery(
        organization_id=ORG_ID, source_id=source_id
    )
    assert decision.run_state == "RUN_ALLOWED"
    assert decision.is_allowed is True


@pytest.mark.asyncio
async def test_evaluate_source_for_discovery_returns_manual_disabled(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session, domain="manual.example.com")
    service = _build_service(session)
    # Disable manually.
    source = (
        await session.execute(
            select(SourceRow).where(SourceRow.id == source_id)
        )
    ).scalar_one()
    source.enabled = False
    await session.flush()
    decision = await service.evaluate_source_for_discovery(
        organization_id=ORG_ID, source_id=source_id
    )
    assert decision.run_state == "RUN_MANUAL_DISABLED"


@pytest.mark.asyncio
async def test_evaluate_source_for_discovery_returns_auto_disabled(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(3):
        await _seed_snapshot(
            session,
            source_id=source_id,
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=3 - i),
        )
    service = _build_service(session)
    await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
        consecutive_breaches=3,
    )
    await service.evaluate_source(
        organization_id=ORG_ID, source_id=source_id
    )
    # Re-enable manually to confirm the
    # auto-disable path still wins.
    source = (
        await session.execute(
            select(SourceRow).where(SourceRow.id == source_id)
        )
    ).scalar_one()
    source.enabled = True
    await session.flush()
    decision = await service.evaluate_source_for_discovery(
        organization_id=ORG_ID, source_id=source_id
    )
    assert decision.run_state == "RUN_AUTO_DISABLED"


# ----------------------------------------------------------------------
# Recovery
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recover_source_transitions_event_to_recovering(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(3):
        await _seed_snapshot(
            session,
            source_id=source_id,
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=3 - i),
        )
    service = _build_service(session)
    await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
        consecutive_breaches=3,
    )
    await service.evaluate_source(
        organization_id=ORG_ID, source_id=source_id
    )
    events, _ = await service.list_events(ORG_ID, source_id=source_id)
    assert len(events) == 1
    event_id = events[0].id
    recovered = await service.recover_source(
        organization_id=ORG_ID,
        event_id=event_id,
        reason="Operator confirmed the source is healthy.",
        actor=USER_ID,
        actor_role="owner",
    )
    assert recovered.status is AutoDisableEventStatus.RECOVERING
    audit = (
        await session.execute(
            select(AuditEntryRow).where(
                AuditEntryRow.action == "connector.auto_disable.recovered"
            )
        )
    ).scalars().all()
    assert len(audit) == 1


@pytest.mark.asyncio
async def test_recover_source_rejects_non_active_event(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(3):
        await _seed_snapshot(
            session,
            source_id=source_id,
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=3 - i),
        )
    service = _build_service(session)
    await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
        consecutive_breaches=3,
    )
    await service.evaluate_source(
        organization_id=ORG_ID, source_id=source_id
    )
    events, _ = await service.list_events(ORG_ID, source_id=source_id)
    event_id = events[0].id
    # First recovery transitions to `recovering`.
    await service.recover_source(
        organization_id=ORG_ID,
        event_id=event_id,
        reason="Operator confirmed.",
    )
    # Second recovery is rejected because the
    # event is no longer `active`.
    with pytest.raises(AutoDisableRecoveryRejected):
        await service.recover_source(
            organization_id=ORG_ID,
            event_id=event_id,
            reason="Operator confirmed.",
        )


@pytest.mark.asyncio
async def test_recover_source_rejects_empty_reason(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(3):
        await _seed_snapshot(
            session,
            source_id=source_id,
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=3 - i),
        )
    service = _build_service(session)
    await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
        consecutive_breaches=3,
    )
    await service.evaluate_source(
        organization_id=ORG_ID, source_id=source_id
    )
    events, _ = await service.list_events(ORG_ID, source_id=source_id)
    with pytest.raises(AutoDisableError):
        await service.recover_source(
            organization_id=ORG_ID,
            event_id=events[0].id,
            reason="   ",
        )


@pytest.mark.asyncio
async def test_recover_source_rejects_unknown_event(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    with pytest.raises(AutoDisableEventNotFound):
        await service.recover_source(
            organization_id=ORG_ID,
            event_id=str(uuid4()),
            reason="ok",
        )


@pytest.mark.asyncio
async def test_finalize_recovery_resolves_event_and_clears_source(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(3):
        await _seed_snapshot(
            session,
            source_id=source_id,
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=3 - i),
        )
    service = _build_service(session)
    await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
        consecutive_breaches=3,
    )
    await service.evaluate_source(
        organization_id=ORG_ID, source_id=source_id
    )
    events, _ = await service.list_events(ORG_ID, source_id=source_id)
    await service.recover_source(
        organization_id=ORG_ID,
        event_id=events[0].id,
        reason="Operator confirmed.",
    )
    final = await service.finalize_recovery(
        organization_id=ORG_ID,
        event_id=events[0].id,
        source_healthy=True,
    )
    assert final.status is AutoDisableEventStatus.RESOLVED
    source = (
        await session.execute(
            select(SourceRow).where(SourceRow.id == source_id)
        )
    ).scalar_one()
    assert source.enabled is True
    assert source.auto_disabled_at is None
    assert source.auto_disabled_reason is None
    assert source.auto_disabled_by_event_id is None


@pytest.mark.asyncio
async def test_finalize_recovery_rejects_unhealthy(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(3):
        await _seed_snapshot(
            session,
            source_id=source_id,
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=3 - i),
        )
    service = _build_service(session)
    await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
        consecutive_breaches=3,
    )
    await service.evaluate_source(
        organization_id=ORG_ID, source_id=source_id
    )
    events, _ = await service.list_events(ORG_ID, source_id=source_id)
    await service.recover_source(
        organization_id=ORG_ID,
        event_id=events[0].id,
        reason="Operator confirmed.",
    )
    final = await service.finalize_recovery(
        organization_id=ORG_ID,
        event_id=events[0].id,
        source_healthy=False,
    )
    assert final.status is AutoDisableEventStatus.ACTIVE


# ----------------------------------------------------------------------
# Sanitization
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_audit_strips_secrets(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    service = _build_service(session)
    rule = await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
    )
    # Trigger an evaluation that emits a rule
    # audit entry; the metadata must be clean.
    audit = (
        await session.execute(
            select(AuditEntryRow).where(
                AuditEntryRow.target_id == rule.id
            )
        )
    ).scalars().all()
    assert len(audit) == 1
    metadata = json.loads(audit[0].metadata_json or "{}")
    # The bounded `SanitizeAlertPayload` helper
    # must not leak API keys, cookies, or PII.
    raw = json.dumps(metadata)
    for forbidden in ("api_key", "apikey", "password", "secret"):
        assert forbidden not in raw.lower()


# ----------------------------------------------------------------------
# Window bound
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_rule_clamps_window_to_test_like_bound(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    service = _build_service(
        session, environment_mode=EnvironmentMode.TEST_LIKE
    )
    rule = await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
        window_seconds=48 * 3600,
    )
    assert rule.window_seconds <= 3600


@pytest.mark.asyncio
async def test_update_rule_clamps_window_to_mode_bound(
    session: AsyncSession,
) -> None:
    source_id = await _seed_source(session)
    service = _build_service(
        session, environment_mode=EnvironmentMode.TEST_LIKE
    )
    rule = await service.create_rule(
        organization_id=ORG_ID,
        source_id=source_id,
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        threshold_value=0.0,
    )
    # Bounded path clips the window to the
    # `test_like` max (1h).
    updated = await service.update_rule(
        organization_id=ORG_ID,
        rule_id=rule.id,
        window_seconds=48 * 3600,
    )
    assert updated.window_seconds <= 3600
