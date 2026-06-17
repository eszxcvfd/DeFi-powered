"""Connector health computer (US-046).

The computer is the only place that owns the
`ConnectorHealthStatus` mapping and the bounded
metrics derivation. The service and the test
fixtures call it from a single seam.

The bounded path reads a list of
`audit_entries`-shaped rows for the source, derives
the closed metrics dataclass, and classifies the
status from the closed `success_rate` and
`captcha_rate` thresholds. The computer never
mutates product state; it returns pure dataclasses
that the service persists on the
`connector_health_snapshots` row.
"""

from __future__ import annotations

import json
import logging
import math
import statistics
from datetime import datetime, timedelta
from typing import Any, Iterable

from livelead.domain.connector_health.enums import (
    ConnectorHealthStatus,
)
from livelead.domain.connector_health.models import (
    MIN_RUNS_FOR_STATUS,
    ConnectorHealthMetrics,
    ConnectorHealthThresholds,
    ConnectorHealthWindow,
)

logger = logging.getLogger("livelead.connector_health_computer")


# Closed set of action names the bounded path
# treats as a successful connector run.
_SUCCESS_ACTIONS: frozenset[str] = frozenset(
    {
        "discovery.run.completed",
        "discovery.run.succeeded",
    }
)

# Closed set of action names the bounded path
# treats as a failed connector run.
_FAILURE_ACTIONS: frozenset[str] = frozenset(
    {
        "discovery.run.failed",
        "discovery.run.error",
        "discovery.run.crashed",
    }
)

# Closed set of action names the bounded path
# treats as a CAPTCHA detection event.
_CAPTCHA_ACTIONS: frozenset[str] = frozenset(
    {
        "connector.captcha_detected",
        "browser.captcha_detected",
    }
)


def _safe_round(value: float, *, digits: int = 4) -> float:
    """Round a metric to a fixed number of digits.

    NaN and infinite values are clamped to zero
    so the bounded path never persists a
    non-finite metric on the snapshot row.
    """

    if not math.isfinite(value):
        return 0.0
    return round(float(value), digits)


def _classify_status(
    *,
    total_runs: int,
    success_rate: float,
    captcha_rate: float,
    thresholds: ConnectorHealthThresholds,
) -> ConnectorHealthStatus:
    """Map the closed `success_rate` and
    `captcha_rate` thresholds to a closed
    `ConnectorHealthStatus` value.

    The mapping is intentionally narrow: a
    connector with no signals in the window
    returns `unknown` so a single early run does
    not flip a connector to `unhealthy`.
    """

    if total_runs < MIN_RUNS_FOR_STATUS:
        return ConnectorHealthStatus.UNKNOWN
    if (
        success_rate < thresholds.degraded_min_success_rate
        or captcha_rate > thresholds.degraded_max_captcha_rate
    ):
        return ConnectorHealthStatus.UNHEALTHY
    if (
        success_rate < thresholds.healthy_min_success_rate
        or captcha_rate > thresholds.healthy_max_captcha_rate
    ):
        return ConnectorHealthStatus.DEGRADED
    return ConnectorHealthStatus.HEALTHY


def bounded_window(
    *,
    now: datetime,
    window_seconds: int,
) -> ConnectorHealthWindow:
    """Return the bounded `(start, end)` pair the
    computation reads.

    The bounded path never reads signals outside
    the window. A window of zero or negative is
    rejected with `CONNECTOR_HEALTH_INVALID_WINDOW`.
    """

    if window_seconds <= 0:
        raise ValueError("CONNECTOR_HEALTH_INVALID_WINDOW")
    start = now - timedelta(seconds=int(window_seconds))
    return ConnectorHealthWindow(start=start, end=now)


def derive_metrics(
    *,
    audit_rows: Iterable[Any],
    window: ConnectorHealthWindow,
    thresholds: ConnectorHealthThresholds,
) -> ConnectorHealthMetrics:
    """Derive the bounded metrics dataclass from a
    list of `audit_entries`-shaped rows for a source.

    The bounded path reads the `metadata_json` of
    each row to extract the `duration_ms`,
    `error_code`, and `error_message` fields. The
    bounded path applies the closed action
    filter and the closed window filter before
    computing the metrics.
    """

    total_runs = 0
    success_count = 0
    failure_count = 0
    captcha_count = 0
    durations: list[float] = []
    last_run_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None

    for row in audit_rows:
        occurred = getattr(row, "occurred_at", None)
        if occurred is None:
            continue
        if occurred.tzinfo is not None:
            occurred = occurred.replace(tzinfo=None)
        if occurred < window.start or occurred > window.end:
            continue
        action = str(getattr(row, "action", "") or "")
        metadata_raw = getattr(row, "metadata_json", "{}") or "{}"
        try:
            metadata = json.loads(metadata_raw)
        except (TypeError, ValueError):
            metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}

        if action in _SUCCESS_ACTIONS:
            total_runs += 1
            success_count += 1
            duration_ms = metadata.get("duration_ms")
            if isinstance(duration_ms, (int, float)) and duration_ms >= 0:
                durations.append(float(duration_ms))
            if last_run_at is None or occurred > last_run_at:
                last_run_at = occurred
        elif action in _FAILURE_ACTIONS:
            total_runs += 1
            failure_count += 1
            if last_run_at is None or occurred > last_run_at:
                last_run_at = occurred
            err_code = metadata.get("error_code") or "unknown"
            err_msg = metadata.get("error_message") or ""
            if isinstance(err_code, str):
                last_error_code = err_code[:64]
            if isinstance(err_msg, str):
                last_error_message = err_msg[
                    : thresholds.max_error_message_length
                ]
        if action in _CAPTCHA_ACTIONS:
            captcha_count += 1

    success_rate = (
        float(success_count) / float(total_runs)
        if total_runs > 0
        else 0.0
    )
    captcha_rate = (
        float(captcha_count) / float(total_runs)
        if total_runs > 0
        else 0.0
    )
    p50 = statistics.median(durations) if durations else 0.0
    if len(durations) >= 2:
        sorted_durations = sorted(durations)
        idx = max(0, int(math.ceil(0.95 * len(sorted_durations))) - 1)
        idx = min(idx, len(sorted_durations) - 1)
        p95 = float(sorted_durations[idx])
    else:
        p95 = p50
    return ConnectorHealthMetrics(
        total_runs=total_runs,
        success_count=success_count,
        failure_count=failure_count,
        success_rate=_safe_round(success_rate),
        p50_latency_ms=_safe_round(p50),
        p95_latency_ms=_safe_round(p95),
        captcha_count=captcha_count,
        captcha_rate=_safe_round(captcha_rate),
        last_run_at=last_run_at,
        last_error_code=last_error_code,
        last_error_message=last_error_message,
    )


def classify_status(
    *,
    metrics: ConnectorHealthMetrics,
    thresholds: ConnectorHealthThresholds,
) -> ConnectorHealthStatus:
    """Classify a per-connector metrics dataclass
    into the closed `ConnectorHealthStatus` enum.

    The bounded path uses the same mapping the
    service uses so the surface and the alert
    evaluator stay aligned.
    """

    return _classify_status(
        total_runs=metrics.total_runs,
        success_rate=metrics.success_rate,
        captcha_rate=metrics.captcha_rate,
        thresholds=thresholds,
    )


__all__ = [
    "bounded_window",
    "classify_status",
    "derive_metrics",
]
