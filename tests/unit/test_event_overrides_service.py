"""Unit tests for the EventOverrideService (US-031)."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.event_overrides import (
    EventOverrideDenied,
    EventOverrideError,
    EventOverrideService,
    can_edit_canonical_event,
)
from livelead.domain.event_overrides.models import (
    OverrideHistoryAction,
    OverrideValueKind,
)
from livelead.domain.identity import Role
from livelead.infrastructure.db.models import (
    Base,
    CampaignRow,
    EventRow,
)
from livelead.infrastructure.db.session import (
    create_engine,
    create_session_factory,
    ensure_sqlite_parent,
)
from livelead.runtime.settings import parse_settings


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "unit.sqlite3"
        settings = parse_settings()
        settings.sqlite_path = db_path
        ensure_sqlite_parent(settings)
        engine = create_engine(settings)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = create_session_factory(engine)
        async with factory() as sess:
            yield sess
        await engine.dispose()


async def _seed(session: AsyncSession) -> tuple[UUID, UUID, UUID, UUID]:
    org_id = uuid4()
    user_id = uuid4()
    other_user_id = uuid4()
    campaign_id = uuid4()
    event_id = uuid4()
    now = datetime.now(UTC)
    session.add(
        CampaignRow(
            id=str(campaign_id),
            organization_id=str(org_id),
            name="Campaign",
            description="",
            target_industry="",
            product_or_service_focus="",
            market_regions_json="[]",
            languages_json="[]",
            timezone="UTC",
            date_start=None,
            date_end=None,
            positive_keywords_json="[]",
            exclude_keywords_json="[]",
            icp_json="{}",
            scoring_weights_json="{}",
            status="active",
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        EventRow(
            id=str(event_id),
            organization_id=str(org_id),
            campaign_id=str(campaign_id),
            canonical_title="EU payments webinar",
            source_url="https://example.com/events/1",
            observed_at=now,
            description="",
            organizer="Org",
            region="EU",
            starts_at=now + timedelta(days=10),
            metadata_json="{}",
            created_at=now,
        )
    )
    await session.flush()
    return org_id, user_id, other_user_id, event_id


@pytest.mark.asyncio
async def test_can_edit_canonical_event_role_gate() -> None:
    assert can_edit_canonical_event(Role.OWNER) is True
    assert can_edit_canonical_event(Role.ADMIN) is True
    assert can_edit_canonical_event(Role.ANALYST) is True
    assert can_edit_canonical_event(Role.SALES_BD) is False
    assert can_edit_canonical_event(Role.REVIEWER) is False
    assert can_edit_canonical_event(Role.COMPLIANCE) is False
    assert can_edit_canonical_event(Role.VIEWER) is False
    assert can_edit_canonical_event(None) is False


@pytest.mark.asyncio
async def test_update_event_fields_is_idempotent_and_appends_history(
    session: AsyncSession,
) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventOverrideService(session)
    result1 = await svc.update_event_fields(
        organization_id=org_id,
        actor_id=str(user_id),
        actor_role=Role.ANALYST,
        event_id=event_id,
        updates={"canonical_title": "EU payments meetup"},
        reason="cleanup",
    )
    assert result1.applied_fields == ["canonical_title"]
    assert result1.history[0].action == OverrideHistoryAction.UPSERTED
    first_history_id = result1.history[0].id

    result2 = await svc.update_event_fields(
        organization_id=org_id,
        actor_id=str(user_id),
        actor_role=Role.ANALYST,
        event_id=event_id,
        updates={"canonical_title": "EU payments meetup v2"},
    )
    assert result2.applied_fields == ["canonical_title"]
    assert result2.history[0].id != first_history_id
    overrides = await svc.list_overrides(org_id, event_id)
    assert len(overrides) == 1
    assert overrides[0].override_value == "EU payments meetup v2"
    assert overrides[0].source_backed_value == "EU payments webinar"


@pytest.mark.asyncio
async def test_canonical_row_reflects_override_immediately(
    session: AsyncSession,
) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventOverrideService(session)
    await svc.update_event_fields(
        organization_id=org_id,
        actor_id=str(user_id),
        actor_role=Role.ANALYST,
        event_id=event_id,
        updates={"organizer": "Acme GmbH", "region": "DACH"},
    )
    await session.commit()
    event = await svc._events.get(event_id, org_id)  # noqa: SLF001
    assert event is not None
    assert event.organizer == "Acme GmbH"
    assert event.region == "DACH"


@pytest.mark.asyncio
async def test_update_event_fields_rejects_unknown_field(
    session: AsyncSession,
) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventOverrideService(session)
    with pytest.raises(EventOverrideError) as exc:
        await svc.update_event_fields(
            organization_id=org_id,
            actor_id=str(user_id),
            actor_role=Role.ANALYST,
            event_id=event_id,
            updates={"id": "nope", "campaign_id": "also-nope"},
        )
    assert "no valid fields" in str(exc.value)


@pytest.mark.asyncio
async def test_update_event_fields_rejects_malformed_timestamp(
    session: AsyncSession,
) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventOverrideService(session)
    with pytest.raises(EventOverrideError) as exc:
        await svc.update_event_fields(
            organization_id=org_id,
            actor_id=str(user_id),
            actor_role=Role.ANALYST,
            event_id=event_id,
            updates={"starts_at": "not-a-timestamp"},
        )
    assert "starts_at" in str(exc.value)


@pytest.mark.asyncio
async def test_update_event_fields_rejects_malformed_url(
    session: AsyncSession,
) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventOverrideService(session)
    with pytest.raises(EventOverrideError) as exc:
        await svc.update_event_fields(
            organization_id=org_id,
            actor_id=str(user_id),
            actor_role=Role.ANALYST,
            event_id=event_id,
            updates={"source_url": "ftp://nope"},
        )
    assert "source_url" in str(exc.value)


@pytest.mark.asyncio
async def test_update_event_fields_denies_non_editor_role(
    session: AsyncSession,
) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventOverrideService(session)
    with pytest.raises(EventOverrideDenied):
        await svc.update_event_fields(
            organization_id=org_id,
            actor_id=str(user_id),
            actor_role=Role.SALES_BD,
            event_id=event_id,
            updates={"canonical_title": "Sales pitch"},
        )


@pytest.mark.asyncio
async def test_clear_override_restores_source_backed_value(
    session: AsyncSession,
) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventOverrideService(session)
    await svc.update_event_fields(
        organization_id=org_id,
        actor_id=str(user_id),
        actor_role=Role.ANALYST,
        event_id=event_id,
        updates={"organizer": "Edited"},
    )
    result = await svc.clear_override(
        organization_id=org_id,
        actor_id=str(user_id),
        actor_role=Role.ANALYST,
        event_id=event_id,
        field="organizer",
    )
    assert result.field == "organizer"
    assert result.restored_value == "Org"
    assert result.history[0].action == OverrideHistoryAction.CLEARED
    remaining = await svc.list_overrides(org_id, event_id)
    assert remaining == []
    event = await svc._events.get(event_id, org_id)  # noqa: SLF001
    assert event is not None
    assert event.organizer == "Org"


@pytest.mark.asyncio
async def test_clear_override_unknown_raises(
    session: AsyncSession,
) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventOverrideService(session)
    with pytest.raises(EventOverrideError):
        await svc.clear_override(
            organization_id=org_id,
            actor_id=str(user_id),
            actor_role=Role.ANALYST,
            event_id=event_id,
            field="canonical_title",
        )


@pytest.mark.asyncio
async def test_clear_override_denies_non_editor(
    session: AsyncSession,
) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventOverrideService(session)
    await svc.update_event_fields(
        organization_id=org_id,
        actor_id=str(user_id),
        actor_role=Role.ANALYST,
        event_id=event_id,
        updates={"organizer": "Edited"},
    )
    with pytest.raises(EventOverrideDenied):
        await svc.clear_override(
            organization_id=org_id,
            actor_id=str(user_id),
            actor_role=Role.VIEWER,
            event_id=event_id,
            field="organizer",
        )


@pytest.mark.asyncio
async def test_history_lists_appends_in_descending_order(
    session: AsyncSession,
) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventOverrideService(session)
    await svc.update_event_fields(
        organization_id=org_id,
        actor_id=str(user_id),
        actor_role=Role.ANALYST,
        event_id=event_id,
        updates={"organizer": "One"},
    )
    await svc.update_event_fields(
        organization_id=org_id,
        actor_id=str(user_id),
        actor_role=Role.ANALYST,
        event_id=event_id,
        updates={"organizer": "Two"},
    )
    await svc.clear_override(
        organization_id=org_id,
        actor_id=str(user_id),
        actor_role=Role.ANALYST,
        event_id=event_id,
        field="organizer",
    )
    history = await svc.list_history(org_id, event_id)
    actions = [h.action for h in history]
    assert actions[0] == OverrideHistoryAction.CLEARED
    assert actions.count(OverrideHistoryAction.UPSERTED) == 2


@pytest.mark.asyncio
async def test_protected_field_list_contains_active_overrides(
    session: AsyncSession,
) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventOverrideService(session)
    await svc.update_event_fields(
        organization_id=org_id,
        actor_id=str(user_id),
        actor_role=Role.ANALYST,
        event_id=event_id,
        updates={"organizer": "Edited", "region": "DACH"},
    )
    protected = await svc.list_protected_fields(org_id, event_id)
    assert protected == {"organizer", "region"}


@pytest.mark.asyncio
async def test_projection_marks_overridden_and_source_values(
    session: AsyncSession,
) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventOverrideService(session)
    await svc.update_event_fields(
        organization_id=org_id,
        actor_id=str(user_id),
        actor_role=Role.ANALYST,
        event_id=event_id,
        updates={"region": "DACH"},
    )
    provenance = await svc.project_field_provenance(org_id, event_id)
    region_entry = next(p for p in provenance if p.field == "region")
    assert region_entry.is_overridden is True
    assert region_entry.effective_value == "DACH"
    assert region_entry.source_value == "EU"
    assert region_entry.actor_role == "analyst"

    organizer_entry = next(p for p in provenance if p.field == "organizer")
    assert organizer_entry.is_overridden is False
    assert organizer_entry.effective_value == "Org"
    assert organizer_entry.source_value == "Org"
