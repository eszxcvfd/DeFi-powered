from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

PAYLOAD = {
    "name": "Source Perf Campaign",
    "target_industry": "Fintech",
    "product_or_service_focus": "Payments",
    "market_regions": ["EU"],
    "languages": ["en"],
    "timezone": "UTC",
    "date_range": {"start": "2026-07-01", "end": "2026-12-31"},
    "positive_keywords": ["webinar"],
    "exclude_keywords": [],
    "icp": {
        "industry": "Payments",
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
}


@pytest.mark.asyncio
async def test_source_performance_invalid_range(client):
    r = await client.get(
        "/reports/source-performance",
        params={"start": "2026-06-10", "end": "2026-06-01", "grouping": "campaign"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_source_performance_invalid_grouping(client):
    r = await client.get(
        "/reports/source-performance", params={"preset": "last_7_days", "grouping": "domain"}
    )
    assert r.status_code == 400
    assert "unsupported" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_source_performance_campaign_grouping_with_seeded_data(client):
    create = await client.post(
        "/campaigns", json={**PAYLOAD, "name": f"SP{uuid4()}", "description": ""}
    )
    cid = create.json()["id"]
    settings = client.app.state.settings
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    sync = sessionmaker(bind=create_engine(url))()
    finding = MockFinding(
        title="Source Perf Webinar",
        source_url=f"https://sp.test/{uuid4()}",
        description="webinar",
        organizer="Org",
        region="EU",
    )
    ingest_finding(
        sync,
        organization_id=DEV_ORGANIZATION_ID,
        campaign_id=UUID(cid),
        source_id=uuid4(),
        finding=finding,
    )
    sync.commit()
    sync.close()

    events = (await client.get(f"/campaigns/{cid}/events")).json()
    event_id = events[0]["id"]
    lead = await client.post(
        "/leads",
        json={
            "display_name": "SP Lead",
            "company": "Co",
            "discovery_source": "event",
            "event_id": event_id,
            "origin_kind": "event",
        },
    )
    assert lead.status_code == 201
    await client.post(f"/leads/{lead.json()['id']}/outcomes", json={"outcome_type": "opportunity"})

    for grouping in ("campaign", "industry", "platform", "connector"):
        r = await client.get(
            "/reports/source-performance", params={"preset": "last_30_days", "grouping": grouping}
        )
        assert r.status_code == 200, grouping
        body = r.json()
        assert body["grouping"] == grouping
        assert "window" in body
        assert "freshness" in body
        if grouping == "campaign":
            assert any(row["metrics"]["events_discovered"] >= 1 for row in body["rows"])
