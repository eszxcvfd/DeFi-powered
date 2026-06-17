"""Connector auto-disable domain models (US-048).

Pure dataclasses with no I/O. The infrastructure
layer is responsible for translating these to and
from SQLAlchemy rows. The model layer deliberately
does not import SQLAlchemy, FastAPI, or any
framework.

The model layer reuses the closed
`AutoDisableTrigger` and `AutoDisableEventStatus`
enums. The `AutoDisableService` is the only
place that mutates
`connector_auto_disable_rules` and
`connector_auto_disable_events`; the REST layer
calls it from the request handlers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from livelead.domain.auto_disable.enums import (
    AutoDisableEventStatus,
    AutoDisableTrigger,
)


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConnectorAutoDisableRule:
    """A single record of a per-source auto-disable
    policy.

    The row carries enough information for the
    bounded `AutoDisableService` to evaluate a
    source against the closed trigger rules
    without reading raw tables.
    """

    id: str
    organization_id: str
    source_id: str
    trigger: AutoDisableTrigger
    threshold_value: float
    window_seconds: int
    consecutive_breaches: int
    cooldown_seconds: int
    enabled: bool
    created_by: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "source_id": self.source_id,
            "trigger": self.trigger.value,
            "threshold_value": float(self.threshold_value),
            "window_seconds": int(self.window_seconds),
            "consecutive_breaches": int(self.consecutive_breaches),
            "cooldown_seconds": int(self.cooldown_seconds),
            "enabled": bool(self.enabled),
            "created_by": self.created_by,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConnectorAutoDisableEvent:
    """A single record of a per-event auto-disable
    history.

    The table is bounded to the most recent N
    events per source so a flapping connector
    cannot fill the table.
    """

    id: str
    organization_id: str
    source_id: str
    trigger: AutoDisableTrigger
    reason: str
    breach_count: int
    window_start: datetime
    window_end: datetime
    status: AutoDisableEventStatus
    alert_event_id: str | None = None
    health_snapshot_id: str | None = None
    recovery_actor_id: str | None = None
    recovery_reason: str | None = None
    recovered_at: datetime | None = None
    audit_correlation_id: str = ""
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "source_id": self.source_id,
            "trigger": self.trigger.value,
            "reason": self.reason,
            "breach_count": int(self.breach_count),
            "window_start": (
                self.window_start.isoformat()
                if self.window_start
                else None
            ),
            "window_end": (
                self.window_end.isoformat() if self.window_end else None
            ),
            "status": self.status.value,
            "alert_event_id": self.alert_event_id,
            "health_snapshot_id": self.health_snapshot_id,
            "recovery_actor_id": self.recovery_actor_id,
            "recovery_reason": self.recovery_reason,
            "recovered_at": (
                self.recovered_at.isoformat()
                if self.recovered_at
                else None
            ),
            "audit_correlation_id": self.audit_correlation_id,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AutoDisableThresholds:
    """The closed set of thresholds the bounded
    auto-disable surface reads.

    The thresholds follow the defaults documented
    in `docs/product/connector-auto-disable-and-recovery.md`
    and are exposed as a single dataclass so a
    future story can extend the surface with
    per-tenant tuning without redefining the
    contract.
    """

    default_health_unhealthy_threshold: float = 1.0
    default_captcha_rate_breach_threshold: float = 0.2
    default_failure_rate_breach_threshold: float = 0.5
    default_needs_user_action_storm_threshold: int = 3
    default_error_spike_threshold: int = 3
    default_window_seconds: int = 1800
    default_consecutive_breaches: int = 3
    default_cooldown_seconds: int = 900
    min_window_seconds: int = 60
    max_window_seconds: int = 24 * 3600
    pilot_live_max_window_seconds: int = 24 * 3600
    test_like_max_window_seconds: int = 3600
    max_reason_length: int = 500
    max_recent_events_per_source: int = 50

    def max_window_seconds_for_mode(self, mode) -> int:
        """Return the closed `max_window_seconds`
        bound for the bounded `EnvironmentMode`.

        The follow-on per-tenant story can extend
        this method with explicit per-tenant
        tuning; the first slice follows the closed
        bound.
        """
        from livelead.domain.runtime.enums import EnvironmentMode

        if mode is EnvironmentMode.PILOT_LIVE:
            return self.pilot_live_max_window_seconds
        if mode is EnvironmentMode.PAUSED:
            return self.test_like_max_window_seconds
        return self.test_like_max_window_seconds


# ---------------------------------------------------------------------------
# Evaluation result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AutoDisableEvaluationResult:
    """The bounded result of an `AutoDisableEvaluator`
    evaluation cycle.

    The service uses the result to decide whether
    to flip `Source.enabled` to `false` and to
    persist a `ConnectorAutoDisableEvent` row.
    """

    should_disable: bool
    trigger: AutoDisableTrigger | None = None
    reason: str | None = None
    breach_count: int = 0
    window_start: datetime | None = None
    window_end: datetime | None = None
    alert_event_id: str | None = None
    health_snapshot_id: str | None = None
    rule_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "should_disable": bool(self.should_disable),
            "trigger": self.trigger.value if self.trigger else None,
            "reason": self.reason,
            "breach_count": int(self.breach_count),
            "window_start": (
                self.window_start.isoformat()
                if self.window_start
                else None
            ),
            "window_end": (
                self.window_end.isoformat() if self.window_end else None
            ),
            "alert_event_id": self.alert_event_id,
            "health_snapshot_id": self.health_snapshot_id,
            "rule_id": self.rule_id,
        }


# ---------------------------------------------------------------------------
# Discovery helper
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SourceRunDecision:
    """The bounded result of the source-side
    `evaluate_source_for_discovery` helper.

    The orchestrator from `US-004` / `US-032` /
    `US-033` / `US-034` reads the decision and
    either dispatches a discovery job or
    refuses with the bounded rejection code
    `SOURCE_AUTO_DISABLED` or
    `SOURCE_MANUAL_DISABLED`.
    """

    run_state: str  # "RUN_ALLOWED", "RUN_AUTO_DISABLED", "RUN_MANUAL_DISABLED"
    reason: str = ""
    event_id: str | None = None

    @property
    def is_allowed(self) -> bool:
        return self.run_state == "RUN_ALLOWED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_state": self.run_state,
            "reason": self.reason,
            "event_id": self.event_id,
        }


__all__ = [
    "AutoDisableEvaluationResult",
    "AutoDisableEventStatus",
    "AutoDisableThresholds",
    "ConnectorAutoDisableEvent",
    "ConnectorAutoDisableRule",
    "SourceRunDecision",
]
