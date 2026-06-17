"""Connector auto-disable application (US-048).

Exposes the bounded evaluator and the bounded
service the REST layer and the source-side
discovery helper share.
"""

from __future__ import annotations

from livelead.application.auto_disable.evaluator import (
    bounded_window,
    count_consecutive_breaches,
    evaluate_rule,
    in_cooldown,
)
from livelead.application.auto_disable.service import (
    AutoDisableError,
    AutoDisableEventNotFound,
    AutoDisableInvalidPayload,
    AutoDisableInvalidTrigger,
    AutoDisableInvalidWindow,
    AutoDisableRecoveryRejected,
    AutoDisableRuleNotFound,
    AutoDisableService,
    AutoDisableSourceNotFound,
)

__all__ = [
    "AutoDisableError",
    "AutoDisableEventNotFound",
    "AutoDisableInvalidPayload",
    "AutoDisableInvalidTrigger",
    "AutoDisableInvalidWindow",
    "AutoDisableRecoveryRejected",
    "AutoDisableRuleNotFound",
    "AutoDisableService",
    "AutoDisableSourceNotFound",
    "bounded_window",
    "count_consecutive_breaches",
    "evaluate_rule",
    "in_cooldown",
]
