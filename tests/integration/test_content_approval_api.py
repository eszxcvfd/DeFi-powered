from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

PAYLOAD = {
    "name": "Approval Campaign",
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
async def test_approve_reject_flow(client):
    create = await client.post("/campaigns", json={**PAYLOAD, "name": "Apr", "description": ""})
    cid = create.json()["id"]
    settings = client.app.state.settings
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    sync = sessionmaker(bind=create_engine(url))()
    finding = MockFinding(
        title="B2B Payments Webinar EU partnership",
        source_url=f"https://t.test/{uuid4()}",
        description="webinar",
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
    gen = await client.post(
        "/content/generate",
        json={
            "event_id": str(eid),
            "settings": {"content_type": "outreach", "platform": "email", "variant_count": 1},
        },
    )
    draft_id = gen.json()["drafts"][0]["id"]

    sub = await client.post(
        f"/events/{eid}/content/drafts/{draft_id}/submit-for-review", json={"assignee": ""}
    )
    assert sub.status_code == 200
    assert sub.json()["review_status"] == "in_review"

    bad = await client.post(
        f"/content/{draft_id}/approve",
        json={"event_id": str(eid), "note": ""},
        headers={"X-Actor-Role": "analyst"},
    )
    assert bad.status_code == 403

    ok = await client.post(
        f"/content/{draft_id}/approve",
        json={"event_id": str(eid), "note": "LGTM", "actor": "reviewer"},
        headers={"X-Actor-Role": "reviewer"},
    )
    assert ok.status_code == 200
    assert ok.json()["review_status"] == "approved"
    assert ok.json()["ready_for_use"] is True
    assert len(ok.json()["review_history"]) >= 2
