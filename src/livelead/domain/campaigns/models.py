"""Campaign domain types — no framework imports."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class DateRange:
    start: date | None = None
    end: date | None = None


@dataclass(frozen=True, slots=True)
class IcpCriteria:
    industry: str = ""
    organization_type: str = ""
    company_size: str = ""
    role_or_title_targets: tuple[str, ...] = ()
    country_or_region: str = ""
    pain_points: tuple[str, ...] = ()
    use_cases: tuple[str, ...] = ()
    positive_keywords: tuple[str, ...] = ()
    excluded_keywords: tuple[str, ...] = ()


DEFAULT_SCORING_WEIGHTS: dict[str, float] = {
    "topic_relevance": 0.25,
    "icp_match": 0.20,
    "organizer_reputation": 0.10,
    "speaker_relevance": 0.10,
    "audience_quality": 0.10,
    "engagement_accessibility": 0.08,
    "replay_availability": 0.07,
    "geographic_fit": 0.05,
    "timing_fit": 0.05,
}


@dataclass(frozen=True, slots=True)
class ScoringWeights:
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_SCORING_WEIGHTS))

    def normalized(self) -> "ScoringWeights":
        total = sum(self.weights.values())
        if total <= 0:
            return ScoringWeights(weights=dict(DEFAULT_SCORING_WEIGHTS))
        return ScoringWeights(weights={k: v / total for k, v in self.weights.items()})


@dataclass(frozen=True, slots=True)
class Campaign:
    id: UUID
    organization_id: UUID
    name: str
    description: str
    target_industry: str
    product_or_service_focus: str
    market_regions: tuple[str, ...]
    languages: tuple[str, ...]
    timezone: str
    date_range: DateRange
    positive_keywords: tuple[str, ...]
    exclude_keywords: tuple[str, ...]
    icp: IcpCriteria
    scoring_weights: ScoringWeights
    status: CampaignStatus
    created_at: datetime
    updated_at: datetime
    parent_campaign_id: UUID | None = None
    created_by_actor: str = "analyst"
    creation_source: str = "user"
    automation_run_id: str | None = None