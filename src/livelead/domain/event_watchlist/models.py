"""Event watchlist domain types (US-030).

Pure data classes plus a small classification helper. Reminder
parsing is intentionally tolerant: the API accepts an ISO-8601
timestamp (with or without timezone) and reduces it to a UTC
``datetime`` for storage, or ``None`` when the caller is clearing
the reminder.

The reminder summary projected into event list/detail responses
uses three states:

- ``none``: the user is not watching the event.
- ``scheduled``: watched with a reminder timestamp in the future.
- ``overdue``: watched with a reminder timestamp already past.

A watched event without a reminder is reported as ``scheduled``
with ``reminder_at = null`` so the UI can show "Watching" without
forcing a date. The classification never raises on a missing
timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class WatchlistAction(StrEnum):
    """Audit-stable action names for watchlist mutations."""

    WATCHED = "watched"
    UNWATCHED = "unwatched"
    REMINDER_SET = "reminder_set"
    REMINDER_CHANGED = "reminder_changed"
    REMINDER_CLEARED = "reminder_cleared"


class WatchlistReminderStatus(StrEnum):
    """Projection shape for the current-user watch state.

    ``not_watched`` is the only state where the projection is
    missing or implicitly empty. ``scheduled`` covers both "no
    reminder" and "reminder in the future"; ``overdue`` means the
    reminder timestamp is in the past relative to ``now``.
    """

    NOT_WATCHED = "not_watched"
    SCHEDULED = "scheduled"
    OVERDUE = "overdue"


def parse_reminder_at(raw: str | None) -> datetime | None:
    """Parse an ISO-8601 string into a UTC ``datetime`` or return ``None``.

    Accepts trailing ``Z`` and naive timestamps. A blank or
    whitespace-only string is treated as "clear reminder" and yields
    ``None``. Other invalid strings raise ``ValueError`` so callers
    can convert that into a 400 response.
    """

    if raw is None:
        return None
    candidate = raw.strip()
    if not candidate:
        return None
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def serialize_reminder_at(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def classify_reminder_status(
    reminder_at: datetime | None, *, now: datetime | None = None
) -> WatchlistReminderStatus:
    """Reduce the watch entry into a stable status for the UI.

    A non-watched entry should never be classified; the projection
    layer reports ``not_watched`` directly. This helper exists for
    the small set of cases where a watched entry needs to be
    rendered with a status badge.
    """

    if reminder_at is None:
        return WatchlistReminderStatus.SCHEDULED
    reference = now or datetime.now(UTC)
    if reminder_at <= reference:
        return WatchlistReminderStatus.OVERDUE
    return WatchlistReminderStatus.SCHEDULED


@dataclass(frozen=True, slots=True)
class EventWatchlistEntry:
    id: UUID
    organization_id: UUID
    user_id: UUID
    event_id: UUID
    reminder_at: datetime | None
    reminder_note: str
    last_actor_id: str
    last_actor_role: str
    last_action_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def reminder_status(self, *, now: datetime | None = None) -> WatchlistReminderStatus:
        return classify_reminder_status(self.reminder_at, now=now)


@dataclass(frozen=True, slots=True)
class EventWatchlistHistoryEntry:
    id: UUID
    organization_id: UUID
    user_id: UUID
    event_id: UUID
    entry_id: UUID | None
    action: WatchlistAction
    actor_id: str
    actor_role: str
    from_reminder_at: str | None
    to_reminder_at: str | None
    note: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EventWatchState:
    """Per-event projection exposed to event list and detail responses.

    The projection deliberately carries only the current-user
    view. The reminder timestamp is included as a string so the
    frontend can render a localized date without re-parsing.
    """

    event_id: UUID
    is_watched: bool
    watchlist_entry_id: UUID | None
    reminder_at: str | None
    reminder_status: WatchlistReminderStatus
    reminder_note: str
    last_action_at: str | None
    reminder_eligible: bool

    @classmethod
    def not_watched(cls, event_id: UUID) -> "EventWatchState":
        return cls(
            event_id=event_id,
            is_watched=False,
            watchlist_entry_id=None,
            reminder_at=None,
            reminder_status=WatchlistReminderStatus.NOT_WATCHED,
            reminder_note="",
            last_action_at=None,
            reminder_eligible=False,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "is_watched": self.is_watched,
            "watchlist_entry_id": str(self.watchlist_entry_id) if self.watchlist_entry_id else None,
            "reminder_at": self.reminder_at,
            "reminder_status": self.reminder_status.value,
            "reminder_note": self.reminder_note,
            "last_action_at": self.last_action_at,
            "reminder_eligible": self.reminder_eligible,
        }


@dataclass(frozen=True, slots=True)
class WatchedEventListItem:
    """A row in the dedicated watched-events list.

    Carries only the fields the watched-events surface needs. The
    event id is canonical; the rest is denormalized for rendering.
    """

    entry_id: UUID
    event_id: UUID
    campaign_id: UUID
    campaign_name: str
    canonical_title: str
    source_url: str
    observed_at: datetime
    region: str
    starts_at: datetime | None
    reminder_at: datetime | None
    reminder_status: WatchlistReminderStatus
    reminder_note: str
    last_action_at: datetime | None


__all__ = [
    "EventWatchState",
    "EventWatchlistEntry",
    "EventWatchlistHistoryEntry",
    "WatchedEventListItem",
    "WatchlistAction",
    "WatchlistReminderStatus",
    "classify_reminder_status",
    "parse_reminder_at",
    "serialize_reminder_at",
]
