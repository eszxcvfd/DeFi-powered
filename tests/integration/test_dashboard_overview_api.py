from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

PAYLOAD = {
    "name": "Dash Campaign",
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
async def test_dashboard_overview_invalid_range(client):
    r = await client.get(
        "/reporting/dashboard-overview", params={"start": "2026-06-10", "end": "2026-06-01"}
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_dashboard_overview_empty_org_shows_unavailable_widgets(client):
    r = await client.get("/reporting/dashboard-overview", params={"preset": "last_30_days"})
    assert r.status_code == 200
    body = r.json()
    assert "time_window" in body
    assert len(body["widgets"]) >= 8
    discovered = next(w for w in body["widgets"] if w["key"] == "events_discovered")
    assert discovered["availability"] == "unavailable"
    assert discovered["value"] is None


@pytest.mark.asyncio
async def test_dashboard_overview_with_seeded_event(client):
    create = await client.post(
        "/campaigns", json={**PAYLOAD, "name": f"Dash {uuid4()}", "description": ""}
    )
    assert create.status_code == 201
    cid = create.json()["id"]
    settings = client.app.state.settings
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    sync = sessionmaker(bind=create_engine(url))()
    finding = MockFinding(
        title="Dash Webinar",
        source_url=f"https://dash.test/{uuid4()}",
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

    r = await client.get("/reporting/dashboard-overview", params={"preset": "last_30_days"})
    assert r.status_code == 200
    discovered = next(w for w in r.json()["widgets"] if w["key"] == "events_discovered")
    assert discovered["availability"] in ("available", "empty")
    assert discovered["freshness"]["source"] == "events.observed_at"
    opportunities = next(w for w in r.json()["widgets"] if w["key"] == "opportunities")
    assert opportunities["availability"] == "unavailable"
