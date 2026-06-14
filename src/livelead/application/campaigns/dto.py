"""Parsed campaign write models at application boundary."""

from dataclasses import dataclass

from livelead.domain.campaigns.models import IcpCriteria, ScoringWeights


@dataclass(slots=True)
class CampaignWriteData:
    name: str
    description: str
    target_industry: str
    product_or_service_focus: str
    market_regions: list[str]
    languages: list[str]
    timezone: str
    date_range: dict[str, str | None]
    positive_keywords: list[str]
    exclude_keywords: list[str]
    icp: IcpCriteria
    scoring_weights: ScoringWeights
    status: str = "draft"