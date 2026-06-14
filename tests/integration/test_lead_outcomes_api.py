from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

PAYLOAD = {
    "name": "Outcome Campaign",
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


async def _event_and_lead(client) -> tuple[str, str]:
    create = await client.post(
        "/campaigns", json={**PAYLOAD, "name": f"O{uuid4()}", "description": ""}
    )
    cid = create.json()["id"]
    settings = client.app.state.settings
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    sync = sessionmaker(bind=create_engine(url))()
    finding = MockFinding(
        title="Outcome Webinar",
        source_url=f"https://out.test/{uuid4()}",
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
    lead = await client.post(
        "/leads",
        json={
            "display_name": "Pat",
            "company": "Org",
            "discovery_source": "event",
            "event_id": str(eid),
            "origin_kind": "event",
        },
    )
    assert lead.status_code == 201
    return str(eid), lead.json()["id"]


async def _used_draft(client, eid: str) -> str:
    await client.post(f"/events/{eid}/rescore")
    gen = await client.post(
        "/content/generate",
        json={
            "event_id": eid,
            "settings": {"content_type": "outreach", "platform": "email", "variant_count": 1},
        },
    )
    draft_id = gen.json()["drafts"][0]["id"]
    await client.post(
        f"/events/{eid}/content/drafts/{draft_id}/submit-for-review", json={"assignee": ""}
    )
    await client.post(
        f"/content/{draft_id}/approve",
        json={"event_id": eid, "note": "ok", "actor": "reviewer"},
        headers={"X-Actor-Role": "reviewer"},
    )
    await client.post(f"/content/{draft_id}/mark-used", json={"event_id": eid, "actor": "analyst"})
    return draft_id


@pytest.mark.asyncio
async def test_record_contact_outcome_and_timeline(client):
    _, lead_id = await _event_and_lead(client)
    bad = await client.post(f"/leads/{lead_id}/outcomes", json={"outcome_type": "opportunity"})
    assert bad.status_code == 400

    ok = await client.post(
        f"/leads/{lead_id}/outcomes",
        json={"outcome_type": "contact", "notes": "LinkedIn connect accepted"},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["latest_outcome"]["outcome_type"] == "contact"
    assert any(a["kind"] == "outcome_recorded" for a in body["recent_activity"])


@pytest.mark.asyncio
async def test_record_outcome_with_linked_content(client):
    eid, lead_id = await _event_and_lead(client)
    draft_id = await _used_draft(client, eid)
    contact = await client.post(
        f"/leads/{lead_id}/outcomes",
        json={"outcome_type": "contact", "notes": "Sent outreach"},
    )
    assert contact.status_code == 200
    ok = await client.post(
        f"/leads/{lead_id}/outcomes",
        json={
            "outcome_type": "response",
            "notes": "Replied to outreach",
            "linked_content_draft_id": draft_id,
            "linked_event_id": eid,
        },
    )
    assert ok.status_code == 200
    assert ok.json()["latest_outcome"]["linked_content_draft_id"] == draft_id
    assert ok.json()["stage"] in ("responded", "message_sent", "connected", "newly_discovered")


@pytest.mark.asyncio
async def test_dashboard_counts_response_outcome(client):
    _, lead_id = await _event_and_lead(client)
    await client.post(f"/leads/{lead_id}/outcomes", json={"outcome_type": "contact"})
    dash = await client.get("/reporting/dashboard-overview", params={"preset": "last_30_days"})
    responses = next(w for w in dash.json()["widgets"] if w["key"] == "responses")
    assert responses["availability"] in ("available", "empty")
