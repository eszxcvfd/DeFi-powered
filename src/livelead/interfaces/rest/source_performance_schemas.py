"""Source-performance API schemas (US-017)."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class SourcePerformanceWindowSchema(BaseModel):
    start: date
    end: date
    preset: str | None = None


class SourcePerformanceMetricsSchema(BaseModel):
    events_discovered: int = 0
    events_prioritized: int = 0
    leads_created: int = 0
    opportunities: int = 0


class SourcePerformanceRowSchema(BaseModel):
    group_key: str
    group_label: str
    metrics: SourcePerformanceMetricsSchema


class UnattributedSourceSummarySchema(BaseModel):
    events_without_source_link: int = 0
    leads_without_group_key: int = 0
    explanation: str = ""


class SourcePerformanceFreshnessSchema(BaseModel):
    last_updated_at: datetime | None = None
    source: str


class SourcePerformanceReportSchema(BaseModel):
    grouping: str
    grouping_label: str
    window: SourcePerformanceWindowSchema
    rows: list[SourcePerformanceRowSchema] = Field(default_factory=list)
    unattributed: UnattributedSourceSummarySchema | None = None
    freshness: SourcePerformanceFreshnessSchema
    generated_at: datetime
