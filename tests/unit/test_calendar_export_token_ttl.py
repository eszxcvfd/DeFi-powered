"""Tests for the calendar export token TTL bound (US-045)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from livelead.application.calendar_export.service import (
    PILOT_LIVE_TTL_DAYS,
    TEST_LIKE_TTL_DAYS,
    _max_ttl_days,
    _normalize_expires_at,
)
from livelead.domain.runtime.enums import EnvironmentMode


def test_pilot_live_ttl_default() -> None:
    assert _max_ttl_days(EnvironmentMode.PILOT_LIVE) == PILOT_LIVE_TTL_DAYS
    assert PILOT_LIVE_TTL_DAYS == 90


def test_test_like_ttl_default() -> None:
    assert _max_ttl_days(EnvironmentMode.TEST_LIKE) == TEST_LIKE_TTL_DAYS
    assert TEST_LIKE_TTL_DAYS == 30


def test_paused_mode_falls_back_to_test_like_ttl() -> None:
    assert _max_ttl_days(EnvironmentMode.PAUSED) == TEST_LIKE_TTL_DAYS


def test_unknown_mode_falls_back_to_test_like_ttl() -> None:
    assert _max_ttl_days("not_a_mode") == TEST_LIKE_TTL_DAYS


def test_normalize_expires_at_returns_mode_default_when_missing() -> None:
    now = datetime(2026, 6, 16, 12, 0, 0)
    bounded = _normalize_expires_at(
        requested=None, now=now, environment_mode=EnvironmentMode.PILOT_LIVE
    )
    assert bounded - now == timedelta(days=PILOT_LIVE_TTL_DAYS)


def test_normalize_expires_at_clamps_to_mode_bound() -> None:
    now = datetime(2026, 6, 16, 12, 0, 0)
    too_far = now + timedelta(days=365)
    bounded = _normalize_expires_at(
        requested=too_far,
        now=now,
        environment_mode=EnvironmentMode.TEST_LIKE,
    )
    assert bounded - now == timedelta(days=TEST_LIKE_TTL_DAYS)


def test_normalize_expires_at_accepts_within_bound_request() -> None:
    now = datetime(2026, 6, 16, 12, 0, 0)
    requested = now + timedelta(days=10)
    bounded = _normalize_expires_at(
        requested=requested,
        now=now,
        environment_mode=EnvironmentMode.PILOT_LIVE,
    )
    assert bounded == requested


def test_normalize_expires_at_rejects_past_request() -> None:
    now = datetime(2026, 6, 16, 12, 0, 0)
    past = now - timedelta(days=1)
    bounded = _normalize_expires_at(
        requested=past,
        now=now,
        environment_mode=EnvironmentMode.PILOT_LIVE,
    )
    assert bounded - now == timedelta(minutes=5)


def test_normalize_expires_at_treats_naive_as_utc() -> None:
    now = datetime(2026, 6, 16, 12, 0, 0)
    requested = datetime(2026, 7, 16, 12, 0, 0)  # naive, 30 days
    bounded = _normalize_expires_at(
        requested=requested,
        now=now,
        environment_mode=EnvironmentMode.PILOT_LIVE,
    )
    assert bounded.tzinfo is None
    assert (bounded - now).days == 30
