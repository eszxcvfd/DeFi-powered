"""Connector auto-disable domain (US-048).

Exposes the closed enums and bounded models
the application service, the REST layer, and
the source-side discovery helper share.
"""

from __future__ import annotations

from livelead.domain.auto_disable.enums import (
    AutoDisableEventStatus,
    AutoDisableTrigger,
)
from livelead.domain.auto_disable.models import (
    AutoDisableEvaluationResult,
    AutoDisableThresholds,
    ConnectorAutoDisableEvent,
    ConnectorAutoDisableRule,
    SourceRunDecision,
)

__all__ = [
    "AutoDisableEventStatus",
    "AutoDisableEvaluationResult",
    "AutoDisableThresholds",
    "AutoDisableTrigger",
    "ConnectorAutoDisableEvent",
    "ConnectorAutoDisableRule",
    "SourceRunDecision",
]
