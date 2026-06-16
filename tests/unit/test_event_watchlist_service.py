"""Unit tests for the EventWatchlistService orchestration (US-030)."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.event_watchlist import (
    EventWatchlistService,
    WatchlistValidationError,
)
from livelead.domain.event_watchlist.models import (
    EventWatchState,
    WatchlistAction,
    WatchlistReminderStatus,
)
from livelead.infrastructure.db.models import (
    Base,
    CampaignRow,
    EventRow,
    EventWatchlistEntryRow,
    OrganizationRow,
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


async def _seed(
    session: AsyncSession,
) -> tuple[UUID, UUID, UUID, UUID]:
    org_id = uuid4()
    user_id = uuid4()
    other_user_id = uuid4()
    event_id = uuid4()
    now = datetime.now(UTC)
    campaign_id = uuid4()
    session.add(
        OrganizationRow(
            id=str(org_id),
            name="Acme",
            created_at=now,
        )
    )
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
async def test_upsert_is_idempotent_and_updates_in_place(session: AsyncSession) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventWatchlistService(session)
    result1 = await svc.upsert(
        organization_id=org_id,
        user_id=user_id,
        actor_id=str(user_id),
        actor_role="analyst",
        event_id=event_id,
        reminder_at_raw=None,
    )
    assert result1.created is True
    assert result1.entry.reminder_at is None
    assert result1.history.action == WatchlistAction.WATCHED
    entry_id = result1.entry.id

    result2 = await svc.upsert(
        organization_id=org_id,
        user_id=user_id,
        actor_id=str(user_id),
        actor_role="analyst",
        event_id=event_id,
        reminder_at_raw=None,
    )
    assert result2.created is False
    assert result2.entry.id == entry_id
    assert result2.history.action == WatchlistAction.WATCHED


@pytest.mark.asyncio
async def test_reminder_set_then_changed_then_cleared(session: AsyncSession) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventWatchlistService(session)

    await svc.upsert(
        organization_id=org_id,
        user_id=user_id,
        actor_id=str(user_id),
        actor_role="analyst",
        event_id=event_id,
        reminder_at_raw=None,
    )
    new_reminder = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    set_result = await svc.upsert(
        organization_id=org_id,
        user_id=user_id,
        actor_id=str(user_id),
        actor_role="analyst",
        event_id=event_id,
        reminder_at_raw=new_reminder,
        reminder_note="check logistics",
    )
    assert set_result.history.action == WatchlistAction.REMINDER_SET
    assert set_result.entry.reminder_note == "check logistics"

    changed = (datetime.now(UTC) + timedelta(days=5)).isoformat()
    changed_result = await svc.upsert(
        organization_id=org_id,
        user_id=user_id,
        actor_id=str(user_id),
        actor_role="analyst",
        event_id=event_id,
        reminder_at_raw=changed,
    )
    assert changed_result.history.action == WatchlistAction.REMINDER_CHANGED

    cleared = await svc.upsert(
        organization_id=org_id,
        user_id=user_id,
        actor_id=str(user_id),
        actor_role="analyst",
        event_id=event_id,
        reminder_at_raw=None,
    )
    assert cleared.history.action == WatchlistAction.REMINDER_CLEARED
    assert cleared.entry.reminder_at is None


@pytest.mark.asyncio
async def test_invalid_reminder_raises_validation_error(session: AsyncSession) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventWatchlistService(session)
    with pytest.raises(WatchlistValidationError):
        await svc.upsert(
            organization_id=org_id,
            user_id=user_id,
            actor_id=str(user_id),
            actor_role="analyst",
            event_id=event_id,
            reminder_at_raw="not-a-timestamp",
        )


@pytest.mark.asyncio
async def test_remove_unknown_entry_is_noop(session: AsyncSession) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventWatchlistService(session)
    result = await svc.remove(
        organization_id=org_id,
        user_id=user_id,
        actor_id=str(user_id),
        actor_role="analyst",
        event_id=event_id,
    )
    assert result.removed is False
    assert result.history is None


@pytest.mark.asyncio
async def test_remove_existing_entry_returns_history(session: AsyncSession) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventWatchlistService(session)
    await svc.upsert(
        organization_id=org_id,
        user_id=user_id,
        actor_id=str(user_id),
        actor_role="analyst",
        event_id=event_id,
        reminder_at_raw=None,
    )
    result = await svc.remove(
        organization_id=org_id,
        user_id=user_id,
        actor_id=str(user_id),
        actor_role="analyst",
        event_id=event_id,
    )
    assert result.removed is True
    assert result.history is not None
    assert result.history.action == WatchlistAction.UNWATCHED


@pytest.mark.asyncio
async def test_other_user_watch_does_not_leak(session: AsyncSession) -> None:
    org_id, user_id, other_user_id, event_id = await _seed(session)
    svc = EventWatchlistService(session)
    await svc.upsert(
        organization_id=org_id,
        user_id=other_user_id,
        actor_id=str(other_user_id),
        actor_role="analyst",
        event_id=event_id,
        reminder_at_raw=None,
    )
    state = await svc.get_state(org_id, user_id, event_id)
    assert state.is_watched is False
    assert state.watchlist_entry_id is None
    assert state.reminder_status == WatchlistReminderStatus.NOT_WATCHED


@pytest.mark.asyncio
async def test_project_state_returns_watch_for_only_current_user(session: AsyncSession) -> None:
    org_id, user_id, other_user_id, event_id = await _seed(session)
    svc = EventWatchlistService(session)
    future = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    await svc.upsert(
        organization_id=org_id,
        user_id=other_user_id,
        actor_id=str(other_user_id),
        actor_role="analyst",
        event_id=event_id,
        reminder_at_raw=future,
    )
    projection = await svc.project_state(org_id, user_id, [event_id])
    assert projection[event_id].is_watched is False
    own_projection = await svc.project_state(org_id, other_user_id, [event_id])
    assert own_projection[event_id].is_watched is True
    assert own_projection[event_id].reminder_status == WatchlistReminderStatus.SCHEDULED


@pytest.mark.asyncio
async def test_evaluate_reminder_eligibility_returns_overdue_only(session: AsyncSession) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventWatchlistService(session)
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    future = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    await svc.upsert(
        organization_id=org_id,
        user_id=user_id,
        actor_id=str(user_id),
        actor_role="analyst",
        event_id=event_id,
        reminder_at_raw=past,
    )
    eligible = await svc.evaluate_reminder_eligibility(org_id)
    assert len(eligible) == 1
    assert eligible[0].status == WatchlistReminderStatus.OVERDUE
    # Setting the reminder to the future hides it from the eligibility list.
    await svc.upsert(
        organization_id=org_id,
        user_id=user_id,
        actor_id=str(user_id),
        actor_role="analyst",
        event_id=event_id,
        reminder_at_raw=future,
    )
    eligible_after = await svc.evaluate_reminder_eligibility(org_id)
    assert eligible_after == []


@pytest.mark.asyncio
async def test_unique_constraint_enforced_by_db(session: AsyncSession) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    now = datetime.now(UTC)
    session.add_all(
        [
            EventWatchlistEntryRow(
                id=str(uuid4()),
                organization_id=str(org_id),
                user_id=str(user_id),
                event_id=str(event_id),
                reminder_at=None,
                reminder_note="",
                last_actor_id=str(user_id),
                last_actor_role="analyst",
                last_action_at=now,
                created_at=now,
                updated_at=now,
            ),
            EventWatchlistEntryRow(
                id=str(uuid4()),
                organization_id=str(org_id),
                user_id=str(user_id),
                event_id=str(event_id),
                reminder_at=None,
                reminder_note="",
                last_actor_id=str(user_id),
                last_actor_role="analyst",
                last_action_at=now,
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    with pytest.raises(Exception):
        await session.flush()


@pytest.mark.asyncio
async def test_history_rows_recorded_in_order(session: AsyncSession) -> None:
    org_id, user_id, _other, event_id = await _seed(session)
    svc = EventWatchlistService(session)
    await svc.upsert(
        organization_id=org_id,
        user_id=user_id,
        actor_id=str(user_id),
        actor_role="analyst",
        event_id=event_id,
        reminder_at_raw=None,
    )
    reminder = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    await svc.upsert(
        organization_id=org_id,
        user_id=user_id,
        actor_id=str(user_id),
        actor_role="analyst",
        event_id=event_id,
        reminder_at_raw=reminder,
    )
    await svc.remove(
        organization_id=org_id,
        user_id=user_id,
        actor_id=str(user_id),
        actor_role="analyst",
        event_id=event_id,
    )
    history = await svc._history.list_for_event(org_id, user_id, event_id, limit=10)  # noqa: SLF001
    actions = [h.action for h in history]
    assert actions[0] == WatchlistAction.UNWATCHED
    assert WatchlistAction.WATCHED in actions
    assert WatchlistAction.REMINDER_SET in actions


def test_event_watch_state_not_watched_factory() -> None:
    state = EventWatchState.not_watched(UUID(int=1))
    assert state.is_watched is False
    assert state.watchlist_entry_id is None
    assert state.reminder_status == WatchlistReminderStatus.NOT_WATCHED
