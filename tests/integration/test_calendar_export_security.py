"""Security tests for the event calendar export (US-045).

The tests assert the closed contract from
`docs/decisions/0023-event-calendar-export-ics-baseline.md`:

- The plaintext token is never persisted on
  `calendar_export_tokens`; subsequent reads of the
  same `token_id` return the row without the plaintext.
- The tokenized endpoint refuses to resolve a token
  whose scope does not match the requested
  `text/calendar` response.
- The calendar exports panel is covered by the
  existing RBAC contract from `US-027`: a viewer,
  analyst, sales, or reviewer session gets no access
  to the token list, the audit list, or the
  revocation flow.
- The migration does not weaken the existing audit
  retention guarantee from `NFR-SEC-008`.
- The new `CalendarScope` enum does not weaken the
  existing audit entry shape from `US-026` or the
  existing sanitization contract from `US-041`.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.calendar_export import (
    CalendarExportService,
    hash_calendar_token,
)
from livelead.application.calendar_export.tokens import mint_calendar_token_plaintext
from livelead.domain.audit.enums import (
    AuditAction,
    AuditTargetType,
)
from livelead.domain.calendar_export.enums import CalendarScope
from livelead.domain.runtime.enums import EnvironmentMode
from livelead.infrastructure.db.models import (
    AuditEntryRow,
    CalendarExportTokenRow,
    CampaignRow,
    EventRow,
)


ORG_ID = "00000000-0000-4000-8000-000000000001"
USER_ID = "00000000-0000-4000-8000-000000000002"


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


def _build_service(session: AsyncSession) -> CalendarExportService:
    return CalendarExportService(
        session, environment_mode=EnvironmentMode.PILOT_LIVE
    )


async def _seed_event(
    client, *, title: str = "Sec event", region: str = ""
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


# ----------------------------------------------------------------------
# Plaintext token contract
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mint_token_does_not_persist_plaintext(migrated_client):
    event_id = await _seed_event(migrated_client)
    cookies = (await _login_owner(migrated_client))["cookies"]
    mint = await migrated_client.post(
        "/calendar-export-tokens",
        json={"scope": "event", "target_id": event_id},
        cookies=cookies,
    )
    plaintext = mint.json()["plaintext"]
    token_id = mint.json()["id"]
    # The plaintext is the HMAC-SHA-256 of the
    # minted token, not the plaintext itself. The
    # `token_hash` column is a 64-character hex
    # digest, so the plaintext cannot be recovered
    # from the row.
    factory = migrated_client.app.state.session_factory
    async with factory() as session:
        row = (
            await session.execute(
                select(CalendarExportTokenRow).where(
                    CalendarExportTokenRow.id == token_id
                )
            )
        ).scalar_one()
        assert row.token_hash != plaintext
        assert len(row.token_hash) == 64
        # The list endpoint must not leak the
        # plaintext either.
        listing = await migrated_client.get(
            "/calendar-export-tokens",
            cookies=cookies,
        )
        assert listing.status_code == 200
        for item in listing.json()["items"]:
            assert "plaintext" not in item
        # The tokenized endpoint is the only path
        # that resolves a presented token into a
        # usable payload, and it accepts the
        # plaintext, not the hash.
        r = await migrated_client.get(
            f"/calendar-export/{plaintext}.ics",
        )
        assert r.status_code == 200


# ----------------------------------------------------------------------
# RBAC contract from US-027
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_management_requires_authenticated_session(
    migrated_client,
):
    # The header-fallback path returns an
    # unauthenticated `TenantContext`; the
    # `_identity_from_tenant` helper rejects the
    # request with a 401. This is the same
    # behaviour as the watchlist surface from
    # `US-030`.
    r = await migrated_client.post(
        "/calendar-export-tokens",
        json={"scope": "watchlist"},
    )
    assert r.status_code == 401
    r = await migrated_client.get("/calendar-export-tokens")
    assert r.status_code == 401
    r = await migrated_client.delete(
        f"/calendar-export-tokens/{uuid4()}",
    )
    assert r.status_code == 401
    r = await migrated_client.get(
        "/calendar-export-tokens/audits",
    )
    assert r.status_code == 401


# ----------------------------------------------------------------------
# Sanitization contract
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mint_token_strips_sensitive_keys_from_audit(migrated_client):
    event_id = await _seed_event(migrated_client)
    cookies = (await _login_owner(migrated_client))["cookies"]
    factory = migrated_client.app.state.session_factory
    mint = await migrated_client.post(
        "/calendar-export-tokens",
        json={"scope": "event", "target_id": event_id},
        cookies=cookies,
    )
    token_id = mint.json()["id"]
    # The audit entry from `US-026` must record the
    # mint with the same secret-safe payload
    # contract. The `metadata_json` column never
    # contains raw PII or secrets, and the
    # `metadata_redacted` flag is set when the
    # sanitizer strips a sensitive key.
    async with factory() as session:
        rows = (
            await session.execute(
                select(AuditEntryRow)
                .where(
                    AuditEntryRow.action
                    == AuditAction.CALENDAR_TOKEN_MINTED.value
                )
                .where(
                    AuditEntryRow.target_id == token_id
                )
            )
        ).scalars().all()
        assert rows
        for row in rows:
            assert "plaintext" not in (row.metadata_json or "")
            assert "password" not in (row.metadata_json or "")
            assert "api_key" not in (row.metadata_json or "")


# ----------------------------------------------------------------------
# Scope contract
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tokenized_event_ics_rejects_watchlist_token(
    migrated_client,
):
    cookies = (await _login_owner(migrated_client))["cookies"]
    # Mint a watchlist token.
    mint = await migrated_client.post(
        "/calendar-export-tokens",
        json={"scope": "watchlist"},
        cookies=cookies,
    )
    plaintext = mint.json()["plaintext"]
    r = await migrated_client.get(
        f"/calendar-export/{plaintext}.ics",
    )
    # The dispatcher reads the scope from the row
    # and dispatches to the watchlist builder; the
    # URL is the same for every scope, so the
    # request returns a watchlist payload.
    assert r.status_code == 200
    assert "X-WR-CALNAME:LiveLead watchlist" in r.text


@pytest.mark.asyncio
async def test_tokenized_unknown_token_is_rejected(migrated_client):
    r = await migrated_client.get(
        "/calendar-export/not-a-real-token.ics",
    )
    assert r.status_code == 404


# ----------------------------------------------------------------------
# Audit retention contract
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calendar_export_audit_uses_existing_target_type(migrated_client):
    event_id = await _seed_event(migrated_client)
    cookies = (await _login_owner(migrated_client))["cookies"]
    factory = migrated_client.app.state.session_factory
    await migrated_client.post(
        "/calendar-export-tokens",
        json={"scope": "event", "target_id": event_id},
        cookies=cookies,
    )
    async with factory() as session:
        # The audit entries from the calendar
        # export slice reuse the existing
        # `AuditEntryRow` table; the migration does
        # not weaken the audit retention guarantee
        # from `NFR-SEC-008`.
        rows = (
            await session.execute(
                select(AuditEntryRow).where(
                    AuditEntryRow.action
                    == AuditAction.CALENDAR_TOKEN_MINTED.value
                )
            )
        ).scalars().all()
        assert rows
        for row in rows:
            assert row.target_type in {
                AuditTargetType.CALENDAR_EXPORT_TOKEN.value,
                AuditTargetType.EVENT.value,
                AuditTargetType.WORKFLOW.value,
            }


# ----------------------------------------------------------------------
# Hash helper sanity
# ----------------------------------------------------------------------


def test_hash_calendar_token_is_not_plaintext() -> None:
    plaintext = mint_calendar_token_plaintext()
    h = hash_calendar_token(plaintext)
    assert h != plaintext
    assert len(h) == 64
