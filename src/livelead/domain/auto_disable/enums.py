"""Connector auto-disable domain enums (US-048).

Closed enumerations that the bounded
`AutoDisableService`, the
`AutoDisableEvaluator`, the `AlertEvent` rows
from `US-041`, the `ConnectorHealthSnapshot`
rows from `US-046`, and the audit entry shape
share. The values are persisted as strings so
the migration can use stable SQL `VARCHAR`
columns; the application layer normalises back
to these enums at the boundary.

The vocabulary follows
`docs/decisions/0026-connector-auto-disable-and-policy-recovery-baseline.md`
and `SPEC.md` `FR-SRC-004` + `SPEC.md` 11.1
kill-switch requirements.
"""

from __future__ import annotations

from enum import StrEnum


class AutoDisableTrigger(StrEnum):
    """Closed set of auto-disable trigger values.

    The bounded `AutoDisableService` reads the
    trigger from the closed `ConnectorHealthStatus`
    enum from `US-046` and the closed
    `AlertMetric` enum from `US-041`. New
    triggers cannot be added without first
    extending the `AutoDisableService` and the
    audit entry shape.
    """

    HEALTH_UNHEALTHY = "health_unhealthy"
    CAPTCHA_RATE_BREACH = "captcha_rate_breach"
    FAILURE_RATE_BREACH = "failure_rate_breach"
    NEEDS_USER_ACTION_STORM = "needs_user_action_storm"
    ERROR_SPIKE = "error_spike"
    MANUAL_KILL_SWITCH = "manual_kill_switch"


class AutoDisableEventStatus(StrEnum):
    """Closed set of auto-disable event status
    values.

    The bounded service uses the status to
    track the lifecycle of an auto-disable
    event.
    """

    ACTIVE = "active"
    RECOVERING = "recovering"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"


__all__ = [
    "AutoDisableEventStatus",
    "AutoDisableTrigger",
]
