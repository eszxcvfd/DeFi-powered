"""US-036 query expansion API and discovery linkage."""

import pytest

ADMIN = {"X-Actor-Role": "admin"}


async def _pin_runnable_source(client):
    src = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "US036 Block Source",
            "domain": "us036-block.example.com",
            "connector_type": "rss",
            "authentication_mode": "none",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "feed", "valid": True},
        },
    )
    return src.json()["id"]


@pytest.mark.asyncio
async def test_generate_blocks_discovery_until_approved(client):
    src_id = await _pin_runnable_source(client)
    camp = await client.post(
        "/campaigns",
        json={
            "name": "US036 Block",
            "target_industry": "Tech",
            "positive_keywords": ["artificial intelligence summit"],
        },
    )
    cid = camp.json()["id"]
    await client.put(f"/campaigns/{cid}/sources", json={"source_ids": [src_id]})

    gen = await client.post(f"/campaigns/{cid}/query-expansions:generate", headers=ADMIN)
    assert gen.status_code == 201
    body = gen.json()
    assert body["requires_review"] is True
    assert body["status"] in ("pending_review", "draft")

    blocked = await client.post(
        f"/campaigns/{cid}/discovery-jobs",
        headers={**ADMIN, "Content-Type": "application/json"},
        json={"use_expansion": True},
    )
    assert blocked.status_code == 409
    assert "review" in blocked.text.lower()

    raw_ok = await client.post(
        f"/campaigns/{cid}/discovery-jobs",
        headers={**ADMIN, "Content-Type": "application/json"},
        json={"use_expansion": False},
    )
    assert raw_ok.status_code in (201, 503)


@pytest.mark.asyncio
async def test_approve_then_discovery_uses_snapshot(client):
    src = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "US036 Source",
            "domain": "us036-qe.example.com",
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
        json={"name": "US036 Approve", "target_industry": "Tech", "positive_keywords": ["summit"]},
    )
    cid = camp.json()["id"]
    await client.put(f"/campaigns/{cid}/sources", json={"source_ids": [src_id]})

    gen = await client.post(f"/campaigns/{cid}/query-expansions:generate", headers=ADMIN)
    assert gen.status_code == 201
    expansion = gen.json()
    flat: list[dict] = []
    for group in expansion["grouped_variants"].values():
        flat.extend(group)

    appr = await client.patch(
        f"/campaigns/{cid}/query-expansions",
        headers={**ADMIN, "Content-Type": "application/json"},
        json={"variants": flat, "approve": True},
    )
    assert appr.status_code == 200
    assert appr.json()["status"] == "approved"

    job = await client.post(
        f"/campaigns/{cid}/discovery-jobs",
        headers={**ADMIN, "Content-Type": "application/json"},
        json={"use_expansion": True},
    )
    assert job.status_code in (201, 503)
    if job.status_code == 201:
        snap = job.json()["criteria_snapshot"]
        assert snap.get("query_expansion", {}).get("expansion_set_id")
        assert len(snap.get("positive_keywords", [])) >= 1