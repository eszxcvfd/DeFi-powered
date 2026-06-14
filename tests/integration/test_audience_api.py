from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

PAYLOAD = {
    "name": "Audience Campaign",
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
async def test_event_detail_includes_audience_hypotheses(client):
    create = await client.post("/campaigns", json={**PAYLOAD, "name": "Aud", "description": ""})
    cid = create.json()["id"]
    settings = client.app.state.settings
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    sync = sessionmaker(bind=create_engine(url))()
    finding = MockFinding(
        title="B2B Payments Webinar EU partnership",
        source_url=f"https://t.test/{uuid4()}",
        description="webinar payments partnership",
        organizer="Org",
        region="EU",
    )
    eid, _ = ingest_finding(
        sync,
        organization_id=DEV_ORGANIZATION_ID,
        campaign_id=UUID(cid),
        source_id=uuid4(),
        finding=finding,
    )
    sync.commit()
    sync.close()

    await client.post(f"/events/{eid}/rescore")
    detail = await client.get(f"/events/{eid}")
    assert detail.status_code == 200
    body = detail.json()
    assert "audience" in body
    aud = body["audience"]
    assert aud["state"] in ("ready", "empty")
    if aud["state"] == "ready":
        assert len(aud["hypotheses"]) >= 1
        h = aud["hypotheses"][0]
        assert h["segment_name"]
        assert h["evidence"]
        assert h["fit_type"] in ("customer", "partner", "referral")

    refresh = await client.post(f"/events/{eid}/audience/refresh")
    assert refresh.status_code == 200