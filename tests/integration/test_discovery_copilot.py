"""US-037 discovery copilot API and handoff."""

import pytest

ADMIN = {"X-Actor-Role": "admin", "Content-Type": "application/json"}


@pytest.mark.asyncio
async def test_copilot_respond_structured(client):
    camp = await client.post(
        "/campaigns",
        json={"name": "US037 Copilot", "target_industry": "Tech", "positive_keywords": ["summit"]},
    )
    cid = camp.json()["id"]
    resp = await client.post(
        f"/campaigns/{cid}/discovery-copilot:respond",
        headers=ADMIN,
        json={"question": "What livestream discovery scope fits this tech summit campaign?"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["structured"]["claims"]
    assert "confidence" in body["structured"]
    assert body["structured"]["risk_flags"] is not None


@pytest.mark.asyncio
async def test_accept_projects_query_expansion_no_autorun(client):
    src = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "US037 Copilot Source",
            "domain": "us037-copilot.example.com",
            "connector_type": "rss",
            "authentication_mode": "none",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "feed", "valid": True},
        },
    )
    src_id = src.json()["id"]
    camp = await client.post(
        "/campaigns",
        json={"name": "US037 Handoff", "target_industry": "Tech", "positive_keywords": ["summit"]},
    )
    cid = camp.json()["id"]
    await client.put(f"/campaigns/{cid}/sources", json={"source_ids": [src_id]})

    resp = await client.post(
        f"/campaigns/{cid}/discovery-copilot:respond",
        headers=ADMIN,
        json={"question": "How should we frame discovery queries for upcoming livestreams?"},
    )
    rid = resp.json()["id"]

    accept = await client.post(
        f"/campaigns/{cid}/discovery-copilot:accept",
        headers=ADMIN,
        json={"response_id": rid},
    )
    assert accept.status_code == 200
    assert accept.json()["expansion_status"] in ("pending_review", "draft")

    blocked = await client.post(
        f"/campaigns/{cid}/discovery-jobs",
        headers=ADMIN,
        json={"use_expansion": True},
    )
    assert blocked.status_code == 409