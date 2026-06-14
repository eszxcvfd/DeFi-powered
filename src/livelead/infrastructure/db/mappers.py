import json
from datetime import date, datetime
from uuid import UUID

from livelead.domain.campaigns.models import (
    Campaign,
    CampaignStatus,
    DateRange,
    IcpCriteria,
    ScoringWeights,
)
from livelead.infrastructure.db.models import CampaignRow


def _parse_date(value: str | date | None) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _tuple_from_json(raw: str) -> tuple[str, ...]:
    data = json.loads(raw or "[]")
    return tuple(str(x) for x in data)


def row_to_campaign(row: CampaignRow) -> Campaign:
    icp_data = json.loads(row.icp_json or "{}")
    weights_data = json.loads(row.scoring_weights_json or "{}")
    icp = IcpCriteria(
        industry=icp_data.get("industry", ""),
        organization_type=icp_data.get("organization_type", ""),
        company_size=icp_data.get("company_size", ""),
        role_or_title_targets=tuple(icp_data.get("role_or_title_targets", [])),
        country_or_region=icp_data.get("country_or_region", ""),
        pain_points=tuple(icp_data.get("pain_points", [])),
        use_cases=tuple(icp_data.get("use_cases", [])),
        positive_keywords=tuple(icp_data.get("positive_keywords", [])),
        excluded_keywords=tuple(icp_data.get("excluded_keywords", [])),
    )
    weights = ScoringWeights(weights={k: float(v) for k, v in weights_data.items()}) if weights_data else ScoringWeights()
    return Campaign(
        id=UUID(row.id),
        organization_id=UUID(row.organization_id),
        name=row.name,
        description=row.description or "",
        target_industry=row.target_industry or "",
        product_or_service_focus=row.product_or_service_focus or "",
        market_regions=_tuple_from_json(row.market_regions_json),
        languages=_tuple_from_json(row.languages_json),
        timezone=row.timezone or "UTC",
        date_range=DateRange(start=_parse_date(row.date_start), end=_parse_date(row.date_end)),
        positive_keywords=_tuple_from_json(row.positive_keywords_json),
        exclude_keywords=_tuple_from_json(row.exclude_keywords_json),
        icp=icp,
        scoring_weights=weights.normalized(),
        status=CampaignStatus(row.status),
        parent_campaign_id=UUID(row.parent_campaign_id) if row.parent_campaign_id else None,
        created_by_actor=row.created_by_actor or "analyst",
        creation_source=row.creation_source or "user",
        automation_run_id=row.automation_run_id,
        created_at=row.created_at if isinstance(row.created_at, datetime) else datetime.now(),
        updated_at=row.updated_at if isinstance(row.updated_at, datetime) else datetime.now(),
    )


def icp_to_json(icp: IcpCriteria) -> str:
    return json.dumps(
        {
            "industry": icp.industry,
            "organization_type": icp.organization_type,
            "company_size": icp.company_size,
            "role_or_title_targets": list(icp.role_or_title_targets),
            "country_or_region": icp.country_or_region,
            "pain_points": list(icp.pain_points),
            "use_cases": list(icp.use_cases),
            "positive_keywords": list(icp.positive_keywords),
            "excluded_keywords": list(icp.excluded_keywords),
        }
    )


def weights_to_json(weights: ScoringWeights) -> str:
    return json.dumps(weights.weights)