"""Webhook retry policy (US-049).

The retry policy is the only place that owns
the bounded retry algorithm with exponential
backoff and bounded jitter. The helper is
pure; it does not touch the database or the
network.

The bounded algorithm returns `None` when
`attempt_count >= max_attempts`; otherwise,
the bounded path computes the next
`next_attempt_at` from the closed
`max_attempts`, `initial_backoff_seconds`,
`backoff_multiplier`, `max_backoff_seconds`,
and `jitter_seconds` bounds.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Any

from livelead.domain.webhooks.models import (
    WebhookDeliveryThresholds,
)

logger = logging.getLogger("livelead.webhook_retry_policy")


def next_attempt_at(
    *,
    attempt_count: int,
    thresholds: WebhookDeliveryThresholds,
    now: datetime,
    jitter: bool = True,
) -> datetime | None:
    """Return the bounded `next_attempt_at`
    for the given `attempt_count`.

    The bounded path returns `None` when
    `attempt_count >= max_attempts`. The
    bounded algorithm is:

    ```text
    backoff = min(
        initial_backoff_seconds
        * (backoff_multiplier ** (attempt_count - 1)),
        max_backoff_seconds,
    )
    jitter_seconds = random.uniform(0, jitter_seconds)
    return now + timedelta(seconds=backoff + jitter)
    ```
    """

    if attempt_count < 0:
        raise ValueError("WEBHOOK_RETRY_INVALID_ATTEMPT")
    if attempt_count >= int(thresholds.max_attempts):
        return None
    # The bounded `attempt_count` is 1-based
    # for the first retry: `attempt_count=1`
    # uses the bounded `initial_backoff_seconds`
    # (30s); `attempt_count=2` doubles to 60s;
    # `attempt_count=3` quadruples to 120s; the
    # bounded `max_backoff_seconds` caps the
    # result.
    exponent = max(0, int(attempt_count) - 1)
    backoff = min(
        float(thresholds.initial_backoff_seconds)
        * (float(thresholds.backoff_multiplier) ** exponent),
        float(thresholds.max_backoff_seconds),
    )
    if backoff <= 0:
        backoff = float(thresholds.initial_backoff_seconds)
    extra_jitter = 0.0
    if jitter and int(thresholds.jitter_seconds) > 0:
        extra_jitter = float(
            random.randint(0, int(thresholds.jitter_seconds))
        )
    return now + timedelta(seconds=backoff + extra_jitter)


def bounded_window_seconds(
    *,
    requested: int,
    thresholds: WebhookDeliveryThresholds,
    environment_mode: Any,
) -> int:
    """Bound the requested window by the
    `EnvironmentMode` and the closed
    `WebhookDeliveryThresholds` defaults.

    A missing or non-positive `requested` is
    replaced with the threshold default; a
    `requested` that exceeds the
    `EnvironmentMode` bound is clipped to the
    bound.
    """

    from livelead.domain.runtime.enums import EnvironmentMode

    try:
        mode = (
            environment_mode
            if isinstance(environment_mode, EnvironmentMode)
            else EnvironmentMode(environment_mode)
        )
    except ValueError:
        mode = EnvironmentMode.TEST_LIKE
    max_window = thresholds.max_window_seconds_for_mode(mode)
    default_window = int(thresholds.initial_backoff_seconds)
    if requested is None or int(requested) <= 0:
        return min(default_window, max_window)
    bounded = min(int(requested), max_window)
    if bounded <= 0:
        raise ValueError("WEBHOOK_WINDOW_INVALID")
    return bounded


__all__ = [
    "bounded_window_seconds",
    "next_attempt_at",
]
