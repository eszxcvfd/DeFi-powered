from datetime import UTC, date, datetime

import pytest

from livelead.domain.reporting.metrics import classify_count_metric
from livelead.domain.reporting.models import MetricAvailability
from livelead.domain.reporting.time_window import (
    InvalidDashboardTimeWindow,
    normalize_time_window,
    window_bounds_utc,
)


def test_normalize_preset_last_7_days():
    w = normalize_time_window(preset="last_7_days", today=date(2026, 6, 14))
    assert w.start == date(2026, 6, 8)
    assert w.end == date(2026, 6, 14)
    assert w.preset == "last_7_days"


def test_normalize_custom_range():
    w = normalize_time_window(
        start=date(2026, 1, 1), end=date(2026, 1, 31), today=date(2026, 6, 14)
    )
    assert w.start == date(2026, 1, 1)
    assert w.end == date(2026, 1, 31)


def test_normalize_rejects_inverted_range():
    with pytest.raises(InvalidDashboardTimeWindow):
        normalize_time_window(start=date(2026, 6, 10), end=date(2026, 6, 1))


def test_window_bounds_utc_end_exclusive():
    w = normalize_time_window(start=date(2026, 6, 1), end=date(2026, 6, 1))
    start, end_ex = window_bounds_utc(w)
    assert start == datetime(2026, 6, 1, tzinfo=UTC)
    assert end_ex == datetime(2026, 6, 2, tzinfo=UTC)


def test_classify_empty_vs_available():
    ts = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    empty = classify_count_metric(
        key="leads_new",
        label="New leads",
        count=0,
        max_observed_at=None,
        freshness_source="leads.created_at",
        durable_source_exists=True,
    )
    assert empty.availability == MetricAvailability.EMPTY
    assert empty.value == 0

    avail = classify_count_metric(
        key="leads_new",
        label="New leads",
        count=3,
        max_observed_at=ts,
        freshness_source="leads.created_at",
        durable_source_exists=True,
    )
    assert avail.availability == MetricAvailability.AVAILABLE
    assert avail.value == 3
    assert avail.freshness.last_updated_at == ts


def test_classify_unavailable_not_zero():
    card = classify_count_metric(
        key="opportunities",
        label="Opportunities",
        count=0,
        max_observed_at=None,
        freshness_source="lead_activities",
        durable_source_exists=False,
        unavailable_reason="No outcomes yet.",
    )
    assert card.availability == MetricAvailability.UNAVAILABLE
    assert card.value is None
