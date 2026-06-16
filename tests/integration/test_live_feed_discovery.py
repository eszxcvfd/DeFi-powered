"""US-032: fixture-backed live feed discovery and canonical event ingestion."""

import pytest

from livelead.application.discovery.service import run_discovery_job
from livelead.infrastructure.connectors import http_fetch

ADMIN = {"X-Actor-Role": "admin"}

RSS_FIXTURE = b"""<?xml version="1.0"?>
<rss><channel>
<item><title>US032 Canonical Webinar Alpha</title><link>https://live-feed-fixture.test/e/a</link>
<description>payments webinar EU</description></item>
</channel></rss>"""


@pytest.fixture
def stub_live_feed(monkeypatch):
    from livelead.infrastructure.connectors import runner as connector_runner

    def fake_fetch(url: str, **kwargs):
        return http_fetch.FetchResult(200, RSS_FIXTURE, "application/rss+xml", None)

    monkeypatch.setattr(connector_runner, "fetch_url", fake_fetch)


@pytest.mark.asyncio
async def test_live_feed_discovery_persists_canonical_events(client, stub_live_feed, monkeypatch):
    monkeypatch.setenv("LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS", "false")

    create_src = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "US032 Live RSS",
            "domain": "live-feed-fixture.test",
            "connector_type": "rss",
            "authentication_mode": "none",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "feed", "valid": True},
        },
    )
    src_id = create_src.json()["id"]
    await client.patch(
        f"/admin/connectors/{src_id}",
        headers=ADMIN,
        json={
            "rate_limit_json": {
                "feed_url": "https://live-feed-fixture.test/rss.xml",
            },
        },
    )
    camp = await client.post(
        "/campaigns",
        json={
            "name": "US032 Camp",
            "target_industry": "Fintech",
            "positive_keywords": ["webinar"],
            "exclude_keywords": [],
        },
    )
    assert camp.status_code == 201
    cid = camp.json()["id"]
    pin = await client.put(
        f"/campaigns/{cid}/sources",
        json={"source_ids": [src_id]},
    )
    assert pin.status_code == 200

    create = await client.post(f"/campaigns/{cid}/discovery-jobs")
    assert create.status_code == 201
    job_id = create.json()["id"]

    run_discovery_job(job_id)

    detail = await client.get(f"/discovery-jobs/{job_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] in ("succeeded", "partial")
    sources = body["progress"].get("sources", {})
    assert sources
    any_live = any(
        s.get("execution_mode") == "live_feed_api" and s.get("status") == "succeeded"
        for s in sources.values()
    )
    assert any_live

    events = await client.get(f"/campaigns/{cid}/events", params={"include_score": "false"})
    assert events.status_code == 200
    titles = [e["canonical_title"] for e in events.json()]
    assert any("US032 Canonical Webinar" in t for t in titles)


@pytest.mark.asyncio
async def test_worker_policy_denied_skips_http_fetch(client, stub_live_feed, monkeypatch):
    """Worker re-checks policy at run time; over-quota after job create must not fetch."""
    monkeypatch.setenv("LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS", "false")
    from livelead.infrastructure.connectors import runner as connector_runner

    calls: list[str] = []

    def spy_fetch(url: str, **kwargs):
        calls.append(url)
        return http_fetch.FetchResult(200, RSS_FIXTURE, "application/rss+xml", None)

    monkeypatch.setattr(connector_runner, "fetch_url", spy_fetch)

    created = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "Later over quota",
            "domain": "quota-denied.test",
            "connector_type": "rss",
            "authentication_mode": "none",
            "enabled": True,
            "approved": True,
            "policy": {
                "access_mode": "feed",
                "valid": True,
                "quota_per_day": 10,
                "quota_used_today": 0,
            },
        },
    )
    src_id = created.json()["id"]
    await client.patch(
        f"/admin/connectors/{src_id}",
        headers=ADMIN,
        json={"rate_limit_json": {"feed_url": "https://quota-denied.test/rss.xml"}},
    )
    camp = await client.post("/campaigns", json={"name": "Denied", "target_industry": "Tech"})
    cid = camp.json()["id"]
    await client.put(f"/campaigns/{cid}/sources", json={"source_ids": [src_id]})
    job_resp = await client.post(f"/campaigns/{cid}/discovery-jobs")
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]
    await client.patch(
        f"/admin/connectors/{src_id}",
        headers=ADMIN,
        json={
            "policy": {
                "access_mode": "feed",
                "valid": True,
                "quota_per_day": 1,
                "quota_used_today": 1,
            }
        },
    )
    run_discovery_job(job_id)

    detail = (await client.get(f"/discovery-jobs/{job_id}")).json()
    src = next(iter(detail["progress"]["sources"].values()))
    assert "policy_denied" in (src.get("error") or "")
    assert calls == []


@pytest.mark.asyncio
async def test_partial_success_one_live_one_fetch_fail(client, stub_live_feed, monkeypatch):
    monkeypatch.setenv("LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS", "false")

    good = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "Good feed",
            "domain": "live-feed-fixture.test",
            "connector_type": "rss",
            "authentication_mode": "none",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "feed", "valid": True},
        },
    )
    await client.patch(
        f"/admin/connectors/{good.json()['id']}",
        headers=ADMIN,
        json={"rate_limit_json": {"feed_url": "https://live-feed-fixture.test/rss.xml"}},
    )
    bad = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "No feed url",
            "domain": "no-feed-url.test",
            "connector_type": "rss",
            "authentication_mode": "none",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "feed", "valid": True},
        },
    )
    bad_id = bad.json()["id"]

    camp = await client.post(
        "/campaigns",
        json={"name": "Partial", "target_industry": "Tech", "positive_keywords": ["webinar"]},
    )
    cid = camp.json()["id"]
    good_id = good.json()["id"]
    pin = await client.put(
        f"/campaigns/{cid}/sources",
        json={"source_ids": [good_id, bad_id]},
    )
    assert pin.status_code == 200

    job_id = (await client.post(f"/campaigns/{cid}/discovery-jobs")).json()["id"]
    run_discovery_job(job_id)
    detail = (await client.get(f"/discovery-jobs/{job_id}")).json()
    assert detail["status"] in ("partial", "succeeded")
    statuses = {s.get("status") for s in detail["progress"]["sources"].values()}
    assert "succeeded" in statuses
    assert "failed" in statuses