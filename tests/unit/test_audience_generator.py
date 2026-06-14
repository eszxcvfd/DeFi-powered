from datetime import UTC, datetime
from uuid import uuid4

from livelead.domain.audience.generator import GenerationContext, generate_audience_analysis
from livelead.domain.audience.safety import contains_sensitive_inference
from livelead.domain.campaigns.models import (
    Campaign,
    CampaignStatus,
    DateRange,
    IcpCriteria,
    ScoringWeights,
)
from livelead.domain.events.models import CanonicalEvent, EventSourceObservation


def _campaign() -> Campaign:
    now = datetime.now(UTC)
    return Campaign(
        id=uuid4(),
        organization_id=uuid4(),
        name="C",
        description="",
        target_industry="Fintech",
        product_or_service_focus="Payments API",
        market_regions=("EU",),
        languages=("en",),
        timezone="UTC",
        date_range=DateRange(),
        positive_keywords=("webinar",),
        exclude_keywords=(),
        icp=IcpCriteria(industry="Payments", country_or_region="EU"),
        scoring_weights=ScoringWeights(),
        status=CampaignStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def _event(title: str = "B2B Payments Webinar EU") -> CanonicalEvent:
    now = datetime.now(UTC)
    return CanonicalEvent(
        id=uuid4(),
        organization_id=uuid4(),
        campaign_id=uuid4(),
        canonical_title=title,
        source_url="https://example.com/e/1",
        observed_at=now,
        description="Partnership-focused webinar on cross-border payments",
        organizer="Payments Org",
        region="EU",
        starts_at=now,
    )


def test_sensitive_inference_blocked():
    assert contains_sensitive_inference("political activist segment")


def test_generate_audience_ready():
    e = _event()
    obs = EventSourceObservation(
        id=uuid4(),
        event_id=e.id,
        source_id=uuid4(),
        source_url=e.source_url,
        observed_at=e.observed_at,
        raw_title=e.canonical_title,
    )
    ctx = GenerationContext(event=e, campaign=_campaign(), observations=(obs,))
    analysis = generate_audience_analysis(ctx)
    assert analysis.state == "ready"
    assert len(analysis.hypotheses) >= 1
    h = analysis.hypotheses[0]
    assert h.reason
    assert len(h.evidence) >= 1


def test_generate_audience_empty_sparse():
    e = CanonicalEvent(
        id=uuid4(),
        organization_id=uuid4(),
        campaign_id=uuid4(),
        canonical_title="x",
        source_url="https://a/b",
        observed_at=datetime.now(UTC),
    )
    ctx = GenerationContext(event=e, campaign=_campaign(), observations=())
    analysis = generate_audience_analysis(ctx)
    assert analysis.state == "empty"