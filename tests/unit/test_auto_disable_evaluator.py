"""Tests for the connector auto-disable evaluator (US-048).

The evaluator is the pure helper that owns the
trigger rule evaluation, the
`consecutive_breaches` counter, the
`cooldown_seconds` window, and the bounded
window helper. The service and the test
fixtures call it from a single seam.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import pytest

from livelead.application.auto_disable.evaluator import (
    bounded_window,
    count_consecutive_breaches,
    evaluate_rule,
    in_cooldown,
)
from livelead.domain.auto_disable.enums import (
    AutoDisableTrigger,
)
from livelead.domain.auto_disable.models import (
    AutoDisableThresholds,
    ConnectorAutoDisableRule,
)
from livelead.domain.connector_health.enums import (
    ConnectorHealthStatus,
)
from livelead.domain.connector_health.models import (
    ConnectorHealthSnapshot,
)
from livelead.domain.observability.enums import (
    AlertEventStatus,
    AlertMetric,
    AlertSeverity,
)


THRESHOLDS = AutoDisableThresholds()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _AlertEventLike:
    id: str
    metric: str
    severity: str
    fired_at: datetime
    status: str = AlertEventStatus.FIRING.value


def _rule(
    *,
    trigger: AutoDisableTrigger = AutoDisableTrigger.HEALTH_UNHEALTHY,
    threshold_value: float = 0.0,
    window_seconds: int = 1800,
    consecutive_breaches: int = 3,
    cooldown_seconds: int = 0,
    enabled: bool = True,
) -> ConnectorAutoDisableRule:
    return ConnectorAutoDisableRule(
        id="rule_01",
        organization_id="org_01",
        source_id="src_01",
        trigger=trigger,
        threshold_value=threshold_value,
        window_seconds=window_seconds,
        consecutive_breaches=consecutive_breaches,
        cooldown_seconds=cooldown_seconds,
        enabled=enabled,
        created_by="system",
    )


def _snapshot(
    *,
    status: ConnectorHealthStatus,
    success_rate: float = 1.0,
    captcha_rate: float = 0.0,
    computed_at: datetime,
) -> ConnectorHealthSnapshot:
    return ConnectorHealthSnapshot(
        id=f"snap_{computed_at.isoformat()}",
        organization_id="org_01",
        source_id="src_01",
        connector_type=type(
            "CT", (), {"value": "rss"}
        )(),  # duck-typed; not used by evaluator
        window_start=computed_at - timedelta(hours=1),
        window_end=computed_at,
        total_runs=10,
        success_count=10,
        failure_count=0,
        success_rate=success_rate,
        p50_latency_ms=100.0,
        p95_latency_ms=200.0,
        captcha_count=0,
        captcha_rate=captcha_rate,
        last_run_at=computed_at,
        last_error_code=None,
        last_error_message=None,
        status=status,
        computed_at=computed_at,
    )


# ---------------------------------------------------------------------------
# bounded_window
# ---------------------------------------------------------------------------


def test_bounded_window_returns_pair() -> None:
    now = datetime(2026, 6, 16, 12, 0, 0)
    start, end = bounded_window(now=now, window_seconds=1800)
    assert (end - start) == timedelta(seconds=1800)
    assert end == now


def test_bounded_window_rejects_zero() -> None:
    now = datetime(2026, 6, 16, 12, 0, 0)
    with pytest.raises(ValueError):
        bounded_window(now=now, window_seconds=0)


def test_bounded_window_rejects_negative() -> None:
    now = datetime(2026, 6, 16, 12, 0, 0)
    with pytest.raises(ValueError):
        bounded_window(now=now, window_seconds=-100)


# ---------------------------------------------------------------------------
# in_cooldown
# ---------------------------------------------------------------------------


def test_in_cooldown_returns_false_when_no_events() -> None:
    rule = _rule(cooldown_seconds=900)
    now = datetime(2026, 6, 16, 12, 0, 0)
    assert in_cooldown(rule=rule, events=[], now=now) is False


def test_in_cooldown_returns_true_when_recent_event() -> None:
    rule = _rule(cooldown_seconds=900, trigger=AutoDisableTrigger.ERROR_SPIKE)
    now = datetime(2026, 6, 16, 12, 0, 0)
    recent = type(
        "E", (), {"trigger": AutoDisableTrigger.ERROR_SPIKE, "created_at": now - timedelta(seconds=60)}
    )()
    assert in_cooldown(rule=rule, events=[recent], now=now) is True


def test_in_cooldown_returns_false_after_window_elapsed() -> None:
    rule = _rule(cooldown_seconds=900)
    now = datetime(2026, 6, 16, 12, 0, 0)
    old = type(
        "E", (), {"trigger": AutoDisableTrigger.HEALTH_UNHEALTHY, "created_at": now - timedelta(hours=1)}
    )()
    assert in_cooldown(rule=rule, events=[old], now=now) is False


def test_in_cooldown_returns_false_for_different_trigger() -> None:
    rule = _rule(cooldown_seconds=900, trigger=AutoDisableTrigger.ERROR_SPIKE)
    now = datetime(2026, 6, 16, 12, 0, 0)
    other = type(
        "E", (), {"trigger": AutoDisableTrigger.HEALTH_UNHEALTHY, "created_at": now - timedelta(seconds=60)}
    )()
    assert in_cooldown(rule=rule, events=[other], now=now) is False


# ---------------------------------------------------------------------------
# count_consecutive_breaches
# ---------------------------------------------------------------------------


def test_count_consecutive_breaches_health_unhealthy() -> None:
    rule = _rule(trigger=AutoDisableTrigger.HEALTH_UNHEALTHY)
    now = datetime(2026, 6, 16, 12, 0, 0)
    snapshots = [
        _snapshot(
            status=ConnectorHealthStatus.HEALTHY, computed_at=now - timedelta(minutes=10)
        ),
        _snapshot(
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=5),
        ),
        _snapshot(
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=3),
        ),
        _snapshot(
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=1),
        ),
    ]
    start, end = bounded_window(now=now, window_seconds=1800)
    count = count_consecutive_breaches(
        rule=rule,
        health_snapshots=snapshots,
        alert_events=[],
        window_start=start,
        window_end=end,
    )
    assert count == 3


def test_count_consecutive_breaches_stops_at_non_breach() -> None:
    rule = _rule(trigger=AutoDisableTrigger.HEALTH_UNHEALTHY)
    now = datetime(2026, 6, 16, 12, 0, 0)
    snapshots = [
        _snapshot(
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=10),
        ),
        _snapshot(
            status=ConnectorHealthStatus.HEALTHY,
            computed_at=now - timedelta(minutes=5),
        ),
        _snapshot(
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=1),
        ),
    ]
    start, end = bounded_window(now=now, window_seconds=1800)
    count = count_consecutive_breaches(
        rule=rule,
        health_snapshots=snapshots,
        alert_events=[],
        window_start=start,
        window_end=end,
    )
    assert count == 1


def test_count_consecutive_breaches_captcha_rate() -> None:
    rule = _rule(
        trigger=AutoDisableTrigger.CAPTCHA_RATE_BREACH,
        threshold_value=0.1,
    )
    now = datetime(2026, 6, 16, 12, 0, 0)
    snapshots = [
        _snapshot(
            status=ConnectorHealthStatus.DEGRADED,
            captcha_rate=0.2,
            computed_at=now - timedelta(minutes=5),
        ),
        _snapshot(
            status=ConnectorHealthStatus.DEGRADED,
            captcha_rate=0.3,
            computed_at=now - timedelta(minutes=3),
        ),
        _snapshot(
            status=ConnectorHealthStatus.DEGRADED,
            captcha_rate=0.4,
            computed_at=now - timedelta(minutes=1),
        ),
    ]
    start, end = bounded_window(now=now, window_seconds=1800)
    count = count_consecutive_breaches(
        rule=rule,
        health_snapshots=snapshots,
        alert_events=[],
        window_start=start,
        window_end=end,
    )
    assert count == 3


def test_count_consecutive_breaches_failure_rate() -> None:
    rule = _rule(
        trigger=AutoDisableTrigger.FAILURE_RATE_BREACH,
        threshold_value=0.3,
    )
    now = datetime(2026, 6, 16, 12, 0, 0)
    snapshots = [
        _snapshot(
            status=ConnectorHealthStatus.DEGRADED,
            success_rate=0.5,
            computed_at=now - timedelta(minutes=5),
        ),
        _snapshot(
            status=ConnectorHealthStatus.DEGRADED,
            success_rate=0.4,
            computed_at=now - timedelta(minutes=3),
        ),
        _snapshot(
            status=ConnectorHealthStatus.DEGRADED,
            success_rate=0.3,
            computed_at=now - timedelta(minutes=1),
        ),
    ]
    start, end = bounded_window(now=now, window_seconds=1800)
    count = count_consecutive_breaches(
        rule=rule,
        health_snapshots=snapshots,
        alert_events=[],
        window_start=start,
        window_end=end,
    )
    assert count == 3


def test_count_consecutive_breaches_needs_user_action_storm() -> None:
    rule = _rule(
        trigger=AutoDisableTrigger.NEEDS_USER_ACTION_STORM,
        threshold_value=3.0,
    )
    now = datetime(2026, 6, 16, 12, 0, 0)
    alerts = [
        _AlertEventLike(
            id=f"a_{i}",
            metric=AlertMetric.DISCOVERY_NEEDS_USER_ACTION_RATE.value,
            severity=AlertSeverity.WARNING.value,
            fired_at=now - timedelta(minutes=i + 1),
        )
        for i in range(3)
    ]
    start, end = bounded_window(now=now, window_seconds=1800)
    count = count_consecutive_breaches(
        rule=rule,
        health_snapshots=[],
        alert_events=alerts,
        window_start=start,
        window_end=end,
    )
    assert count == 3


def test_count_consecutive_breaches_error_spike() -> None:
    rule = _rule(
        trigger=AutoDisableTrigger.ERROR_SPIKE,
        threshold_value=3.0,
    )
    now = datetime(2026, 6, 16, 12, 0, 0)
    alerts = [
        _AlertEventLike(
            id=f"a_{i}",
            metric=AlertMetric.CONNECTOR_FAILURE_RATE.value,
            severity=AlertSeverity.CRITICAL.value,
            fired_at=now - timedelta(minutes=i + 1),
        )
        for i in range(5)
    ]
    start, end = bounded_window(now=now, window_seconds=1800)
    count = count_consecutive_breaches(
        rule=rule,
        health_snapshots=[],
        alert_events=alerts,
        window_start=start,
        window_end=end,
    )
    assert count == 5


def test_count_consecutive_breaches_ignores_info_severity() -> None:
    rule = _rule(
        trigger=AutoDisableTrigger.NEEDS_USER_ACTION_STORM,
        threshold_value=3.0,
    )
    now = datetime(2026, 6, 16, 12, 0, 0)
    alerts = [
        _AlertEventLike(
            id="a_1",
            metric=AlertMetric.DISCOVERY_NEEDS_USER_ACTION_RATE.value,
            severity=AlertSeverity.INFO.value,
            fired_at=now - timedelta(minutes=1),
        )
    ]
    start, end = bounded_window(now=now, window_seconds=1800)
    count = count_consecutive_breaches(
        rule=rule,
        health_snapshots=[],
        alert_events=alerts,
        window_start=start,
        window_end=end,
    )
    assert count == 0


# ---------------------------------------------------------------------------
# evaluate_rule
# ---------------------------------------------------------------------------


def test_evaluate_rule_disabled_rule_returns_no_disable() -> None:
    rule = _rule(enabled=False)
    now = datetime(2026, 6, 16, 12, 0, 0)
    snapshots = [
        _snapshot(
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=1),
        )
    ]
    result = evaluate_rule(
        rule=rule,
        health_snapshots=snapshots,
        alert_events=[],
        recent_events=[],
        now=now,
    )
    assert result.should_disable is False


def test_evaluate_rule_fires_health_unhealthy() -> None:
    rule = _rule(
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        consecutive_breaches=3,
    )
    now = datetime(2026, 6, 16, 12, 0, 0)
    snapshots = [
        _snapshot(
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=3),
        ),
        _snapshot(
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=2),
        ),
        _snapshot(
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=1),
        ),
    ]
    result = evaluate_rule(
        rule=rule,
        health_snapshots=snapshots,
        alert_events=[],
        recent_events=[],
        now=now,
    )
    assert result.should_disable is True
    assert result.trigger is AutoDisableTrigger.HEALTH_UNHEALTHY
    assert "health_unhealthy" in (result.reason or "")


def test_evaluate_rule_does_not_fire_below_threshold() -> None:
    rule = _rule(
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        consecutive_breaches=3,
    )
    now = datetime(2026, 6, 16, 12, 0, 0)
    snapshots = [
        _snapshot(
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=2),
        ),
        _snapshot(
            status=ConnectorHealthStatus.HEALTHY,
            computed_at=now - timedelta(minutes=1),
        ),
    ]
    result = evaluate_rule(
        rule=rule,
        health_snapshots=snapshots,
        alert_events=[],
        recent_events=[],
        now=now,
    )
    assert result.should_disable is False


def test_evaluate_rule_respects_cooldown() -> None:
    rule = _rule(
        trigger=AutoDisableTrigger.HEALTH_UNHEALTHY,
        consecutive_breaches=3,
        cooldown_seconds=900,
    )
    now = datetime(2026, 6, 16, 12, 0, 0)
    snapshots = [
        _snapshot(
            status=ConnectorHealthStatus.UNHEALTHY,
            computed_at=now - timedelta(minutes=1),
        )
    ] * 3
    recent = type(
        "E", (), {"trigger": AutoDisableTrigger.HEALTH_UNHEALTHY, "created_at": now - timedelta(seconds=60)}
    )()
    result = evaluate_rule(
        rule=rule,
        health_snapshots=snapshots,
        alert_events=[],
        recent_events=[recent],
        now=now,
    )
    assert result.should_disable is False
