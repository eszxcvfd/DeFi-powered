from livelead.application.campaigns.dto import CampaignWriteData
from livelead.domain.campaigns.models import IcpCriteria, ScoringWeights
from livelead.domain.campaigns.validation import validate_campaign_name, validate_scoring_weights


def _icp_from_dict(data: dict | None) -> IcpCriteria:
    data = data or {}
    return IcpCriteria(
        industry=data.get("industry", ""),
        organization_type=data.get("organization_type", ""),
        company_size=data.get("company_size", ""),
        role_or_title_targets=tuple(data.get("role_or_title_targets", [])),
        country_or_region=data.get("country_or_region", ""),
        pain_points=tuple(data.get("pain_points", [])),
        use_cases=tuple(data.get("use_cases", [])),
        positive_keywords=tuple(data.get("positive_keywords", [])),
        excluded_keywords=tuple(data.get("excluded_keywords", [])),
    )


def parse_create_body(body: dict) -> tuple[CampaignWriteData | None, list[str]]:
    errors: list[str] = []
    name = body.get("name", "")
    errors.extend(validate_campaign_name(name))
    raw_weights = body.get("scoring_weights") or {}
    weights, w_err = validate_scoring_weights({k: float(v) for k, v in raw_weights.items()} if raw_weights else {})
    errors.extend(w_err)
    if errors:
        return None, errors
    dr = body.get("date_range") or {}
    return (
        CampaignWriteData(
            name=name,
            description=body.get("description", ""),
            target_industry=body.get("target_industry", ""),
            product_or_service_focus=body.get("product_or_service_focus", ""),
            market_regions=list(body.get("market_regions", [])),
            languages=list(body.get("languages", [])),
            timezone=body.get("timezone", "UTC"),
            date_range={"start": dr.get("start"), "end": dr.get("end")},
            positive_keywords=list(body.get("positive_keywords", [])),
            exclude_keywords=list(body.get("exclude_keywords", [])),
            icp=_icp_from_dict(body.get("icp")),
            scoring_weights=weights or ScoringWeights(),
        ),
        [],
    )


def parse_patch_body(body: dict) -> tuple[dict | None, list[str]]:
    errors: list[str] = []
    patch: dict = {}
    if "name" in body:
        errors.extend(validate_campaign_name(body["name"]))
        patch["name"] = body["name"]
    for key in (
        "description",
        "target_industry",
        "product_or_service_focus",
        "market_regions",
        "languages",
        "timezone",
        "positive_keywords",
        "exclude_keywords",
        "date_range",
        "status",
    ):
        if key in body:
            patch[key] = body[key]
    if "icp" in body:
        patch["icp"] = _icp_from_dict(body["icp"])
    if "scoring_weights" in body:
        raw = body["scoring_weights"] or {}
        weights, w_err = validate_scoring_weights({k: float(v) for k, v in raw.items()} if raw else {})
        errors.extend(w_err)
        if weights:
            patch["scoring_weights"] = weights
    if errors:
        return None, errors
    return patch, []