from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

PAYLOAD = {
    "name": "Lead Campaign",
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


async def _event_id(client) -> UUID:
    create = await client.post(
        "/campaigns", json={**PAYLOAD, "name": f"L{uuid4()}", "description": ""}
    )
    cid = create.json()["id"]
    settings = client.app.state.settings
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    sync = sessionmaker(bind=create_engine(url))()
    finding = MockFinding(
        title="Lead Webinar EU",
        source_url=f"https://lead.test/{uuid4()}",
        description="webinar",
        organizer="Acme Org",
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
    return eid


@pytest.mark.asyncio
async def test_create_list_patch_lead_from_event(client):
    eid = await _event_id(client)
    detail = await client.get(f"/events/{eid}")
    assert detail.json()["leads"]["has_linked_lead"] is False

    create = await client.post(
        "/leads",
        json={
            "display_name": "Jordan Lee",
            "company": "Acme Org",
            "discovery_source": "event",
            "event_id": str(eid),
            "public_url": "https://linkedin.com/in/jordan",
            "origin_kind": "event",
        },
    )
    assert create.status_code == 201
    lead_id = create.json()["id"]
    assert create.json()["stage"] == "newly_discovered"
    assert len(create.json()["recent_activity"]) >= 1

    detail2 = await client.get(f"/events/{eid}")
    assert detail2.json()["leads"]["has_linked_lead"] is True

    listed = await client.get("/leads")
    assert any(row["id"] == lead_id for row in listed.json())

    patch = await client.patch(
        f"/leads/{lead_id}",
        json={"stage": "watched", "activity_note": "Called organizer"},
    )
    assert patch.status_code == 200
    assert patch.json()["stage"] == "watched"
    kinds = [a["kind"] for a in patch.json()["recent_activity"]]
    assert "stage_changed" in kinds
    assert "note" in kinds


@pytest.mark.asyncio
async def test_duplicate_lead_blocked(client):
    eid = await _event_id(client)
    body = {
        "display_name": "Sam Park",
        "company": "Beta Inc",
        "discovery_source": "event",
        "event_id": str(eid),
        "public_url": "https://example.com/sam",
        "origin_kind": "event",
    }
    first = await client.post("/leads", json=body)
    assert first.status_code == 201
    second = await client.post("/leads", json=body)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_same_organizer_two_events_allowed(client):
    eid1 = await _event_id(client)
    eid2 = await _event_id(client)
    body = {
        "display_name": "Shared Organizer",
        "company": "Shared Organizer",
        "discovery_source": "event",
        "origin_kind": "event",
    }
    first = await client.post(
        "/leads",
        json={**body, "event_id": str(eid1), "public_url": f"https://a.test/{uuid4()}"},
    )
    second = await client.post(
        "/leads",
        json={**body, "event_id": str(eid2), "public_url": f"https://b.test/{uuid4()}"},
    )
    assert first.status_code == 201
    assert second.status_code == 201


@pytest.mark.asyncio
async def test_manual_lead_requires_note(client):
    bad = await client.post(
        "/leads",
        json={"display_name": "Manual Only", "origin_kind": "manual"},
    )
    assert bad.status_code == 400
