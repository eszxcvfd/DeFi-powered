"""Connector health surface domain models (US-046).

Pure dataclasses with no I/O. The infrastructure
layer is responsible for translating these to and
from SQLAlchemy rows. The model layer deliberately
does not import SQLAlchemy, FastAPI, or any
framework.

The model layer reuses the closed
`ConnectorHealthStatus` enum and the closed
`ConnectorType` enum from
`livelead.domain.sources.models`. The
`ConnectorHealthService` is the only place that
mutates `connector_health_snapshots` and
`connector_health_errors`; the REST layer calls
it from the request handlers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from livelead.domain.connector_health.enums import (
    ConnectorHealthStatus,
)
from livelead.domain.sources.models import (
    ConnectorType,
)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConnectorHealthSnapshot:
    """A single record of a per-connector health
    computation result.

    The row carries enough information to answer
    the `FR-ADM-002` question "is connector X
    healthy right now?" without reading raw
    tables.
    """

    id: str
    organization_id: str
    source_id: str
    connector_type: ConnectorType
    window_start: datetime
    window_end: datetime
    total_runs: int
    success_count: int
    failure_count: int
    success_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    captcha_count: int
    captcha_rate: float
    last_run_at: datetime | None
    last_error_code: str | None
    last_error_message: str | None
    status: ConnectorHealthStatus
    audit_correlation_id: str = ""
    computed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "source_id": self.source_id,
            "connector_type": self.connector_type.value,
            "window_start": (
                self.window_start.isoformat()
                if self.window_start
                else None
            ),
            "window_end": (
                self.window_end.isoformat() if self.window_end else None
            ),
            "total_runs": int(self.total_runs),
            "success_count": int(self.success_count),
            "failure_count": int(self.failure_count),
            "success_rate": float(self.success_rate),
            "p50_latency_ms": float(self.p50_latency_ms),
            "p95_latency_ms": float(self.p95_latency_ms),
            "captcha_count": int(self.captcha_count),
            "captcha_rate": float(self.captcha_rate),
            "last_run_at": (
                self.last_run_at.isoformat() if self.last_run_at else None
            ),
            "last_error_code": self.last_error_code,
            "last_error_message": self.last_error_message,
            "status": self.status.value,
            "audit_correlation_id": self.audit_correlation_id,
            "computed_at": (
                self.computed_at.isoformat() if self.computed_at else None
            ),
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }


# ---------------------------------------------------------------------------
# Error rollup
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConnectorHealthError:
    """A single record of a recent error rollup.

    The table is bounded to the most recent N
    errors per source so a single failing
    connector cannot fill the table.
    """

    id: str
    organization_id: str
    source_id: str
    error_code: str
    error_message: str
    first_seen_at: datetime
    last_seen_at: datetime
    occurrence_count: int
    audit_correlation_id: str = ""
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "source_id": self.source_id,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "first_seen_at": (
                self.first_seen_at.isoformat()
                if self.first_seen_at
                else None
            ),
            "last_seen_at": (
                self.last_seen_at.isoformat()
                if self.last_seen_at
                else None
            ),
            "occurrence_count": int(self.occurrence_count),
            "audit_correlation_id": self.audit_correlation_id,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }


# ---------------------------------------------------------------------------
# Metrics derivation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConnectorHealthMetrics:
    """The bounded metrics the `ConnectorHealthComputer`
    derives from the `audit_entries` rows for a source.

    The metrics are the input to the
    `ConnectorHealthStatus` classification; the
    service persists the metrics on the
    `ConnectorHealthSnapshot` row.
    """

    total_runs: int
    success_count: int
    failure_count: int
    success_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    captcha_count: int
    captcha_rate: float
    last_run_at: datetime | None
    last_error_code: str | None
    last_error_message: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_runs": int(self.total_runs),
            "success_count": int(self.success_count),
            "failure_count": int(self.failure_count),
            "success_rate": float(self.success_rate),
            "p50_latency_ms": float(self.p50_latency_ms),
            "p95_latency_ms": float(self.p95_latency_ms),
            "captcha_count": int(self.captcha_count),
            "captcha_rate": float(self.captcha_rate),
            "last_run_at": (
                self.last_run_at.isoformat() if self.last_run_at else None
            ),
            "last_error_code": self.last_error_code,
            "last_error_message": self.last_error_message,
        }


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConnectorHealthThresholds:
    """The closed set of thresholds the bounded
    computation reads.

    The thresholds follow the defaults documented
    in `docs/product/connector-health-surface.md`
    and are exposed as a single dataclass so a
    future story can extend the surface with
    per-tenant tuning without redefining the
    contract.
    """

    healthy_min_success_rate: float = 0.9
    degraded_min_success_rate: float = 0.7
    healthy_max_captcha_rate: float = 0.05
    degraded_max_captcha_rate: float = 0.2
    default_window_seconds: int = 3600
    pilot_live_max_window_seconds: int = 24 * 3600
    test_like_max_window_seconds: int = 3600
    recent_errors_limit: int = 20
    max_error_message_length: int = 500

    def max_window_seconds(self) -> int:
        """Return the closed default `max_window_seconds`
        bound for the bounded surface.

        The follow-on per-tenant story can extend
        this method with explicit per-tenant
        tuning; the first slice follows the closed
        bound.
        """

        return self.pilot_live_max_window_seconds


# ---------------------------------------------------------------------------
# Summary view
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConnectorHealthSummaryEntry:
    """A single entry in the bounded per-source
    health summary.

    The entry carries the latest snapshot, the
    closed thresholds, the current values, and
    the breach flag for one source.
    """

    source_id: str
    source_name: str
    connector_type: ConnectorType
    snapshot: ConnectorHealthSnapshot | None
    healthy_min_success_rate: float
    degraded_min_success_rate: float
    healthy_max_captcha_rate: float
    degraded_max_captcha_rate: float
    breach: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "connector_type": self.connector_type.value,
            "snapshot": self.snapshot.to_dict() if self.snapshot else None,
            "healthy_min_success_rate": float(
                self.healthy_min_success_rate
            ),
            "degraded_min_success_rate": float(
                self.degraded_min_success_rate
            ),
            "healthy_max_captcha_rate": float(
                self.healthy_max_captcha_rate
            ),
            "degraded_max_captcha_rate": float(
                self.degraded_max_captcha_rate
            ),
            "breach": bool(self.breach),
        }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


# `total_runs` lower bound for the bounded path.
# Below this bound the bounded path reports
# `unknown` so a single early run does not flip a
# connector to `unhealthy`.
MIN_RUNS_FOR_STATUS: int = 1


@dataclass(frozen=True, slots=True)
class ConnectorHealthWindow:
    """A bounded window the `ConnectorHealthService`
    reads.

    The window is a closed `(start, end)` pair in
    UTC. The bounded path never reads signals
    outside the window.
    """

    start: datetime
    end: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
        }


__all__ = [
    "ConnectorHealthError",
    "ConnectorHealthMetrics",
    "ConnectorHealthSnapshot",
    "ConnectorHealthSummaryEntry",
    "ConnectorHealthThresholds",
    "ConnectorHealthWindow",
    "MIN_RUNS_FOR_STATUS",
]
