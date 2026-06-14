from livelead.domain.content.models import ContentReviewStatus
from livelead.domain.content.review import actor_may_review, can_transition, is_ready_for_later_use


def test_transitions():
    assert can_transition(ContentReviewStatus.DRAFT, ContentReviewStatus.IN_REVIEW)
    assert can_transition(ContentReviewStatus.IN_REVIEW, ContentReviewStatus.APPROVED)
    assert not can_transition(ContentReviewStatus.DRAFT, ContentReviewStatus.APPROVED)


def test_reviewer_role():
    assert actor_may_review("reviewer")
    assert not actor_may_review("analyst")


def test_ready_only_approved():
    assert is_ready_for_later_use(ContentReviewStatus.APPROVED)
    assert not is_ready_for_later_use(ContentReviewStatus.DRAFT)
