"""Integration tests for the event calendar export (ICS) API (US-045).

Uses the real /auth/login flow so the integration suite exercises the
same boundary the frontend would. Each test gets its own migrated
SQLite via the `migrated_client` fixture.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.calendar_export.enums import CalendarScope
from livelead.infrastructure.db.models import (
    CalendarExportTokenRow,
    CampaignRow,
    EventRow,
    EventWatchlistEntryRow,
)

ORG_ID = "00000000-0000-4000-8000-000000000001"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _bootstrap_owner_email() -> str:
    from livelead.runtime.settings import parse_settings

    return parse_settings().auth_default_owner_email


def _bootstrap_owner_password() -> str:
    from livelead.runtime.settings import parse_settings

    return parse_settings().auth_default_owner_password


async def _login_owner(client) -> dict:
    r = await client.post(
        "/auth/login",
        json={
            "email": _bootstrap_owner_email(),
            "password": _bootstrap_owner_password(),
            "organization_id": ORG_ID,
        },
    )
    assert r.status_code == 200, r.text
    return {"cookies": dict(r.cookies)}


async def _seed_event(
    client, *, title: str = "Demo", region: str = ""
) -> str:
    factory = client.app.state.session_factory
    async with factory() as session:
        campaign_id = str(uuid4())
        session.add(
            CampaignRow(
                id=campaign_id,
                organization_id=ORG_ID,
                name="Test Campaign",
                created_at=datetime.utcnow(),
            )
        )
        event_id = str(uuid4())
        session.add(
            EventRow(
                id=event_id,
                organization_id=ORG_ID,
                campaign_id=campaign_id,
                canonical_title=title,
                source_url="https://example.com/e",
                observed_at=datetime.utcnow(),
                region=region,
                starts_at=datetime.utcnow() + timedelta(hours=1),
                created_at=datetime.utcnow(),
            )
        )
        await session.commit()
    return event_id


async def _seed_watchlist(client, *, event_id: str, user_id: str) -> None:
    factory = client.app.state.session_factory
    async with factory() as session:
        session.add(
            EventWatchlistEntryRow(
                id=str(uuid4()),
                organization_id=ORG_ID,
                user_id=user_id,
                event_id=event_id,
                reminder_at=None,
                reminder_note="",
                last_actor_id=user_id,
                last_actor_role="owner",
                last_action_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        await session.commit()


# ----------------------------------------------------------------------
# Current-user ICS endpoints
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_ics_returns_text_calendar(migrated_client):
    event_id = await _seed_event(migrated_client, title="ICS target")
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.get(
        f"/events/{event_id}.ics",
        cookies=cookies,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    body = r.text
    assert body.startswith("BEGIN:VCALENDAR\r\n")
    assert "UID:" + event_id in body
    assert "SUMMARY:ICS target" in body


@pytest.mark.asyncio
async def test_event_ics_returns_404_for_unknown_event(migrated_client):
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.get(
        f"/events/{uuid4()}.ics",
        cookies=cookies,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_watchlist_ics_returns_envelope(migrated_client):
    cookies_dict = await _login_owner(migrated_client)
    cookies = cookies_dict["cookies"]
    me = await migrated_client.get("/auth/me", cookies=cookies)
    assert me.status_code == 200
    user_id = me.json()["user_id"]
    event_id = await _seed_event(migrated_client, title="Watched")
    await _seed_watchlist(migrated_client, event_id=event_id, user_id=user_id)
    r = await migrated_client.get(
        "/watchlist/events.ics",
        cookies=cookies,
    )
    assert r.status_code == 200
    assert "X-WR-CALNAME:LiveLead watchlist" in r.text
    assert "SUMMARY:Watched" in r.text


@pytest.mark.asyncio
async def test_filter_ics_returns_envelope(migrated_client):
    await _seed_event(migrated_client, title="Fintech", region="us")
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.get(
        "/events.ics",
        params={"region": "us", "label": "US only"},
        cookies=cookies,
    )
    assert r.status_code == 200
    assert "LiveLead events (US only)" in r.text
    assert "SUMMARY:Fintech" in r.text


# ----------------------------------------------------------------------
# Token mint + revoke
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mint_event_token_returns_plaintext(migrated_client):
    event_id = await _seed_event(migrated_client, title="Tokenized")
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.post(
        "/calendar-export-tokens",
        json={"scope": "event", "target_id": event_id},
        cookies=cookies,
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["scope"] == "event"
    assert payload["target_id"] == event_id
    assert "plaintext" in payload
    assert len(payload["plaintext"]) == 32


@pytest.mark.asyncio
async def test_mint_token_rejects_unknown_scope(migrated_client):
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.post(
        "/calendar-export-tokens",
        json={"scope": "not_a_scope"},
        cookies=cookies,
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_mint_event_token_rejects_missing_target(migrated_client):
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.post(
        "/calendar-export-tokens",
        json={"scope": "event"},
        cookies=cookies,
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_mint_filter_token_requires_filter(migrated_client):
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.post(
        "/calendar-export-tokens",
        json={"scope": "event_filter"},
        cookies=cookies,
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_list_tokens_excludes_revoked_by_default(migrated_client):
    event_id = await _seed_event(migrated_client)
    cookies = (await _login_owner(migrated_client))["cookies"]
    mint = await migrated_client.post(
        "/calendar-export-tokens",
        json={"scope": "event", "target_id": event_id},
        cookies=cookies,
    )
    token_id = mint.json()["id"]
    r = await migrated_client.get(
        "/calendar-export-tokens",
        cookies=cookies,
    )
    assert r.status_code == 200
    assert r.json()["total"] == 1
    rev = await migrated_client.delete(
        f"/calendar-export-tokens/{token_id}",
        cookies=cookies,
    )
    assert rev.status_code == 200
    after = await migrated_client.get(
        "/calendar-export-tokens",
        cookies=cookies,
    )
    assert after.json()["total"] == 0
    incl = await migrated_client.get(
        "/calendar-export-tokens",
        params={"include_revoked": "true"},
        cookies=cookies,
    )
    assert incl.json()["total"] == 1
    assert incl.json()["items"][0]["revoked_at"] is not None


@pytest.mark.asyncio
async def test_revoke_unknown_token_returns_404(migrated_client):
    cookies = (await _login_owner(migrated_client))["cookies"]
    r = await migrated_client.delete(
        f"/calendar-export-tokens/{uuid4()}",
        cookies=cookies,
    )
    assert r.status_code == 404


# ----------------------------------------------------------------------
# Tokenized ICS endpoint
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tokenized_event_ics_returns_payload(migrated_client):
    event_id = await _seed_event(migrated_client, title="Sub")
    cookies = (await _login_owner(migrated_client))["cookies"]
    mint = await migrated_client.post(
        "/calendar-export-tokens",
        json={"scope": "event", "target_id": event_id},
        cookies=cookies,
    )
    plaintext = mint.json()["plaintext"]
    r = await migrated_client.get(
        f"/calendar-export/{plaintext}.ics",
    )
    assert r.status_code == 200
    assert "SUMMARY:Sub" in r.text


@pytest.mark.asyncio
async def test_tokenized_unknown_returns_404(migrated_client):
    r = await migrated_client.get(
        "/calendar-export/not-a-real-token.ics",
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_tokenized_revoked_returns_410(migrated_client):
    event_id = await _seed_event(migrated_client)
    cookies = (await _login_owner(migrated_client))["cookies"]
    mint = await migrated_client.post(
        "/calendar-export-tokens",
        json={"scope": "event", "target_id": event_id},
        cookies=cookies,
    )
    token_id = mint.json()["id"]
    plaintext = mint.json()["plaintext"]
    await migrated_client.delete(
        f"/calendar-export-tokens/{token_id}",
        cookies=cookies,
    )
    r = await migrated_client.get(
        f"/calendar-export/{plaintext}.ics",
    )
    assert r.status_code == 410


@pytest.mark.asyncio
async def test_tokenized_expired_returns_410(migrated_client):
    event_id = await _seed_event(migrated_client)
    cookies = (await _login_owner(migrated_client))["cookies"]
    mint = await migrated_client.post(
        "/calendar-export-tokens",
        json={"scope": "event", "target_id": event_id},
        cookies=cookies,
    )
    token_id = mint.json()["id"]
    plaintext = mint.json()["plaintext"]
    factory = migrated_client.app.state.session_factory
    async with factory() as session:
        row = (
            await session.execute(
                select(CalendarExportTokenRow).where(
                    CalendarExportTokenRow.id == token_id
                )
            )
        ).scalar_one()
        row.expires_at = datetime.utcnow() - timedelta(seconds=1)
        await session.commit()
    r = await migrated_client.get(
        f"/calendar-export/{plaintext}.ics",
    )
    assert r.status_code == 410


@pytest.mark.asyncio
async def test_tokenized_watchlist_ics(migrated_client):
    cookies_dict = await _login_owner(migrated_client)
    cookies = cookies_dict["cookies"]
    me = await migrated_client.get("/auth/me", cookies=cookies)
    user_id = me.json()["user_id"]
    event_id = await _seed_event(migrated_client, title="Watched")
    await _seed_watchlist(migrated_client, event_id=event_id, user_id=user_id)
    mint = await migrated_client.post(
        "/calendar-export-tokens",
        json={"scope": "watchlist"},
        cookies=cookies,
    )
    plaintext = mint.json()["plaintext"]
    r = await migrated_client.get(
        f"/calendar-export/{plaintext}.ics",
    )
    assert r.status_code == 200
    assert "X-WR-CALNAME:LiveLead watchlist" in r.text
    assert "SUMMARY:Watched" in r.text


@pytest.mark.asyncio
async def test_audit_listing_returns_entries(migrated_client):
    event_id = await _seed_event(migrated_client)
    cookies = (await _login_owner(migrated_client))["cookies"]
    await migrated_client.post(
        "/calendar-export-tokens",
        json={"scope": "event", "target_id": event_id},
        cookies=cookies,
    )
    r = await migrated_client.get(
        "/calendar-export-tokens/audits",
        cookies=cookies,
    )
    assert r.status_code == 200
    assert r.json()["total"] >= 1
