import pytest

from livelead.domain.ai_feedback.validation import (
    assert_no_auto_learning_side_effect,
    validate_audience_hypothesis_feedback,
    validate_discovery_copilot_feedback,
)


def test_not_helpful_requires_reason():
    with pytest.raises(ValueError, match="reason_code"):
        validate_discovery_copilot_feedback(state="not_helpful", reason_code=None, note=None)


def test_helpful_allows_optional_reason():
    state, reason, note = validate_discovery_copilot_feedback(
        state="helpful", reason_code=None, note="  "
    )
    assert state == "helpful"
    assert reason is None
    assert note is None


def test_audience_incorrect_requires_reason():
    with pytest.raises(ValueError, match="reason_code"):
        validate_audience_hypothesis_feedback(state="incorrect", reason_code=None, note=None)


def test_audience_correct_no_reason_required():
    state, _, _ = validate_audience_hypothesis_feedback(
        state="correct", reason_code=None, note=None
    )
    assert state == "correct"


def test_no_auto_learning_guard():
    with pytest.raises(ValueError, match="autonomous"):
        assert_no_auto_learning_side_effect("mutate_scoring_weights")