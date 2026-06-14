"""Task status transition rules."""

from livelead.domain.engagement.models import EngagementTaskStatus

_ALLOWED: dict[EngagementTaskStatus, frozenset[EngagementTaskStatus]] = {
    EngagementTaskStatus.TODO: frozenset(
        {EngagementTaskStatus.IN_PROGRESS, EngagementTaskStatus.DONE, EngagementTaskStatus.SKIPPED}
    ),
    EngagementTaskStatus.IN_PROGRESS: frozenset(
        {EngagementTaskStatus.TODO, EngagementTaskStatus.DONE, EngagementTaskStatus.SKIPPED}
    ),
    EngagementTaskStatus.DONE: frozenset({EngagementTaskStatus.IN_PROGRESS, EngagementTaskStatus.TODO}),
    EngagementTaskStatus.SKIPPED: frozenset({EngagementTaskStatus.TODO, EngagementTaskStatus.IN_PROGRESS}),
}


def can_transition(current: EngagementTaskStatus, new: EngagementTaskStatus) -> bool:
    if current == new:
        return True
    return new in _ALLOWED.get(current, frozenset())


def parse_task_status(raw: str) -> EngagementTaskStatus | None:
    try:
        return EngagementTaskStatus(raw.upper())
    except ValueError:
        return None