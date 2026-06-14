"""Funnel report API schemas (US-016)."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class FunnelCohortSchema(BaseModel):
    start: date
    end: date
    preset: str | None = None
    rule: str


class FunnelStepSchema(BaseModel):
    key: str
    label: str
    count: int
    note: str | None = None


class UnattributedLeadSummarySchema(BaseModel):
    manual_leads_in_cohort: int
    explanation: str


class FunnelFreshnessSchema(BaseModel):
    last_updated_at: datetime | None = None
    source: str


class FunnelReportSchema(BaseModel):
    cohort: FunnelCohortSchema
    steps: list[FunnelStepSchema] = Field(default_factory=list)
    unattributed: UnattributedLeadSummarySchema | None = None
    freshness: FunnelFreshnessSchema
    generated_at: datetime
