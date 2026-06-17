"""Tests for the webhook thresholds (US-049)."""

from __future__ import annotations

from livelead.domain.runtime.enums import EnvironmentMode
from livelead.domain.webhooks.models import (
    WebhookDeliveryThresholds,
)


def test_thresholds_default_attempts_is_six() -> None:
    thresholds = WebhookDeliveryThresholds()
    assert thresholds.max_attempts == 6


def test_thresholds_default_backoff_is_bounded() -> None:
    thresholds = WebhookDeliveryThresholds()
    assert thresholds.initial_backoff_seconds == 30
    assert thresholds.max_backoff_seconds == 3600
    assert thresholds.jitter_seconds == 30
    assert thresholds.backoff_multiplier == 2.0


def test_thresholds_max_window_for_mode_pilot_live() -> None:
    thresholds = WebhookDeliveryThresholds()
    assert (
        thresholds.max_window_seconds_for_mode(EnvironmentMode.PILOT_LIVE)
        == 24 * 3600
    )


def test_thresholds_max_window_for_mode_test_like() -> None:
    thresholds = WebhookDeliveryThresholds()
    assert (
        thresholds.max_window_seconds_for_mode(EnvironmentMode.TEST_LIKE)
        == 3600
    )


def test_thresholds_max_window_for_mode_paused_uses_test_like_bound() -> None:
    thresholds = WebhookDeliveryThresholds()
    assert (
        thresholds.max_window_seconds_for_mode(EnvironmentMode.PAUSED)
        == 3600
    )


def test_thresholds_replay_window_is_300() -> None:
    thresholds = WebhookDeliveryThresholds()
    assert thresholds.signature_replay_window_seconds == 300


def test_thresholds_request_timeout_is_bounded() -> None:
    thresholds = WebhookDeliveryThresholds()
    assert thresholds.request_timeout_seconds == 30


def test_thresholds_max_target_url_length_is_bounded() -> None:
    thresholds = WebhookDeliveryThresholds()
    assert thresholds.max_target_url_length == 2048
    assert thresholds.max_name_length == 200
    assert thresholds.max_response_message_length == 500
    assert thresholds.max_event_types_per_subscription == 16
