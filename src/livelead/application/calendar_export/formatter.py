"""ICS line-set formatter for the event calendar export (US-045).

The formatter is the only place that owns the calendar
`STATUS` mapping and the `X-LIVELEAD-EVENT-ID`
extension. The service and the test fixtures call it
from a single seam. The formatter follows the closed
mapping from `SPEC.md` `FR-NOR-003`:

- `UPCOMING`  -> `TENTATIVE`
- `LIVE`      -> `CONFIRMED`
- `ENDED`     -> `CANCELLED`

The line set is intentionally narrow: `UID`, `SUMMARY`,
`DESCRIPTION`, `URL`, `LOCATION`, `DTSTART`, `DTEND`,
`DTSTAMP`, `STATUS`, and `X-LIVELEAD-EVENT-ID`. A later
calendar auth story can add additional extensions
behind the same `CalendarExportFormatter` seam.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from livelead.domain.calendar_export.enums import (
    CALENDAR_STATUS_BY_TIME_STATE,
    CalendarTimeState,
)
from livelead.domain.calendar_export.models import (
    CalendarExportFilter,
    EventTimeStateView,
)


# Maximum line length allowed by the ICS spec; longer
# lines are wrapped at logical boundaries. The value
# matches the common 75-octet limit.
_MAX_LINE_LENGTH = 75


def _format_ics_timestamp(value: datetime) -> str:
    """Format a UTC datetime as an ICS timestamp (YYYYMMDDTHHMMSSZ)."""

    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    value = value.astimezone(UTC)
    return value.strftime("%Y%m%dT%H%M%SZ")


def _ics_escape(text: str) -> str:
    """Escape a string for safe inclusion in an ICS text field."""

    candidate = str(text or "")
    candidate = candidate.replace("\\", "\\\\")
    candidate = candidate.replace(";", "\\;")
    candidate = candidate.replace(",", "\\,")
    candidate = candidate.replace("\r\n", "\\n")
    candidate = candidate.replace("\n", "\\n")
    return candidate


def _fold_line(line: str) -> str:
    """Fold a long ICS line into a multi-line continuation block."""

    if len(line.encode("utf-8")) <= _MAX_LINE_LENGTH:
        return line
    chunks: list[str] = []
    current = ""
    for ch in line:
        candidate = current + ch
        if len(candidate.encode("utf-8")) > _MAX_LINE_LENGTH - 1 and current:
            chunks.append(current)
            current = ch
        else:
            current = candidate
    if current:
        chunks.append(current)
    folded = chunks[0]
    for chunk in chunks[1:]:
        folded += "\r\n " + chunk
    return folded


def format_uid(event_id: str, organization_id: str) -> str:
    """Return a stable UID for a calendar event.

    The UID embeds the organization id and the event id
    so a later shared-watchlist story can extend the
    payload without a UID collision.
    """

    return f"{event_id}@{organization_id}.livelead"


def format_calendar_name(
    scope_value: str,
    *,
    filter_label: str = "",
) -> str:
    """Return the calendar `NAME` and `X-WR-CALNAME` for the feed."""

    if scope_value == "watchlist":
        return "LiveLead watchlist"
    if scope_value == "event_filter":
        suffix = filter_label or "default"
        return f"LiveLead events ({suffix})"
    return "LiveLead events"


def format_event(
    *,
    event_id: str,
    organization_id: str,
    title: str,
    description: str,
    source_url: str,
    location: str,
    time_state: CalendarTimeState,
    starts_at: datetime | None,
    ended_at: datetime | None,
    dtstamp: datetime | None = None,
) -> list[str]:
    """Return the ICS line set for one event."""

    stamp = _format_ics_timestamp(dtstamp or datetime.now(UTC))
    status = CALENDAR_STATUS_BY_TIME_STATE.get(time_state, "TENTATIVE")
    lines: list[str] = ["BEGIN:VEVENT"]
    lines.append(f"UID:{_ics_escape(format_uid(event_id, organization_id))}")
    lines.append(f"DTSTAMP:{stamp}")
    if starts_at is not None:
        lines.append(f"DTSTART:{_format_ics_timestamp(starts_at)}")
    if ended_at is not None:
        lines.append(f"DTEND:{_format_ics_timestamp(ended_at)}")
    if title:
        lines.append(f"SUMMARY:{_ics_escape(title)}")
    description_text = description or ""
    if source_url:
        if description_text:
            description_text = description_text + "\n\n"
        description_text = (
            description_text
            + f"Source: {source_url}\nEvent id: {event_id}"
        )
    if description_text:
        lines.append(f"DESCRIPTION:{_ics_escape(description_text)}")
    if source_url:
        lines.append(f"URL:{_ics_escape(source_url)}")
    if location:
        lines.append(f"LOCATION:{_ics_escape(location)}")
    lines.append(f"STATUS:{status}")
    lines.append(f"X-LIVELEAD-EVENT-ID:{_ics_escape(event_id)}")
    lines.append("END:VEVENT")
    return lines


def build_calendar(
    *,
    scope_value: str,
    organization_id: str,
    events: list[EventTimeStateView],
    titles: dict[str, str],
    descriptions: dict[str, str],
    source_urls: dict[str, str],
    locations: dict[str, str],
    dtstamp: datetime | None = None,
    filter_label: str = "",
) -> str:
    """Build the full VCALENDAR payload for the bounded export.

    The `events` list is the time-ordered projection. The
    per-event dictionaries carry the denormalized fields
    the formatter needs; the service is the only place
    that knows where the dictionaries come from.
    """

    stamp = _format_ics_timestamp(dtstamp or datetime.now(UTC))
    name = format_calendar_name(scope_value, filter_label=filter_label)
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LiveLead//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_ics_escape(name)}",
        f"X-WR-TIMEZONE:UTC",
        f"X-LIVELEAD-CALENDAR-DTSTAMP:{stamp}",
    ]
    for view in events:
        event_id = str(view.event_id)
        lines.extend(
            format_event(
                event_id=event_id,
                organization_id=str(organization_id),
                title=titles.get(event_id, ""),
                description=descriptions.get(event_id, ""),
                source_url=source_urls.get(event_id, ""),
                location=locations.get(event_id, ""),
                time_state=view.time_state,
                starts_at=view.starts_at,
                ended_at=view.ended_at,
                dtstamp=dtstamp,
            )
        )
    lines.append("END:VCALENDAR")
    folded_lines = [_fold_line(line) for line in lines]
    return "\r\n".join(folded_lines) + "\r\n"


def classify_time_state(
    *,
    event_id: str,
    starts_at: datetime | None,
    ended_at: datetime | None,
    now: datetime | None = None,
) -> EventTimeStateView:
    """Classify a canonical event into the closed time-state set.

    The classification is intentionally narrow so the
    `X-LIVELEAD-EVENT-ID` extension and the calendar
    `STATUS` field stay stable. A future story can
    extend the classification with explicit
    acceptance criteria.
    """

    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    started = starts_at
    if started is not None and started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    ended = ended_at
    if ended is not None and ended.tzinfo is None:
        ended = ended.replace(tzinfo=UTC)
    if started is None:
        state = CalendarTimeState.UPCOMING
    elif reference < started:
        state = CalendarTimeState.UPCOMING
    elif ended is not None and reference >= ended:
        state = CalendarTimeState.ENDED
    else:
        state = CalendarTimeState.LIVE
    return EventTimeStateView(
        event_id=str(event_id),
        time_state=state,
        starts_at=started,
        ended_at=ended,
    )


def filter_label(filter_obj: CalendarExportFilter) -> str:
    """Return the human-readable label for a filter payload."""

    return filter_obj.label_text()


__all__ = [
    "build_calendar",
    "classify_time_state",
    "filter_label",
    "format_calendar_name",
    "format_event",
    "format_uid",
]
