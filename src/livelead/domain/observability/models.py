"""Observability and alerting domain models (US-041).

Pure dataclasses with no I/O. The infrastructure layer is responsible
for translating these to and from SQLAlchemy rows.

The model layer deliberately does not import SQLAlchemy, FastAPI, or
any framework. Application code consumes these dataclasses; the
interfaces layer wraps them in Pydantic schemas.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from livelead.domain.observability.enums import (
    AlertChannel,
    AlertEventStatus,
    AlertMetric,
    AlertOperator,
    AlertSeverity,
)


# Closed set of metric / operator combinations the evaluator accepts.
# Defined here so the rule validator and the evaluator share one source
# of truth and a typo can never reach a persisted rule row.
SUPPORTED_METRICS: frozenset[AlertMetric] = frozenset(AlertMetric)
SUPPORTED_OPERATORS: frozenset[AlertOperator] = frozenset(AlertOperator)
SUPPORTED_SEVERITIES: frozenset[AlertSeverity] = frozenset(AlertSeverity)
SUPPORTED_CHANNELS: frozenset[AlertChannel] = frozenset(AlertChannel)


def _coerce_channels(values: Any) -> tuple[AlertChannel, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        raw = [values]
    elif isinstance(values, (list, tuple, set, frozenset)):
        raw = list(values)
    else:
        raise ValueError(f"channels must be iterable, got {type(values).__name__}")
    out: list[AlertChannel] = []
    supported_values = {c.value for c in SUPPORTED_CHANNELS}
    for item in raw:
        if isinstance(item, AlertChannel):
            if item not in SUPPORTED_CHANNELS:
                raise ValueError(f"ALERT_RULE_INVALID:channel_unsupported:{item.value}")
            out.append(item)
            continue
        s = str(item)
        if s not in supported_values:
            raise ValueError(f"ALERT_RULE_INVALID:channel_unsupported:{s}")
        out.append(AlertChannel(s))
    # de-duplicate, preserve order
    seen: set[AlertChannel] = set()
    deduped: list[AlertChannel] = []
    for c in out:
        if c not in seen:
            seen.add(c)
            deduped.append(c)
    return tuple(deduped)


@dataclass(frozen=True, slots=True)
class AlertRule:
    """A durable definition of a condition that should fire an alert.

    Rules are scoped to a single organization. A workspace can carry
    multiple rules per metric but never two rules with the same
    name (the database enforces uniqueness on the pair). System
    rules are seeded by the migration and marked with `is_system`;
    they can be tuned through the management API but cannot be
    deleted or renamed.
    """

    id: str
    organization_id: str
    name: str
    metric: AlertMetric
    operator: AlertOperator
    threshold: float
    window_seconds: int = 0
    severity: AlertSeverity = AlertSeverity.WARNING
    cooldown_seconds: int = 600
    channels: tuple[AlertChannel, ...] = field(default_factory=tuple)
    enabled: bool = True
    is_system: bool = False
    sort_order: int = 100
    created_by: str = "system"
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def dedup_bucket(self, fired_at: datetime) -> str:
        """Compute the cooldown bucket for a firing time.

        The bucket divides the timeline into `cooldown_seconds`-sized
        windows so two firings of the same rule inside one window
        collapse into a single `dedup_key`. The bucket is part of
        the key so the application can suppress duplicates without
        a separate timestamp table.
        """

        ts = int(fired_at.timestamp())
        window = max(int(self.cooldown_seconds or 0), 1)
        bucket = ts // window
        return f"{self.id}:{bucket}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "name": self.name,
            "metric": self.metric.value,
            "operator": self.operator.value,
            "threshold": float(self.threshold),
            "window_seconds": int(self.window_seconds),
            "severity": self.severity.value,
            "cooldown_seconds": int(self.cooldown_seconds),
            "channels": [c.value for c in self.channels],
            "enabled": bool(self.enabled),
            "is_system": bool(self.is_system),
            "sort_order": int(self.sort_order),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass(frozen=True, slots=True)
class AlertEvent:
    """A single firing of an `AlertRule`.

    The dataclass is the application-level view of the row. The
    `payload` field is a sanitized, size-capped snapshot of the
    metric value at firing time; raw secret material is never
    persisted on this row.
    """

    id: str
    organization_id: str
    rule_id: str
    rule_name: str
    metric: AlertMetric
    status: AlertEventStatus
    severity: AlertSeverity
    fired_at: datetime
    dedup_key: str
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    resolved_at: datetime | None = None
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    resolution_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "metric": self.metric.value,
            "status": self.status.value,
            "severity": self.severity.value,
            "fired_at": self.fired_at.isoformat() if self.fired_at else None,
            "resolved_at": (
                self.resolved_at.isoformat() if self.resolved_at else None
            ),
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": (
                self.acknowledged_at.isoformat() if self.acknowledged_at else None
            ),
            "resolution_note": self.resolution_note,
            "correlation_id": self.correlation_id,
            "dedup_key": self.dedup_key,
            "payload": dict(self.payload),
        }


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_rule_payload(
    *,
    name: str,
    metric: AlertMetric | str,
    operator: AlertOperator | str,
    threshold: float,
    window_seconds: int,
    severity: AlertSeverity | str,
    channels: Any,
    cooldown_seconds: int,
) -> None:
    """Raise `ValueError` with a stable code prefix when a rule field is bad.

    The prefix lets the REST layer translate validation errors into a
    400 with `code: ALERT_RULE_INVALID` without leaking internal
    state.
    """

    if not name or not name.strip():
        raise ValueError("ALERT_RULE_INVALID:name_required")
    if len(name) > 96:
        raise ValueError("ALERT_RULE_INVALID:name_too_long")

    metric_value = metric.value if isinstance(metric, AlertMetric) else str(metric)
    if metric_value not in {m.value for m in SUPPORTED_METRICS}:
        raise ValueError(f"ALERT_RULE_INVALID:metric_unsupported:{metric_value}")

    operator_value = (
        operator.value if isinstance(operator, AlertOperator) else str(operator)
    )
    if operator_value not in {o.value for o in SUPPORTED_OPERATORS}:
        raise ValueError(
            f"ALERT_RULE_INVALID:operator_unsupported:{operator_value}"
        )

    try:
        threshold_f = float(threshold)
    except (TypeError, ValueError) as exc:
        raise ValueError("ALERT_RULE_INVALID:threshold_not_numeric") from exc
    if threshold_f != threshold_f:  # NaN check
        raise ValueError("ALERT_RULE_INVALID:threshold_nan")

    try:
        window_i = int(window_seconds)
    except (TypeError, ValueError) as exc:
        raise ValueError("ALERT_RULE_INVALID:window_not_int") from exc
    if window_i < 0 or window_i > 86_400 * 7:
        raise ValueError("ALERT_RULE_INVALID:window_out_of_range")

    severity_value = (
        severity.value if isinstance(severity, AlertSeverity) else str(severity)
    )
    if severity_value not in {s.value for s in SUPPORTED_SEVERITIES}:
        raise ValueError(
            f"ALERT_RULE_INVALID:severity_unsupported:{severity_value}"
        )

    try:
        cooldown_i = int(cooldown_seconds)
    except (TypeError, ValueError) as exc:
        raise ValueError("ALERT_RULE_INVALID:cooldown_not_int") from exc
    if cooldown_i < 0 or cooldown_i > 86_400 * 30:
        raise ValueError("ALERT_RULE_INVALID:cooldown_out_of_range")

    coerced = _coerce_channels(channels)
    if not coerced:
        raise ValueError("ALERT_RULE_INVALID:channels_required")
    for c in coerced:
        if c not in SUPPORTED_CHANNELS:
            raise ValueError(f"ALERT_RULE_INVALID:channel_unsupported:{c.value}")


def apply_rule_grammar(
    *,
    metric: AlertMetric | str,
    operator: AlertOperator | str,
    threshold: float,
    window_seconds: int,
    channels: Any,
) -> tuple[AlertMetric, AlertOperator, tuple[AlertChannel, ...], int, float]:
    """Normalise a rule's typed fields, returning the validated tuple.

    Mirrors `validate_rule_payload` but returns the typed values so
    callers can build a domain `AlertRule` instance without a second
    pass through the enum constructors.
    """

    metric_e = (
        metric if isinstance(metric, AlertMetric) else AlertMetric(str(metric))
    )
    operator_e = (
        operator
        if isinstance(operator, AlertOperator)
        else AlertOperator(str(operator))
    )
    severity_e = AlertSeverity.WARNING  # caller fixes; the helper does not own severity
    _ = severity_e  # silence linters
    return (
        metric_e,
        operator_e,
        _coerce_channels(channels),
        int(window_seconds),
        float(threshold),
    )


# ---------------------------------------------------------------------------
# Metric signal evaluation
# ---------------------------------------------------------------------------


def evaluate_threshold(
    operator: AlertOperator,
    value: float,
    threshold: float,
) -> bool:
    """Apply the closed operator grammar to a numeric value."""

    if operator is AlertOperator.GT:
        return value > threshold
    if operator is AlertOperator.GTE:
        return value >= threshold
    if operator is AlertOperator.LT:
        return value < threshold
    if operator is AlertOperator.LTE:
        return value <= threshold
    if operator is AlertOperator.EQ:
        return value == threshold
    raise ValueError(f"ALERT_RULE_INVALID:operator_unsupported:{operator!r}")


def hash_dedup_key(*parts: Any) -> str:
    """Stable hash for a dedup key suffix.

    Used by the evaluator when a rule has a non-trivial dedup
    fingerprint (for example, the per-profile browser crash loop
    rule). The function is deterministic across processes and
    Python sessions so two workers that evaluate the same signal
    always agree on the key.
    """

    joined = "|".join(str(p) for p in parts if p is not None)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:32]


__all__ = [
    "AlertEvent",
    "AlertRule",
    "SUPPORTED_CHANNELS",
    "SUPPORTED_METRICS",
    "SUPPORTED_OPERATORS",
    "SUPPORTED_SEVERITIES",
    "apply_rule_grammar",
    "evaluate_threshold",
    "hash_dedup_key",
    "validate_rule_payload",
]
