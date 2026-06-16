"""Unit tests for the live-toggle service (US-040).

These tests cover the validation and state machine in isolation,
using the real repository and audit service against an in-memory
SQLite database (the test app's session).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import AuditService
from livelead.application.runtime.live_toggles import (
    LiveToggleService,
    LiveToggleValidationError,
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
        self.calls = 0

    async def __call__(self) -> LaunchGateReport:
        self.calls += 1
        check = LaunchGateCheck(
            name="auth.dev_headers_disabled",
            severity=LaunchGateSeverity.OK if self.passed else LaunchGateSeverity.BLOCKING,
        )
        return LaunchGateReport(
            checks=(check,),
            environment_mode=self.mode,
        )


def _settings() -> AppSettings:
    return AppSettings(environment_mode="test_like", launch_gate_backup_max_age_hours=24)


def _service(
    session: AsyncSession,
    *,
    settings: AppSettings,
    audit: AuditService,
    gate: _StubGate,
    mode: EnvironmentMode,
) -> LiveToggleService:
    return LiveToggleService(
        session,
        audit_service=audit,
        settings=settings,
        environment_mode=mode,
        gate_provider=gate,
    )


@pytest.mark.asyncio
async def test_enable_requires_approval_note(session: AsyncSession):
    audit = AuditService(session)
    settings = _settings()
    gate = _StubGate(passed=True)
    service = _service(session, settings=settings, audit=audit, gate=gate, mode=EnvironmentMode.PILOT_LIVE)
    with pytest.raises(LiveToggleValidationError):
        await service.enable(
            organization_id=str(uuid4()),
            integration=LiveIntegration.DISCOVERY,
            actor="ops",
            actor_role="admin",
            approval_note="",
        )


@pytest.mark.asyncio
async def test_enable_requires_admin_or_owner(session: AsyncSession):
    audit = AuditService(session)
    settings = _settings()
    gate = _StubGate(passed=True)
    service = _service(session, settings=settings, audit=audit, gate=gate, mode=EnvironmentMode.PILOT_LIVE)
    with pytest.raises(LiveToggleValidationError):
        await service.enable(
            organization_id=str(uuid4()),
            integration=LiveIntegration.DISCOVERY,
            actor="viewer",
            actor_role="viewer",
            approval_note="approved",
        )


@pytest.mark.asyncio
async def test_enable_rejects_when_mode_is_not_pilot_live(session: AsyncSession):
    audit = AuditService(session)
    settings = _settings()
    gate = _StubGate(passed=True)
    service = _service(
        session,
        settings=settings,
        audit=audit,
        gate=gate,
        mode=EnvironmentMode.TEST_LIKE,
    )
    with pytest.raises(LiveToggleValidationError):
        await service.enable(
            organization_id=str(uuid4()),
            integration=LiveIntegration.AI_COPILOT,
            actor="ops",
            actor_role="owner",
            approval_note="ready",
        )


@pytest.mark.asyncio
async def test_enable_rejects_when_gate_fails(session: AsyncSession):
    audit = AuditService(session)
    settings = _settings()
    gate = _StubGate(passed=False)
    service = _service(session, settings=settings, audit=audit, gate=gate, mode=EnvironmentMode.PILOT_LIVE)
    with pytest.raises(LiveToggleValidationError):
        await service.enable(
            organization_id=str(uuid4()),
            integration=LiveIntegration.DISCOVERY,
            actor="ops",
            actor_role="admin",
            approval_note="go",
        )


@pytest.mark.asyncio
async def test_enable_persists_toggle_and_audits_when_accepted(session: AsyncSession):
    audit = AuditService(session)
    settings = _settings()
    gate = _StubGate(passed=True)
    service = _service(session, settings=settings, audit=audit, gate=gate, mode=EnvironmentMode.PILOT_LIVE)
    org_id = str(uuid4())
    result = await service.enable(
        organization_id=org_id,
        integration=LiveIntegration.NOTIFICATIONS,
        actor="ops@example.com",
        actor_role="owner",
        approval_note="incident drill",
    )
    await session.commit()
    assert result.accepted
    assert result.toggle.state == LiveToggleState.ENABLED
    toggle = await service.get_toggle(org_id, LiveIntegration.NOTIFICATIONS)
    assert toggle.state == LiveToggleState.ENABLED
    entries, _ = await audit.list_entries(org_id, action="environment.toggle.changed", limit=10)
    assert entries and entries[0].action.value == "environment.toggle.changed"


@pytest.mark.asyncio
async def test_disable_records_state_and_audit(session: AsyncSession):
    audit = AuditService(session)
    settings = _settings()
    gate = _StubGate(passed=True)
    service = _service(session, settings=settings, audit=audit, gate=gate, mode=EnvironmentMode.PILOT_LIVE)
    org_id = str(uuid4())
    await service.enable(
        organization_id=org_id,
        integration=LiveIntegration.DISCOVERY,
        actor="ops",
        actor_role="admin",
        approval_note="on",
    )
    await session.commit()
    result = await service.disable(
        organization_id=org_id,
        integration=LiveIntegration.DISCOVERY,
        actor="ops",
        actor_role="admin",
        reason="incident",
    )
    await session.commit()
    assert result.toggle.state == LiveToggleState.DISABLED
    assert result.toggle.previous_state == LiveToggleState.ENABLED
