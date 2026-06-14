from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

PAYLOAD = {
    "name": "Funnel Campaign",
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
async def test_funnel_invalid_range(client):
    r = await client.get("/reports/funnel", params={"start": "2026-06-10", "end": "2026-06-01"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_funnel_ordered_steps_empty_cohort(client):
    r = await client.get("/reports/funnel", params={"preset": "last_7_days"})
    assert r.status_code == 200
    body = r.json()
    assert body["cohort"]["rule"]
    keys = [s["key"] for s in body["steps"]]
    assert keys == ["event", "lead", "contact", "response", "meeting", "opportunity"]


@pytest.mark.asyncio
async def test_funnel_event_lead_and_outcome_counts(client):
    create = await client.post(
        "/campaigns", json={**PAYLOAD, "name": f"F{uuid4()}", "description": ""}
    )
    cid = create.json()["id"]
    settings = client.app.state.settings
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    sync = sessionmaker(bind=create_engine(url))()
    finding = MockFinding(
        title="Funnel Webinar",
        source_url=f"https://fun.test/{uuid4()}",
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

    lead = await client.post(
        "/leads",
        json={
            "display_name": "Funnel Lead",
            "company": "Co",
            "discovery_source": "event",
            "event_id": (await client.get(f"/campaigns/{cid}/events")).json()[0]["id"],
            "origin_kind": "event",
        },
    )
    assert lead.status_code == 201
    lead_id = lead.json()["id"]
    await client.post(f"/leads/{lead_id}/outcomes", json={"outcome_type": "contact"})

    manual = await client.post(
        "/leads",
        json={
            "display_name": "Manual Only",
            "company": "Co",
            "discovery_source": "referral",
            "origin_kind": "manual",
            "manual_entry_note": "Conference badge",
        },
    )
    assert manual.status_code == 201

    r = await client.get("/reports/funnel", params={"preset": "last_30_days"})
    assert r.status_code == 200
    steps = {s["key"]: s["count"] for s in r.json()["steps"]}
    assert steps["event"] >= 1
    assert steps["lead"] >= 2
    assert steps["contact"] >= 1
    assert r.json()["unattributed"] is not None
    assert r.json()["unattributed"]["manual_leads_in_cohort"] >= 1
