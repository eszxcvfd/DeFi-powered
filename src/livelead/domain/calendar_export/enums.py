"""Event calendar export domain enums (US-045).

Closed enumerations that the calendar export service, the
`CalendarExportFormatter`, and the audit entry shape share. The values
are persisted as strings so the migration can use stable SQL `VARCHAR`
columns; the application layer normalises back to these enums at the
boundary.

The vocabulary follows `docs/decisions/0023-event-calendar-export-ics-baseline.md`
and the calendar `STATUS` mapping from `SPEC.md` `FR-NOR-003` and
`FR-EVT-005`:

- `UPCOMING`  -> `TENTATIVE`
- `LIVE`      -> `CONFIRMED`
- `ENDED`     -> `CANCELLED`
"""

from __future__ import annotations

from enum import StrEnum


class CalendarScope(StrEnum):
    """Closed set of calendar export scopes the service accepts.

    The token table stores the `scope` as a string; the
    service normalises back to this enum at the boundary.
    New scopes cannot be added without first extending
    the `CalendarExportService` and the audit entry
    shape.
    """

    EVENT = "event"
    WATCHLIST = "watchlist"
    EVENT_FILTER = "event_filter"


class CalendarExportResult(StrEnum):
    """Outcome classification for a calendar export attempt.

    The bounded path returns one of these values from
    `CalendarExportService.resolve_token` and from the
    current-user ICS endpoints; the audit entry records
    the same string so the admin audit log filter from
    `US-026` can reason about the calendar export
    surface.
    """

    SUCCESS = "success"
    FORBIDDEN = "forbidden"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID_SCOPE = "invalid_scope"
    NOT_FOUND = "not_found"


class CalendarTimeState(StrEnum):
    """Canonical event time state classification (US-005 / FR-NOR-003).

    The bounded path classifies each canonical event into
    one of the three states so the formatter can map the
    state to the calendar `STATUS` field.
    """

    UPCOMING = "upcoming"
    LIVE = "live"
    ENDED = "ended"


# ---------------------------------------------------------------------------
# Calendar STATUS mapping
# ---------------------------------------------------------------------------


CALENDAR_STATUS_BY_TIME_STATE: dict[CalendarTimeState, str] = {
    CalendarTimeState.UPCOMING: "TENTATIVE",
    CalendarTimeState.LIVE: "CONFIRMED",
    CalendarTimeState.ENDED: "CANCELLED",
}

SUPPORTED_CALENDAR_SCOPES: tuple[CalendarScope, ...] = (
    CalendarScope.EVENT,
    CalendarScope.WATCHLIST,
    CalendarScope.EVENT_FILTER,
)


__all__ = [
    "CALENDAR_STATUS_BY_TIME_STATE",
    "CalendarExportResult",
    "CalendarScope",
    "CalendarTimeState",
    "SUPPORTED_CALENDAR_SCOPES",
]
