from uuid import uuid4

import pytest

from livelead.infrastructure.browser.adapter import reset_runtime_for_tests

ADMIN = {"X-Actor-Role": "admin"}
COMPLIANCE = {"X-Actor-Role": "compliance"}


async def _cloak_source(client):
    r = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": f"Cloak {uuid4().hex[:6]}",
            "domain": "partners.example.com",
            "connector_type": "browser",
            "automation_engine": "cloakbrowser",
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
async def test_cloakbrowser_blocked_until_dual_approval(client):
    src = await _cloak_source(client)
    sid = src["id"]

    blocked = await client.post(
        "/browser-sessions",
        headers=ADMIN,
        json={"source_id": sid, "initial_url": "https://partners.example.com/"},
    )
    assert blocked.status_code == 409
    assert "cloakbrowser" in str(blocked.json().get("detail", {}))

    req = await client.post(
        f"/admin/cloakbrowser-policy/sources/{sid}/request",
        headers=ADMIN,
        json={
            "purpose_rationale": "Approved partner portal read-only",
            "pinned_version": "1.0.0",
        },
    )
    assert req.status_code == 200
    assert req.json()["policy_state"] == "pending"

    still = await client.post(
        "/browser-sessions",
        headers=ADMIN,
        json={"source_id": sid, "initial_url": "https://partners.example.com/"},
    )
    assert still.status_code == 409

    oa = await client.post(
        f"/admin/cloakbrowser-policy/sources/{sid}/approve-owner-admin",
        headers=ADMIN,
    )
    assert oa.status_code == 200
    assert oa.json()["owner_admin_approved"] is True
    assert oa.json()["compliance_approved"] is False

    comp = await client.post(
        f"/admin/cloakbrowser-policy/sources/{sid}/approve-compliance",
        headers=COMPLIANCE,
    )
    assert comp.status_code == 200
    assert comp.json()["policy_state"] == "approved"

    client.app.state.settings.cloakbrowser_runtime_version = "1.0.0"

    ok = await client.post(
        "/browser-sessions",
        headers=ADMIN,
        json={"source_id": sid, "initial_url": "https://partners.example.com/"},
    )
    assert ok.status_code == 201
    assert ok.json()["engine"] == "cloakbrowser"


@pytest.mark.asyncio
async def test_revoke_and_kill_switch_block_launch(client):
    src = await _cloak_source(client)
    sid = src["id"]
    await client.post(
        f"/admin/cloakbrowser-policy/sources/{sid}/request",
        headers=ADMIN,
        json={"purpose_rationale": "scope", "pinned_version": "1.0.0"},
    )
    await client.post(f"/admin/cloakbrowser-policy/sources/{sid}/approve-owner-admin", headers=ADMIN)
    await client.post(f"/admin/cloakbrowser-policy/sources/{sid}/approve-compliance", headers=COMPLIANCE)
    client.app.state.settings.cloakbrowser_runtime_version = "1.0.0"

    revoke = await client.post(
        f"/admin/cloakbrowser-policy/sources/{sid}/revoke",
        headers=ADMIN,
        json={"reason": "policy review"},
    )
    assert revoke.status_code == 200
    assert revoke.json()["policy_state"] == "revoked"

    denied = await client.post(
        "/browser-sessions",
        headers=ADMIN,
        json={"source_id": sid, "initial_url": "https://partners.example.com/"},
    )
    assert denied.status_code == 409

    await client.post(
        f"/admin/cloakbrowser-policy/sources/{sid}/request",
        headers=ADMIN,
        json={"purpose_rationale": "scope again", "pinned_version": "1.0.0"},
    )
    await client.post(f"/admin/cloakbrowser-policy/sources/{sid}/approve-owner-admin", headers=ADMIN)
    await client.post(f"/admin/cloakbrowser-policy/sources/{sid}/approve-compliance", headers=COMPLIANCE)

    await client.post(
        "/admin/cloakbrowser-policy/kill-switch",
        headers=ADMIN,
        json={"active": True},
    )
    ks = await client.post(
        "/browser-sessions",
        headers=ADMIN,
        json={"source_id": sid, "initial_url": "https://partners.example.com/"},
    )
    assert ks.status_code == 409
    denied = ks.json()["detail"]["policy_denied"]
    assert "cloakbrowser_kill_switch" in denied