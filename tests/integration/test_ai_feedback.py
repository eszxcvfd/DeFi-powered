"""US-038 AI feedback API."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

ADMIN = {"X-Actor-Role": "admin", "Content-Type": "application/json"}
OTHER_ORG = "00000000-0000-4000-8000-000000000099"


@pytest.mark.asyncio
async def test_copilot_feedback_upsert_and_revision(client):
    camp = await client.post(
        "/campaigns",
        json={"name": "US038 FB", "target_industry": "Tech", "positive_keywords": ["summit"]},
    )
    cid = camp.json()["id"]
    resp = await client.post(
        f"/campaigns/{cid}/discovery-copilot:respond",
        headers=ADMIN,
        json={"question": "What discovery scope fits this tech summit campaign best?"},
    )
    rid = resp.json()["id"]
    before = resp.json()["structured"]["claims"][0]["text"]

    bad = await client.put(
        f"/discovery-copilot-responses/{rid}/feedback",
        headers=ADMIN,
        json={"state": "not_helpful"},
    )
    assert bad.status_code == 400

    ok = await client.put(
        f"/discovery-copilot-responses/{rid}/feedback",
        headers=ADMIN,
        json={"state": "not_helpful", "reason_code": "weak_usefulness"},
    )
    assert ok.status_code == 200
    assert ok.json()["state"] == "not_helpful"

    list_resp = await client.get(
        f"/campaigns/{cid}/discovery-copilot/responses",
        headers=ADMIN,
    )
    assert list_resp.json()[0]["viewer_feedback"]["state"] == "not_helpful"

    revise = await client.put(
        f"/discovery-copilot-responses/{rid}/feedback",
        headers=ADMIN,
        json={"state": "helpful"},
    )
    assert revise.json()["state"] == "helpful"

    again = await client.get(f"/campaigns/{cid}/discovery-copilot/responses", headers=ADMIN)
    assert again.json()[0]["viewer_feedback"]["state"] == "helpful"
    assert again.json()[0]["structured"]["claims"][0]["text"] == before


@pytest.mark.asyncio
async def test_audience_feedback_on_event_detail(client):
    create = await client.post(
        "/campaigns",
        json={
            "name": "US038 Aud",
            "target_industry": "Fintech",
            "positive_keywords": ["webinar"],
        },
    )
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

    await client.post(f"/events/{eid}/rescore", headers=ADMIN)
    detail = await client.get(f"/events/{eid}", headers=ADMIN)
    hyps = detail.json()["audience"]["hypotheses"]
    if not hyps:
        pytest.skip("no audience hypotheses in fixture")
    hid = hyps[0]["id"]
    reason_before = hyps[0]["reason"]

    put = await client.put(
        f"/audience-hypotheses/{hid}/feedback",
        headers=ADMIN,
        json={"state": "incorrect", "reason_code": "wrong_audience_fit"},
    )
    assert put.status_code == 200

    detail2 = await client.get(f"/events/{eid}", headers=ADMIN)
    assert detail2.json()["audience"]["hypotheses"][0]["viewer_feedback"]["state"] == "incorrect"
    assert detail2.json()["audience"]["hypotheses"][0]["reason"] == reason_before


@pytest.mark.asyncio
async def test_cross_tenant_copilot_feedback_denied(client):
    camp = await client.post(
        "/campaigns",
        json={"name": "US038 ISO", "target_industry": "Tech", "positive_keywords": ["x"]},
    )
    cid = camp.json()["id"]
    resp = await client.post(
        f"/campaigns/{cid}/discovery-copilot:respond",
        headers=ADMIN,
        json={"question": "How should we frame discovery for this campaign scope?"},
    )
    rid = resp.json()["id"]
    other = await client.put(
        f"/discovery-copilot-responses/{rid}/feedback",
        headers={"X-Actor-Role": "admin", "X-Organization-Id": OTHER_ORG, "Content-Type": "application/json"},
        json={"state": "helpful"},
    )
    assert other.status_code == 400