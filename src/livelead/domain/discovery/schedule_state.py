"""Schedule enabled state and overlap policy (US-035)."""

from __future__ import annotations

from enum import StrEnum

from livelead.domain.discovery.lifecycle import is_terminal
from livelead.domain.discovery.models import DiscoveryJobStatus


class ScheduleEnabledState(StrEnum):
    ENABLED = "enabled"
    PAUSED = "paused"
    DISABLED = "disabled"


def schedule_may_dispatch(enabled_state: str) -> bool:
    return enabled_state == ScheduleEnabledState.ENABLED.value


def should_skip_overlap(*, active_job_status: str | None) -> bool:
    """Skip-while-running: do not dispatch if a linked job is still active."""
    if not active_job_status:
        return False
    try:
        status = DiscoveryJobStatus(active_job_status)
    except ValueError:
        return False
    return not is_terminal(status)