"""Tests for the connector health enums (US-046)."""

from __future__ import annotations

from livelead.domain.connector_health.enums import (
    ConnectorHealthStatus,
)
from livelead.domain.connector_health.models import (
    MIN_RUNS_FOR_STATUS,
)


def test_connector_health_status_is_closed() -> None:
    assert set(ConnectorHealthStatus) == {
        ConnectorHealthStatus.HEALTHY,
        ConnectorHealthStatus.DEGRADED,
        ConnectorHealthStatus.UNHEALTHY,
        ConnectorHealthStatus.UNKNOWN,
    }


def test_connector_health_status_values_are_stable_strings() -> None:
    assert ConnectorHealthStatus.HEALTHY.value == "healthy"
    assert ConnectorHealthStatus.DEGRADED.value == "degraded"
    assert ConnectorHealthStatus.UNHEALTHY.value == "unhealthy"
    assert ConnectorHealthStatus.UNKNOWN.value == "unknown"


def test_min_runs_for_status_default() -> None:
    assert MIN_RUNS_FOR_STATUS == 1


def test_connector_health_status_round_trip() -> None:
    for status in ConnectorHealthStatus:
        assert ConnectorHealthStatus(status.value) is status
