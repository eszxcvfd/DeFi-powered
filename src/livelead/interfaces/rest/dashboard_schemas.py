"""Dashboard overview API schemas (US-014)."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class DashboardTimeWindowSchema(BaseModel):
    start: date
    end: date
    preset: str | None = None


class WidgetFreshnessSchema(BaseModel):
    last_updated_at: datetime | None = None
    source: str


class DashboardMetricCardSchema(BaseModel):
    key: str
    label: str
    availability: str
    value: int | None = None
    freshness: WidgetFreshnessSchema
    unavailable_reason: str | None = None


class DashboardOverviewSchema(BaseModel):
    time_window: DashboardTimeWindowSchema
    widgets: list[DashboardMetricCardSchema] = Field(default_factory=list)
    generated_at: datetime
