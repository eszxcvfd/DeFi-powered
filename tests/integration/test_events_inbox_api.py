import pytest


@pytest.mark.asyncio
async def test_list_organization_events(client):
    r = await client.get("/events", params={"limit": 10})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
