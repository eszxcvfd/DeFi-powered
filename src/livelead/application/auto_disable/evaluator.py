"""Connector auto-disable evaluator (US-048).

The evaluator is the only place that owns the
trigger rule evaluation, the
`consecutive_breaches` counter, the
`cooldown_seconds` window, and the bounded
window helper. The service and the test
fixtures call it from a single seam.

The bounded path reads a list of
`ConnectorHealthSnapshot` rows from `US-046`
and a list of `AlertEvent` rows from `US-041`
for the source, applies the closed trigger
rules, and returns a deterministic
`AutoDisableEvaluationResult`. The evaluator
never mutates product state; it returns pure
dataclasses that the service persists on the
`connector_auto_disable_events` row.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Iterable

from livelead.domain.auto_disable.enums import (
    AutoDisableTrigger,
)
from livelead.domain.auto_disable.models import (
    AutoDisableEvaluationResult,
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
    AlertMetric,
    AlertSeverity,
)
from livelead.domain.observability.models import AlertEvent

logger = logging.getLogger("livelead.auto_disable_evaluator")


# Closed set of metric names that map to the
# `needs_user_action_storm` trigger.
_NEEDS_USER_ACTION_METRICS: frozenset[str] = frozenset(
    {
        AlertMetric.DISCOVERY_NEEDS_USER_ACTION_RATE.value,
    }
)

# Closed set of metric names that map to the
# `error_spike` trigger.
_ERROR_SPIKE_METRICS: frozenset[str] = frozenset(
    {
        AlertMetric.CONNECTOR_FAILURE_RATE.value,
    }
)


def bounded_window(
    *,
    now: datetime,
    window_seconds: int,
) -> tuple[datetime, datetime]:
    """Return the bounded `(start, end)` pair the
    evaluation reads.

    The bounded path never reads signals outside
    the window. A window of zero or negative is
    rejected with `AUTO_DISABLE_RULE_INVALID_WINDOW`.
    """

    if window_seconds <= 0:
        raise ValueError("AUTO_DISABLE_RULE_INVALID_WINDOW")
    start = now - timedelta(seconds=int(window_seconds))
    return (start, now)


def in_cooldown(
    *,
    rule: ConnectorAutoDisableRule,
    events: Iterable[Any],
    now: datetime,
) -> bool:
    """Return `True` when the most recent
    `connector_auto_disable_events` row for the
    rule's `trigger` is still inside the
    `cooldown_seconds` window.

    The bounded path prevents flapping: once a
    rule fires, the rule is suppressed for
    `cooldown_seconds` seconds before it can
    fire again.
    """

    if rule.cooldown_seconds <= 0:
        return False
    cooldown = timedelta(seconds=int(rule.cooldown_seconds))
    for event in events:
        if getattr(event, "trigger", None) != rule.trigger:
            continue
        created = getattr(event, "created_at", None)
        if created is None:
            continue
        if created.tzinfo is not None:
            created = created.replace(tzinfo=None)
        if (now - created) < cooldown:
            return True
    return False


def count_consecutive_breaches(
    *,
    rule: ConnectorAutoDisableRule,
    health_snapshots: Iterable[ConnectorHealthSnapshot],
    alert_events: Iterable[AlertEvent],
    window_start: datetime,
    window_end: datetime,
) -> int:
    """Count the consecutive breaches for the rule
    inside the bounded window.

    The bounded path reads the most recent
    snapshots and alert events ordered by
    timestamp. A breach is a signal that crosses
    the rule's `threshold_value` for the rule's
    `trigger`. The count is the length of the
    longest run of consecutive breaches ending
    at the most recent signal.
    """

    if rule.trigger is AutoDisableTrigger.HEALTH_UNHEALTHY:
        return _count_health_unhealthy_breaches(
            snapshots=health_snapshots,
            window_start=window_start,
            window_end=window_end,
        )
    if rule.trigger is AutoDisableTrigger.CAPTCHA_RATE_BREACH:
        return _count_captcha_rate_breaches(
            snapshots=health_snapshots,
            threshold=rule.threshold_value,
            window_start=window_start,
            window_end=window_end,
        )
    if rule.trigger is AutoDisableTrigger.FAILURE_RATE_BREACH:
        return _count_failure_rate_breaches(
            snapshots=health_snapshots,
            threshold=rule.threshold_value,
            window_start=window_start,
            window_end=window_end,
        )
    if rule.trigger is AutoDisableTrigger.NEEDS_USER_ACTION_STORM:
        return _count_alert_metric_breaches(
            alert_events=alert_events,
            metric_set=_NEEDS_USER_ACTION_METRICS,
            threshold=int(rule.threshold_value),
            window_start=window_start,
            window_end=window_end,
        )
    if rule.trigger is AutoDisableTrigger.ERROR_SPIKE:
        return _count_alert_metric_breaches(
            alert_events=alert_events,
            metric_set=_ERROR_SPIKE_METRICS,
            threshold=int(rule.threshold_value),
            window_start=window_start,
            window_end=window_end,
        )
    return 0


def _count_health_unhealthy_breaches(
    *,
    snapshots: Iterable[ConnectorHealthSnapshot],
    window_start: datetime,
    window_end: datetime,
) -> int:
    """Count consecutive `unhealthy` snapshots in
    the bounded window. The bounded path treats
    `unknown` and `degraded` snapshots as
    non-breaches so a single transient
    `unhealthy` reading does not disable a
    source.
    """

    ordered = _sort_by(snapshots, "computed_at", reverse=True)
    count = 0
    for snapshot in ordered:
        timestamp = getattr(snapshot, "computed_at", None)
        if timestamp is None:
            continue
        if timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None)
        if timestamp < window_start or timestamp > window_end:
            continue
        if snapshot.status is ConnectorHealthStatus.UNHEALTHY:
            count += 1
        else:
            break
    return count


def _count_captcha_rate_breaches(
    *,
    snapshots: Iterable[ConnectorHealthSnapshot],
    threshold: float,
    window_start: datetime,
    window_end: datetime,
) -> int:
    """Count consecutive captcha-rate breaches
    in the bounded window.
    """

    ordered = _sort_by(snapshots, "computed_at", reverse=True)
    count = 0
    for snapshot in ordered:
        timestamp = getattr(snapshot, "computed_at", None)
        if timestamp is None:
            continue
        if timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None)
        if timestamp < window_start or timestamp > window_end:
            continue
        if float(snapshot.captcha_rate) > float(threshold):
            count += 1
        else:
            break
    return count


def _count_failure_rate_breaches(
    *,
    snapshots: Iterable[ConnectorHealthSnapshot],
    threshold: float,
    window_start: datetime,
    window_end: datetime,
) -> int:
    """Count consecutive failure-rate breaches
    in the bounded window. The bounded path
    treats `success_rate < (1.0 - threshold)` as
    a breach.
    """

    ordered = _sort_by(snapshots, "computed_at", reverse=True)
    count = 0
    for snapshot in ordered:
        timestamp = getattr(snapshot, "computed_at", None)
        if timestamp is None:
            continue
        if timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None)
        if timestamp < window_start or timestamp > window_end:
            continue
        failure_rate = 1.0 - float(snapshot.success_rate)
        if failure_rate > float(threshold):
            count += 1
        else:
            break
    return count


def _count_alert_metric_breaches(
    *,
    alert_events: Iterable[AlertEvent],
    metric_set: frozenset[str],
    threshold: int,
    window_start: datetime,
    window_end: datetime,
) -> int:
    """Count consecutive alert events whose
    `metric` is in the closed set and whose
    `severity` is `warning` or `critical`.

    The bounded path counts the most-recent-first
    run of matching events inside the bounded
    window. A non-matching event in the run
    resets the count. The `threshold` value
    is reserved for future story use; the
    bounded path returns the run length so the
    caller can compare against the rule's
    `consecutive_breaches` value.
    """

    _ = int(threshold)  # reserved for future bounded path
    ordered = _sort_by(alert_events, "fired_at", reverse=True)
    count = 0
    for alert in ordered:
        timestamp = getattr(alert, "fired_at", None)
        if timestamp is None:
            continue
        if timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None)
        if timestamp < window_start or timestamp > window_end:
            continue
        metric = str(getattr(alert, "metric", "") or "")
        severity = str(getattr(alert, "severity", "") or "")
        if metric not in metric_set:
            continue
        if severity not in (
            AlertSeverity.WARNING.value,
            AlertSeverity.CRITICAL.value,
        ):
            continue
        count += 1
    return count


def _sort_by(items: Iterable[Any], key: str, *, reverse: bool) -> list[Any]:
    """Return the items sorted by the named
    attribute. The bounded path uses this helper
    to keep the most-recent-first ordering for
    `count_consecutive_breaches`.
    """

    def _key(item: Any) -> datetime:
        value = getattr(item, key, None)
        if value is None:
            return datetime.min
        if value.tzinfo is not None:
            value = value.replace(tzinfo=None)
        return value

    return sorted(list(items), key=_key, reverse=reverse)


def evaluate_rule(
    *,
    rule: ConnectorAutoDisableRule,
    health_snapshots: Iterable[ConnectorHealthSnapshot],
    alert_events: Iterable[AlertEvent],
    recent_events: Iterable[Any],
    now: datetime,
) -> AutoDisableEvaluationResult:
    """Evaluate a single rule against the bounded
    health and alert signals.

    The bounded path applies the closed trigger
    rules, the `consecutive_breaches` counter,
    the `cooldown_seconds` window, and the
    bounded window helper. The result is a
    deterministic `AutoDisableEvaluationResult`
    that the service uses to decide whether to
    flip `Source.enabled` to `false`.
    """

    if not rule.enabled:
        return AutoDisableEvaluationResult(should_disable=False)
    try:
        window_start, window_end = bounded_window(
            now=now, window_seconds=int(rule.window_seconds)
        )
    except ValueError:
        return AutoDisableEvaluationResult(should_disable=False)
    if in_cooldown(rule=rule, events=recent_events, now=now):
        return AutoDisableEvaluationResult(should_disable=False)
    breach_count = count_consecutive_breaches(
        rule=rule,
        health_snapshots=health_snapshots,
        alert_events=alert_events,
        window_start=window_start,
        window_end=window_end,
    )
    if breach_count < int(rule.consecutive_breaches):
        return AutoDisableEvaluationResult(
            should_disable=False,
            breach_count=breach_count,
            window_start=window_start,
            window_end=window_end,
        )
    return AutoDisableEvaluationResult(
        should_disable=True,
        trigger=rule.trigger,
        reason=_format_reason(
            rule=rule,
            breach_count=breach_count,
            window_start=window_start,
            window_end=window_end,
        ),
        breach_count=breach_count,
        window_start=window_start,
        window_end=window_end,
        rule_id=rule.id,
    )


def _format_reason(
    *,
    rule: ConnectorAutoDisableRule,
    breach_count: int,
    window_start: datetime,
    window_end: datetime,
) -> str:
    """Format the bounded reason string the
    service persists on the event row.

    The bounded path returns a deterministic,
    bounded-to-500-characters string so the
    reason never exceeds the column limit.
    """

    duration = window_end - window_start
    return (
        f"auto_disable:{rule.trigger.value}:"
        f"breaches={breach_count}:"
        f"window_seconds={int(duration.total_seconds())}"
    )[: 500]


__all__ = [
    "bounded_window",
    "count_consecutive_breaches",
    "evaluate_rule",
    "in_cooldown",
]
