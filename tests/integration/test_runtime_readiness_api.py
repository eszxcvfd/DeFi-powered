"""Integration tests for runtime read/ready/health and live-toggle admin
endpoints (US-040).

The tests rely on the existing `client` fixture in `tests/conftest.py`
which builds a FastAPI app with an in-process lifespan, allowing the
routes to execute end-to-end.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from livelead.domain.runtime.enums import (
    BackupVerificationStatus,
    EnvironmentMode,
    LiveIntegration,
    LiveToggleState,
)
from livelead.infrastructure.db.models import (
    BackupSnapshotRow,
    LiveIntegrationToggleRow,
    WorkerHeartbeatRow,
)
from livelead.infrastructure.observability.worker_heartbeat import (
    record_heartbeat_async,
)


def _owner_headers() -> dict[str, str]:
    """Return headers that resolve the request to an owner in the dev
    fallback path used by tests.
    """

    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "owner",
    }


@pytest.mark.asyncio
async def test_health_live_returns_ok(client):
    r = await client.get("/health/live")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "livelead-api"


@pytest.mark.asyncio
async def test_health_ready_returns_test_like_profile(client):
    r = await client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["environment_mode"] in ("test_like", "pilot_live", "paused")
    assert "blocking" in body
    assert "warnings" in body


@pytest.mark.asyncio
async def test_health_ready_includes_blockers_when_redis_unreachable(
    client, monkeypatch
):
    from livelead.application.runtime import readiness as readiness_module
    from datetime import UTC, datetime

    # Patch the readiness module's `ping_redis` reference directly.
    monkeypatch.setattr(
        readiness_module, "ping_redis", lambda settings: False
    )

    # Also patch the sqlite probe so we can isolate the redis check.
    monkeypatch.setattr(
        readiness_module.RuntimeReadinessService,
        "_probe_sqlite",
        lambda self: True,
    )

    r = await client.get("/health/ready")
    body = r.json()
    names = {c["name"] for c in body["blocking"]} | {c["name"] for c in body["warnings"]}
    assert "queue.redis_reachable" in names


@pytest.mark.asyncio
async def test_admin_runtime_readiness_requires_owner(client):
    r = await client.get(
        "/admin/runtime-readiness",
        headers={
            "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
            "X-Actor-Role": "viewer",
        },
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_runtime_readiness_returns_profile(client):
    r = await client.get("/admin/runtime-readiness", headers=_owner_headers())
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] in ("test_like", "pilot_live", "paused")
    assert "gate" in body
    assert "toggles" in body
    assert "backup_freshness" in body
    assert "auth_allow_dev_headers" in body


@pytest.mark.asyncio
async def test_admin_live_toggles_list_and_enable_block_in_test_like(client):
    # In test_like mode, enable must be rejected.
    r = await client.get("/admin/live-toggles", headers=_owner_headers())
    assert r.status_code == 200
    assert r.json()["toggles"] == []
    r = await client.post(
        "/admin/live-toggles/discovery:enable",
        json={"approval_note": "ready"},
        headers=_owner_headers(),
    )
    assert r.status_code == 409
    assert "pilot_live" in r.json()["detail"]


@pytest.mark.asyncio
async def test_admin_backup_record_and_list(client):
    r = await client.post(
        "/admin/backup-snapshots:record",
        json={"backup_id": "ops-001", "database_path": "data/livelead.sqlite3"},
        headers=_owner_headers(),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["backup_id"] == "ops-001"
    assert body["verification_status"] == "recorded"

    r = await client.get(
        "/admin/backup-snapshots",
        headers=_owner_headers(),
    )
    assert r.status_code == 200
    listing = r.json()
    assert any(s["backup_id"] == "ops-001" for s in listing["snapshots"])


@pytest.mark.asyncio
async def test_admin_backup_verify_transitions_to_verified(client):
    r = await client.post(
        "/admin/backup-snapshots:record",
        json={"backup_id": "ops-002", "database_path": "data/livelead.sqlite3"},
        headers=_owner_headers(),
    )
    assert r.status_code == 201
    r = await client.post(
        "/admin/backup-snapshots/ops-002:verify",
        json={"status": "verified_restore"},
        headers=_owner_headers(),
    )
    assert r.status_code == 200
    assert r.json()["verification_status"] == "verified_restore"


@pytest.mark.asyncio
async def test_admin_cutover_pause_and_rollback(client):
    # Start in paused so we don't depend on the default test_like.
    r = await client.post(
        "/admin/cutover/pause",
        json={"reason": "incident drill"},
        headers=_owner_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["new_mode"] == "paused"

    r = await client.post(
        "/admin/cutover/rollback",
        json={"reason": "drill done", "target_mode": "test_like"},
        headers=_owner_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["new_mode"] == "test_like"


@pytest.mark.asyncio
async def test_admin_cutover_enter_pilot_live_requires_backup_and_gate(client):
    r = await client.post(
        "/admin/cutover/enter-pilot-live",
        json={"reason": "go live"},
        headers=_owner_headers(),
    )
    assert r.status_code == 409
    # Either backup count or gate failure is acceptable; the message
    # always includes the blocking rationale.
    assert "blocked" in r.json()["detail"] or "required" in r.json()["detail"]


@pytest.mark.asyncio
async def test_admin_cutover_events_listing(client):
    r = await client.post(
        "/admin/cutover/pause",
        json={"reason": "test"},
        headers=_owner_headers(),
    )
    assert r.status_code == 200
    r = await client.get(
        "/admin/cutover/events",
        headers=_owner_headers(),
    )
    assert r.status_code == 200
    events = r.json()["events"]
    assert any(e["action"] == "pause" for e in events)


@pytest.mark.asyncio
async def test_live_toggle_enable_succeeds_in_pilot_live_with_seed(
    client, monkeypatch
):
    """End-to-end: switch to pilot_live, record a backup and heartbeat,
    then enable a live toggle. The launch gate is monkeypatched to
    pass so the test does not have to disable dev headers.
    """

    from livelead.application.runtime.registry import RuntimeRegistry
    from livelead.domain.runtime.enums import LaunchGateSeverity
    from livelead.domain.runtime.models import LaunchGateCheck, LaunchGateReport

    # 1. Switch to pilot_live
    registry: RuntimeRegistry = client.app.state.runtime_registry
    registry.set_mode(EnvironmentMode.PILOT_LIVE)

    # 2. Record a backup snapshot
    r = await client.post(
        "/admin/backup-snapshots:record",
        json={"backup_id": "ops-pilot", "database_path": "data/livelead.sqlite3"},
        headers=_owner_headers(),
    )
    assert r.status_code == 201

    # 3. Record a worker heartbeat via the helper
    session_factory = client.app.state.session_factory
    await record_heartbeat_async(session_factory, last_task="seed")
    await record_heartbeat_async(session_factory, last_task="seed")

    # 4. Monkeypatch the gate provider used by the live-toggle service
    #    to a synchronous pass-through so the test does not require
    #    disabling dev headers.
    async def _passing_gate(*_args, **_kwargs):
        from datetime import UTC, datetime
        return LaunchGateReport(
            checks=(LaunchGateCheck(name="seed", severity=LaunchGateSeverity.OK),),
            environment_mode=EnvironmentMode.PILOT_LIVE,
            evaluated_at=datetime.now(UTC),
        )

    from livelead.interfaces.rest import live_toggles as live_toggles_module
    monkeypatch.setattr(live_toggles_module, "_build_gate", _passing_gate)

    # 5. Enable a live toggle
    r = await client.post(
        "/admin/live-toggles/discovery:enable",
        json={"approval_note": "first pilot go-live"},
        headers=_owner_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["state"] == "enabled"

    # 6. Disable it
    r = await client.post(
        "/admin/live-toggles/discovery:disable",
        json={"reason": "drill complete"},
        headers=_owner_headers(),
    )
    assert r.status_code == 200
    assert r.json()["state"] == "disabled"


@pytest.mark.asyncio
async def test_pilot_live_readiness_passes_with_full_setup(client, monkeypatch):
    """When the operator pre-seeds backups, heartbeats, and the gate
    is monkeypatched to pass, the live toggle enable succeeds.
    """

    from livelead.application.runtime.registry import RuntimeRegistry
    from livelead.domain.runtime.enums import LaunchGateSeverity
    from livelead.domain.runtime.models import LaunchGateCheck, LaunchGateReport

    registry = client.app.state.runtime_registry
    registry.set_mode(EnvironmentMode.PILOT_LIVE)

    # Record a backup and heartbeat
    r = await client.post(
        "/admin/backup-snapshots:record",
        json={"backup_id": "ops-ready", "database_path": "data/livelead.sqlite3"},
        headers=_owner_headers(),
    )
    assert r.status_code == 201
    session_factory = client.app.state.session_factory
    await record_heartbeat_async(session_factory, last_task="seed")

    # Patch the gate used by both the live-toggle service and the
    # cutover service to a passing report.
    async def _passing_gate(*_args, **_kwargs):
        from datetime import UTC, datetime
        return LaunchGateReport(
            checks=(LaunchGateCheck(name="seed", severity=LaunchGateSeverity.OK),),
            environment_mode=EnvironmentMode.PILOT_LIVE,
            evaluated_at=datetime.now(UTC),
        )

    from livelead.interfaces.rest import live_toggles as live_toggles_module
    from livelead.interfaces.rest import cutover as cutover_module
    monkeypatch.setattr(live_toggles_module, "_build_gate", _passing_gate)
    monkeypatch.setattr(cutover_module, "_build_gate", _passing_gate)

    r = await client.post(
        "/admin/live-toggles/notifications:enable",
        json={"approval_note": "pilot ready"},
        headers=_owner_headers(),
    )
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "enabled"
