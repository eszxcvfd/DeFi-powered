from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

PAYLOAD = {
    "name": "Reminder Campaign",
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


async def _lead_with_follow_up(client, due: date) -> str:
    create = await client.post(
        "/campaigns", json={**PAYLOAD, "name": f"R{uuid4()}", "description": ""}
    )
    cid = create.json()["id"]
    settings = client.app.state.settings
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    sync = sessionmaker(bind=create_engine(url))()
    finding = MockFinding(
        title="Reminder Webinar",
        source_url=f"https://rem.test/{uuid4()}",
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
            "display_name": f"Rem {uuid4()}",
            "company": "Co",
            "discovery_source": "event",
            "event_id": str(eid),
            "origin_kind": "event",
            "follow_up_date": due.isoformat(),
        },
    )
    assert lead.status_code == 201
    return lead.json()["id"]


@pytest.mark.asyncio
async def test_reminder_queue_and_complete(client):
    today = date.today()
    lead_id = await _lead_with_follow_up(client, today)

    detail = await client.get(f"/leads/{lead_id}")
    assert detail.json()["reminder"]["has_reminder"] is True
    assert detail.json()["reminder"]["state"] in ("due", "scheduled", "overdue")

    queue = await client.get("/reminders/queue")
    assert queue.status_code == 200
    if queue.json():
        ids = [row["lead_id"] for row in queue.json()]
        assert lead_id in ids
        rem_id = queue.json()[0]["id"]
        done = await client.post(f"/reminders/{rem_id}/complete", json={"note": "done"})
        assert done.status_code == 200
        assert done.json()["state"] == "completed"

    alerts = await client.get("/reminders/alerts")
    assert alerts.status_code == 200


@pytest.mark.asyncio
async def test_reschedule_reminder(client):
    lead_id = await _lead_with_follow_up(client, date.today() + timedelta(days=7))
    patch = await client.patch(
        f"/leads/{lead_id}",
        json={"follow_up_date": (date.today() + timedelta(days=14)).isoformat()},
    )
    assert patch.status_code == 200
    assert patch.json()["reminder"]["has_reminder"] is True
