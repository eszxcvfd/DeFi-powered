"""Performance baseline and SLO domain models (US-044).

Pure dataclasses with no I/O. The infrastructure
layer is responsible for translating these to and
from SQLAlchemy rows. The model layer deliberately
does not import SQLAlchemy, FastAPI, or any
framework.

The model layer reuses the `AlertMetric` enum
from `US-041` indirectly through the
`PerformanceMetric` enum. The
`PerformanceBaselineService` is the only place
that mutates `performance_snapshots`; the worker
actors and the REST layer call it from the
request handlers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from livelead.domain.performance.enums import (
    DEFAULT_API_READ_LATENCY_P95_MS,
    DEFAULT_API_READ_LATENCY_WINDOW_SECONDS,
    DEFAULT_BROWSER_SESSION_BUDGET_PCT,
    DEFAULT_BROWSER_SESSION_BUDGET_WINDOW_SECONDS,
    DEFAULT_CONCURRENCY_USERS_CAP,
    DEFAULT_CONCURRENCY_USERS_WINDOW_SECONDS,
    DEFAULT_DISCOVERY_FIRST_PROGRESS_P95_MS,
    DEFAULT_DISCOVERY_FIRST_PROGRESS_WINDOW_SECONDS,
    DEFAULT_EVENT_LIST_PAGINATION_P95_MS,
    DEFAULT_EVENT_LIST_PAGINATION_WINDOW_SECONDS,
    PerformanceMetric,
    PerformanceScenario,
    SUPPORTED_PERFORMANCE_METRICS,
    SUPPORTED_PERFORMANCE_SCENARIOS,
)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PerformanceSnapshot:
    """A single record of a load-test scenario result.

    The row carries enough information to prove that
    the SLO is achievable on the pilot hardware.
    """

    id: str
    organization_id: str
    scenario: PerformanceScenario
    started_at: datetime
    completed_at: datetime | None
    p50_ms: float
    p95_ms: float
    p99_ms: float
    rps: float
    error_rate: float
    concurrent_users: int
    audit_correlation_id: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "scenario": self.scenario.value,
            "started_at": (
                self.started_at.isoformat() if self.started_at else None
            ),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "p50_ms": float(self.p50_ms),
            "p95_ms": float(self.p95_ms),
            "p99_ms": float(self.p99_ms),
            "rps": float(self.rps),
            "error_rate": float(self.error_rate),
            "concurrent_users": int(self.concurrent_users),
            "audit_correlation_id": self.audit_correlation_id,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at else None
            ),
        }


# ---------------------------------------------------------------------------
# Browser session sample
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BrowserSessionSample:
    """A single browser session budget sample.

    The sample is recorded at session start, every
    30 seconds during the session, and at session
    end. When the `budget_pct` exceeds the
    configured threshold, the session is stopped
    safely by the enforcer.
    """

    id: str
    organization_id: str
    session_id: str
    profile_id: str
    memory_rss_mb: int
    cpu_pct: int
    budget_pct: int
    audited_at: datetime
    breach: bool = False
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "session_id": self.session_id,
            "profile_id": self.profile_id,
            "memory_rss_mb": int(self.memory_rss_mb),
            "cpu_pct": int(self.cpu_pct),
            "budget_pct": int(self.budget_pct),
            "breach": bool(self.breach),
            "audited_at": self.audited_at.isoformat() if self.audited_at else None,
            "created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }


# ---------------------------------------------------------------------------
# Summary view
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PerformanceSummaryEntry:
    """A single entry in the bounded SLO summary.

    The entry carries the latest snapshot, the
    SLO budget, the current percentile, and the
    breach flag for one scenario.
    """

    scenario: PerformanceScenario
    metric: PerformanceMetric
    snapshot: PerformanceSnapshot | None
    budget_p95_ms: float
    window_seconds: int
    breach: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario.value,
            "metric": self.metric.value,
            "snapshot": self.snapshot.to_dict() if self.snapshot else None,
            "budget_p95_ms": float(self.budget_p95_ms),
            "window_seconds": int(self.window_seconds),
            "breach": bool(self.breach),
        }


# ---------------------------------------------------------------------------
# SLO thresholds
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SloThresholds:
    """The closed set of SLO thresholds the bounded harness uses.

    The thresholds follow `NFR-PERF-001..005` and
    the documented defaults in
    `docs/product/performance-baseline-and-slo-guardrails.md`.
    """

    api_read_latency_p95_ms: int = DEFAULT_API_READ_LATENCY_P95_MS
    event_list_pagination_p95_ms: int = DEFAULT_EVENT_LIST_PAGINATION_P95_MS
    discovery_first_progress_p95_ms: int = (
        DEFAULT_DISCOVERY_FIRST_PROGRESS_P95_MS
    )
    concurrency_users_cap: int = DEFAULT_CONCURRENCY_USERS_CAP
    browser_session_budget_pct: int = DEFAULT_BROWSER_SESSION_BUDGET_PCT
    api_read_latency_window_seconds: int = (
        DEFAULT_API_READ_LATENCY_WINDOW_SECONDS
    )
    event_list_pagination_window_seconds: int = (
        DEFAULT_EVENT_LIST_PAGINATION_WINDOW_SECONDS
    )
    discovery_first_progress_window_seconds: int = (
        DEFAULT_DISCOVERY_FIRST_PROGRESS_WINDOW_SECONDS
    )
    concurrency_users_window_seconds: int = (
        DEFAULT_CONCURRENCY_USERS_WINDOW_SECONDS
    )
    browser_session_budget_window_seconds: int = (
        DEFAULT_BROWSER_SESSION_BUDGET_WINDOW_SECONDS
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_scenario(value: PerformanceScenario | str) -> PerformanceScenario:
    """Validate a candidate scenario against the closed enum."""

    if isinstance(value, PerformanceScenario):
        if value not in SUPPORTED_PERFORMANCE_SCENARIOS:
            raise ValueError(
                f"PERFORMANCE_INVALID:scenario_unsupported:{value.value}"
            )
        return value
    s = str(value)
    if s not in {x.value for x in SUPPORTED_PERFORMANCE_SCENARIOS}:
        raise ValueError(f"PERFORMANCE_INVALID:scenario_unsupported:{s}")
    return PerformanceScenario(s)


def validate_metric(value: PerformanceMetric | str) -> PerformanceMetric:
    """Validate a candidate metric against the closed enum."""

    if isinstance(value, PerformanceMetric):
        if value not in SUPPORTED_PERFORMANCE_METRICS:
            raise ValueError(
                f"PERFORMANCE_INVALID:metric_unsupported:{value.value}"
            )
        return value
    s = str(value)
    if s not in {m.value for m in SUPPORTED_PERFORMANCE_METRICS}:
        raise ValueError(f"PERFORMANCE_INVALID:metric_unsupported:{s}")
    return PerformanceMetric(s)


__all__ = [
    "BrowserSessionSample",
    "PerformanceSnapshot",
    "PerformanceSummaryEntry",
    "SloThresholds",
    "validate_metric",
    "validate_scenario",
]
