import pytest


@pytest.mark.asyncio
async def test_browser_launch_sources_auto_provisions_playwright(client):
    from uuid import UUID, uuid4

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from livelead.application.events.ingest import ingest_finding
    from livelead.domain.events.normalize import MockFinding
    from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID

    ADMIN = {"X-Actor-Role": "admin"}
    feed = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "Feed for prov",
            "domain": "feed-prov.test",
            "connector_type": "rss",
            "authentication_mode": "none",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "feed", "valid": True},
        },
    )
    assert feed.status_code == 201
    feed_id = UUID(feed.json()["id"])

    camp = await client.post(
        "/campaigns",
        json={
            "name": f"Prov {uuid4()}",
            "target_industry": "Tech",
            "product_or_service_focus": "SaaS",
            "market_regions": ["EU"],
            "languages": ["en"],
            "timezone": "UTC",
            "date_range": {"start": "2026-07-01", "end": "2026-12-31"},
            "positive_keywords": [],
            "exclude_keywords": [],
            "icp": {
                "industry": "Tech",
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
            "description": "",
        },
    )
    assert camp.status_code == 201
    cid = camp.json()["id"]
    settings = client.app.state.settings
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    sync = sessionmaker(bind=create_engine(url))()
    finding = MockFinding(
        title="Ev",
        source_url="https://evidence-auto.example.com/page",
        description="d",
        organizer="O",
        region="EU",
    )
    ingest_finding(
        sync,
        organization_id=DEV_ORGANIZATION_ID,
        campaign_id=UUID(cid),
        source_id=feed_id,
        finding=finding,
    )
    sync.commit()
    event_id = str(
        sync.execute(text("SELECT id FROM events ORDER BY created_at DESC LIMIT 1")).scalar()
    )
    sync.close()

    r = await client.get(f"/events/{event_id}/browser-launch-sources")
    assert r.status_code == 200
    body = r.json()
    assert any(o["runnable"] and o["engine"] == "playwright" for o in body)
    assert any("evidence-auto.example.com" in o["domain"] for o in body)
