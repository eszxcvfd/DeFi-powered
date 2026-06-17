"""Tests for the connector auto-disable thresholds (US-048)."""

from __future__ import annotations

import pytest

from livelead.domain.auto_disable.models import (
    AutoDisableThresholds,
)
from livelead.domain.runtime.enums import EnvironmentMode


def test_thresholds_default_window_is_bounded() -> None:
    thresholds = AutoDisableThresholds()
    assert thresholds.default_window_seconds == 1800
    assert thresholds.default_consecutive_breaches == 3
    assert thresholds.default_cooldown_seconds == 900


def test_thresholds_max_window_for_mode_pilot_live() -> None:
    thresholds = AutoDisableThresholds()
    assert (
        thresholds.max_window_seconds_for_mode(EnvironmentMode.PILOT_LIVE)
        == 24 * 3600
    )


def test_thresholds_max_window_for_mode_test_like() -> None:
    thresholds = AutoDisableThresholds()
    assert (
        thresholds.max_window_seconds_for_mode(EnvironmentMode.TEST_LIKE)
        == 3600
    )


def test_thresholds_max_window_for_mode_paused_uses_test_like_bound() -> None:
    thresholds = AutoDisableThresholds()
    assert (
        thresholds.max_window_seconds_for_mode(EnvironmentMode.PAUSED)
        == 3600
    )


def test_thresholds_recent_events_per_source_is_bounded() -> None:
    thresholds = AutoDisableThresholds()
    assert thresholds.max_recent_events_per_source == 50
    assert thresholds.max_reason_length == 500


def test_thresholds_captcha_rate_default_is_breach_threshold() -> None:
    thresholds = AutoDisableThresholds()
    assert thresholds.default_captcha_rate_breach_threshold == pytest.approx(0.2)


def test_thresholds_failure_rate_default_is_breach_threshold() -> None:
    thresholds = AutoDisableThresholds()
    assert thresholds.default_failure_rate_breach_threshold == pytest.approx(0.5)
