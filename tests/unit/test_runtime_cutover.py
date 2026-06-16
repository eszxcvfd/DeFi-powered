"""Unit tests for the cutover service (US-040)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService
from livelead.application.runtime.cutover import (
    CutoverError,
    CutoverService,
)
from livelead.domain.runtime.enums import (
    EnvironmentMode,
    LaunchGateSeverity,
    LiveIntegration,
    LiveToggleState,
)
from livelead.domain.runtime.models import LaunchGateCheck, LaunchGateReport
from livelead.runtime.settings import AppSettings


class _StubGate:
    def __init__(self, *, passed: bool, mode: EnvironmentMode = EnvironmentMode.PILOT_LIVE):
        self.passed = passed
        self.mode = mode

    async def __call__(self) -> LaunchGateReport:
        check = LaunchGateCheck(
            name="auth.dev_headers_disabled",
            severity=LaunchGateSeverity.OK if self.passed else LaunchGateSeverity.BLOCKING,
        )
        return LaunchGateReport(
            checks=(check,),
            environment_mode=self.mode,
        )


def _settings(*, pin: str | None = None) -> AppSettings:
    return AppSettings(
        environment_mode="test_like",
        launch_gate_min_backup_count=1,
        pilot_live_admin_pin=pin,
    )


def _service(
    session: AsyncSession,
    *,
    settings: AppSettings,
    audit: AuditService,
    gate: _StubGate,
    mode: EnvironmentMode,
    backup_count: int = 0,
    on_mode_change=None,
) -> CutoverService:
    return CutoverService(
        session,
        audit_service=audit,
        settings=settings,
        current_mode_provider=lambda: mode,
        gate_provider=gate,
        backup_count_provider=lambda: _count_coro(backup_count),
        on_mode_change=on_mode_change,
    )


async def _count_coro(value: int) -> int:
    return value


@pytest.mark.asyncio
async def test_enter_pilot_live_requires_admin_or_owner(session: AsyncSession):
    audit = AuditService(session)
    settings = _settings()
    gate = _StubGate(passed=True)
    service = _service(
        session,
        settings=settings,
        audit=audit,
        gate=gate,
        mode=EnvironmentMode.PILOT_LIVE,
    )
    with pytest.raises(CutoverError):
        await service.enter_pilot_live(
            organization_id=str(uuid4()),
            actor="viewer",
            actor_role="viewer",
            reason="go",
        )


@pytest.mark.asyncio
async def test_enter_pilot_live_requires_reason(session: AsyncSession):
    audit = AuditService(session)
    settings = _settings()
    gate = _StubGate(passed=True)
    service = _service(
        session,
        settings=settings,
        audit=audit,
        gate=gate,
        mode=EnvironmentMode.PILOT_LIVE,
    )
    with pytest.raises(CutoverError):
        await service.enter_pilot_live(
            organization_id=str(uuid4()),
            actor="ops",
            actor_role="owner",
            reason="",
        )


@pytest.mark.asyncio
async def test_enter_pilot_live_rejects_when_gate_fails(session: AsyncSession):
    audit = AuditService(session)
    settings = _settings()
    gate = _StubGate(passed=False)
    service = _service(
        session,
        settings=settings,
        audit=audit,
        gate=gate,
        mode=EnvironmentMode.PILOT_LIVE,
    )
    with pytest.raises(CutoverError):
        await service.enter_pilot_live(
            organization_id=str(uuid4()),
            actor="ops",
            actor_role="owner",
            reason="go",
        )


@pytest.mark.asyncio
async def test_enter_pilot_live_rejects_when_no_backup(session: AsyncSession):
    audit = AuditService(session)
    settings = _settings()
    gate = _StubGate(passed=True)
    service = _service(
        session,
        settings=settings,
        audit=audit,
        gate=gate,
        mode=EnvironmentMode.PILOT_LIVE,
        backup_count=0,
    )
    with pytest.raises(CutoverError):
        await service.enter_pilot_live(
            organization_id=str(uuid4()),
            actor="ops",
            actor_role="owner",
            reason="go",
        )


@pytest.mark.asyncio
async def test_enter_pilot_live_requires_admin_pin_when_configured(
    session: AsyncSession,
):
    audit = AuditService(session)
    settings = _settings(pin="secret-pin")
    gate = _StubGate(passed=True)
    service = _service(
        session,
        settings=settings,
        audit=audit,
        gate=gate,
        mode=EnvironmentMode.PILOT_LIVE,
        backup_count=1,
    )
    with pytest.raises(CutoverError):
        await service.enter_pilot_live(
            organization_id=str(uuid4()),
            actor="ops",
            actor_role="owner",
            reason="go",
            admin_pin="wrong",
        )


@pytest.mark.asyncio
async def test_enter_pilot_live_succeeds_and_emits_event(
    session: AsyncSession,
):
    audit = AuditService(session)
    settings = _settings()
    gate = _StubGate(passed=True)
    mode_holder = {"value": EnvironmentMode.TEST_LIKE}

    def _mode():
        return mode_holder["value"]

    def _on_change(new_mode):
        mode_holder["value"] = new_mode

    service = CutoverService(
        session,
        audit_service=audit,
        settings=settings,
        current_mode_provider=_mode,
        gate_provider=gate,
        backup_count_provider=lambda: _count_coro(1),
        on_mode_change=_on_change,
    )
    result = await service.enter_pilot_live(
        organization_id="00000000-0000-4000-8000-000000000001",
        actor="ops",
        actor_role="owner",
        reason="first go-live",
    )
    await session.commit()
    assert result.new_mode == EnvironmentMode.PILOT_LIVE
    assert mode_holder["value"] == EnvironmentMode.PILOT_LIVE
    events = await service.list_events(limit=5)
    assert any(e.action.value == "enter_pilot_live" for e in events)


@pytest.mark.asyncio
async def test_pause_disables_live_toggles(session: AsyncSession):
    audit = AuditService(session)
    settings = _settings()
    gate = _StubGate(passed=True)
    org_id = "00000000-0000-4000-8000-000000000001"
    # Pre-enable a toggle so we can confirm pause disables it.
    from livelead.infrastructure.db.repositories.runtime import (
        LiveIntegrationToggleRepository,
    )

    repo = LiveIntegrationToggleRepository(session)
    await repo.upsert(
        org_id, LiveIntegration.DISCOVERY, new_state=LiveToggleState.ENABLED, actor="seed"
    )
    await session.commit()
    service = _service(
        session,
        settings=settings,
        audit=audit,
        gate=gate,
        mode=EnvironmentMode.PILOT_LIVE,
    )
    result = await service.pause(
        organization_id=org_id,
        actor="ops",
        actor_role="owner",
        reason="incident",
    )
    await session.commit()
    assert result.new_mode == EnvironmentMode.PAUSED
    toggle = await repo.get(org_id, LiveIntegration.DISCOVERY)
    assert toggle is not None
    assert toggle.state == LiveToggleState.DISABLED


@pytest.mark.asyncio
async def test_rollback_disables_toggles_and_returns_to_test_like(
    session: AsyncSession,
):
    audit = AuditService(session)
    settings = _settings()
    gate = _StubGate(passed=True)
    org_id = "00000000-0000-4000-8000-000000000001"
    from livelead.infrastructure.db.repositories.runtime import (
        LiveIntegrationToggleRepository,
    )

    repo = LiveIntegrationToggleRepository(session)
    await repo.upsert(
        org_id, LiveIntegration.AI_COPILOT, new_state=LiveToggleState.ENABLED, actor="seed"
    )
    await session.commit()
    service = _service(
        session,
        settings=settings,
        audit=audit,
        gate=gate,
        mode=EnvironmentMode.PILOT_LIVE,
    )
    result = await service.rollback(
        organization_id=org_id,
        actor="ops",
        actor_role="owner",
        reason="drill",
        target_mode=EnvironmentMode.PAUSED,
    )
    await session.commit()
    assert result.new_mode == EnvironmentMode.PAUSED
    toggle = await repo.get(org_id, LiveIntegration.AI_COPILOT)
    assert toggle is not None
    assert toggle.state == LiveToggleState.DISABLED
