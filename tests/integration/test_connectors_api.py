import pytest

ADMIN = {"X-Actor-Role": "admin"}


@pytest.mark.asyncio
async def test_admin_connector_registry_and_secrets_redacted(client):
    create = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "API Feed",
            "domain": "feed.example.com",
            "connector_type": "official_api",
            "authentication_mode": "api_key",
            "enabled": True,
            "approved": True,
            "policy": {
                "access_mode": "api",
                "quota_per_day": 100,
                "quota_used_today": 0,
                "valid": True,
            },
            "secret_plaintext": "plaintext-should-not-leak",
        },
    )
    assert create.status_code == 201
    body = create.json()
    assert body["has_secret"] is True
    assert "plaintext" not in body["secret_display"]
    assert body["secret_display"] == "***REDACTED***"
    assert body["runnable"] is True

    listed = await client.get("/admin/connectors", headers=ADMIN)
    assert listed.status_code == 200
    assert any(c["name"] == "API Feed" for c in listed.json())


@pytest.mark.asyncio
async def test_denied_browser_without_secret(client):
    create = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "Browser",
            "domain": "site.example.com",
            "connector_type": "browser",
            "authentication_mode": "session",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "browser", "valid": True},
        },
    )
    assert create.status_code == 201
    assert create.json()["runnable"] is False
    assert "missing_secret" in create.json()["denied_reasons"]


@pytest.mark.asyncio
async def test_runnable_sources_catalog(client):
    r = await client.get("/campaigns/runnable-sources")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
