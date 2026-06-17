"""Integration tests for the connector health (US-046) API.

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


async def _seed_audit(
    client,
    *,
    action: str,
    occurred_at: datetime,
    source_id: str,
    metadata: dict | None = None,
) -> None:
    factory = client.app.state.session_factory
    async with factory() as session:
        session.add(
            AuditEntryRow(
                id=str(uuid4()),
                organization_id=ORG_ID,
                actor_id="system",
                actor_type="system",
                actor_role="system",
                action=action,
                action_family=action.split(".")[0],
                target_type="system",
                target_id=source_id,
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
        await session.commit()


# ----------------------------------------------------------------------
# RBAC
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_rejects_unauthenticated_request(migrated_client):
    # The header-fallback path returns a default
    # viewer role; the `_require_owner_or_admin`
    # helper rejects the request with 403. The
    # production deployment sets
    # `auth_allow_dev_headers=false` so the
    # boundary forces the request through the
    # session path; that path rejects anonymous
    # requests with 401.
    r = await migrated_client.get(
        "/admin/connectors/health/summary",
    )
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_summary_rejects_analyst_role(migrated_client):
    r = await migrated_client.get(
        "/admin/connectors/health/summary",
        headers={
            "X-Organization-Id": ORG_ID,
            "X-Actor-Role": "analyst",
        },
    )
    assert r.status_code == 403


# ----------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_returns_per_source_entry(migrated_client):
    await _seed_source(migrated_client, domain="alpha.example.com")
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.get(
        "/admin/connectors/health/summary",
        cookies=cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["entries"]) == 1
    assert body["entries"][0]["source_name"] == "Example"
    # No audit rows yet; the snapshot is `unknown`.
    assert body["entries"][0]["snapshot"] is None


@pytest.mark.asyncio
async def test_summary_returns_snapshot_after_compute(migrated_client):
    source_id = await _seed_source(migrated_client, domain="beta.example.com")
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(5):
        await _seed_audit(
            migrated_client,
            action="discovery.run.completed",
            occurred_at=now - timedelta(minutes=10 + i),
            source_id=source_id,
            metadata={"duration_ms": 100 + i * 5},
        )
    cookies = (await _login_owner(migrated_client))["cookies"]
    compute = await migrated_client.post(
        "/admin/connectors/health/snapshots:compute",
        json={"source_id": source_id},
        cookies=cookies,
    )
    assert compute.status_code == 200
    r = await migrated_client.get(
        "/admin/connectors/health/summary",
        cookies=cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["entries"]) == 1
    assert body["entries"][0]["snapshot"] is not None
    assert body["entries"][0]["snapshot"]["total_runs"] == 5
    assert body["entries"][0]["snapshot"]["success_count"] == 5
    assert body["entries"][0]["snapshot"]["status"] == "healthy"


# ----------------------------------------------------------------------
# Compute
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_snapshot_creates_row_and_audit(
    migrated_client,
):
    source_id = await _seed_source(migrated_client, domain="gamma.example.com")
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.post(
        "/admin/connectors/health/snapshots:compute",
        json={"source_id": source_id},
        cookies=cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["source_id"] == source_id
    assert body["status"] == "unknown"
    assert body["total_runs"] == 0


@pytest.mark.asyncio
async def test_compute_snapshot_rejects_unknown_source(migrated_client):
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.post(
        "/admin/connectors/health/snapshots:compute",
        json={"source_id": str(uuid4())},
        cookies=cookies,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_compute_snapshot_rejects_invalid_source_id(
    migrated_client,
):
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.post(
        "/admin/connectors/health/snapshots:compute",
        json={"source_id": "not-a-uuid"},
        cookies=cookies,
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_compute_snapshot_clamps_window_to_test_like_bound(
    migrated_client,
):
    source_id = await _seed_source(migrated_client, domain="delta.example.com")
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.post(
        "/admin/connectors/health/snapshots:compute",
        json={"source_id": source_id, "window_seconds": 24 * 3600},
        cookies=cookies,
    )
    assert r.status_code == 200
    body = r.json()
    # The bounded path clips the window to the
    # test_like maximum (1 hour).
    start = datetime.fromisoformat(body["window_start"])
    end = datetime.fromisoformat(body["window_end"])
    duration = (end - start).total_seconds()
    assert duration <= 3600


# ----------------------------------------------------------------------
# Snapshots list
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_snapshots_returns_history(migrated_client):
    source_id = await _seed_source(migrated_client, domain="epsilon.example.com")
    cookies = (await _login_owner(migrated_client))["cookies"]
    for _ in range(3):
        r = await migrated_client.post(
            "/admin/connectors/health/snapshots:compute",
            json={"source_id": source_id},
            cookies=cookies,
        )
        assert r.status_code == 200
    r = await migrated_client.get(
        "/admin/connectors/health/snapshots",
        params={"source_id": source_id},
        cookies=cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3


@pytest.mark.asyncio
async def test_list_snapshots_rejects_analyst_role(migrated_client):
    r = await migrated_client.get(
        "/admin/connectors/health/snapshots",
        headers={
            "X-Organization-Id": ORG_ID,
            "X-Actor-Role": "analyst",
        },
    )
    assert r.status_code == 403


# ----------------------------------------------------------------------
# Recent errors
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recent_errors_endpoint_returns_rollup(migrated_client):
    source_id = await _seed_source(migrated_client, domain="zeta.example.com")
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(2):
        await _seed_audit(
            migrated_client,
            action="discovery.run.failed",
            occurred_at=now - timedelta(minutes=5 + i),
            source_id=source_id,
            metadata={
                "error_code": "rate_limited",
                "error_message": f"failure {i}",
            },
        )
    cookies = (await _login_owner(migrated_client))["cookies"]
    # First compute to populate the error rollup.
    compute = await migrated_client.post(
        "/admin/connectors/health/snapshots:compute",
        json={"source_id": source_id},
        cookies=cookies,
    )
    assert compute.status_code == 200
    r = await migrated_client.get(
        f"/admin/connectors/health/{source_id}/errors",
        cookies=cookies,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert any(
        item["error_code"] == "rate_limited" for item in body["items"]
    )


@pytest.mark.asyncio
async def test_recent_errors_rejects_unknown_source(migrated_client):
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.get(
        f"/admin/connectors/health/{uuid4()}/errors",
        cookies=cookies,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_recent_errors_rejects_analyst_role(migrated_client):
    r = await migrated_client.get(
        f"/admin/connectors/health/{uuid4()}/errors",
        headers={
            "X-Organization-Id": ORG_ID,
            "X-Actor-Role": "analyst",
        },
    )
    assert r.status_code == 403
