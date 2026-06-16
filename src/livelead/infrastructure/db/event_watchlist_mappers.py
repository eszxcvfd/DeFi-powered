"""Map watchlist ORM rows to domain dataclasses (US-030)."""

from __future__ import annotations

from uuid import UUID

from livelead.domain.event_watchlist.models import (
    EventWatchlistEntry,
    EventWatchlistHistoryEntry,
    WatchlistAction,
)
from livelead.infrastructure.db.models import EventWatchlistEntryRow, EventWatchlistHistoryRow


def row_to_entry(row: EventWatchlistEntryRow) -> EventWatchlistEntry:
    return EventWatchlistEntry(
        id=UUID(row.id),
        organization_id=UUID(row.organization_id),
        user_id=UUID(row.user_id),
        event_id=UUID(row.event_id),
        reminder_at=_parse_iso(row.reminder_at),
        reminder_note=row.reminder_note or "",
        last_actor_id=row.last_actor_id or "",
        last_actor_role=row.last_actor_role or "",
        last_action_at=row.last_action_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def row_to_history(row: EventWatchlistHistoryRow) -> EventWatchlistHistoryEntry:
    return EventWatchlistHistoryEntry(
        id=UUID(row.id),
        organization_id=UUID(row.organization_id),
        user_id=UUID(row.user_id),
        event_id=UUID(row.event_id),
        entry_id=UUID(row.entry_id) if row.entry_id else None,
        action=WatchlistAction(row.action),
        actor_id=row.actor_id or "",
        actor_role=row.actor_role or "",
        from_reminder_at=row.from_reminder_at,
        to_reminder_at=row.to_reminder_at,
        note=row.note or "",
        created_at=row.created_at,
    )


def _parse_iso(raw: str | None):
    if not raw:
        return None
    # Round-trip through the domain parser to keep timezone handling
    # in one place. The history and entry rows store the string we
    # accepted from the API plus a normalized ISO string, so a
    # re-parse is safe and idempotent.
    from datetime import datetime

    candidate = raw.strip()
    if not candidate:
        return None
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


__all__ = ["row_to_entry", "row_to_history"]
