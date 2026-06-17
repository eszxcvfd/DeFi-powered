"""Tests for the connector health window bound (US-046)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from livelead.application.connector_health.service import (
    _bounded_window_seconds,
    _max_window_seconds,
)
from livelead.domain.connector_health.models import (
    ConnectorHealthThresholds,
)
from livelead.domain.runtime.enums import EnvironmentMode


def test_pilot_live_max_window_default() -> None:
    assert _max_window_seconds(EnvironmentMode.PILOT_LIVE) == 24 * 3600


def test_test_like_max_window_default() -> None:
    assert _max_window_seconds(EnvironmentMode.TEST_LIKE) == 3600


def test_paused_mode_falls_back_to_test_like_window() -> None:
    assert _max_window_seconds(EnvironmentMode.PAUSED) == 3600


def test_unknown_mode_falls_back_to_test_like_window() -> None:
    assert _max_window_seconds("not_a_mode") == 3600


def test_bounded_window_returns_threshold_default_when_missing() -> None:
    thresholds = ConnectorHealthThresholds()
    bounded = _bounded_window_seconds(
        requested=0,
        thresholds=thresholds,
        environment_mode=EnvironmentMode.PILOT_LIVE,
    )
    assert bounded == thresholds.default_window_seconds


def test_bounded_window_clamps_to_mode_bound() -> None:
    thresholds = ConnectorHealthThresholds()
    bounded = _bounded_window_seconds(
        requested=365 * 24 * 3600,
        thresholds=thresholds,
        environment_mode=EnvironmentMode.TEST_LIKE,
    )
    assert bounded == _max_window_seconds(EnvironmentMode.TEST_LIKE)


def test_bounded_window_accepts_within_bound_request() -> None:
    thresholds = ConnectorHealthThresholds()
    bounded = _bounded_window_seconds(
        requested=10 * 60,
        thresholds=thresholds,
        environment_mode=EnvironmentMode.PILOT_LIVE,
    )
    assert bounded == 600
