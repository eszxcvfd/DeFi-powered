"""Connector health surface domain types (US-046)."""

from __future__ import annotations

from livelead.domain.connector_health.enums import (
    AccessMode,
    AuthenticationMode,
    ConnectorHealthStatus,
    ConnectorType,
)
from livelead.domain.connector_health.models import (
    MIN_RUNS_FOR_STATUS,
    ConnectorHealthError,
    ConnectorHealthMetrics,
    ConnectorHealthSnapshot,
    ConnectorHealthSummaryEntry,
    ConnectorHealthThresholds,
    ConnectorHealthWindow,
)

__all__ = [
    "AccessMode",
    "AuthenticationMode",
    "ConnectorHealthError",
    "ConnectorHealthMetrics",
    "ConnectorHealthSnapshot",
    "ConnectorHealthStatus",
    "ConnectorHealthSummaryEntry",
    "ConnectorHealthThresholds",
    "ConnectorHealthWindow",
    "ConnectorType",
    "MIN_RUNS_FOR_STATUS",
]
