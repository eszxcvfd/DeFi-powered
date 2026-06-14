"""Dashboard reporting read-model types (US-014)."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class MetricAvailability(StrEnum):
    AVAILABLE = "available"
    EMPTY = "empty"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class DashboardTimeWindow:
    start: date
    end: date
    preset: str | None = None


@dataclass(frozen=True, slots=True)
class WidgetFreshness:
    last_updated_at: datetime | None
    source: str


@dataclass(frozen=True, slots=True)
class DashboardMetricCard:
    key: str
    label: str
    availability: MetricAvailability
    value: int | None
    freshness: WidgetFreshness
    unavailable_reason: str | None = None


@dataclass(frozen=True, slots=True)
class DashboardOverview:
    time_window: DashboardTimeWindow
    widgets: tuple[DashboardMetricCard, ...]
    generated_at: datetime
