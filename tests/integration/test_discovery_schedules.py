"""US-035: discovery schedule persistence and scheduler dispatch."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from livelead.application.discovery.schedule_dispatch import dispatch_due_schedules
from livelead.application.discovery.service import run_discovery_job
from livelead.infrastructure.db.models import Base, DiscoveryJobRow, DiscoveryScheduleRow
from livelead.runtime.settings import parse_settings

ADMIN = {"X-Actor-Role": "admin"}


def _sync_set_next_run_past(schedule_id: str, monkeypatch) -> None:
    settings = parse_settings()
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    engine = create_engine(url, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        row = s.get(DiscoveryScheduleRow, schedule_id)
        assert row is not None
        row.next_run_at = datetime.now(UTC) - timedelta(minutes=5)
        s.commit()


@pytest.mark.asyncio
async def test_create_schedule_lists_next_run(client):
    src = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "US035 Schedule Source",
            "domain": "us035-sched.example.com",
            "connector_type": "rss",
            "authentication_mode": "none",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "feed", "valid": True},
        },
    )
    assert src.status_code == 201
    src_id = src.json()["id"]

    camp = await client.post(
        "/campaigns",
        json={"name": "US035 Camp", "target_industry": "Tech", "positive_keywords": ["summit"]},
    )
    cid = camp.json()["id"]
    await client.put(f"/campaigns/{cid}/sources", json={"source_ids": [src_id]})

    created = await client.post(
        f"/campaigns/{cid}/discovery-schedules",
        headers=ADMIN,
        json={"recurrence": {"kind": "daily", "timezone": "UTC", "hour": 9, "minute": 0}},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["enabled_state"] == "enabled"
    assert body["next_run_at"] is not None
    assert "Daily" in body["recurrence_summary"]

    listed = await client.get(f"/campaigns/{cid}/discovery-schedules", headers=ADMIN)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_scheduler_dispatch_creates_discovery_job(client, monkeypatch):
    monkeypatch.setenv("LIVELEAD_DISCOVERY_USE_MOCK_CONNECTORS", "true")

    src = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "US035 Dispatch Source",
            "domain": "us035-dispatch.example.com",
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
        json={"name": "US035 Dispatch Camp", "target_industry": "Tech", "positive_keywords": ["x"]},
    )
    cid = camp.json()["id"]
    await client.put(f"/campaigns/{cid}/sources", json={"source_ids": [src_id]})

    sched = await client.post(
        f"/campaigns/{cid}/discovery-schedules",
        headers=ADMIN,
        json={"recurrence": {"kind": "daily", "timezone": "UTC", "hour": 12, "minute": 0}},
    )
    schedule_id = sched.json()["id"]
    _sync_set_next_run_past(schedule_id, monkeypatch)

    results = dispatch_due_schedules(enqueue=False)
    assert any(r.get("schedule_id") == schedule_id and r.get("outcome") == "job_created" for r in results)

    settings = parse_settings()
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    engine = create_engine(url, echo=False)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        jobs = list(
            s.execute(
                select(DiscoveryJobRow).where(DiscoveryJobRow.discovery_schedule_id == schedule_id)
            ).scalars()
        )
    assert len(jobs) == 1
    run_discovery_job(jobs[0].id)
    detail = await client.get(f"/discovery-jobs/{jobs[0].id}", headers=ADMIN)
    assert detail.json()["status"] in ("succeeded", "partial", "failed")


@pytest.mark.asyncio
async def test_paused_schedule_not_dispatched(client, monkeypatch):
    src = await client.post(
        "/admin/connectors",
        headers=ADMIN,
        json={
            "name": "US035 Paused Source",
            "domain": "us035-pause.example.com",
            "connector_type": "rss",
            "authentication_mode": "none",
            "enabled": True,
            "approved": True,
            "policy": {"access_mode": "feed", "valid": True},
        },
    )
    src_id = src.json()["id"]
    camp = await client.post("/campaigns", json={"name": "US035 Pause", "target_industry": "Tech"})
    cid = camp.json()["id"]
    await client.put(f"/campaigns/{cid}/sources", json={"source_ids": [src_id]})

    sched = await client.post(
        f"/campaigns/{cid}/discovery-schedules",
        headers=ADMIN,
        json={"recurrence": {"kind": "daily", "timezone": "UTC", "hour": 8, "minute": 0}},
    )
    schedule_id = sched.json()["id"]
    _sync_set_next_run_past(schedule_id, monkeypatch)

    paused = await client.patch(
        f"/discovery-schedules/{schedule_id}",
        headers=ADMIN,
        json={"enabled_state": "paused"},
    )
    assert paused.status_code == 200

    results = dispatch_due_schedules(enqueue=False)
    assert not any(r.get("schedule_id") == schedule_id for r in results)