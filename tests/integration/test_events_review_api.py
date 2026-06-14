from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

PAYLOAD = {
    "name": "Events Review Campaign",
    "description": "US-005",
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
        "company_size": "50-200",
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
async def test_event_list_detail_provenance_and_merge(client):
    create = await client.post("/campaigns", json=PAYLOAD)
    assert create.status_code == 201
    cid = create.json()["id"]
    job_id = str(uuid4())

    settings = client.app.state.settings
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    sync = sessionmaker(bind=create_engine(url))()
    try:
        org = DEV_ORGANIZATION_ID
        camp = UUID(cid)
        src_a = uuid4()
        src_b = uuid4()
        title = "B2B Payments Webinar EU"
        f1 = MockFinding(
            title=title,
            source_url=f"https://source-a.test/events/{uuid4()}",
            description="webinar",
            organizer="Org A",
            region="EU",
        )
        f2 = MockFinding(
            title=title,
            source_url=f"https://source-b.test/events/{uuid4()}",
            description="webinar duplicate path",
            organizer="Org B",
            region="EU",
        )
        eid1, a1 = ingest_finding(
            sync,
            organization_id=org,
            campaign_id=camp,
            source_id=src_a,
            finding=f1,
            discovery_job_id=job_id,
        )
        eid2, a2 = ingest_finding(
            sync,
            organization_id=org,
            campaign_id=camp,
            source_id=src_b,
            finding=f2,
            discovery_job_id=job_id,
        )
        sync.commit()
        assert a1 == "created"
        assert a2 == "merged"
        assert eid1 == eid2
    finally:
        sync.close()

    listed = await client.get(f"/campaigns/{cid}/events", params={"include_score": "false"})
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["observation_count"] >= 2
    assert body[0]["confidence_summary"] in ("high", "medium", "merged")

    filtered = await client.get(f"/campaigns/{cid}/events", params={"q": "Payments", "include_score": "false"})
    assert len(filtered.json()) == 1

    detail = await client.get(f"/events/{eid1}")
    assert detail.status_code == 200
    d = detail.json()
    assert len(d["observations"]) >= 2
    assert d["provenance"]["observation_count"] >= 2
    assert d["provenance"]["field_confidence"]