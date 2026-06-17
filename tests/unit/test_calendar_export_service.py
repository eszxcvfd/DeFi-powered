"""Unit tests for the event calendar export service (US-045)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.calendar_export import (
    CalendarExportError,
    CalendarExportInvalidScope,
    CalendarExportNotFound,
    CalendarExportService,
    CalendarExportTokenExpired,
    CalendarExportTokenRevoked,
    hash_calendar_token,
    mint_calendar_token_plaintext,
    verify_calendar_token,
)
from livelead.application.calendar_export.tokens import (
    hash_calendar_token as _hash_token,
)
from livelead.domain.calendar_export.enums import (
    CalendarExportResult,
    CalendarScope,
    CalendarTimeState,
)
from livelead.domain.calendar_export.models import CalendarExportFilter
from livelead.domain.runtime.enums import EnvironmentMode
from livelead.infrastructure.db.models import (
    CalendarExportAuditRow,
    CalendarExportTokenRow,
    CampaignRow,
    EventRow,
    EventWatchlistEntryRow,
)


ORG_ID = "00000000-0000-4000-8000-000000000001"
USER_ID = "00000000-0000-4000-8000-000000000002"


def _build_service(session: AsyncSession) -> CalendarExportService:
    return CalendarExportService(
        session, environment_mode=EnvironmentMode.PILOT_LIVE
    )


async def _make_event(
    session: AsyncSession,
    *,
    campaign_id: str | None = None,
    title: str = "Q3 SaaS Growth",
    description: str = "B2B SaaS growth event",
    region: str = "",
    starts_at: datetime | None = None,
) -> str:
    if campaign_id is None:
        campaign_id = str(uuid4())
        campaign_row = CampaignRow(
            id=campaign_id,
            organization_id=ORG_ID,
            name="Test Campaign",
            created_at=datetime.utcnow(),
        )
        session.add(campaign_row)
    event_id = str(uuid4())
    event_row = EventRow(
        id=event_id,
        organization_id=ORG_ID,
        campaign_id=campaign_id,
        canonical_title=title,
        source_url="https://example.com/event",
        observed_at=datetime.utcnow(),
        description=description,
        region=region,
        starts_at=starts_at or datetime.utcnow() + timedelta(hours=1),
        created_at=datetime.utcnow(),
    )
    session.add(event_row)
    await session.flush()
    return event_id


def test_hash_calendar_token_is_deterministic() -> None:
    token = "abcdefghijklmnopqrstuvwxyz123456"
    assert hash_calendar_token(token) == _hash_token(token)
    assert len(hash_calendar_token(token)) == 64


def test_hash_calendar_token_rejects_empty() -> None:
    assert hash_calendar_token("") != hash_calendar_token("x")


def test_verify_calendar_token_matches_hash() -> None:
    plaintext = mint_calendar_token_plaintext()
    h = hash_calendar_token(plaintext)
    assert verify_calendar_token(plaintext, h) is True
    assert verify_calendar_token("wrong", h) is False
    assert verify_calendar_token(plaintext, "") is False


def test_mint_calendar_token_plaintext_is_url_safe() -> None:
    plaintext = mint_calendar_token_plaintext()
    assert len(plaintext) == 32
    # URL-safe alphabet only.
    allowed = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    )
    assert set(plaintext).issubset(allowed)


@pytest.mark.asyncio
async def test_mint_token_event_scope_persists_row_and_audit(
    session: AsyncSession,
) -> None:
    event_id = await _make_event(session)
    service = _build_service(session)
    token, plaintext = await service.mint_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        scope=CalendarScope.EVENT,
        target_id=event_id,
        request_id="req-1",
        ip_address="127.0.0.1",
        user_agent="ua",
        actor=USER_ID,
        actor_role="analyst",
    )
    assert token.id
    assert token.scope is CalendarScope.EVENT
    assert token.target_id == event_id
    assert token.audit_correlation_id
    assert verify_calendar_token(plaintext, token.token_hash)
    rows = (
        await session.execute(
            select(CalendarExportTokenRow).where(
                CalendarExportTokenRow.id == token.id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    audit_rows = (
        await session.execute(
            select(CalendarExportAuditRow).where(
                CalendarExportAuditRow.token_id == token.id
            )
        )
    ).scalars().all()
    assert len(audit_rows) == 1
    assert audit_rows[0].result == "success"


@pytest.mark.asyncio
async def test_mint_token_event_scope_rejects_missing_target(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    with pytest.raises(CalendarExportError):
        await service.mint_token(
            organization_id=ORG_ID,
            user_id=USER_ID,
            scope=CalendarScope.EVENT,
        )


@pytest.mark.asyncio
async def test_mint_token_event_filter_requires_filter_payload(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    with pytest.raises(CalendarExportError):
        await service.mint_token(
            organization_id=ORG_ID,
            user_id=USER_ID,
            scope=CalendarScope.EVENT_FILTER,
        )


@pytest.mark.asyncio
async def test_mint_token_unknown_scope_rejected(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    with pytest.raises(CalendarExportInvalidScope):
        await service.mint_token(
            organization_id=ORG_ID,
            user_id=USER_ID,
            scope="not_a_scope",
        )


@pytest.mark.asyncio
async def test_mint_token_ttl_clamps_to_mode_default(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    requested = datetime.utcnow() + timedelta(days=365)
    token, _ = await service.mint_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        scope=CalendarScope.WATCHLIST,
        expires_at=requested,
    )
    bound = (token.expires_at - datetime.utcnow()).days
    assert 0 < bound <= 90  # pilot_live bound


@pytest.mark.asyncio
async def test_revoke_token_idempotent_and_audits(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    token, _ = await service.mint_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        scope=CalendarScope.WATCHLIST,
    )
    revoked = await service.revoke_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        token_id=token.id,
    )
    assert revoked.revoked_at is not None
    again = await service.revoke_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        token_id=token.id,
    )
    assert again.revoked_at == revoked.revoked_at


@pytest.mark.asyncio
async def test_revoke_token_rejects_cross_user(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    token, _ = await service.mint_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        scope=CalendarScope.WATCHLIST,
    )
    with pytest.raises(CalendarExportNotFound):
        await service.revoke_token(
            organization_id=ORG_ID,
            user_id="00000000-0000-4000-8000-0000deadbeef",
            token_id=token.id,
        )


@pytest.mark.asyncio
async def test_resolve_token_returns_expired_error(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    token, plaintext = await service.mint_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        scope=CalendarScope.WATCHLIST,
    )
    # Force expiry into the past.
    row = (
        await session.execute(
            select(CalendarExportTokenRow).where(
                CalendarExportTokenRow.id == token.id
            )
        )
    ).scalar_one()
    row.expires_at = datetime.utcnow() - timedelta(seconds=1)
    await session.flush()
    with pytest.raises(CalendarExportTokenExpired):
        await service.resolve_token(
            organization_id=ORG_ID,
            plaintext=plaintext,
        )


@pytest.mark.asyncio
async def test_resolve_token_returns_revoked_error(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    token, plaintext = await service.mint_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        scope=CalendarScope.WATCHLIST,
    )
    await service.revoke_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        token_id=token.id,
    )
    with pytest.raises(CalendarExportTokenRevoked):
        await service.resolve_token(
            organization_id=ORG_ID,
            plaintext=plaintext,
        )


@pytest.mark.asyncio
async def test_resolve_token_unknown_raises_not_found(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    with pytest.raises(CalendarExportNotFound):
        await service.resolve_token(
            organization_id=ORG_ID,
            plaintext="not-a-real-token",
        )


@pytest.mark.asyncio
async def test_resolve_token_increments_use_count(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    token, plaintext = await service.mint_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        scope=CalendarScope.WATCHLIST,
    )
    first, _ = await service.resolve_token(
        organization_id=ORG_ID, plaintext=plaintext
    )
    second, _ = await service.resolve_token(
        organization_id=ORG_ID, plaintext=plaintext
    )
    assert first.use_count == 1
    assert second.use_count == 2


@pytest.mark.asyncio
async def test_build_event_ics_returns_text_calendar_body(
    session: AsyncSession,
) -> None:
    event_id = await _make_event(session, title="Demo")
    service = _build_service(session)
    body, count = await service.build_event_ics(
        organization_id=ORG_ID,
        requester_id=USER_ID,
        event_id=event_id,
    )
    assert count == 1
    assert body.startswith("BEGIN:VCALENDAR\r\n")
    assert "BEGIN:VEVENT" in body
    assert "UID:" + event_id in body
    assert "SUMMARY:Demo" in body
    assert "STATUS:TENTATIVE" in body


@pytest.mark.asyncio
async def test_build_event_ics_unknown_event_raises_not_found(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    with pytest.raises(CalendarExportNotFound):
        await service.build_event_ics(
            organization_id=ORG_ID,
            requester_id=USER_ID,
            event_id=str(uuid4()),
        )


@pytest.mark.asyncio
async def test_build_watchlist_ics_emits_watchlist_envelope(
    session: AsyncSession,
) -> None:
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
            canonical_title="Watched Event",
            source_url="https://example.com/e",
            observed_at=datetime.utcnow(),
            region="",
            starts_at=datetime.utcnow() + timedelta(hours=1),
            created_at=datetime.utcnow(),
        )
    )
    await session.flush()
    session.add(
        EventWatchlistEntryRow(
            id=str(uuid4()),
            organization_id=ORG_ID,
            user_id=USER_ID,
            event_id=event_id,
            reminder_at=None,
            reminder_note="",
            last_actor_id=USER_ID,
            last_actor_role="analyst",
            last_action_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    )
    await session.flush()
    service = _build_service(session)
    body, count = await service.build_watchlist_ics(
        organization_id=ORG_ID,
        user_id=USER_ID,
    )
    assert count == 1
    assert "X-WR-CALNAME:LiveLead watchlist" in body
    assert "Watched Event" in body


@pytest.mark.asyncio
async def test_build_watchlist_ics_empty_user_returns_empty_feed(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    body, count = await service.build_watchlist_ics(
        organization_id=ORG_ID, user_id=USER_ID
    )
    assert count == 0
    assert "BEGIN:VCALENDAR" in body
    assert "LiveLead watchlist" in body


@pytest.mark.asyncio
async def test_build_filter_ics_uses_label(
    session: AsyncSession,
) -> None:
    await _make_event(session, title="Fintech event", region="us")
    service = _build_service(session)
    body, count = await service.build_filter_ics(
        organization_id=ORG_ID,
        requester_id=USER_ID,
        filter_obj=CalendarExportFilter(region="us", label="US events"),
    )
    assert count >= 1
    assert "LiveLead events (US events)" in body
    assert "Fintech event" in body


@pytest.mark.asyncio
async def test_build_filter_ics_empty_returns_envelope(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    body, count = await service.build_filter_ics(
        organization_id=ORG_ID,
        requester_id=USER_ID,
        filter_obj=CalendarExportFilter(label="Empty"),
    )
    assert count == 0
    assert "LiveLead events (Empty)" in body


@pytest.mark.asyncio
async def test_build_tokenized_ics_for_event(
    session: AsyncSession,
) -> None:
    event_id = await _make_event(session)
    service = _build_service(session)
    token, plaintext = await service.mint_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        scope=CalendarScope.EVENT,
        target_id=event_id,
    )
    body, count, scope = await service.build_tokenized_ics(
        organization_id=token.organization_id,
        plaintext=plaintext,
    )
    assert scope is CalendarScope.EVENT
    assert count == 1
    assert "BEGIN:VEVENT" in body


@pytest.mark.asyncio
async def test_build_tokenized_ics_for_watchlist(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    token, plaintext = await service.mint_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        scope=CalendarScope.WATCHLIST,
    )
    body, count, scope = await service.build_tokenized_ics(
        organization_id=token.organization_id,
        plaintext=plaintext,
    )
    assert scope is CalendarScope.WATCHLIST
    assert "BEGIN:VCALENDAR" in body


@pytest.mark.asyncio
async def test_build_tokenized_ics_for_event_filter(
    session: AsyncSession,
) -> None:
    await _make_event(session, region="us")
    service = _build_service(session)
    token, plaintext = await service.mint_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        scope=CalendarScope.EVENT_FILTER,
        filter_json={"region": "us", "label": "US only"},
    )
    body, count, scope = await service.build_tokenized_ics(
        organization_id=token.organization_id,
        plaintext=plaintext,
    )
    assert scope is CalendarScope.EVENT_FILTER
    assert "LiveLead events (US only)" in body


@pytest.mark.asyncio
async def test_list_tokens_excludes_revoked_by_default(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    token, _ = await service.mint_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        scope=CalendarScope.WATCHLIST,
    )
    active = await service.list_tokens(ORG_ID, USER_ID)
    assert len(active) == 1
    await service.revoke_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        token_id=token.id,
    )
    active_again = await service.list_tokens(ORG_ID, USER_ID)
    assert active_again == []
    all_tokens = await service.list_tokens(
        ORG_ID, USER_ID, include_revoked=True
    )
    assert len(all_tokens) == 1
    assert all_tokens[0].revoked_at is not None


@pytest.mark.asyncio
async def test_list_audits_returns_recent_entries(
    session: AsyncSession,
) -> None:
    service = _build_service(session)
    await service.mint_token(
        organization_id=ORG_ID,
        user_id=USER_ID,
        scope=CalendarScope.WATCHLIST,
    )
    audits = await service.list_audits(ORG_ID, USER_ID)
    assert len(audits) >= 1
    assert audits[0].scope is CalendarScope.WATCHLIST
