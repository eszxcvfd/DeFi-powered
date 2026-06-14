import pytest

from livelead.application.discovery.service import run_discovery_job

ADMIN = {"X-Actor-Role": "admin"}


@pytest.mark.asyncio
async def test_discovery_job_lifecycle_with_mock_worker(client):
    await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "Mock RSS",
            "domain": "success-mock.example.com",
            "connector_type": "rss",
            "authentication_mode": "none",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "feed", "valid": True},
        },
    )
    camp = await client.post(
        "/campaigns",
        json={"name": "Disc Camp", "target_industry": "Tech"},
    )
    assert camp.status_code == 201
    cid = camp.json()["id"]

    create = await client.post(f"/campaigns/{cid}/discovery-jobs")
    assert create.status_code == 201
    job_id = create.json()["id"]
    assert create.json()["status"] == "queued"

    run_discovery_job(job_id)

    detail = await client.get(f"/discovery-jobs/{job_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] in ("succeeded", "partial", "running", "failed")
    assert "job.started" in str(body["progress"].get("events", []))

    events = await client.get(f"/campaigns/{cid}/events", params={"include_score": "false"})
    assert events.status_code == 200
    titles = [e["canonical_title"] for e in events.json()]
    assert len(titles) >= 1
    assert not any("Deterministic mock" in t for t in titles)
    assert any("success-mock-example-com" in t for t in titles)


@pytest.mark.asyncio
async def test_create_discovery_job_redis_down(client, monkeypatch):
    import apps.worker.discovery_tasks as discovery_tasks
    import redis

    def mock_send(*args, **kwargs):
        raise redis.exceptions.ConnectionError("Connection refused")

    monkeypatch.setattr(discovery_tasks.run_discovery_job, "send", mock_send)

    await client.post(
        "/admin/connectors",
        headers={"X-Actor-Role": "admin"},
        json={
            "name": "Mock RSS",
            "domain": "success-mock.example.com",
            "connector_type": "rss",
            "authentication_mode": "none",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "feed", "valid": True},
        },
    )

    camp = await client.post(
        "/campaigns",
        json={"name": "Failed Redis Camp", "target_industry": "Tech"},
    )
    assert camp.status_code == 201
    cid = camp.json()["id"]

    create = await client.post(f"/campaigns/{cid}/discovery-jobs")
    assert create.status_code == 503
    assert "Discovery queue service is currently unavailable" in create.json()["detail"]

    # Verify that the job was still created in the database but marked as failed
    import os

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from livelead.infrastructure.db.models import DiscoveryJobRow

    db_path = os.environ.get("LIVELEAD_SQLITE_PATH")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(
            select(DiscoveryJobRow).where(DiscoveryJobRow.campaign_id == cid)
        )
        job = result.scalar_one()
        assert job.status == "failed"
        assert "Queue connection failed" in job.error_summary

    await engine.dispose()
