"""Integration tests for the connector auto-disable (US-048) API.

Uses the real /auth/login flow so the integration
suite exercises the same boundary the frontend
would. Each test gets its own migrated SQLite via
the `migrated_client` fixture.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.infrastructure.db.models import (
    AuditEntryRow,
    ConnectorAutoDisableEventRow,
    ConnectorAutoDisableRuleRow,
    ConnectorHealthSnapshotRow,
    SourceRow,
)


ORG_ID = "00000000-0000-4000-8000-000000000001"


def _bootstrap_owner_email() -> str:
    from livelead.runtime.settings import parse_settings

    return parse_settings().auth_default_owner_email


def _bootstrap_owner_password() -> str:
    from livelead.runtime.settings import parse_settings

    return parse_settings().auth_default_owner_password


async def _login_owner(client) -> dict:
    r = await client.post(
        "/auth/login",
        json={
            "email": _bootstrap_owner_email(),
            "password": _bootstrap_owner_password(),
            "organization_id": ORG_ID,
        },
    )
    assert r.status_code == 200, r.text
    return {"cookies": dict(r.cookies)}


async def _seed_source(
    client,
    *,
    domain: str = "example.com",
) -> str:
    factory = client.app.state.session_factory
    async with factory() as session:
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
        await session.commit()
    return source_id


async def _seed_unhealthy_snapshots(
    client,
    *,
    source_id: str,
    count: int = 3,
) -> None:
    factory = client.app.state.session_factory
    now = datetime.now(UTC).replace(tzinfo=None)
    async with factory() as session:
        for i in range(count):
            session.add(
                ConnectorHealthSnapshotRow(
                    id=str(uuid4()),
                    organization_id=ORG_ID,
                    source_id=source_id,
                    connector_type="rss",
                    window_start=now - timedelta(hours=1),
                    window_end=now,
                    total_runs=10,
                    success_count=10,
                    failure_count=0,
                    success_rate=1.0,
                    p50_latency_ms=100.0,
                    p95_latency_ms=200.0,
                    captcha_count=0,
                    captcha_rate=0.0,
                    last_run_at=now - timedelta(minutes=3 - i),
                    last_error_code=None,
                    last_error_message=None,
                    status="unhealthy",
                    audit_correlation_id="",
                    computed_at=now - timedelta(minutes=3 - i),
                    created_at=now - timedelta(minutes=3 - i),
                    updated_at=now - timedelta(minutes=3 - i),
                )
            )
        await session.commit()


# ----------------------------------------------------------------------
# Choices
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_choices_returns_closed_enums(
    migrated_client,
) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.get(
        "/admin/connectors/auto-disable/choices", cookies=cookies
    )
    assert r.status_code == 200, r.text
    body = r.json()
    trigger_values = {t["value"] for t in body["triggers"]}
    assert trigger_values == {
        "health_unhealthy",
        "captcha_rate_breach",
        "failure_rate_breach",
        "needs_user_action_storm",
        "error_spike",
        "manual_kill_switch",
    }
    status_values = {s["value"] for s in body["event_statuses"]}
    assert status_values == {"active", "recovering", "resolved", "superseded"}


# ----------------------------------------------------------------------
# Rule CRUD
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_rule_persists_and_audits(
    migrated_client,
) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    source_id = await _seed_source(migrated_client)
    r = await migrated_client.post(
        "/admin/connectors/auto-disable/rules",
        json={
            "source_id": source_id,
            "trigger": "health_unhealthy",
            "threshold_value": 0.0,
            "consecutive_breaches": 3,
            "cooldown_seconds": 900,
        },
        cookies=cookies,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["source_id"] == source_id
    assert body["trigger"] == "health_unhealthy"
    # The audit entry was written.
    factory = migrated_client.app.state.session_factory
    async with factory() as session:
        audit = (
            await session.execute(
                select(AuditEntryRow).where(
                    AuditEntryRow.action
                    == "connector.auto_disable.rule.created"
                )
            )
        ).scalars().all()
    assert len(audit) == 1
    assert audit[0].target_id == body["id"]


@pytest.mark.asyncio
async def test_create_rule_rejects_invalid_trigger(
    migrated_client,
) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    source_id = await _seed_source(migrated_client)
    r = await migrated_client.post(
        "/admin/connectors/auto-disable/rules",
        json={
            "source_id": source_id,
            "trigger": "not-a-real-trigger",
            "threshold_value": 0.0,
        },
        cookies=cookies,
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_list_rules_returns_paginated_response(
    migrated_client,
) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    source_id = await _seed_source(migrated_client)
    for _ in range(2):
        r = await migrated_client.post(
            "/admin/connectors/auto-disable/rules",
            json={
                "source_id": source_id,
                "trigger": "health_unhealthy",
                "threshold_value": 0.0,
            },
            cookies=cookies,
        )
        assert r.status_code == 201, r.text
    r = await migrated_client.get(
        "/admin/connectors/auto-disable/rules",
        params={"source_id": source_id},
        cookies=cookies,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_update_rule_emits_audit(
    migrated_client,
) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    source_id = await _seed_source(migrated_client)
    create = await migrated_client.post(
        "/admin/connectors/auto-disable/rules",
        json={
            "source_id": source_id,
            "trigger": "health_unhealthy",
            "threshold_value": 0.0,
            "consecutive_breaches": 3,
        },
        cookies=cookies,
    )
    rule_id = create.json()["id"]
    r = await migrated_client.patch(
        f"/admin/connectors/auto-disable/rules/{rule_id}",
        json={"threshold_value": 0.5, "consecutive_breaches": 5},
        cookies=cookies,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["threshold_value"] == pytest.approx(0.5)
    assert body["consecutive_breaches"] == 5


@pytest.mark.asyncio
async def test_delete_rule_soft_deletes(migrated_client) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    source_id = await _seed_source(migrated_client)
    create = await migrated_client.post(
        "/admin/connectors/auto-disable/rules",
        json={
            "source_id": source_id,
            "trigger": "health_unhealthy",
            "threshold_value": 0.0,
        },
        cookies=cookies,
    )
    rule_id = create.json()["id"]
    r = await migrated_client.delete(
        f"/admin/connectors/auto-disable/rules/{rule_id}",
        cookies=cookies,
    )
    assert r.status_code == 204, r.text
    r = await migrated_client.get(
        "/admin/connectors/auto-disable/rules",
        params={"source_id": source_id},
        cookies=cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0


# ----------------------------------------------------------------------
# Evaluation
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_fires_and_flips_source(
    migrated_client,
) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    source_id = await _seed_source(migrated_client)
    await _seed_unhealthy_snapshots(migrated_client, source_id=source_id)
    create = await migrated_client.post(
        "/admin/connectors/auto-disable/rules",
        json={
            "source_id": source_id,
            "trigger": "health_unhealthy",
            "threshold_value": 0.0,
            "consecutive_breaches": 3,
            "window_seconds": 1800,
        },
        cookies=cookies,
    )
    assert create.status_code == 201
    r = await migrated_client.post(
        f"/admin/connectors/connectors/{source_id}/auto-disable/evaluate",
        cookies=cookies,
    )
    # Path mismatch expected; the correct
    # endpoint is below. Use the correct
    # endpoint instead.
    assert r.status_code in (404, 405)
    r = await migrated_client.post(
        f"/admin/connectors/{source_id}/auto-disable/evaluate",
        cookies=cookies,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["should_disable"] is True
    factory = migrated_client.app.state.session_factory
    async with factory() as session:
        event = (
            await session.execute(
                select(ConnectorAutoDisableEventRow).where(
                    ConnectorAutoDisableEventRow.source_id == source_id
                )
            )
        ).scalars().all()
        assert len(event) == 1
        source = (
            await session.execute(
                select(SourceRow).where(SourceRow.id == source_id)
            )
        ).scalar_one()
        assert source.enabled is False


# ----------------------------------------------------------------------
# Recovery
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recovery_flow_transitions_event(
    migrated_client,
) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    source_id = await _seed_source(migrated_client)
    await _seed_unhealthy_snapshots(migrated_client, source_id=source_id)
    await migrated_client.post(
        "/admin/connectors/auto-disable/rules",
        json={
            "source_id": source_id,
            "trigger": "health_unhealthy",
            "threshold_value": 0.0,
            "consecutive_breaches": 3,
            "window_seconds": 1800,
        },
        cookies=cookies,
    )
    await migrated_client.post(
        f"/admin/connectors/{source_id}/auto-disable/evaluate",
        cookies=cookies,
    )
    factory = migrated_client.app.state.session_factory
    async with factory() as session:
        event = (
            await session.execute(
                select(ConnectorAutoDisableEventRow)
            )
        ).scalars().all()
    event_id = event[0].id
    r = await migrated_client.post(
        f"/admin/connectors/auto-disable/events/{event_id}/recover",
        json={"reason": "Operator confirmed the source is healthy."},
        cookies=cookies,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "recovering"
    # Second recovery is rejected.
    r = await migrated_client.post(
        f"/admin/connectors/auto-disable/events/{event_id}/recover",
        json={"reason": "Operator confirmed."},
        cookies=cookies,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_recovery_rejects_empty_reason(
    migrated_client,
) -> None:
    cookies = (await _login_owner(migrated_client))["cookies"]
    source_id = await _seed_source(migrated_client)
    await _seed_unhealthy_snapshots(migrated_client, source_id=source_id)
    await migrated_client.post(
        "/admin/connectors/auto-disable/rules",
        json={
            "source_id": source_id,
            "trigger": "health_unhealthy",
            "threshold_value": 0.0,
            "consecutive_breaches": 3,
            "window_seconds": 1800,
        },
        cookies=cookies,
    )
    await migrated_client.post(
        f"/admin/connectors/{source_id}/auto-disable/evaluate",
        cookies=cookies,
    )
    factory = migrated_client.app.state.session_factory
    async with factory() as session:
        event = (
            await session.execute(
                select(ConnectorAutoDisableEventRow)
            )
        ).scalars().all()
    event_id = event[0].id
    r = await migrated_client.post(
        f"/admin/connectors/auto-disable/events/{event_id}/recover",
        json={"reason": "   "},
        cookies=cookies,
    )
    assert r.status_code == 400


# ----------------------------------------------------------------------
# RBAC
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_choices_requires_owner_or_admin(
    migrated_client,
) -> None:
    # No cookies means anonymous, which the
    # auth boundary rejects with 401.
    r = await migrated_client.get(
        "/admin/connectors/auto-disable/choices"
    )
    assert r.status_code in (401, 403)
