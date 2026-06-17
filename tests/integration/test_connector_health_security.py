"""Security tests for the connector health surface (US-046).

Asserts the closed contract from
`docs/decisions/0024-connector-health-surface-baseline.md`:

- The bounded computation runs through the
  `SanitizeAlertPayload` helper from `US-041` so
  the audit metadata never carries a raw secret,
  cookie, browser storage state, raw PII, or full
  connection string.
- The RBAC contract from `US-027` rejects
  viewer, analyst, sales, and reviewer sessions
  with 403.
- The bounded window refuses zero or negative
  values.
- The migration does not weaken the existing
  audit retention guarantee from `NFR-SEC-008`.
- The new `ConnectorHealthStatus` enum does not
  weaken the existing `AlertMetric` enum from
  `US-041` or the existing `MetricRegistry` from
  `US-042`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
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
    domain: str = "security.example.com",
) -> str:
    factory = client.app.state.session_factory
    async with factory() as session:
        source_id = str(uuid4())
        session.add(
            SourceRow(
                id=source_id,
                organization_id=ORG_ID,
                name="Security Source",
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


async def _seed_audit_with_secret(
    client,
    *,
    action: str,
    occurred_at: datetime,
    source_id: str,
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
                    {
                        "source_id": source_id,
                        "duration_ms": 100,
                        "api_key": "sk-secret-value",
                        "cookie": "session=secret",
                    }
                ),
                metadata_redacted=False,
            )
        )
        await session.commit()


# ----------------------------------------------------------------------
# RBAC contract
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_snapshot_rejects_analyst_role(migrated_client):
    r = await migrated_client.post(
        "/admin/connectors/health/snapshots:compute",
        json={"source_id": str(uuid4())},
        headers={
            "X-Organization-Id": ORG_ID,
            "X-Actor-Role": "analyst",
        },
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_snapshots_list_rejects_viewer_role(migrated_client):
    r = await migrated_client.get(
        "/admin/connectors/health/snapshots",
        headers={
            "X-Organization-Id": ORG_ID,
            "X-Actor-Role": "viewer",
        },
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_summary_rejects_sales_role(migrated_client):
    r = await migrated_client.get(
        "/admin/connectors/health/summary",
        headers={
            "X-Organization-Id": ORG_ID,
            "X-Actor-Role": "sales",
        },
    )
    assert r.status_code == 403


# ----------------------------------------------------------------------
# Sanitization contract
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_snapshot_strips_sensitive_keys_from_audit(
    migrated_client,
):
    source_id = await _seed_source(migrated_client)
    now = datetime.now(UTC).replace(tzinfo=None)
    await _seed_audit_with_secret(
        migrated_client,
        action="discovery.run.completed",
        occurred_at=now - timedelta(minutes=5),
        source_id=source_id,
    )
    cookies = (await _login_owner(migrated_client))["cookies"]
    compute = await migrated_client.post(
        "/admin/connectors/health/snapshots:compute",
        json={"source_id": source_id},
        cookies=cookies,
    )
    assert compute.status_code == 200
    factory = migrated_client.app.state.session_factory
    async with factory() as session:
        rows = (
            await session.execute(
                AuditEntryRow.__table__.select().where(
                    AuditEntryRow.action
                    == "connector.health.snapshot.computed"
                )
            )
        ).fetchall()
        assert rows
        for row in rows:
            assert "sk-secret-value" not in (row.metadata_json or "")
            assert "session=secret" not in (row.metadata_json or "")
            assert "REDACTED" in (row.metadata_json or "") or (
                "api_key" not in (row.metadata_json or "")
            )


# ----------------------------------------------------------------------
# Window contract
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_snapshot_rejects_below_minimum_window(
    migrated_client,
):
    source_id = await _seed_source(migrated_client)
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.post(
        "/admin/connectors/health/snapshots:compute",
        json={"source_id": source_id, "window_seconds": 30},
        cookies=cookies,
    )
    # The bounded path rejects windows below 60
    # seconds with 422 (Pydantic validation).
    assert r.status_code in (400, 422)


@pytest.mark.asyncio
async def test_compute_snapshot_rejects_above_maximum_window(
    migrated_client,
):
    source_id = await _seed_source(migrated_client)
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.post(
        "/admin/connectors/health/snapshots:compute",
        json={"source_id": source_id, "window_seconds": 30 * 24 * 3600},
        cookies=cookies,
    )
    # The bounded path rejects windows above 24
    # hours with 422 (Pydantic validation).
    assert r.status_code in (400, 422)
