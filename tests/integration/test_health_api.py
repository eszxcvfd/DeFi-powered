import pytest


@pytest.mark.asyncio
async def test_health_returns_json(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "livelead-api"
    assert body["version"] == "0.1.0"
    assert body["environment"] == "development"
    assert any(c["name"] == "sqlite" for c in body["components"])