from datetime import UTC, datetime
from uuid import uuid4

from livelead.domain.campaigns.models import (
    Campaign,
    CampaignStatus,
    DateRange,
    IcpCriteria,
    ScoringWeights,
)
from livelead.domain.events.models import CanonicalEvent
from livelead.domain.scoring.calculator import (
    calculate_event_score,
    clamp_score,
    priority_from_score,
)
from livelead.domain.scoring.models import PriorityLevel


def _campaign(**kwargs) -> Campaign:
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid4(),
        organization_id=uuid4(),
        name="Test",
        description="",
        target_industry="Fintech",
        product_or_service_focus="Payments",
        market_regions=("EU",),
        languages=("en",),
        timezone="UTC",
        date_range=DateRange(),
        positive_keywords=("webinar", "payments"),
        exclude_keywords=(),
        icp=IcpCriteria(industry="Payments", country_or_region="EU"),
        scoring_weights=ScoringWeights(),
        status=CampaignStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    defaults.update(kwargs)
    return Campaign(**defaults)


def _event(title: str = "B2B Payments Webinar EU") -> CanonicalEvent:
    now = datetime.now(UTC)
    return CanonicalEvent(
        id=uuid4(),
        organization_id=uuid4(),
        campaign_id=uuid4(),
        canonical_title=title,
        source_url="https://example.com/e/1",
        observed_at=now,
        description="webinar on cross-border payments",
        organizer="Payments Org",
        region="EU",
        starts_at=now,
    )


def test_clamp_score():
    assert clamp_score(150) == 100.0
    assert clamp_score(-5) == 0.0


def test_priority_thresholds():
    assert priority_from_score(90) == PriorityLevel.VERY_HIGH
    assert priority_from_score(75) == PriorityLevel.HIGH
    assert priority_from_score(55) == PriorityLevel.WATCH
    assert priority_from_score(35) == PriorityLevel.REFERENCE_ONLY
    assert priority_from_score(10) == PriorityLevel.POOR_FIT


def test_calculate_event_score_in_range():
    result = calculate_event_score(_event(), _campaign())
    assert 0 <= result.total_score <= 100
    assert result.scoring_version
    assert len(result.components) == 9
    weighted_sum = round(sum(c.weighted_contribution for c in result.components), 2)
    assert abs(weighted_sum - result.total_score) <= 20.0


def test_exclude_keyword_reduces_score():
    base = calculate_event_score(_event("Regular summit"), _campaign(exclude_keywords=("scam",)))
    bad = calculate_event_score(_event("crypto scam summit"), _campaign(exclude_keywords=("scam",)))
    assert bad.total_score <= base.total_score
