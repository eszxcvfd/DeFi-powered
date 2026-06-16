"""Unit tests for the event watchlist domain helpers (US-030)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from livelead.domain.event_watchlist.models import (
    WatchlistReminderStatus,
    classify_reminder_status,
    parse_reminder_at,
    serialize_reminder_at,
)


def test_parse_reminder_at_accepts_naive_iso():
    parsed = parse_reminder_at("2026-07-01T09:00:00")
    assert parsed is not None
    assert parsed.tzinfo is not None
    assert parsed.year == 2026 and parsed.month == 7 and parsed.day == 1


def test_parse_reminder_at_accepts_zulu():
    parsed = parse_reminder_at("2026-07-01T09:00:00Z")
    assert parsed is not None
    assert parsed.utcoffset() == timedelta(0)


def test_parse_reminder_at_blank_returns_none():
    assert parse_reminder_at("") is None
    assert parse_reminder_at("   ") is None
    assert parse_reminder_at(None) is None


def test_parse_reminder_at_invalid_raises():
    with pytest.raises(ValueError):
        parse_reminder_at("not-a-date")


def test_serialize_reminder_at_round_trip():
    original = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    text = serialize_reminder_at(original)
    assert text is not None
    assert text.endswith("Z")
    parsed = parse_reminder_at(text)
    assert parsed == original


def test_classify_reminder_status_no_reminder_is_scheduled():
    assert classify_reminder_status(None) == WatchlistReminderStatus.SCHEDULED


def test_classify_reminder_status_overdue():
    now = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    past = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    assert classify_reminder_status(past, now=now) == WatchlistReminderStatus.OVERDUE


def test_classify_reminder_status_future_is_scheduled():
    now = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    future = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    assert classify_reminder_status(future, now=now) == WatchlistReminderStatus.SCHEDULED
