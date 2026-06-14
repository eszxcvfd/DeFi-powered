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
async def test_profile_crud_and_lock(client):
    create = await client.post(
        "/admin/browser-profiles",
        headers=ADMIN,
        json={"name": "Gov profile", "ttl_days": 30},
    )
    assert create.status_code == 201
    body = create.json()
    assert body["lifecycle_state"] == "active"
    assert body["raw_state_exposed"] is False
    pid = body["id"]

    listed = await client.get("/admin/browser-profiles", headers=ADMIN)
    assert listed.status_code == 200
    assert any(p["id"] == pid for p in listed.json())

    lock = await client.post(f"/admin/browser-profiles/{pid}/lock", headers=ADMIN)
    assert lock.status_code == 200
    assert lock.json()["lifecycle_state"] == "locked"

    check = await client.get(f"/admin/browser-profiles/{pid}/launch-check", headers=ADMIN)
    assert check.json()["eligible"] is False


@pytest.mark.asyncio
async def test_session_launch_with_eligible_profile(client):
    src = await _browser_source(client)
    prof = await client.post(
        "/admin/browser-profiles",
        headers=ADMIN,
        json={"name": "Session profile", "ttl_days": 30},
    )
    pid = prof.json()["id"]

    create = await client.post(
        "/browser-sessions",
        headers=ADMIN,
        json={
            "source_id": src["id"],
            "initial_url": "https://example.com/",
            "browser_profile_id": pid,
        },
    )
    assert create.status_code == 201
    sid = create.json()["id"]
    for _ in range(40):
        if (await client.get(f"/browser-sessions/{sid}", headers=ADMIN)).json()["state"] == "running":
            break
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_session_blocked_for_locked_profile(client):
    src = await _browser_source(client)
    prof = await client.post(
        "/admin/browser-profiles",
        headers=ADMIN,
        json={"name": "Locked", "ttl_days": 30},
    )
    pid = prof.json()["id"]
    await client.post(f"/admin/browser-profiles/{pid}/lock", headers=ADMIN)

    create = await client.post(
        "/browser-sessions",
        headers=ADMIN,
        json={
            "source_id": src["id"],
            "initial_url": "https://example.com/",
            "browser_profile_id": pid,
        },
    )
    assert create.status_code == 409
    assert "profile_blocked" in create.json()["detail"]


@pytest.mark.asyncio
async def test_consent_and_state_material(client):
    prof = await client.post(
        "/admin/browser-profiles",
        headers=ADMIN,
        json={"name": "Consent", "ttl_days": 30},
    )
    pid = prof.json()["id"]

    denied = await client.post(
        f"/admin/browser-profiles/{pid}/state-material",
        headers=ADMIN,
        json={"storage_state": {"cookies": []}},
    )
    assert denied.status_code == 409

    await client.post(
        f"/admin/browser-profiles/{pid}/consent",
        headers=ADMIN,
        json={"granted": True},
    )
    stored = await client.post(
        f"/admin/browser-profiles/{pid}/state-material",
        headers=ADMIN,
        json={"storage_state": {"cookies": [], "origins": []}},
    )
    assert stored.status_code == 200
    assert stored.json()["state_material_present"] is True
    detail = await client.get(f"/admin/browser-profiles/{pid}", headers=ADMIN)
    assert "ciphertext" not in detail.text.lower()


@pytest.mark.asyncio
async def test_expire_blocks_launch(client):
    src = await _browser_source(client)
    prof = await client.post(
        "/admin/browser-profiles",
        headers=ADMIN,
        json={"name": "Expire me", "ttl_days": 30},
    )
    pid = prof.json()["id"]
    await client.post(f"/admin/browser-profiles/{pid}/expire", headers=ADMIN)

    create = await client.post(
        "/browser-sessions",
        headers=ADMIN,
        json={
            "source_id": src["id"],
            "initial_url": "https://example.com/",
            "browser_profile_id": pid,
        },
    )
    assert create.status_code == 409