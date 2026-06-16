"""Event watchlist API integration (US-030)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from livelead.application.events.ingest import ingest_finding
from livelead.domain.events.normalize import MockFinding
from livelead.domain.identity import (
    MembershipState,
    Role,
    hash_email_for_limiter,
    hash_password,
)
from livelead.interfaces.auth.tenant_context import DEV_ORGANIZATION_ID
from livelead.infrastructure.db.models import (
    EventRow,
    OrganizationMembershipRow,
    UserRow,
)

ORG = "00000000-0000-4000-8000-000000000001"

PAYLOAD = {
    "name": "Watchlist Campaign",
    "description": "US-030",
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


async def _login(
    client,
    *,
    email: str,
    password: str,
    role: Role,
    organization_id: str = ORG,
) -> dict:
    factory = client.app.state.session_factory
    from sqlalchemy import delete
    from livelead.infrastructure.db.models import (
        OrganizationMembershipRow as _OMR,
        UserRow as _UR,
    )
    async with factory() as sess:
        await sess.execute(delete(_OMR))
        await sess.execute(delete(_UR).where(_UR.email == "owner@example.com"))
        await sess.commit()

    material = hash_password(password)
    email_hash = hash_email_for_limiter(email)
    async with factory() as sess:
        user = UserRow(
            id=str(uuid4()),
            email=email,
            email_hash=email_hash,
            display_name=email,
            password_hash=material.password_hash,
            password_salt=material.salt,
            password_iterations=material.iterations,
            disabled=False,
        )
        sess.add(user)
        await sess.flush()
        sess.add(
            OrganizationMembershipRow(
                id=str(uuid4()),
                user_id=user.id,
                organization_id=organization_id,
                role=role.value,
                state=MembershipState.ACTIVE.value,
            )
        )
        await sess.commit()
        user_id = user.id

    r = await client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
            "organization_id": organization_id,
        },
    )
    assert r.status_code == 200, r.text
    return {"cookies": dict(r.cookies), "user_id": user_id}


async def _seed_event(client) -> str:
    create = await client.post("/campaigns", json=PAYLOAD)
    assert create.status_code == 201, create.text
    cid = create.json()["id"]
    settings = client.app.state.settings
    url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
    sync = sessionmaker(bind=create_engine(url))()
    try:
        finding = MockFinding(
            title="Watchlist Webinar EU",
            source_url=f"https://watch.test/{uuid4()}",
            description="webinar",
            organizer="Org",
            region="EU",
        )
        eid, _action = ingest_finding(
            sync,
            organization_id=DEV_ORGANIZATION_ID,
            campaign_id=UUID(cid),
            source_id=uuid4(),
            finding=finding,
        )
        sync.commit()
    finally:
        sync.close()
    return str(eid)


@pytest.mark.asyncio
async def test_watch_unwatch_and_reminder_lifecycle(client):
    owner = await _login(
        client,
        email="watch-owner@example.com",
        password="Hello-World-2026",
        role=Role.OWNER,
    )
    cookies = owner["cookies"]
    event_id = await _seed_event(client)

    # Watch without reminder
    put = await client.put(
        f"/events/{event_id}/watchlist",
        json={"reminder_at": None, "reminder_note": ""},
        cookies=cookies,
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["watch"]["is_watched"] is True
    assert body["watch"]["reminder_at"] is None
    assert body["watch"]["reminder_status"] == "scheduled"
    assert body["history"][0]["action"] == "watched"
    entry_id = body["entry_id"]
    assert entry_id

    # Set a future reminder
    future = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    put2 = await client.put(
        f"/events/{event_id}/watchlist",
        json={"reminder_at": future, "reminder_note": "follow-up"},
        cookies=cookies,
    )
    assert put2.status_code == 200
    body2 = put2.json()
    assert body2["entry_id"] == entry_id
    assert body2["watch"]["reminder_at"] is not None
    assert body2["watch"]["reminder_note"] == "follow-up"
    assert body2["watch"]["reminder_status"] == "scheduled"
    assert body2["history"][0]["action"] == "reminder_set"

    # Change the reminder
    later = (datetime.now(UTC) + timedelta(days=14)).isoformat()
    put3 = await client.put(
        f"/events/{event_id}/watchlist",
        json={"reminder_at": later, "reminder_note": "follow-up"},
        cookies=cookies,
    )
    assert put3.status_code == 200
    body3 = put3.json()
    assert body3["history"][0]["action"] == "reminder_changed"

    # Clear the reminder
    put4 = await client.put(
        f"/events/{event_id}/watchlist",
        json={"reminder_at": None, "reminder_note": ""},
        cookies=cookies,
    )
    assert put4.status_code == 200
    body4 = put4.json()
    assert body4["watch"]["is_watched"] is True
    assert body4["watch"]["reminder_at"] is None
    assert body4["history"][0]["action"] == "reminder_cleared"

    # Verify event detail carries the current-user watch state
    detail = await client.get(f"/events/{event_id}", cookies=cookies)
    assert detail.status_code == 200
    assert detail.json()["watch"]["is_watched"] is True
    assert detail.json()["watch"]["reminder_status"] == "scheduled"

    # Unwatch
    delete = await client.delete(
        f"/events/{event_id}/watchlist", cookies=cookies
    )
    assert delete.status_code == 200, delete.text
    assert delete.json()["watch"]["is_watched"] is False
    assert delete.json()["watch"]["reminder_status"] == "not_watched"
    assert delete.json()["history"][0]["action"] == "unwatched"


@pytest.mark.asyncio
async def test_watch_invalid_reminder_returns_400(client):
    owner = await _login(
        client,
        email="bad-watch-owner@example.com",
        password="Hello-World-2026",
        role=Role.OWNER,
    )
    cookies = owner["cookies"]
    event_id = await _seed_event(client)
    r = await client.put(
        f"/events/{event_id}/watchlist",
        json={"reminder_at": "not-a-timestamp", "reminder_note": ""},
        cookies=cookies,
    )
    assert r.status_code == 400
    assert "reminder_at" in r.json()["detail"]


@pytest.mark.asyncio
async def test_other_user_watch_does_not_leak_in_event_detail(client):
    owner = await _login(
        client,
        email="owner-a@example.com",
        password="Hello-World-2026",
        role=Role.OWNER,
    )
    analyst = await _login(
        client,
        email="analyst-a@example.com",
        password="Hello-World-2026",
        role=Role.ANALYST,
    )
    event_id = await _seed_event(client)

    # Owner watches the event
    put = await client.put(
        f"/events/{event_id}/watchlist",
        json={"reminder_at": None, "reminder_note": ""},
        cookies=owner["cookies"],
    )
    assert put.status_code == 200

    # The analyst sees an unwatched state in the event detail
    detail = await client.get(f"/events/{event_id}", cookies=analyst["cookies"])
    assert detail.status_code == 200
    assert detail.json()["watch"]["is_watched"] is False

    # And in the campaign event list
    cid = (await client.get("/events", cookies=analyst["cookies"])).json()[0]["campaign_id"]
    listed = await client.get(
        f"/campaigns/{cid}/events", cookies=analyst["cookies"]
    )
    assert listed.status_code == 200
    match = next(r for r in listed.json() if r["id"] == event_id)
    assert match["watch"] is not None
    assert match["watch"]["is_watched"] is False

    # The owner sees the watched state in the campaign event list
    listed_owner = await client.get(
        f"/campaigns/{cid}/events", cookies=owner["cookies"]
    )
    assert listed_owner.status_code == 200
    match_owner = next(r for r in listed_owner.json() if r["id"] == event_id)
    assert match_owner["watch"] is not None
    assert match_owner["watch"]["is_watched"] is True


@pytest.mark.asyncio
async def test_watched_filter_in_campaign_event_list(client):
    owner = await _login(
        client,
        email="filter-owner@example.com",
        password="Hello-World-2026",
        role=Role.OWNER,
    )
    cookies = owner["cookies"]
    first = await _seed_event(client)
    second = await _seed_event(client)

    # Watch only the first
    put = await client.put(
        f"/events/{first}/watchlist",
        json={"reminder_at": None, "reminder_note": ""},
        cookies=cookies,
    )
    assert put.status_code == 200

    listed = await client.get(
        "/events",
        cookies=cookies,
    )
    assert listed.status_code == 200
    ids = [r["id"] for r in listed.json()]
    assert first in ids
    assert second in ids

    only_watched = await client.get(
        "/events?watched=true", cookies=cookies
    )
    assert only_watched.status_code == 200
    only_watched_ids = [r["id"] for r in only_watched.json()]
    assert only_watched_ids == [first]

    not_watched = await client.get(
        "/events?watched=false", cookies=cookies
    )
    assert not_watched.status_code == 200
    not_watched_ids = [r["id"] for r in not_watched.json()]
    assert second in not_watched_ids
    assert first not in not_watched_ids


@pytest.mark.asyncio
async def test_watched_events_list_endpoint(client):
    owner = await _login(
        client,
        email="list-owner@example.com",
        password="Hello-World-2026",
        role=Role.OWNER,
    )
    cookies = owner["cookies"]
    eid_a = await _seed_event(client)
    eid_b = await _seed_event(client)

    await client.put(
        f"/events/{eid_a}/watchlist",
        json={"reminder_at": None, "reminder_note": ""},
        cookies=cookies,
    )
    future = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    await client.put(
        f"/events/{eid_b}/watchlist",
        json={"reminder_at": future, "reminder_note": "with reminder"},
        cookies=cookies,
    )

    listing = await client.get("/watchlist/events", cookies=cookies)
    assert listing.status_code == 200, listing.text
    body = listing.json()
    assert body["total"] == 2
    ids = [row["event_id"] for row in body["items"]]
    assert eid_a in ids
    assert eid_b in ids
    a_row = next(r for r in body["items"] if r["event_id"] == eid_a)
    assert a_row["reminder_status"] == "scheduled"
    assert a_row["reminder_at"] is None
    b_row = next(r for r in body["items"] if r["event_id"] == eid_b)
    assert b_row["reminder_status"] == "scheduled"
    assert b_row["reminder_at"] is not None
    assert b_row["reminder_note"] == "with reminder"

    # Filter by has_reminder=true
    only_with = await client.get(
        "/watchlist/events?has_reminder=true", cookies=cookies
    )
    assert only_with.status_code == 200
    assert {row["event_id"] for row in only_with.json()["items"]} == {eid_b}

    # Remove one and confirm the list shrinks
    delete = await client.delete(
        f"/events/{eid_a}/watchlist", cookies=cookies
    )
    assert delete.status_code == 200
    listing_after = await client.get("/watchlist/events", cookies=cookies)
    assert listing_after.status_code == 200
    assert listing_after.json()["total"] == 1


@pytest.mark.asyncio
async def test_watchlist_endpoint_requires_authentication(client):
    event_id = await _seed_event(client)
    put = await client.put(
        f"/events/{event_id}/watchlist",
        json={"reminder_at": None, "reminder_note": ""},
    )
    assert put.status_code == 401
    delete = await client.delete(f"/events/{event_id}/watchlist")
    assert delete.status_code == 401
    listing = await client.get("/watchlist/events")
    assert listing.status_code == 401


@pytest.mark.asyncio
async def test_reminder_eligibility_uses_watchlist_entries(client):
    owner = await _login(
        client,
        email="elig-owner@example.com",
        password="Hello-World-2026",
        role=Role.OWNER,
    )
    cookies = owner["cookies"]
    eid_overdue = await _seed_event(client)
    eid_future = await _seed_event(client)

    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    future = (datetime.now(UTC) + timedelta(days=10)).isoformat()
    await client.put(
        f"/events/{eid_overdue}/watchlist",
        json={"reminder_at": past, "reminder_note": "overdue"},
        cookies=cookies,
    )
    await client.put(
        f"/events/{eid_future}/watchlist",
        json={"reminder_at": future, "reminder_note": "future"},
        cookies=cookies,
    )

    # Use the detail endpoint to confirm the projection reports overdue
    detail = await client.get(f"/events/{eid_overdue}", cookies=cookies)
    assert detail.status_code == 200
    assert detail.json()["watch"]["reminder_status"] == "overdue"
    assert detail.json()["watch"]["reminder_eligible"] is True
    detail_future = await client.get(f"/events/{eid_future}", cookies=cookies)
    assert detail_future.json()["watch"]["reminder_status"] == "scheduled"
    assert detail_future.json()["watch"]["reminder_eligible"] is True


@pytest.mark.asyncio
async def test_delete_unwatched_event_is_idempotent(client):
    owner = await _login(
        client,
        email="idem-owner@example.com",
        password="Hello-World-2026",
        role=Role.OWNER,
    )
    cookies = owner["cookies"]
    event_id = await _seed_event(client)
    delete = await client.delete(
        f"/events/{event_id}/watchlist", cookies=cookies
    )
    assert delete.status_code == 200
    assert delete.json()["watch"]["is_watched"] is False
    # Second call still returns 200 with no-op history
    delete_again = await client.delete(
        f"/events/{event_id}/watchlist", cookies=cookies
    )
    assert delete_again.status_code == 200
    assert delete_again.json()["watch"]["is_watched"] is False
    assert delete_again.json()["history"] == []
