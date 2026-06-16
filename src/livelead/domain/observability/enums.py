"""Observability and alerting enums (US-041).

Closed enumerations that the evaluator, the rule-management API, and
the alert-event lifecycle share. The values are persisted as strings
so the migration can use stable SQL `VARCHAR` columns; the application
layer normalises back to these enums at the boundary.
"""

from __future__ import annotations

from enum import StrEnum


class AlertMetric(StrEnum):
    """Closed set of metrics the first observability slice ships.

    Each metric maps to a single durable signal that the evaluator
    knows how to read. New metrics must be added here and to the
    evaluator's signal table; user-defined metrics are not part of
    the first slice.
    """

    BACKUP_AGE_HOURS = "backup.age_hours"
    WORKER_HEARTBEAT_AGE_SECONDS = "worker.heartbeat.age_seconds"
    CONNECTOR_FAILURE_RATE = "connector.failure_rate"
    DISCOVERY_NEEDS_USER_ACTION_RATE = "discovery.needs_user_action_rate"
    BROWSER_CRASH_LOOP = "browser.crash_loop"
    AUDIT_RETENTION_BREACH_RISK = "audit.retention_breach_risk"


class AlertOperator(StrEnum):
    """Closed set of threshold operators the evaluator understands.

    The grammar is intentionally tiny: `gt` / `gte` / `lt` / `lte` /
    `eq`. Anything else is rejected at rule creation with
    `ALERT_RULE_INVALID`.
    """

    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"


class AlertSeverity(StrEnum):
    """Severity ladder for alert events.

    The `critical` severity is the only one that defaults to email
    delivery for the seed rules. The other severities stay in-app
    unless a workspace owner opts in through the rule management
    API.
    """

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertChannel(StrEnum):
    """Delivery channel subset for the first observability slice.

    The first slice ships two channels: in-app inbox and email. Both
    are reused from `US-029` so the alert delivery path stays
    aligned with the rest of the product.
    """

    IN_APP = "in_app"
    EMAIL = "email"


class AlertEventStatus(StrEnum):
    """Lifecycle of a single alert event.

    The evaluator transitions `firing` -> `resolved` when the source
    signal clears. Operators transition `firing` -> `acknowledged`
    through the management API. A duplicate landing inside the
    cooldown window becomes `suppressed` and is recorded as a
    separate event row.
    """

    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
