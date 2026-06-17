"""Unit tests for the performance baseline and SLO enums (US-044)."""

from __future__ import annotations

import pytest

from livelead.domain.performance.enums import (
    DEFAULT_API_READ_LATENCY_P95_MS,
    DEFAULT_BROWSER_SESSION_BUDGET_PCT,
    DEFAULT_CONCURRENCY_USERS_CAP,
    DEFAULT_DISCOVERY_FIRST_PROGRESS_P95_MS,
    DEFAULT_EVENT_LIST_PAGINATION_P95_MS,
    PerformanceMetric,
    PerformanceScenario,
    Sloseverity,
    SUPPORTED_PERFORMANCE_METRICS,
    SUPPORTED_PERFORMANCE_SCENARIOS,
)
from livelead.domain.performance.models import (
    SloThresholds,
    validate_metric,
    validate_scenario,
)


def test_performance_metric_enum_is_closed() -> None:
    assert {m.value for m in PerformanceMetric} == {
        "api.read.latency_ms",
        "event.list.pagination.latency_ms",
        "discovery.first_progress_ms",
        "concurrency.users",
        "browser.session.budget_pct",
    }


def test_performance_scenario_enum_is_closed() -> None:
    assert {s.value for s in PerformanceScenario} == {
        "api_read_latency",
        "event_list_pagination",
        "discovery_first_progress",
        "concurrency_cap",
        "browser_session_budget",
    }


def test_supported_performance_sets_match_enum() -> None:
    assert SUPPORTED_PERFORMANCE_METRICS == frozenset(PerformanceMetric)
    assert SUPPORTED_PERFORMANCE_SCENARIOS == frozenset(PerformanceScenario)


def test_slo_severity_enum_is_closed() -> None:
    assert {s.value for s in Sloseverity} == {"warning", "critical"}


def test_default_thresholds_match_nfr_perf() -> None:
    assert DEFAULT_API_READ_LATENCY_P95_MS == 500
    assert DEFAULT_EVENT_LIST_PAGINATION_P95_MS == 2_000
    assert DEFAULT_DISCOVERY_FIRST_PROGRESS_P95_MS == 5_000
    assert DEFAULT_CONCURRENCY_USERS_CAP == 100
    assert DEFAULT_BROWSER_SESSION_BUDGET_PCT == 90


def test_validate_scenario_accepts_enum() -> None:
    assert validate_scenario(PerformanceScenario.API_READ_LATENCY) == (
        PerformanceScenario.API_READ_LATENCY
    )


def test_validate_scenario_accepts_string() -> None:
    assert validate_scenario("api_read_latency") == (
        PerformanceScenario.API_READ_LATENCY
    )


def test_validate_scenario_rejects_unknown() -> None:
    with pytest.raises(ValueError) as exc:
        validate_scenario("not_a_scenario")
    assert "scenario_unsupported" in str(exc.value)


def test_validate_metric_accepts_enum() -> None:
    assert validate_metric(PerformanceMetric.API_READ_LATENCY_MS) == (
        PerformanceMetric.API_READ_LATENCY_MS
    )


def test_validate_metric_rejects_unknown() -> None:
    with pytest.raises(ValueError) as exc:
        validate_metric("not_a_metric")
    assert "metric_unsupported" in str(exc.value)


def test_slo_thresholds_defaults_match_spec() -> None:
    thresholds = SloThresholds()
    assert thresholds.api_read_latency_p95_ms == 500
    assert thresholds.event_list_pagination_p95_ms == 2_000
    assert thresholds.discovery_first_progress_p95_ms == 5_000
    assert thresholds.concurrency_users_cap == 100
    assert thresholds.browser_session_budget_pct == 90
