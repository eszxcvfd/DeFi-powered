from uuid import UUID, uuid4

import pytest

from livelead.domain.events.normalize import MockFinding, build_canonical_from_finding
from livelead.infrastructure.db.repositories.events import EventRepository
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

PAYLOAD = {
    "name": "Scoring Campaign",
    "description": "US-006",
    "target_industry": "Fintech",
    "product_or_service_focus": "Payments",
    "market_regions": ["EU"],
    "languages": ["en"],
    "timezone": "UTC",
    "date_range": {"start": "2026-07-01", "end": "2026-12-31"},
    "positive_keywords": ["webinar", "payments"],
    "exclude_keywords": [],
    "icp": {
        "industry": "Payments",
        "organization_type": "SaaS",
        "company_size": "50-200",
        "role_or_title_targets": [],
        "country_or_region": "EU",
        "pain_points": [],
        "use_cases": [],
        "positive_keywords": ["B2B"],
        "excluded_keywords": [],
    },
    "scoring_weights": {"topic_relevance": 0.4, "icp_match": 0.3},
}


@pytest.mark.asyncio
async def test_events_list_detail_rescore(client):
    create = await client.post("/campaigns", json=PAYLOAD)
    assert create.status_code == 201
    cid = create.json()["id"]

    factory = client.app.state.session_factory
    async with factory() as session:
        repo = EventRepository(session)
        finding = MockFinding(
            title="B2B Payments Webinar EU",
            source_url=f"https://events.test/{uuid4()}",
            description="webinar payments EU",
            organizer="Org",
            region="EU",
        )
        event, obs = build_canonical_from_finding(
            organization_id=DEV_ORGANIZATION_ID,
            campaign_id=UUID(cid),
            source_id=uuid4(),
            finding=finding,
        )
        await repo.add_event_with_observation(event, obs)
        await session.commit()
        eid = str(event.id)

    listed = await client.get(f"/campaigns/{cid}/events")
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) >= 1
    row = next(i for i in items if i["id"] == eid)
    assert row["score"]["score_state"] == "missing"

    score_first = await client.post(f"/events/{eid}/rescore")
    assert score_first.status_code == 200
    body = score_first.json()
    assert body["score_state"] == "ready"
    assert body["score"]["total_score"] >= 0
    assert body["score"]["scoring_version"]
    assert len(body["score"]["components"]) >= 1

    listed2 = await client.get(f"/campaigns/{cid}/events")
    row2 = next(i for i in listed2.json() if i["id"] == eid)
    assert row2["score"]["score_state"] == "ready"
    assert row2["score"]["priority_level"]

    rescore = await client.post(f"/events/{eid}/rescore")
    assert rescore.status_code == 200
    assert rescore.json()["score"]["calculated_at"]
