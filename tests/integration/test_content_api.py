from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

PAYLOAD = {
    "name": "Content Campaign",
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
async def test_content_generate_and_edit(client):
    create = await client.post("/campaigns", json={**PAYLOAD, "name": "Cnt", "description": ""})
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
    await client.post(f"/events/{eid}/engagement-plans")

    ctx = await client.get(f"/events/{eid}/content/context")
    assert ctx.status_code == 200

    gen = await client.post(
        "/content/generate",
        json={
            "event_id": str(eid),
            "settings": {
                "content_type": "outreach",
                "platform": "email",
                "variant_count": 2,
                "cta": "Learn more",
            },
        },
    )
    assert gen.status_code == 200
    body = gen.json()
    assert len(body["drafts"]) == 2
    draft_id = body["drafts"][0]["id"]

    detail = await client.get(f"/events/{eid}")
    assert len(detail.json()["generated_content"]) == 2

    patch = await client.patch(
        f"/events/{eid}/content/drafts/{draft_id}",
        json={
            "body_text": "Edited draft for Payments Webinar EU.\n\nCTA: Learn more",
            "editor": "analyst",
        },
    )
    assert patch.status_code == 200
    assert patch.json()["last_editor"] == "analyst"
