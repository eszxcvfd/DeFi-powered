"""Integration tests for the observability admin API (US-041)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from livelead.domain.observability.enums import (
    AlertChannel,
    AlertMetric,
    AlertOperator,
    AlertSeverity,
)
from livelead.infrastructure.db.models import (
    AlertEventRow,
    AlertRuleRow,
    BackupSnapshotRow,
    DiscoveryJobRow,
    WorkerHeartbeatRow,
)
from livelead.infrastructure.db.repositories.runtime import (
    BackupSnapshotRepository,
)
from livelead.infrastructure.observability.worker_heartbeat import (
    record_heartbeat_async,
)


def _owner_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "owner",
    }


def _admin_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "admin",
    }


def _viewer_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "viewer",
    }


def _analyst_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
        "X-Actor-Role": "analyst",
    }


@pytest.mark.asyncio
async def test_summary_returns_owner_view(migrated_client):
    r = await migrated_client.get("/admin/observability/summary", headers=_owner_headers())
    assert r.status_code == 200
    body = r.json()
    assert "environment_mode" in body
    assert "gate_passed" in body
    assert "open_alerts_by_severity" in body
    assert "recent_alerts" in body
    assert "rules_total" in body
    assert "rules_enabled" in body
    # The seed rules are inserted by the migration; expect at least 6
    assert body["rules_total"] >= 6
    assert body["rules_enabled"] >= 6


@pytest.mark.asyncio
async def test_summary_forbidden_for_viewer(migrated_client):
    r = await migrated_client.get("/admin/observability/summary", headers=_viewer_headers())
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_summary_forbidden_for_analyst(migrated_client):
    r = await migrated_client.get("/admin/observability/summary", headers=_analyst_headers())
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_alert_rules_returns_seed_set(migrated_client):
    r = await migrated_client.get("/admin/observability/alert-rules", headers=_owner_headers())
    assert r.status_code == 200
    body = r.json()
    names = {item["name"] for item in body["items"]}
    expected = {
        "backup.stale",
        "worker.heartbeat.missing",
        "connector.failure_spike",
        "discovery.needs_user_action_storm",
        "browser.crash_loop",
        "audit.retention_breach_risk",
    }
    assert expected.issubset(names)


@pytest.mark.asyncio
async def test_create_alert_rule_round_trip(migrated_client):
    payload = {
        "name": f"test.user.rule.{uuid4().hex[:8]}",
        "metric": "connector.failure_rate",
        "operator": "gt",
        "threshold": 0.4,
        "window_seconds": 600,
        "severity": "warning",
        "cooldown_seconds": 600,
        "channels": ["in_app"],
        "enabled": True,
    }
    r = await migrated_client.post(
        "/admin/observability/alert-rules",
        json=payload,
        headers=_owner_headers(),
    )
    assert r.status_code == 201, r.text
    rule = r.json()
    assert rule["name"] == payload["name"]
    assert rule["is_system"] is False
    assert rule["severity"] == "warning"
    rule_id = rule["id"]
    # PATCH threshold
    r2 = await migrated_client.patch(
        f"/admin/observability/alert-rules/{rule_id}",
        json={"threshold": 0.6},
        headers=_owner_headers(),
    )
    assert r2.status_code == 200
    assert r2.json()["threshold"] == 0.6
    # DELETE
    r3 = await migrated_client.delete(
        f"/admin/observability/alert-rules/{rule_id}",
        headers=_owner_headers(),
    )
    assert r3.status_code == 204
    # The list endpoint keeps soft-deleted user rules visible but with enabled=false.
    r4 = await migrated_client.get(
        "/admin/observability/alert-rules", headers=_owner_headers()
    )
    remaining = {item["id"]: item for item in r4.json()["items"]}
    assert rule_id in remaining
    assert remaining[rule_id]["enabled"] is False


@pytest.mark.asyncio
async def test_create_alert_rule_rejects_unknown_metric(migrated_client):
    payload = {
        "name": f"bad.metric.{uuid4().hex[:8]}",
        "metric": "not.a.real.metric",
        "operator": "gt",
        "threshold": 1.0,
        "window_seconds": 0,
        "severity": "warning",
        "cooldown_seconds": 600,
        "channels": ["in_app"],
        "enabled": True,
    }
    r = await migrated_client.post(
        "/admin/observability/alert-rules",
        json=payload,
        headers=_owner_headers(),
    )
    assert r.status_code == 400
    assert "ALERT_RULE_INVALID" in r.json()["detail"]


@pytest.mark.asyncio
async def test_create_alert_rule_rejects_unknown_channel(migrated_client):
    payload = {
        "name": f"bad.channel.{uuid4().hex[:8]}",
        "metric": "backup.age_hours",
        "operator": "gt",
        "threshold": 1.0,
        "window_seconds": 0,
        "severity": "warning",
        "cooldown_seconds": 600,
        "channels": ["in_app", "pager"],
        "enabled": True,
    }
    r = await migrated_client.post(
        "/admin/observability/alert-rules",
        json=payload,
        headers=_owner_headers(),
    )
    assert r.status_code == 400
    assert "ALERT_RULE_INVALID" in r.json()["detail"]


@pytest.mark.asyncio
async def test_create_alert_rule_rejects_unknown_severity(migrated_client):
    payload = {
        "name": f"bad.sev.{uuid4().hex[:8]}",
        "metric": "backup.age_hours",
        "operator": "gt",
        "threshold": 1.0,
        "window_seconds": 0,
        "severity": "fatal",
        "cooldown_seconds": 600,
        "channels": ["in_app"],
        "enabled": True,
    }
    r = await migrated_client.post(
        "/admin/observability/alert-rules",
        json=payload,
        headers=_owner_headers(),
    )
    assert r.status_code == 400
    assert "ALERT_RULE_INVALID" in r.json()["detail"]


@pytest.mark.asyncio
async def test_delete_system_rule_returns_409(migrated_client):
    rules = await migrated_client.get(
        "/admin/observability/alert-rules", headers=_owner_headers()
    )
    system_rule_id = next(
        item["id"] for item in rules.json()["items"] if item["is_system"]
    )
    r = await migrated_client.delete(
        f"/admin/observability/alert-rules/{system_rule_id}",
        headers=_owner_headers(),
    )
    assert r.status_code == 409
    assert "ALERT_RULE_PROTECTED" in r.json()["detail"]


@pytest.mark.asyncio
async def test_patch_system_rule_threshold_is_allowed(migrated_client):
    rules = await migrated_client.get(
        "/admin/observability/alert-rules", headers=_owner_headers()
    )
    system_rule_id = next(
        item["id"] for item in rules.json()["items"] if item["is_system"]
    )
    r = await migrated_client.patch(
        f"/admin/observability/alert-rules/{system_rule_id}",
        json={"threshold": 27.0},
        headers=_owner_headers(),
    )
    assert r.status_code == 200
    assert r.json()["threshold"] == 27.0


@pytest.mark.asyncio
async def test_list_alert_events_returns_paginated(migrated_client):
    r = await migrated_client.get(
        "/admin/observability/alert-events?limit=10", headers=_owner_headers()
    )
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    assert body["limit"] == 10


@pytest.mark.asyncio
async def test_acknowledge_alert_event(migrated_client):
    # Insert an event directly so we can acknowledge it.
    from sqlalchemy import select

    from livelead.infrastructure.db.session import (
        create_engine,
        create_session_factory,
    )
    from livelead.runtime.settings import parse_settings

    settings = parse_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    async with factory() as session:
        rules = (
            await session.execute(
                select(AlertRuleRow).where(AlertRuleRow.name == "backup.stale")
            )
        ).scalars().all()
        assert rules
        rule = rules[0]
        event_row = AlertEventRow(
            id=str(uuid4()),
            organization_id=rule.organization_id,
            rule_id=rule.id,
            rule_name=rule.name,
            metric=rule.metric,
            status="firing",
            severity=rule.severity,
            payload_json=json.dumps({"rule_name": rule.name, "value": 99.0}),
            dedup_key=f"{rule.id}:manual",
            correlation_id="",
        )
        session.add(event_row)
        await session.commit()
        event_id = event_row.id
    await engine.dispose()

    r = await migrated_client.post(
        f"/admin/observability/alert-events/{event_id}/acknowledge",
        headers=_owner_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "acknowledged"
    assert body["acknowledged_by"]


@pytest.mark.asyncio
async def test_acknowledge_unknown_event_returns_404(migrated_client):
    r = await migrated_client.post(
        "/admin/observability/alert-events/00000000-0000-4000-8000-aaaaaaaaaaaa/acknowledge",
        headers=_owner_headers(),
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_alert_rules_role_gates(migrated_client):
    # viewer, analyst, sales, reviewer are all forbidden
    for role in ("viewer", "analyst", "sales", "reviewer"):
        r = await migrated_client.get(
            "/admin/observability/alert-rules",
            headers={
                "X-Organization-Id": "00000000-0000-4000-8000-000000000001",
                "X-Actor-Role": role,
            },
        )
        assert r.status_code == 403, f"{role} should be forbidden"


@pytest.mark.asyncio
async def test_alert_rules_admin_allowed(migrated_client):
    r = await migrated_client.get(
        "/admin/observability/alert-rules", headers=_admin_headers()
    )
    assert r.status_code == 200
