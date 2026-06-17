"""Tests for the connector health computer (US-046)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from livelead.application.connector_health.computer import (
    bounded_window,
    classify_status,
    derive_metrics,
)
from livelead.domain.connector_health.enums import (
    ConnectorHealthStatus,
)
from livelead.domain.connector_health.models import (
    ConnectorHealthMetrics,
    ConnectorHealthThresholds,
)


@dataclass
class _Row:
    action: str
    metadata_json: str
    occurred_at: datetime


def _row(
    action: str,
    *,
    occurred_at: datetime,
    metadata: dict | None = None,
) -> _Row:
    import json

    return _Row(
        action=action,
        metadata_json=json.dumps(metadata or {}),
        occurred_at=occurred_at,
    )


def test_bounded_window_rejects_zero() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    with pytest.raises(ValueError):
        bounded_window(now=now, window_seconds=0)


def test_bounded_window_rejects_negative() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    with pytest.raises(ValueError):
        bounded_window(now=now, window_seconds=-1)


def test_bounded_window_returns_window_pair() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    window = bounded_window(now=now, window_seconds=3600)
    assert window.end == now
    assert window.end - window.start == timedelta(seconds=3600)


def test_derive_metrics_empty_window() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    window = bounded_window(now=now, window_seconds=3600)
    metrics = derive_metrics(
        audit_rows=[],
        window=window,
        thresholds=ConnectorHealthThresholds(),
    )
    assert metrics.total_runs == 0
    assert metrics.success_count == 0
    assert metrics.failure_count == 0
    assert metrics.success_rate == 0.0
    assert metrics.captcha_count == 0
    assert metrics.captcha_rate == 0.0
    assert metrics.p50_latency_ms == 0.0
    assert metrics.p95_latency_ms == 0.0
    assert metrics.last_run_at is None
    assert metrics.last_error_code is None
    assert metrics.last_error_message is None


def test_derive_metrics_counts_successes_failures_captchas() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    window = bounded_window(now=now, window_seconds=3600)
    rows = [
        _row(
            "discovery.run.completed",
            occurred_at=now - timedelta(minutes=30),
            metadata={"source_id": "src-1", "duration_ms": 120},
        ),
        _row(
            "discovery.run.completed",
            occurred_at=now - timedelta(minutes=20),
            metadata={"source_id": "src-1", "duration_ms": 240},
        ),
        _row(
            "discovery.run.failed",
            occurred_at=now - timedelta(minutes=10),
            metadata={
                "source_id": "src-1",
                "error_code": "timeout",
                "error_message": "request timed out",
            },
        ),
        _row(
            "connector.captcha_detected",
            occurred_at=now - timedelta(minutes=5),
            metadata={"source_id": "src-1"},
        ),
    ]
    metrics = derive_metrics(
        audit_rows=rows,
        window=window,
        thresholds=ConnectorHealthThresholds(),
    )
    assert metrics.total_runs == 3
    assert metrics.success_count == 2
    assert metrics.failure_count == 1
    assert abs(metrics.success_rate - (2 / 3)) < 1e-3
    assert abs(metrics.captcha_rate - (1 / 3)) < 1e-3
    assert metrics.last_error_code == "timeout"
    assert metrics.last_error_message == "request timed out"
    assert metrics.last_run_at is not None


def test_derive_metrics_skips_rows_outside_window() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    window = bounded_window(now=now, window_seconds=3600)
    rows = [
        _row(
            "discovery.run.completed",
            occurred_at=now - timedelta(hours=2),
            metadata={"source_id": "src-1", "duration_ms": 120},
        ),
        _row(
            "discovery.run.completed",
            occurred_at=now - timedelta(minutes=5),
            metadata={"source_id": "src-1", "duration_ms": 240},
        ),
    ]
    metrics = derive_metrics(
        audit_rows=rows,
        window=window,
        thresholds=ConnectorHealthThresholds(),
    )
    assert metrics.total_runs == 1
    assert metrics.success_count == 1


def test_classify_status_healthy() -> None:
    metrics = ConnectorHealthMetrics(
        total_runs=10,
        success_count=10,
        failure_count=0,
        success_rate=1.0,
        p50_latency_ms=100.0,
        p95_latency_ms=200.0,
        captcha_count=0,
        captcha_rate=0.0,
        last_run_at=None,
        last_error_code=None,
        last_error_message=None,
    )
    assert (
        classify_status(
            metrics=metrics,
            thresholds=ConnectorHealthThresholds(),
        )
        is ConnectorHealthStatus.HEALTHY
    )


def test_classify_status_degraded_by_success_rate() -> None:
    metrics = ConnectorHealthMetrics(
        total_runs=10,
        success_count=8,
        failure_count=2,
        success_rate=0.8,
        p50_latency_ms=100.0,
        p95_latency_ms=200.0,
        captcha_count=0,
        captcha_rate=0.0,
        last_run_at=None,
        last_error_code=None,
        last_error_message=None,
    )
    assert (
        classify_status(
            metrics=metrics,
            thresholds=ConnectorHealthThresholds(),
        )
        is ConnectorHealthStatus.DEGRADED
    )


def test_classify_status_degraded_by_captcha_rate() -> None:
    metrics = ConnectorHealthMetrics(
        total_runs=10,
        success_count=10,
        failure_count=0,
        success_rate=1.0,
        p50_latency_ms=100.0,
        p95_latency_ms=200.0,
        captcha_count=1,
        captcha_rate=0.1,
        last_run_at=None,
        last_error_code=None,
        last_error_message=None,
    )
    assert (
        classify_status(
            metrics=metrics,
            thresholds=ConnectorHealthThresholds(),
        )
        is ConnectorHealthStatus.DEGRADED
    )


def test_classify_status_unhealthy_by_success_rate() -> None:
    metrics = ConnectorHealthMetrics(
        total_runs=10,
        success_count=5,
        failure_count=5,
        success_rate=0.5,
        p50_latency_ms=100.0,
        p95_latency_ms=200.0,
        captcha_count=0,
        captcha_rate=0.0,
        last_run_at=None,
        last_error_code=None,
        last_error_message=None,
    )
    assert (
        classify_status(
            metrics=metrics,
            thresholds=ConnectorHealthThresholds(),
        )
        is ConnectorHealthStatus.UNHEALTHY
    )


def test_classify_status_unhealthy_by_captcha_rate() -> None:
    metrics = ConnectorHealthMetrics(
        total_runs=10,
        success_count=10,
        failure_count=0,
        success_rate=1.0,
        p50_latency_ms=100.0,
        p95_latency_ms=200.0,
        captcha_count=3,
        captcha_rate=0.3,
        last_run_at=None,
        last_error_code=None,
        last_error_message=None,
    )
    assert (
        classify_status(
            metrics=metrics,
            thresholds=ConnectorHealthThresholds(),
        )
        is ConnectorHealthStatus.UNHEALTHY
    )


def test_classify_status_unknown_when_no_signals() -> None:
    metrics = ConnectorHealthMetrics(
        total_runs=0,
        success_count=0,
        failure_count=0,
        success_rate=0.0,
        p50_latency_ms=0.0,
        p95_latency_ms=0.0,
        captcha_count=0,
        captcha_rate=0.0,
        last_run_at=None,
        last_error_code=None,
        last_error_message=None,
    )
    assert (
        classify_status(
            metrics=metrics,
            thresholds=ConnectorHealthThresholds(),
        )
        is ConnectorHealthStatus.UNKNOWN
    )
