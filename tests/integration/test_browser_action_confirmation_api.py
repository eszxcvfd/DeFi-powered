import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from livelead.infrastructure.browser.adapter import reset_runtime_for_tests

ADMIN = {"X-Actor-Role": "admin"}


async def _browser_source(client, *, gated: bool = True):
    rate = {}
    if gated:
        rate["browser_confirmation_gated_actions"] = ["submit_form"]
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
    src = r.json()
    if rate:
        settings = client.app.state.settings
        db_url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
        engine = create_engine(db_url)
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE sources SET rate_limit_json = :j WHERE id = :id"),
                {"j": json.dumps(rate), "id": src["id"]},
            )
    return src


@pytest.fixture(autouse=True)
def _reset_browser():
    reset_runtime_for_tests()
    yield
    reset_runtime_for_tests()


@pytest.mark.asyncio
async def test_submit_form_returns_confirmation_required(client):
    src = await _browser_source(client)
    create = await client.post(
        "/browser-sessions",
        json={"source_id": src["id"], "initial_url": "https://example.com/"},
    )
    assert create.status_code == 201
    sid = create.json()["id"]
    for _ in range(40):
        if (await client.get(f"/browser-sessions/{sid}")).json()["state"] == "running":
            break
        await asyncio.sleep(0.1)

    act = await client.post(
        f"/browser-sessions/{sid}/actions",
        json={"action_type": "submit_form", "parameters": {"form_id": "lead", "target_label": "Contact"}},
    )
    assert act.status_code == 200
    body = act.json()
    assert body["lifecycle"] == "confirmation_required"
    assert body["confirmation_id"]
    assert body["preview"]["title"]
    cid = body["confirmation_id"]

    confirm = await client.post(
        f"/browser-sessions/{sid}/confirmations/{cid}/confirm",
        headers=ADMIN,
    )
    assert confirm.status_code == 200
    assert confirm.json()["lifecycle"] == "completed"
    assert confirm.json()["confirmation_state"] == "executed"


@pytest.mark.asyncio
async def test_cancel_confirmation(client):
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

    act = await client.post(
        f"/browser-sessions/{sid}/actions",
        json={"action_type": "submit_form", "parameters": {}},
    )
    cid = act.json()["confirmation_id"]
    cancel = await client.post(
        f"/browser-sessions/{sid}/confirmations/{cid}/cancel",
        headers=ADMIN,
    )
    assert cancel.status_code == 200
    assert cancel.json()["lifecycle"] == "cancelled"
    assert cancel.json()["confirmation_state"] == "cancelled"


@pytest.mark.asyncio
async def test_expired_confirmation_cannot_execute(client):
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

    act = await client.post(
        f"/browser-sessions/{sid}/actions",
        json={"action_type": "submit_form", "parameters": {}},
    )
    cid = act.json()["confirmation_id"]

    settings = client.app.state.settings
    db_url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    engine = create_engine(db_url)
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE browser_action_confirmations SET expires_at = :exp WHERE id = :id"),
            {"exp": past, "id": cid},
        )

    confirm = await client.post(
        f"/browser-sessions/{sid}/confirmations/{cid}/confirm",
        headers=ADMIN,
    )
    assert confirm.status_code == 200
    assert confirm.json()["confirmation_state"] == "expired"
    assert confirm.json()["lifecycle"] == "blocked"