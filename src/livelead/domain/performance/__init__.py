"""Performance baseline and SLO domain (US-044)."""

from __future__ import annotations

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
    Sloseverity,
    SUPPORTED_PERFORMANCE_METRICS,
    SUPPORTED_PERFORMANCE_SCENARIOS,
)
from livelead.domain.performance.models import (
    BrowserSessionSample,
    PerformanceSnapshot,
    PerformanceSummaryEntry,
    SloThresholds,
    validate_metric,
    validate_scenario,
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
    "BrowserSessionSample",
    "PerformanceMetric",
    "PerformanceScenario",
    "PerformanceSnapshot",
    "PerformanceSummaryEntry",
    "SloThresholds",
    "Sloseverity",
    "SUPPORTED_PERFORMANCE_METRICS",
    "SUPPORTED_PERFORMANCE_SCENARIOS",
    "validate_metric",
    "validate_scenario",
]
