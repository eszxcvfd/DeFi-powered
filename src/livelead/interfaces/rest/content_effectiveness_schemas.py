"""Content-effectiveness API schemas (US-018)."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class ContentEffectivenessWindowSchema(BaseModel):
    start: date
    end: date
    preset: str | None = None


class ContentEffectivenessMetricsSchema(BaseModel):
    content_used: int = 0
    outcomes_linked: int = 0
    outcomes_contact: int = 0
    outcomes_response: int = 0
    outcomes_meeting: int = 0
    outcomes_opportunity: int = 0


class ContentEffectivenessRowSchema(BaseModel):
    group_key: str
    group_label: str
    metrics: ContentEffectivenessMetricsSchema


class UnattributedContentSummarySchema(BaseModel):
    used_content_without_metadata: int = 0
    outcomes_without_content_link: int = 0
    explanation: str = ""


class ContentEffectivenessFreshnessSchema(BaseModel):
    last_updated_at: datetime | None = None
    source: str


class ContentEffectivenessReportSchema(BaseModel):
    grouping: str
    grouping_label: str
    window: ContentEffectivenessWindowSchema
    rows: list[ContentEffectivenessRowSchema] = Field(default_factory=list)
    unattributed: UnattributedContentSummarySchema | None = None
    freshness: ContentEffectivenessFreshnessSchema
    correlation_note: str
    generated_at: datetime
