"""Tests for the calendar export ICS line set formatter (US-045)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from livelead.application.calendar_export.formatter import (
    build_calendar,
    classify_time_state,
    filter_label,
    format_calendar_name,
    format_event,
    format_uid,
)
from livelead.domain.calendar_export.enums import (
    CalendarTimeState,
)
from livelead.domain.calendar_export.models import (
    CalendarExportFilter,
    EventTimeStateView,
)


def test_format_uid_includes_org_and_event() -> None:
    assert (
        format_uid("evt-1", "org-1")
        == "evt-1@org-1.livelead"
    )


def test_format_calendar_name_per_scope() -> None:
    assert (
        format_calendar_name(CalendarTimeState.UPCOMING.value)
        == "LiveLead events"
    )
    assert format_calendar_name("watchlist") == "LiveLead watchlist"
    assert (
        format_calendar_name("event_filter", filter_label="Q3")
        == "LiveLead events (Q3)"
    )


def test_format_event_includes_required_lines() -> None:
    stamp = datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)
    lines = format_event(
        event_id="evt-1",
        organization_id="org-1",
        title="Q3 SaaS Growth",
        description="B2B SaaS growth event",
        source_url="https://example.com/q3",
        location="Online",
        time_state=CalendarTimeState.LIVE,
        starts_at=datetime(2026, 6, 16, 13, 0, 0, tzinfo=UTC),
        ended_at=datetime(2026, 6, 16, 14, 0, 0, tzinfo=UTC),
        dtstamp=stamp,
    )
    joined = "\r\n".join(lines)
    assert "BEGIN:VEVENT" in joined
    assert "END:VEVENT" in joined
    assert "UID:evt-1@org-1.livelead" in joined
    assert "DTSTART:20260616T130000Z" in joined
    assert "DTEND:20260616T140000Z" in joined
    assert "SUMMARY:Q3 SaaS Growth" in joined
    assert "DESCRIPTION:B2B SaaS growth event" in joined
    assert "URL:https://example.com/q3" in joined
    assert "LOCATION:Online" in joined
    assert "STATUS:CONFIRMED" in joined
    assert "X-LIVELEAD-EVENT-ID:evt-1" in joined


def test_format_event_escapes_special_characters() -> None:
    lines = format_event(
        event_id="evt-1",
        organization_id="org-1",
        title="Title with; comma, and newline\nsecond line",
        description="",
        source_url="",
        location="",
        time_state=CalendarTimeState.UPCOMING,
        starts_at=datetime(2026, 6, 16, 13, 0, 0, tzinfo=UTC),
        ended_at=None,
        dtstamp=datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC),
    )
    joined = "\r\n".join(lines)
    assert "Title with\\; comma\\, and newline\\nsecond line" in joined
    assert "STATUS:TENTATIVE" in joined
    assert "DTEND:" not in joined


def test_format_event_omits_dtend_when_missing() -> None:
    lines = format_event(
        event_id="evt-1",
        organization_id="org-1",
        title="T",
        description="",
        source_url="",
        location="",
        time_state=CalendarTimeState.UPCOMING,
        starts_at=datetime(2026, 6, 16, 13, 0, 0, tzinfo=UTC),
        ended_at=None,
    )
    joined = "\r\n".join(lines)
    assert "DTEND:" not in joined


def test_format_event_appends_source_and_event_id_in_description() -> None:
    lines = format_event(
        event_id="evt-1",
        organization_id="org-1",
        title="T",
        description="Existing description",
        source_url="https://example.com/event",
        location="",
        time_state=CalendarTimeState.UPCOMING,
        starts_at=datetime(2026, 6, 16, 13, 0, 0, tzinfo=UTC),
        ended_at=None,
    )
    joined = "\r\n".join(lines)
    assert "Existing description" in joined
    assert "Source: https://example.com/event" in joined
    assert "Event id: evt-1" in joined


def test_classify_time_state_upcoming() -> None:
    now = datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)
    view = classify_time_state(
        event_id="evt-1",
        starts_at=now + timedelta(hours=1),
        ended_at=now + timedelta(hours=2),
        now=now,
    )
    assert view.time_state is CalendarTimeState.UPCOMING


def test_classify_time_state_live() -> None:
    now = datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)
    view = classify_time_state(
        event_id="evt-1",
        starts_at=now - timedelta(hours=1),
        ended_at=now + timedelta(hours=1),
        now=now,
    )
    assert view.time_state is CalendarTimeState.LIVE


def test_classify_time_state_ended() -> None:
    now = datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)
    view = classify_time_state(
        event_id="evt-1",
        starts_at=now - timedelta(hours=2),
        ended_at=now - timedelta(hours=1),
        now=now,
    )
    assert view.time_state is CalendarTimeState.ENDED


def test_classify_time_state_default_upcoming() -> None:
    now = datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)
    view = classify_time_state(
        event_id="evt-1",
        starts_at=None,
        ended_at=None,
        now=now,
    )
    assert view.time_state is CalendarTimeState.UPCOMING


def test_build_calendar_emits_vcalendar_envelope() -> None:
    now = datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)
    view = EventTimeStateView(
        event_id="evt-1",
        time_state=CalendarTimeState.LIVE,
        starts_at=now,
        ended_at=now + timedelta(hours=1),
    )
    body = build_calendar(
        scope_value="watchlist",
        organization_id="org-1",
        events=[view],
        titles={"evt-1": "T"},
        descriptions={},
        source_urls={},
        locations={},
        dtstamp=now,
    )
    assert body.startswith("BEGIN:VCALENDAR\r\n")
    assert body.rstrip("\r\n").endswith("END:VCALENDAR")
    assert "BEGIN:VEVENT" in body
    assert "END:VEVENT" in body
    assert "X-WR-CALNAME:LiveLead watchlist" in body


def test_build_calendar_event_filter_includes_label() -> None:
    now = datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)
    view = EventTimeStateView(
        event_id="evt-1",
        time_state=CalendarTimeState.UPCOMING,
        starts_at=now + timedelta(hours=1),
        ended_at=None,
    )
    body = build_calendar(
        scope_value="event_filter",
        organization_id="org-1",
        events=[view],
        titles={"evt-1": "T"},
        descriptions={},
        source_urls={},
        locations={},
        dtstamp=now,
        filter_label="Q3",
    )
    assert "X-WR-CALNAME:LiveLead events (Q3)" in body


def test_filter_label_prefers_explicit() -> None:
    flt = CalendarExportFilter(campaign_id="cmp-1", label="Q3 focus")
    assert filter_label(flt) == "Q3 focus"


def test_filter_label_composes_when_unlabeled() -> None:
    flt = CalendarExportFilter(campaign_id="cmp-1", industry="fintech")
    assert filter_label(flt) == "campaign=cmp-1, industry=fintech"


def test_filter_label_default_when_empty() -> None:
    assert filter_label(CalendarExportFilter()) == "default"
