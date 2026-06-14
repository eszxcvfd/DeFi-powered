from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DateRangeSchema(BaseModel):
    start: date | None = None
    end: date | None = None


class IcpCriteriaSchema(BaseModel):
    industry: str = ""
    organization_type: str = ""
    company_size: str = ""
    role_or_title_targets: list[str] = Field(default_factory=list)
    country_or_region: str = ""
    pain_points: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    positive_keywords: list[str] = Field(default_factory=list)
    excluded_keywords: list[str] = Field(default_factory=list)


class CampaignCreateSchema(BaseModel):
    name: str
    description: str = ""
    target_industry: str = ""
    product_or_service_focus: str = ""
    market_regions: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    timezone: str = "UTC"
    date_range: DateRangeSchema = Field(default_factory=DateRangeSchema)
    positive_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    icp: IcpCriteriaSchema = Field(default_factory=IcpCriteriaSchema)
    scoring_weights: dict[str, float] = Field(default_factory=dict)
    parent_campaign_id: UUID | None = None


class CampaignPatchSchema(BaseModel):
    name: str | None = None
    description: str | None = None
    target_industry: str | None = None
    product_or_service_focus: str | None = None
    market_regions: list[str] | None = None
    languages: list[str] | None = None
    timezone: str | None = None
    date_range: DateRangeSchema | None = None
    positive_keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    icp: IcpCriteriaSchema | None = None
    scoring_weights: dict[str, float] | None = None
    status: str | None = None


class CampaignSummarySchema(BaseModel):
    id: UUID
    name: str
    target_industry: str
    status: str
    updated_at: datetime
    parent_campaign_id: UUID | None = None
    parent_name: str | None = None
    created_by_actor: str = "analyst"
    creation_source: str = "user"
    creation_source_label: str = "Manual"
    automation_run_id: str | None = None
    child_count: int = 0
    depth: int = 0


class CampaignDetailSchema(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str
    target_industry: str
    product_or_service_focus: str
    market_regions: list[str]
    languages: list[str]
    timezone: str
    date_range: DateRangeSchema
    positive_keywords: list[str]
    exclude_keywords: list[str]
    icp: IcpCriteriaSchema
    scoring_weights: dict[str, float]
    status: str
    created_at: datetime
    updated_at: datetime
    parent_campaign_id: UUID | None = None
    parent_name: str | None = None
    created_by_actor: str = "analyst"
    creation_source: str = "user"
    creation_source_label: str = "Manual"
    automation_run_id: str | None = None
    child_count: int = 0
    deferred: dict[str, str] = Field(
        default_factory=lambda: {
            "source_selection": "enabled",
            "run_discovery": "enabled",
        }
    )
