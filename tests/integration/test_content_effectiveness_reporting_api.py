from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

PAYLOAD = {
    "name": "CE Campaign",
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


async def _used_draft_with_tone(client, tone: str = "professional"):
    create = await client.post(
        "/campaigns", json={**PAYLOAD, "name": f"CE{uuid4()}", "description": ""}
    )
    cid = create.json()["id"]
    settings = client.app.state.settings
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    sync = sessionmaker(bind=create_engine(url))()
    finding = MockFinding(
        title="CE Webinar",
        source_url=f"https://ce.test/{uuid4()}",
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
            "settings": {
                "content_type": "outreach",
                "platform": "email",
                "tone": tone,
                "variant_count": 1,
            },
        },
    )
    draft_id = gen.json()["drafts"][0]["id"]
    await client.post(
        f"/events/{eid}/content/drafts/{draft_id}/submit-for-review", json={"assignee": ""}
    )
    await client.post(
        f"/content/{draft_id}/approve",
        json={"event_id": str(eid), "note": "ok", "actor": "reviewer"},
        headers={"X-Actor-Role": "reviewer"},
    )
    await client.post(
        f"/content/{draft_id}/mark-used",
        json={"event_id": str(eid), "actor": "analyst"},
    )
    return eid, draft_id, cid


@pytest.mark.asyncio
async def test_content_effectiveness_invalid_grouping(client):
    r = await client.get(
        "/reports/content-effectiveness", params={"preset": "last_7_days", "grouping": "campaign"}
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_content_effectiveness_tone_grouping_with_used_content(client):
    eid, draft_id, _cid = await _used_draft_with_tone(client, "casual")
    lead = await client.post(
        "/leads",
        json={
            "display_name": "CE Lead",
            "company": "Co",
            "discovery_source": "event",
            "event_id": eid,
            "origin_kind": "event",
        },
    )
    assert lead.status_code == 201
    lid = lead.json()["id"]
    await client.post(
        f"/leads/{lid}/outcomes",
        json={
            "outcome_type": "contact",
            "linked_content_draft_id": draft_id,
            "linked_event_id": eid,
        },
    )

    for grouping in ("content_type", "tone", "template"):
        r = await client.get(
            "/reports/content-effectiveness",
            params={"preset": "last_30_days", "grouping": grouping},
        )
        assert r.status_code == 200, grouping
        body = r.json()
        assert body["grouping"] == grouping
        assert body["correlation_note"]
        if grouping == "tone":
            assert any(row["group_key"] == "casual" for row in body["rows"])
            casual = next(row for row in body["rows"] if row["group_key"] == "casual")
            assert casual["metrics"]["content_used"] >= 1
            assert casual["metrics"]["outcomes_linked"] >= 1
