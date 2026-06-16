"""US-039 scoring suggestion domain tests."""

import pytest

from livelead.domain.campaigns.models import ScoringWeights
from livelead.domain.scoring_suggestions.generator import (
    CampaignFeedbackRollup,
    generate_scoring_suggestions,
)
from livelead.domain.scoring_suggestions.validation import (
    ScoringSuggestionValidationError,
    assert_may_decide,
    validate_suggestion_deltas,
)


def test_generate_returns_none_without_signals():
    current = ScoringWeights()
    assert generate_scoring_suggestions(current=current, rollup=CampaignFeedbackRollup()) is None


def test_generate_produces_bounded_deltas_for_audience_incorrect():
    current = ScoringWeights()
    result = generate_scoring_suggestions(
        current=current,
        rollup=CampaignFeedbackRollup(audience_incorrect=3, audience_wrong_fit=2),
    )
    assert result is not None
    assert result.deltas
    for d in result.deltas:
        assert abs(d.delta) <= 0.05 + 1e-9


def test_validate_rejects_unsafe_delta():
    current = ScoringWeights()
    proposed = dict(current.normalized().weights)
    proposed["topic_relevance"] = proposed.get("topic_relevance", 0.25) + 0.2
    with pytest.raises(ScoringSuggestionValidationError):
        validate_suggestion_deltas(current, proposed)


def test_assert_may_decide_blocks_approved():
    with pytest.raises(ScoringSuggestionValidationError):
        assert_may_decide("approved")