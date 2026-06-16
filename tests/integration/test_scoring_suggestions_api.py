"""US-039 scoring suggestion API."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

ADMIN = {"X-Actor-Role": "admin", "Content-Type": "application/json"}

CAMPAIGN_PAYLOAD = {
    "target_industry": "Fintech",
    "product_or_service_focus": "Payments",
    "market_regions": ["EU"],
    "languages": ["en"],
    "timezone": "UTC",
    "positive_keywords": ["webinar", "payments", "partnership"],
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


async def _ingest_event_with_audience(client, campaign_id: str, *, suffix: str) -> str | None:
    settings = client.app.state.settings
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    sync = sessionmaker(bind=create_engine(url))()
    finding = MockFinding(
        title=f"Cross-border payments live webinar EU {suffix}",
        source_url=f"https://t.test/{uuid4()}",
        description="Partnership-focused session on cross-border payments",
        organizer="Payments Org",
        region="EU",
    )
    eid, _ = ingest_finding(
        sync,
        organization_id=DEV_ORGANIZATION_ID,
        campaign_id=UUID(campaign_id),
        source_id=uuid4(),
        finding=finding,
    )
    sync.commit()
    sync.close()

    await client.post(f"/events/{eid}/rescore", headers=ADMIN)
    await client.post(f"/events/{eid}/audience/refresh", headers=ADMIN)
    detail = await client.get(f"/events/{eid}", headers=ADMIN)
    hyps = detail.json()["audience"]["hypotheses"]
    if not hyps:
        return None
    hid = hyps[0]["id"]
    await client.put(
        f"/audience-hypotheses/{hid}/feedback",
        headers=ADMIN,
        json={"state": "incorrect", "reason_code": "wrong_audience_fit"},
    )
    return hid


async def _seed_audience_incorrect_feedback(client, *, events: int = 3) -> tuple[str, list[str]]:
    create = await client.post(
        "/campaigns",
        json={**CAMPAIGN_PAYLOAD, "name": f"US039 Suggest {uuid4().hex[:8]}"},
    )
    assert create.status_code == 201
    cid = create.json()["id"]
    hyp_ids: list[str] = []
    for i in range(events):
        hid = await _ingest_event_with_audience(client, cid, suffix=str(i))
        if hid:
            hyp_ids.append(hid)
    return cid, hyp_ids


async def _seed_copilot_not_helpful(client, *, count: int = 2) -> str:
    create = await client.post(
        "/campaigns",
        json={**CAMPAIGN_PAYLOAD, "name": f"US039 Copilot {uuid4().hex[:8]}"},
    )
    cid = create.json()["id"]
    for _ in range(count):
        resp = await client.post(
            f"/campaigns/{cid}/discovery-copilot:respond",
            headers=ADMIN,
            json={"question": "What discovery scope fits this payments webinar campaign best?"},
        )
        assert resp.status_code == 201
        rid = resp.json()["id"]
        await client.put(
            f"/discovery-copilot-responses/{rid}/feedback",
            headers=ADMIN,
            json={"state": "not_helpful", "reason_code": "weak_usefulness"},
        )
    return cid


@pytest.mark.asyncio
async def test_generate_requires_feedback(client):
    camp = await client.post(
        "/campaigns",
        json={**CAMPAIGN_PAYLOAD, "name": "US039 Empty"},
    )
    cid = camp.json()["id"]
    resp = await client.post(f"/campaigns/{cid}/scoring-suggestions:generate", headers=ADMIN)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_updates_weights_reject_does_not(client):
    cid, hyp_ids = await _seed_audience_incorrect_feedback(client, events=4)
    assert len(hyp_ids) >= 2, "expected audience hypotheses for scoring suggestion seed"

    before = await client.get(f"/campaigns/{cid}", headers=ADMIN)
    weights_before = dict(before.json()["scoring_weights"])

    gen = await client.post(f"/campaigns/{cid}/scoring-suggestions:generate", headers=ADMIN)
    assert gen.status_code == 201
    sid = gen.json()["id"]
    assert gen.json()["status"] == "pending_review"
    assert gen.json()["deltas"]

    mid = await client.get(f"/campaigns/{cid}", headers=ADMIN)
    assert mid.json()["scoring_weights"] == weights_before

    gen2 = await client.post(f"/campaigns/{cid}/scoring-suggestions:generate", headers=ADMIN)
    assert gen2.status_code == 201
    rej_id = gen2.json()["id"]
    reject = await client.post(
        f"/campaigns/{cid}/scoring-suggestions/{rej_id}:reject",
        headers=ADMIN,
        json={"review_note": "not now"},
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"

    after_reject = await client.get(f"/campaigns/{cid}", headers=ADMIN)
    assert after_reject.json()["scoring_weights"] == weights_before

    approve = await client.post(
        f"/campaigns/{cid}/scoring-suggestions/{sid}:approve",
        headers=ADMIN,
    )
    assert approve.status_code == 200
    assert approve.json()["suggestion"]["status"] == "approved"
    assert approve.json()["suggestion"]["weight_snapshot_id"]

    after = await client.get(f"/campaigns/{cid}", headers=ADMIN)
    assert after.json()["scoring_weights"] != weights_before

    list_resp = await client.get(f"/campaigns/{cid}/scoring-suggestions", headers=ADMIN)
    assert len(list_resp.json()) >= 2


@pytest.mark.asyncio
async def test_generate_from_copilot_feedback(client):
    cid = await _seed_copilot_not_helpful(client, count=2)
    gen = await client.post(f"/campaigns/{cid}/scoring-suggestions:generate", headers=ADMIN)
    assert gen.status_code == 201
    body = gen.json()
    assert body["status"] == "pending_review"
    assert any(s["kind"] == "discovery_copilot_feedback" for s in body["signals"])