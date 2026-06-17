"""Performance baseline and SLO enums (US-044).

Closed enumerations for the bounded performance
harness. The values are persisted as strings so the
migration can use stable SQL `VARCHAR` columns; the
application layer normalises back to these enums at
the boundary.

The `PerformanceMetric` enum extends the closed
`AlertMetric` enum from `US-041` and the
`MetricRegistry` from `US-042` with five new
metrics. New metrics cannot be added without first
being added to the `US-041` `AlertMetric` enum.
"""

from __future__ import annotations

from enum import StrEnum


class PerformanceMetric(StrEnum):
    """Closed set of performance metrics the SLO harness exports.

    Each metric maps to a single `NFR-PERF-*` target
    and to a single SLO alert rule from the seed set
    in the migration. New metrics must be added
    here, to the `US-041` `AlertMetric` enum, and to
    the `US-042` `MetricRegistry` in the same change.
    """

    API_READ_LATENCY_MS = "api.read.latency_ms"
    EVENT_LIST_PAGINATION_LATENCY_MS = "event.list.pagination.latency_ms"
    DISCOVERY_FIRST_PROGRESS_MS = "discovery.first_progress_ms"
    CONCURRENCY_USERS = "concurrency.users"
    BROWSER_SESSION_BUDGET_PCT = "browser.session.budget_pct"


class PerformanceScenario(StrEnum):
    """Closed set of scenario identifiers the bounded harness accepts."""

    API_READ_LATENCY = "api_read_latency"
    EVENT_LIST_PAGINATION = "event_list_pagination"
    DISCOVERY_FIRST_PROGRESS = "discovery_first_progress"
    CONCURRENCY_CAP = "concurrency_cap"
    BROWSER_SESSION_BUDGET = "browser_session_budget"


class Sloseverity(StrEnum):
    """Severity ladder for SLO alert rules.

    The first slice maps the seed SLO rules to
    `warning` for the operational metrics and
    `critical` for the browser session budget breach
    (per the documentation in
    `docs/product/performance-baseline-and-slo-guardrails.md`).
    """

    WARNING = "warning"
    CRITICAL = "critical"


# Default SLO budgets that follow `NFR-PERF-001..005`.
DEFAULT_API_READ_LATENCY_P95_MS: int = 500
DEFAULT_EVENT_LIST_PAGINATION_P95_MS: int = 2_000
DEFAULT_DISCOVERY_FIRST_PROGRESS_P95_MS: int = 5_000
DEFAULT_CONCURRENCY_USERS_CAP: int = 100
DEFAULT_BROWSER_SESSION_BUDGET_PCT: int = 90

# Default evaluation windows (seconds).
DEFAULT_API_READ_LATENCY_WINDOW_SECONDS: int = 300
DEFAULT_EVENT_LIST_PAGINATION_WINDOW_SECONDS: int = 600
DEFAULT_DISCOVERY_FIRST_PROGRESS_WINDOW_SECONDS: int = 300
DEFAULT_CONCURRENCY_USERS_WINDOW_SECONDS: int = 60
DEFAULT_BROWSER_SESSION_BUDGET_WINDOW_SECONDS: int = 120

SUPPORTED_PERFORMANCE_METRICS: frozenset[PerformanceMetric] = frozenset(
    PerformanceMetric
)
SUPPORTED_PERFORMANCE_SCENARIOS: frozenset[PerformanceScenario] = frozenset(
    PerformanceScenario
)


__all__ = [
    "DEFAULT_API_READ_LATENCY_P95_MS",
    "DEFAULT_API_READ_LATENCY_WINDOW_SECONDS",
    "DEFAULT_BROWSER_SESSION_BUDGET_PCT",
    "DEFAULT_BROWSER_SESSION_BUDGET_WINDOW_SECONDS",
    "DEFAULT_CONCURRENCY_USERS_CAP",
    "DEFAULT_CONCURRENCY_USERS_WINDOW_SECONDS",
    "DEFAULT_DISCOVERY_FIRST_PROGRESS_P95_MS",
    "DEFAULT_DISCOVERY_FIRST_PROGRESS_WINDOW_SECONDS",
    "DEFAULT_EVENT_LIST_PAGINATION_P95_MS",
    "DEFAULT_EVENT_LIST_PAGINATION_WINDOW_SECONDS",
    "PerformanceMetric",
    "PerformanceScenario",
    "Sloseverity",
    "SUPPORTED_PERFORMANCE_METRICS",
    "SUPPORTED_PERFORMANCE_SCENARIOS",
]
