"""Unit tests for the performance baseline service (US-044)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.performance import (
    PerformanceBaselineService,
    PerformanceError,
)
from livelead.domain.performance.enums import (
    DEFAULT_API_READ_LATENCY_P95_MS,
    PerformanceScenario,
    Sloseverity,
)
from livelead.domain.performance.models import (
    SloThresholds,
    validate_scenario,
)


def test_validate_scenario_rejects_unknown_string() -> None:
    with pytest.raises(ValueError):
        validate_scenario("not_a_scenario")


def test_slo_thresholds_default_budget_p95_for_api_read_latency() -> None:
    thresholds = SloThresholds()
    assert thresholds.api_read_latency_p95_ms == (
        DEFAULT_API_READ_LATENCY_P95_MS
    )


@pytest.mark.asyncio
async def test_run_scenario_rejects_unknown_scenario(session: AsyncSession):
    service = PerformanceBaselineService(session)
    with pytest.raises(PerformanceError) as exc:
        await service.run_scenario(
            organization_id="00000000-0000-4000-8000-000000000001",
            scenario="not_a_scenario",
        )
    assert "scenario_unsupported" in str(exc.value)


def test_metric_for_scenario_dispatch() -> None:
    """The bounded service maps each scenario to a single
    performance metric; the mapping is closed and
    matches the documentation in
    `docs/product/performance-baseline-and-slo-guardrails.md`."""

    service = PerformanceBaselineService(
        session=None,  # type: ignore[arg-type]
    )
    assert (
        service._metric_for(PerformanceScenario.API_READ_LATENCY).value
        == "api.read.latency_ms"
    )
    assert (
        service._metric_for(PerformanceScenario.EVENT_LIST_PAGINATION).value
        == "event.list.pagination.latency_ms"
    )
    assert (
        service._metric_for(PerformanceScenario.DISCOVERY_FIRST_PROGRESS).value
        == "discovery.first_progress_ms"
    )
    assert (
        service._metric_for(PerformanceScenario.CONCURRENCY_CAP).value
        == "concurrency.users"
    )
    assert (
        service._metric_for(PerformanceScenario.BROWSER_SESSION_BUDGET).value
        == "browser.session.budget_pct"
    )


def test_budget_for_scenario_dispatch() -> None:
    service = PerformanceBaselineService(
        session=None,  # type: ignore[arg-type]
    )
    budget, window = service._budget_for(PerformanceScenario.API_READ_LATENCY)
    assert budget == 500.0
    assert window == 300
    budget, window = service._budget_for(PerformanceScenario.EVENT_LIST_PAGINATION)
    assert budget == 2_000.0
    assert window == 600
    budget, window = service._budget_for(PerformanceScenario.DISCOVERY_FIRST_PROGRESS)
    assert budget == 5_000.0
    assert window == 300
    budget, window = service._budget_for(PerformanceScenario.CONCURRENCY_CAP)
    assert budget == 100.0
    assert window == 60
    budget, window = service._budget_for(PerformanceScenario.BROWSER_SESSION_BUDGET)
    assert budget == 90.0
    assert window == 120
