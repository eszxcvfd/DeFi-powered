"""Content review state transitions."""

from livelead.domain.content.models import ContentReviewStatus

_ALLOWED: dict[ContentReviewStatus, frozenset[ContentReviewStatus]] = {
    ContentReviewStatus.DRAFT: frozenset({ContentReviewStatus.IN_REVIEW}),
    ContentReviewStatus.IN_REVIEW: frozenset(
        {ContentReviewStatus.APPROVED, ContentReviewStatus.REJECTED}
    ),
    ContentReviewStatus.REJECTED: frozenset(
        {ContentReviewStatus.IN_REVIEW, ContentReviewStatus.DRAFT}
    ),
    ContentReviewStatus.APPROVED: frozenset(
        {ContentReviewStatus.IN_REVIEW}
    ),  # re-open for revision
}


def can_transition(current: ContentReviewStatus, new: ContentReviewStatus) -> bool:
    if current == new:
        return True
    return new in _ALLOWED.get(current, frozenset())


REVIEWER_ROLES = frozenset({"reviewer", "admin", "owner"})


def actor_may_review(role: str) -> bool:
    return role in REVIEWER_ROLES


def is_ready_for_later_use(status: ContentReviewStatus) -> bool:
    return status == ContentReviewStatus.APPROVED
