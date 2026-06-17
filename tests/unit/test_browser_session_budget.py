"""Unit tests for the browser session budget enforcer (US-044)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.performance import (
    BrowserSessionBudgetEnforcer,
)
from livelead.application.performance.browser_session_budget import (
    _safe_budget_pct,
)
from livelead.domain.performance.models import SloThresholds


def test_safe_budget_pct_picks_max_of_memory_and_cpu() -> None:
    # memory wins (clamped).
    assert _safe_budget_pct(memory_rss_mb=900, cpu_pct=50) == 900
    # cpu wins (memory clamped lower).
    assert _safe_budget_pct(memory_rss_mb=30, cpu_pct=80) == 80
    # equal.
    assert _safe_budget_pct(memory_rss_mb=42, cpu_pct=42) == 42


def test_safe_budget_pct_clamps_negative_to_zero() -> None:
    assert _safe_budget_pct(memory_rss_mb=-5, cpu_pct=10) == 10
    assert _safe_budget_pct(memory_rss_mb=10, cpu_pct=-5) == 10
    assert _safe_budget_pct(memory_rss_mb=-5, cpu_pct=-5) == 0


def test_safe_budget_pct_clamps_oversize_to_max() -> None:
    # memory clamped to 1024.
    assert _safe_budget_pct(memory_rss_mb=5000, cpu_pct=99) == 1024
    # cpu clamped to 100.
    assert _safe_budget_pct(memory_rss_mb=200, cpu_pct=500) == 200


def test_breach_threshold_uses_slo_defaults() -> None:
    thresholds = SloThresholds()
    assert thresholds.browser_session_budget_pct == 90
    assert thresholds.browser_session_budget_window_seconds == 120
