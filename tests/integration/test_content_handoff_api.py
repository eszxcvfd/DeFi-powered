from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

PAYLOAD = {
    "name": "Handoff Campaign",
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


async def _approved_draft(client):
    create = await client.post("/campaigns", json={**PAYLOAD, "name": f"H{uuid4()}", "description": ""})
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
        json={"event_id": str(eid), "settings": {"content_type": "outreach", "platform": "email", "variant_count": 1}},
    )
    draft_id = gen.json()["drafts"][0]["id"]
    await client.post(f"/events/{eid}/content/drafts/{draft_id}/submit-for-review", json={"assignee": ""})
    await client.post(
        f"/content/{draft_id}/approve",
        json={"event_id": str(eid), "note": "ok", "actor": "reviewer"},
        headers={"X-Actor-Role": "reviewer"},
    )
    return eid, draft_id


@pytest.mark.asyncio
async def test_export_and_mark_used(client):
    eid, draft_id = await _approved_draft(client)

    bad = await client.get(f"/content/{draft_id}/export", params={"event_id": str(eid), "format": "pdf"})
    assert bad.status_code == 400

    exp = await client.get(f"/content/{draft_id}/export", params={"event_id": str(eid), "format": "markdown"})
    assert exp.status_code == 200
    assert "text/markdown" in exp.headers.get("content-type", "")
    assert "internal only" not in exp.text

    used = await client.post(
        f"/content/{draft_id}/mark-used",
        json={"event_id": str(eid), "actor": "analyst"},
    )
    assert used.status_code == 200
    body = used.json()
    assert body["usage_status"] == "used"
    assert any(h["action"] == "export" for h in body["handoff_history"])
    assert any(h["action"] == "mark_used" for h in body["handoff_history"])

    again = await client.post(
        f"/content/{draft_id}/mark-used",
        json={"event_id": str(eid), "actor": "analyst"},
    )
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_unapproved_export_blocked(client):
    create = await client.post("/campaigns", json={**PAYLOAD, "name": f"U{uuid4()}", "description": ""})
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
        json={"event_id": str(eid), "settings": {"content_type": "outreach", "platform": "email", "variant_count": 1}},
    )
    draft_id = gen.json()["drafts"][0]["id"]
    blocked = await client.get(f"/content/{draft_id}/export", params={"event_id": str(eid)})
    assert blocked.status_code == 400