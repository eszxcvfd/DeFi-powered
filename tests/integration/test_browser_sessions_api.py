import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.infrastructure.browser.adapter import reset_runtime_for_tests
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

ADMIN = {"X-Actor-Role": "admin"}


async def _browser_source(client, *, approved=True, with_secret=False):
    payload = {
        "name": f"Browser {uuid4().hex[:6]}",
        "domain": f"browser-{uuid4().hex[:6]}.example.com",
        "connector_type": "browser",
        "authentication_mode": "none",
        "enabled": True,
        "approved": approved,
        "policy": {"access_mode": "browser", "valid": True},
    }
    if with_secret:
        payload["authentication_mode"] = "session"
        payload["secret_plaintext"] = "cookie-stub"
    r = await client.post("/admin/connectors", headers=ADMIN, json=payload)
    assert r.status_code == 201
    return r.json()


@pytest.fixture(autouse=True)
def _reset_browser_runtime():
    reset_runtime_for_tests()
    yield
    reset_runtime_for_tests()


@pytest.mark.asyncio
async def test_browser_session_policy_denied(client):
    src = await _browser_source(client, approved=False)
    r = await client.post(
        "/browser-sessions",
        json={"source_id": src["id"], "initial_url": "https://example.com/page"},
    )
    assert r.status_code == 409
    assert "policy_denied" in r.json()["detail"]


@pytest.mark.asyncio
async def test_browser_session_create_status_stop(client):
    src = await _browser_source(client)
    create = await client.post(
        "/browser-sessions",
        json={"source_id": src["id"], "initial_url": "https://example.com/supervised"},
    )
    assert create.status_code == 201
    body = create.json()
    assert body["state"] in ("queued", "starting", "running")
    assert body["engine"] == "playwright"
    assert body["isolation"]["isolation_key"]
    sid = body["id"]

    for _ in range(30):
        st = await client.get(f"/browser-sessions/{sid}")
        assert st.status_code == 200
        if st.json()["state"] == "running":
            break
        await asyncio.sleep(0.1)
    assert (await client.get(f"/browser-sessions/{sid}")).json()["state"] == "running"

    stop = await client.post(f"/browser-sessions/{sid}/stop")
    assert stop.status_code == 200
    assert stop.json()["state"] == "stopped"
    assert stop.json()["terminal"] is True


@pytest.mark.asyncio
async def test_browser_session_from_event(client):
    src = await _browser_source(client)
    camp = await client.post(
        "/campaigns",
        json={
            "name": f"BRW {uuid4()}",
            "target_industry": "Tech",
            "product_or_service_focus": "SaaS",
            "market_regions": ["EU"],
            "languages": ["en"],
            "timezone": "UTC",
            "date_range": {"start": "2026-07-01", "end": "2026-12-31"},
            "positive_keywords": [],
            "exclude_keywords": [],
            "icp": {
                "industry": "Tech",
                "organization_type": "SaaS",
                "company_size": "",
                "role_or_title_targets": [],
                "country_or_region": "EU",
                "pain_points": [],
                "use_cases": [],
                "positive_keywords": [],
                "excluded_keywords": [],
            },
            "scoring_weights": {},
            "description": "",
        },
    )
    assert camp.status_code == 201
    cid = camp.json()["id"]
    settings = client.app.state.settings
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    sync = sessionmaker(bind=create_engine(url))()
    finding = MockFinding(
        title="Browser event",
        source_url="https://events.example.com/1",
        description="d",
        organizer="Org",
        region="EU",
    )
    ingest_finding(
        sync,
        organization_id=DEV_ORGANIZATION_ID,
        campaign_id=UUID(cid),
        source_id=UUID(src["id"]),
        finding=finding,
    )
    sync.commit()
    event_id = str(
        sync.execute(text("SELECT id FROM events ORDER BY created_at DESC LIMIT 1")).scalar()
    )
    sync.close()

    create = await client.post(
        "/browser-sessions",
        json={"event_id": event_id, "source_id": src["id"]},
    )
    assert create.status_code == 201
    assert create.json()["target"]["kind"] == "event"
