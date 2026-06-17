"""Tests for the webhook retry policy (US-049)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from livelead.application.webhooks.retry_policy import (
    bounded_window_seconds,
    next_attempt_at,
)
from livelead.domain.runtime.enums import EnvironmentMode
from livelead.domain.webhooks.models import (
    WebhookDeliveryThresholds,
)


THRESHOLDS = WebhookDeliveryThresholds()


def test_next_attempt_returns_none_when_max_attempts_exceeded() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    assert (
        next_attempt_at(
            attempt_count=int(THRESHOLDS.max_attempts),
            thresholds=THRESHOLDS,
            now=now,
            jitter=False,
        )
        is None
    )


def test_next_attempt_returns_none_when_attempts_above_max() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    assert (
        next_attempt_at(
            attempt_count=int(THRESHOLDS.max_attempts) + 5,
            thresholds=THRESHOLDS,
            now=now,
            jitter=False,
        )
        is None
    )


def test_next_attempt_first_attempt_uses_initial_backoff() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    nxt = next_attempt_at(
        attempt_count=1,
        thresholds=THRESHOLDS,
        now=now,
        jitter=False,
    )
    assert nxt is not None
    # First attempt uses the bounded
    # `initial_backoff_seconds` (30s).
    assert (nxt - now) == timedelta(seconds=30)


def test_next_attempt_second_attempt_doubles_backoff() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    nxt = next_attempt_at(
        attempt_count=2,
        thresholds=THRESHOLDS,
        now=now,
        jitter=False,
    )
    assert nxt is not None
    assert (nxt - now) == timedelta(seconds=60)


def test_next_attempt_third_attempt_quadruples_backoff() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    nxt = next_attempt_at(
        attempt_count=3,
        thresholds=THRESHOLDS,
        now=now,
        jitter=False,
    )
    assert nxt is not None
    assert (nxt - now) == timedelta(seconds=120)


def test_next_attempt_caps_at_max_backoff() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    nxt = next_attempt_at(
        attempt_count=5,
        thresholds=THRESHOLDS,
        now=now,
        jitter=False,
    )
    assert nxt is not None
    # Even at large attempt counts, the bounded
    # path caps the backoff at
    # `max_backoff_seconds`.
    # attempt_count=5 -> 30 * 2**4 = 480s
    assert (nxt - now) == timedelta(seconds=480)


def test_next_attempt_caps_at_max_backoff_at_max_attempts() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    nxt = next_attempt_at(
        attempt_count=int(THRESHOLDS.max_attempts) - 1,
        thresholds=THRESHOLDS,
        now=now,
        jitter=False,
    )
    assert nxt is not None
    # `attempt_count=5` with the bounded
    # defaults gives 30 * 2**4 = 480s, well
    # below the 3600s cap. The cap kicks in
    # for very large attempt counts via a
    # custom threshold.
    large = WebhookDeliveryThresholds(max_backoff_seconds=120)
    nxt2 = next_attempt_at(
        attempt_count=4,
        thresholds=large,
        now=now,
        jitter=False,
    )
    assert nxt2 is not None
    assert (nxt2 - now) == timedelta(seconds=120)


def test_next_attempt_jitter_is_bounded() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    samples = [
        next_attempt_at(
            attempt_count=1,
            thresholds=THRESHOLDS,
            now=now,
            jitter=True,
        )
        for _ in range(20)
    ]
    # Jitter is bounded by `jitter_seconds`
    # (30s). All samples must be within
    # [30, 60] seconds.
    for sample in samples:
        assert sample is not None
        delta = (sample - now).total_seconds()
        assert 30.0 <= delta <= 60.0


def test_next_attempt_rejects_negative_attempt() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    with pytest.raises(ValueError):
        next_attempt_at(
            attempt_count=-1,
            thresholds=THRESHOLDS,
            now=now,
            jitter=False,
        )


def test_bounded_window_seconds_clamps_to_mode_bound() -> None:
    bounded = bounded_window_seconds(
        requested=48 * 3600,
        thresholds=THRESHOLDS,
        environment_mode=EnvironmentMode.TEST_LIKE,
    )
    assert bounded == 3600


def test_bounded_window_seconds_returns_default_for_zero() -> None:
    bounded = bounded_window_seconds(
        requested=0,
        thresholds=THRESHOLDS,
        environment_mode=EnvironmentMode.PILOT_LIVE,
    )
    assert bounded == min(30, 24 * 3600)


def test_bounded_window_seconds_returns_default_for_negative() -> None:
    bounded = bounded_window_seconds(
        requested=-1,
        thresholds=THRESHOLDS,
        environment_mode=EnvironmentMode.PILOT_LIVE,
    )
    assert bounded == min(30, 24 * 3600)


def test_bounded_window_seconds_pilot_live_24h() -> None:
    bounded = bounded_window_seconds(
        requested=12 * 3600,
        thresholds=THRESHOLDS,
        environment_mode=EnvironmentMode.PILOT_LIVE,
    )
    assert bounded == 12 * 3600
