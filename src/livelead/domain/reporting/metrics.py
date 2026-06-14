"""Metric availability classification helpers (US-014)."""

from datetime import datetime

from livelead.domain.reporting.models import (
    DashboardMetricCard,
    MetricAvailability,
    WidgetFreshness,
)


def classify_count_metric(
    *,
    key: str,
    label: str,
    count: int,
    max_observed_at: datetime | None,
    freshness_source: str,
    durable_source_exists: bool,
    unavailable_reason: str | None = None,
) -> DashboardMetricCard:
    if not durable_source_exists:
        return DashboardMetricCard(
            key=key,
            label=label,
            availability=MetricAvailability.UNAVAILABLE,
            value=None,
            freshness=WidgetFreshness(last_updated_at=None, source=freshness_source),
            unavailable_reason=unavailable_reason or "No durable source data for this metric yet.",
        )
    if count == 0:
        availability = MetricAvailability.EMPTY
        value: int | None = 0
    else:
        availability = MetricAvailability.AVAILABLE
        value = count
    return DashboardMetricCard(
        key=key,
        label=label,
        availability=availability,
        value=value,
        freshness=WidgetFreshness(last_updated_at=max_observed_at, source=freshness_source),
        unavailable_reason=None,
    )
