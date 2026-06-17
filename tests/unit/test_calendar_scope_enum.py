"""Tests for the event calendar export enums (US-045)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from livelead.domain.calendar_export.enums import (
    CALENDAR_STATUS_BY_TIME_STATE,
    CalendarExportResult,
    CalendarScope,
    CalendarTimeState,
    SUPPORTED_CALENDAR_SCOPES,
)


def test_calendar_scope_is_closed() -> None:
    assert set(SUPPORTED_CALENDAR_SCOPES) == {
        CalendarScope.EVENT,
        CalendarScope.WATCHLIST,
        CalendarScope.EVENT_FILTER,
    }


def test_calendar_scope_values_are_stable_strings() -> None:
    assert CalendarScope.EVENT.value == "event"
    assert CalendarScope.WATCHLIST.value == "watchlist"
    assert CalendarScope.EVENT_FILTER.value == "event_filter"


def test_calendar_time_state_is_closed() -> None:
    assert set(CalendarTimeState) == {
        CalendarTimeState.UPCOMING,
        CalendarTimeState.LIVE,
        CalendarTimeState.ENDED,
    }


def test_calendar_status_mapping_is_complete() -> None:
    assert CALENDAR_STATUS_BY_TIME_STATE == {
        CalendarTimeState.UPCOMING: "TENTATIVE",
        CalendarTimeState.LIVE: "CONFIRMED",
        CalendarTimeState.ENDED: "CANCELLED",
    }


def test_calendar_export_result_is_closed() -> None:
    expected = {
        CalendarExportResult.SUCCESS,
        CalendarExportResult.FORBIDDEN,
        CalendarExportResult.EXPIRED,
        CalendarExportResult.REVOKED,
        CalendarExportResult.INVALID_SCOPE,
        CalendarExportResult.NOT_FOUND,
    }
    assert set(CalendarExportResult) == expected


def test_calendar_scope_round_trip() -> None:
    for scope in SUPPORTED_CALENDAR_SCOPES:
        assert CalendarScope(scope.value) is scope


def test_calendar_time_state_classification_simple() -> None:
    """A simple sanity check on the time-state classification."""

    now = datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)
    past = now - timedelta(days=1)
    future = now + timedelta(days=1)
    assert past < now < future
