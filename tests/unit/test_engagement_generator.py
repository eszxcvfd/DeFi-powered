from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from livelead.domain.audience.models import AudienceHypothesis, FitType
from livelead.domain.campaigns.models import (
    Campaign,
    CampaignStatus,
    DateRange,
    IcpCriteria,
    ScoringWeights,
)
from livelead.domain.engagement.generator import PlanGenerationContext, generate_engagement_plan
from livelead.domain.engagement.models import EngagementTaskStatus
from livelead.domain.engagement.safety import task_text_is_unsafe
from livelead.domain.engagement.transitions import can_transition
from livelead.domain.events.models import CanonicalEvent
from livelead.domain.scoring.models import EventScore, PriorityLevel, ScoreExplanation


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


def _event() -> CanonicalEvent:
    now = datetime.now(UTC)
    return CanonicalEvent(
        id=uuid4(),
        organization_id=uuid4(),
        campaign_id=uuid4(),
        canonical_title="B2B Payments Webinar EU",
        source_url="https://example.com/e/1",
        observed_at=now,
        description="Partnership webinar",
        organizer="Org",
        region="EU",
        starts_at=now,
    )


def _score(total: float = 72.0) -> EventScore:
    now = datetime.now(UTC)
    return EventScore(
        id=uuid4(),
        event_id=uuid4(),
        campaign_id=uuid4(),
        total_score=total,
        priority_level=PriorityLevel.HIGH,
        scoring_version="us-006-v1",
        calculated_at=now,
        weights_snapshot={},
        components=(),
        explanation=ScoreExplanation(components=(), missing_fields=(), score_reducers=()),
    )


def test_unsafe_task_detected():
    assert task_text_is_unsafe("Mass DM attendees", "reach everyone")


def test_task_transition_allows_done_from_todo():
    assert can_transition(EngagementTaskStatus.TODO, EngagementTaskStatus.DONE)


def test_generate_plan_ready_with_phases():
    e = _event()
    c = replace(_campaign(), id=e.campaign_id, organization_id=e.organization_id)
    hyp = AudienceHypothesis(
        id=uuid4(),
        event_id=e.id,
        segment_name="Payment ops leaders",
        fit_type=FitType.CUSTOMER,
        reason="ICP match",
        confidence=0.8,
        generated_by="rules",
        model_version="us-007-v1",
        evidence=(),
    )
    score = replace(_score(), event_id=e.id, campaign_id=e.campaign_id)
    ctx = PlanGenerationContext(event=e, campaign=c, score=score, hypotheses=(hyp,))
    state = generate_engagement_plan(ctx)
    assert state.state == "ready"
    assert state.plan
    phases = {t.phase.value for t in state.tasks}
    assert phases == {"PRE_EVENT", "LIVE_EVENT", "POST_EVENT"}
    assert all(t.status.value == "TODO" for t in state.tasks)
