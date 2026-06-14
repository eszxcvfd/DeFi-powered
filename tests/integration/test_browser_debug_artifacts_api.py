import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from livelead.infrastructure.browser.adapter import reset_runtime_for_tests

ADMIN = {"X-Actor-Role": "admin"}


async def _browser_source(client):
    r = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": f"Browser {uuid4().hex[:6]}",
            "domain": "example.com",
            "connector_type": "browser",
            "authentication_mode": "none",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "browser", "valid": True},
        },
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture(autouse=True)
def _reset_browser():
    reset_runtime_for_tests()
    yield
    reset_runtime_for_tests()


@pytest.mark.asyncio
async def test_screenshot_and_list_artifacts(client):
    src = await _browser_source(client)
    create = await client.post(
        "/browser-sessions",
        json={"source_id": src["id"], "initial_url": "https://example.com/"},
    )
    sid = create.json()["id"]
    for _ in range(40):
        if (await client.get(f"/browser-sessions/{sid}")).json()["state"] == "running":
            break
        await asyncio.sleep(0.1)

    shot = await client.post(f"/browser-sessions/{sid}/artifacts/screenshot", headers=ADMIN)
    assert shot.status_code == 200
    body = shot.json()
    assert body["status"] == "active"
    assert body["artifact_type"] == "screenshot"
    aid = body["id"]

    listed = await client.get(f"/browser-sessions/{sid}/artifacts", headers=ADMIN)
    assert listed.status_code == 200
    assert any(a["id"] == aid for a in listed.json())

    dl = await client.get(f"/browser-sessions/{sid}/artifacts/{aid}/download", headers=ADMIN)
    assert dl.status_code == 200
    assert dl.headers["content-type"].startswith("image/")


@pytest.mark.asyncio
async def test_debug_enable_creates_console_and_trace(client):
    src = await _browser_source(client)
    create = await client.post(
        "/browser-sessions",
        json={"source_id": src["id"], "initial_url": "https://example.com/"},
    )
    sid = create.json()["id"]
    for _ in range(40):
        if (await client.get(f"/browser-sessions/{sid}")).json()["state"] == "running":
            break
        await asyncio.sleep(0.1)

    dbg = await client.post(
        f"/browser-sessions/{sid}/debug",
        headers=ADMIN,
        json={"enabled": True},
    )
    assert dbg.status_code == 200
    assert dbg.json()["debug_enabled"] is True

    listed = await client.get(f"/browser-sessions/{sid}/artifacts", headers=ADMIN)
    types = {a["artifact_type"] for a in listed.json()}
    assert "console_log" in types
    assert "trace" in types


@pytest.mark.asyncio
async def test_expired_artifact_download_forbidden(client):
    src = await _browser_source(client)
    create = await client.post(
        "/browser-sessions",
        json={"source_id": src["id"], "initial_url": "https://example.com/"},
    )
    sid = create.json()["id"]
    for _ in range(40):
        if (await client.get(f"/browser-sessions/{sid}")).json()["state"] == "running":
            break
        await asyncio.sleep(0.1)

    shot = await client.post(f"/browser-sessions/{sid}/artifacts/screenshot", headers=ADMIN)
    aid = shot.json()["id"]

    settings = client.app.state.settings
    db_url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    engine = create_engine(db_url)
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE browser_debug_artifacts SET expires_at = :exp WHERE id = :id"),
            {"exp": past, "id": aid},
        )

    dl = await client.get(f"/browser-sessions/{sid}/artifacts/{aid}/download", headers=ADMIN)
    assert dl.status_code == 403