"""Connector health surface domain enums (US-046).

Closed enumerations that the connector health
service, the `ConnectorHealthComputer`, the
`MetricRegistry` from `US-042`, the
`AlertMetric` enum from `US-041`, and the
audit entry shape share. The values are persisted
as strings so the migration can use stable SQL
`VARCHAR` columns; the application layer
normalises back to these enums at the boundary.

The vocabulary follows
`docs/decisions/0024-connector-health-surface-baseline.md`
and `SPEC.md` `FR-ADM-002`:

- `healthy`   — success rate >= 0.9 and CAPTCHA rate <= 0.05
- `degraded`  — success rate in [0.7, 0.9) or CAPTCHA rate in (0.05, 0.2]
- `unhealthy` — success rate < 0.7 or CAPTCHA rate > 0.2
- `unknown`   — no signals in the bounded window
"""

from __future__ import annotations

from enum import StrEnum

from livelead.domain.sources.models import (
    AccessMode,
    AuthenticationMode,
    ConnectorType,
)


class ConnectorHealthStatus(StrEnum):
    """Closed set of connector health status values.

    The bounded computation reads from the closed
    `success_rate` and `captcha_rate` thresholds
    and returns one of these four values. New
    statuses cannot be added without first
    extending the `ConnectorHealthService` and
    the audit entry shape.
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


# Re-export the source enums so the bounded
# connector health surface can build a single
# import surface for the audit and the metrics
# consumers.
__all__ = [
    "AccessMode",
    "AuthenticationMode",
    "ConnectorHealthStatus",
    "ConnectorType",
]
