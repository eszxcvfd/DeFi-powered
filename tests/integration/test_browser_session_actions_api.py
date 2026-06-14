import asyncio
from uuid import uuid4

import pytest

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
async def test_read_only_scroll_action(client):
    src = await _browser_source(client)
    create = await client.post(
        "/browser-sessions",
        json={"source_id": src["id"], "initial_url": "https://example.com/"},
    )
    assert create.status_code == 201
    sid = create.json()["id"]
    for _ in range(40):
        st = await client.get(f"/browser-sessions/{sid}")
        if st.json()["state"] == "running":
            break
        await asyncio.sleep(0.1)
    assert (await client.get(f"/browser-sessions/{sid}")).json()["state"] == "running"

    act = await client.post(
        f"/browser-sessions/{sid}/actions",
        json={"action_type": "scroll", "parameters": {"delta_y": 200}},
    )
    assert act.status_code == 200
    body = act.json()
    assert body["action_type"] == "scroll"
    assert body["lifecycle"] == "completed"
    assert body["summary"]


@pytest.mark.asyncio
async def test_action_blocked_when_not_allowlisted(client):
    import json

    from sqlalchemy import create_engine, text

    src = await _browser_source(client)
    settings = client.app.state.settings
    db_url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE sources SET rate_limit_json = :j WHERE id = :id"),
            {
                "j": json.dumps({"browser_read_only_actions": ["scroll"]}),
                "id": src["id"],
            },
        )
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
        json={"action_type": "navigate", "parameters": {"url": "https://example.com/other"}},
    )
    assert act.status_code == 200
    assert act.json()["lifecycle"] == "blocked"
    assert "action_not_allowlisted" in (act.json().get("policy_reason") or "")
