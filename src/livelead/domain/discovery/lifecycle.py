"""Pure job lifecycle rules."""

from livelead.domain.discovery.models import DiscoveryJobStatus, SourceRunStatus

TERMINAL = frozenset(
    {
        DiscoveryJobStatus.SUCCEEDED,
        DiscoveryJobStatus.FAILED,
        DiscoveryJobStatus.PARTIAL,
        DiscoveryJobStatus.CANCELLED,
        DiscoveryJobStatus.NEEDS_USER_ACTION,
    }
)


def aggregate_job_status(source_statuses: list[SourceRunStatus], *, cancelled: bool) -> DiscoveryJobStatus:
    if cancelled:
        return DiscoveryJobStatus.CANCELLED
    if any(s == SourceRunStatus.NEEDS_USER_ACTION for s in source_statuses):
        return DiscoveryJobStatus.NEEDS_USER_ACTION
    successes = sum(1 for s in source_statuses if s == SourceRunStatus.SUCCEEDED)
    failures = sum(1 for s in source_statuses if s == SourceRunStatus.FAILED)
    if successes and failures:
        return DiscoveryJobStatus.PARTIAL
    if successes and not failures:
        return DiscoveryJobStatus.SUCCEEDED
    if failures and not successes:
        return DiscoveryJobStatus.FAILED
    return DiscoveryJobStatus.RUNNING


def can_cancel(status: DiscoveryJobStatus) -> bool:
    return status in (DiscoveryJobStatus.QUEUED, DiscoveryJobStatus.RUNNING)


def is_terminal(status: DiscoveryJobStatus) -> bool:
    return status in TERMINAL