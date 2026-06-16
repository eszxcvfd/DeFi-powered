"""Event watchlist persistence repositories (US-030).

The repository owns every read and write for
``event_watchlist_entries`` and ``event_watchlist_history``. All
methods take ``organization_id`` first so tenant isolation is
mandatory at the data layer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.event_watchlist.models import (
    EventWatchlistEntry,
    EventWatchlistHistoryEntry,
    WatchedEventListItem,
    WatchlistAction,
    WatchlistReminderStatus,
    classify_reminder_status,
    serialize_reminder_at,
)
from livelead.infrastructure.db.event_watchlist_mappers import row_to_entry, row_to_history
from livelead.infrastructure.db.models import (
    CampaignRow,
    EventRow,
    EventWatchlistEntryRow,
    EventWatchlistHistoryRow,
)


def _now() -> datetime:
    return datetime.now(UTC)


class EventWatchlistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_entry(
        self, organization_id: UUID, user_id: UUID, event_id: UUID
    ) -> EventWatchlistEntry | None:
        result = await self._session.execute(
            select(EventWatchlistEntryRow).where(
                and_(
                    EventWatchlistEntryRow.organization_id == str(organization_id),
                    EventWatchlistEntryRow.user_id == str(user_id),
                    EventWatchlistEntryRow.event_id == str(event_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        return row_to_entry(row) if row else None

    async def get_entry_by_id(
        self, organization_id: UUID, entry_id: UUID
    ) -> EventWatchlistEntry | None:
        result = await self._session.execute(
            select(EventWatchlistEntryRow).where(
                and_(
                    EventWatchlistEntryRow.id == str(entry_id),
                    EventWatchlistEntryRow.organization_id == str(organization_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        return row_to_entry(row) if row else None

    async def upsert_entry(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        event_id: UUID,
        reminder_at: datetime | None,
        reminder_note: str,
        actor_id: str,
        actor_role: str,
    ) -> EventWatchlistEntry:
        existing = await self.get_entry(organization_id, user_id, event_id)
        now = _now()
        if existing:
            result = await self._session.execute(
                select(EventWatchlistEntryRow).where(
                    EventWatchlistEntryRow.id == str(existing.id)
                )
            )
            row = result.scalar_one()
            row.reminder_at = serialize_reminder_at(reminder_at)
            row.reminder_note = reminder_note[:500]
            row.last_actor_id = actor_id
            row.last_actor_role = actor_role
            row.last_action_at = now
            row.updated_at = now
            self._session.add(row)
            await self._session.flush()
            return row_to_entry(row)
        row = EventWatchlistEntryRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            user_id=str(user_id),
            event_id=str(event_id),
            reminder_at=serialize_reminder_at(reminder_at),
            reminder_note=reminder_note[:500],
            last_actor_id=actor_id,
            last_actor_role=actor_role,
            last_action_at=now,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_entry(row)

    async def delete_entry(
        self, organization_id: UUID, user_id: UUID, event_id: UUID
    ) -> bool:
        result = await self._session.execute(
            select(EventWatchlistEntryRow).where(
                and_(
                    EventWatchlistEntryRow.organization_id == str(organization_id),
                    EventWatchlistEntryRow.user_id == str(user_id),
                    EventWatchlistEntryRow.event_id == str(event_id),
                )
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self._session.delete(row)
        await self._session.flush()
        return True

    async def list_for_user(
        self,
        organization_id: UUID,
        user_id: UUID,
        *,
        with_reminder: bool | None = None,
        has_reminder: bool | None = None,
        limit: int = 100,
    ) -> list[WatchedEventListItem]:
        """List watched events for the current user with optional filters.

        ``with_reminder=True`` returns only entries that have a
        non-null ``reminder_at``; ``with_reminder=False`` returns
        only entries that do not. ``has_reminder`` is the explicit
        alias used by the API surface. ``None`` returns every entry.
        """

        stmt = (
            select(EventWatchlistEntryRow, EventRow, CampaignRow)
            .join(EventRow, EventRow.id == EventWatchlistEntryRow.event_id)
            .join(CampaignRow, CampaignRow.id == EventRow.campaign_id)
            .where(
                and_(
                    EventWatchlistEntryRow.organization_id == str(organization_id),
                    EventWatchlistEntryRow.user_id == str(user_id),
                )
            )
            .order_by(desc(EventWatchlistEntryRow.updated_at))
            .limit(max(1, min(int(limit), 500)))
        )
        if has_reminder is True:
            stmt = stmt.where(EventWatchlistEntryRow.reminder_at.is_not(None))
        elif has_reminder is False:
            stmt = stmt.where(EventWatchlistEntryRow.reminder_at.is_(None))
        result = await self._session.execute(stmt)
        rows = result.all()
        out: list[WatchedEventListItem] = []
        for entry_row, event_row, campaign_row in rows:
            entry = row_to_entry(entry_row)
            out.append(
                WatchedEventListItem(
                    entry_id=entry.id,
                    event_id=entry.event_id,
                    campaign_id=UUID(event_row.id),
                    campaign_name=campaign_row.name or "",
                    canonical_title=event_row.canonical_title,
                    source_url=event_row.source_url,
                    observed_at=event_row.observed_at,
                    region=event_row.region or "",
                    starts_at=event_row.starts_at,
                    reminder_at=entry.reminder_at,
                    reminder_status=entry.reminder_status(),
                    reminder_note=entry.reminder_note,
                    last_action_at=entry.last_action_at,
                )
            )
        return out

    async def list_projection_for_events(
        self,
        organization_id: UUID,
        user_id: UUID,
        event_ids: Iterable[UUID],
    ) -> dict[UUID, EventWatchlistEntry]:
        ids = [str(e) for e in event_ids]
        if not ids:
            return {}
        result = await self._session.execute(
            select(EventWatchlistEntryRow).where(
                and_(
                    EventWatchlistEntryRow.organization_id == str(organization_id),
                    EventWatchlistEntryRow.user_id == str(user_id),
                    EventWatchlistEntryRow.event_id.in_(ids),
                )
            )
        )
        return {row_to_entry(r).event_id: row_to_entry(r) for r in result.scalars().all()}

    async def list_projection_for_user(
        self, organization_id: UUID, user_id: UUID
    ) -> dict[UUID, EventWatchlistEntry]:
        result = await self._session.execute(
            select(EventWatchlistEntryRow).where(
                and_(
                    EventWatchlistEntryRow.organization_id == str(organization_id),
                    EventWatchlistEntryRow.user_id == str(user_id),
                )
            )
        )
        return {row_to_entry(r).event_id: row_to_entry(r) for r in result.scalars().all()}

    async def list_open_reminders(
        self, organization_id: UUID, *, now: datetime | None = None
    ) -> list[EventWatchlistEntry]:
        reference = now or _now()
        result = await self._session.execute(
            select(EventWatchlistEntryRow).where(
                and_(
                    EventWatchlistEntryRow.organization_id == str(organization_id),
                    EventWatchlistEntryRow.reminder_at.is_not(None),
                )
            )
        )
        rows = result.scalars().all()
        out: list[EventWatchlistEntry] = []
        for row in rows:
            if not row.reminder_at:
                continue
            from datetime import datetime as _dt

            try:
                value = _dt.fromisoformat(row.reminder_at.replace("Z", "+00:00"))
            except ValueError:
                continue
            if value <= reference:
                out.append(row_to_entry(row))
        return out


class EventWatchlistHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        event_id: UUID,
        entry_id: UUID | None,
        action: WatchlistAction,
        actor_id: str,
        actor_role: str,
        from_reminder_at: str | None = None,
        to_reminder_at: str | None = None,
        note: str = "",
    ) -> EventWatchlistHistoryEntry:
        now = _now()
        row = EventWatchlistHistoryRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            user_id=str(user_id),
            event_id=str(event_id),
            entry_id=str(entry_id) if entry_id else None,
            action=action.value,
            actor_id=actor_id,
            actor_role=actor_role,
            from_reminder_at=from_reminder_at,
            to_reminder_at=to_reminder_at,
            note=note[:500],
            created_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_history(row)

    async def list_for_event(
        self,
        organization_id: UUID,
        user_id: UUID,
        event_id: UUID,
        *,
        limit: int = 50,
    ) -> list[EventWatchlistHistoryEntry]:
        result = await self._session.execute(
            select(EventWatchlistHistoryRow)
            .where(
                and_(
                    EventWatchlistHistoryRow.organization_id == str(organization_id),
                    EventWatchlistHistoryRow.user_id == str(user_id),
                    EventWatchlistHistoryRow.event_id == str(event_id),
                )
            )
            .order_by(desc(EventWatchlistHistoryRow.created_at))
            .limit(max(1, min(int(limit), 200)))
        )
        return [row_to_history(r) for r in result.scalars().all()]


__all__ = [
    "EventWatchlistHistoryRepository",
    "EventWatchlistRepository",
    "WatchlistReminderStatus",
    "classify_reminder_status",
]
