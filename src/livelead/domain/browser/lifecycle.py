"""Pure browser session lifecycle rules."""

from datetime import UTC, datetime

from livelead.domain.browser.models import (
    BrowserSessionState,
    LaunchContextKind,
)

TERMINAL_STATES = frozenset(
    {
        BrowserSessionState.STOPPED,
        BrowserSessionState.COMPLETED,
        BrowserSessionState.FAILED,
    }
)

_STOP_ELIGIBLE = frozenset(
    {
        BrowserSessionState.QUEUED,
        BrowserSessionState.STARTING,
        BrowserSessionState.RUNNING,
        BrowserSessionState.NEEDS_USER_ACTION,
        BrowserSessionState.STOPPING,
    }
)


def is_terminal(state: BrowserSessionState) -> bool:
    return state in TERMINAL_STATES


def can_request_stop(state: BrowserSessionState, *, stop_requested: bool) -> bool:
    if stop_requested and state == BrowserSessionState.STOPPING:
        return True
    return state in _STOP_ELIGIBLE and state != BrowserSessionState.STOPPING


def next_state_after_stop_request(state: BrowserSessionState) -> BrowserSessionState:
    if state in TERMINAL_STATES:
        return state
    return BrowserSessionState.STOPPING


def validate_launch_target(
    *,
    kind: LaunchContextKind,
    event_id_present: bool,
    source_id_present: bool,
    initial_url: str,
) -> tuple[str, ...]:
    errors: list[str] = []
    if kind == LaunchContextKind.EVENT and not event_id_present:
        errors.append("event_required")
    if not source_id_present:
        errors.append("source_required")
    url = (initial_url or "").strip()
    if not url:
        errors.append("missing_initial_url")
    elif not (url.startswith("http://") or url.startswith("https://")):
        errors.append("invalid_initial_url")
    return tuple(errors)


def runtime_seconds(
    *,
    started_at: datetime | None,
    ended_at: datetime | None,
    now: datetime | None = None,
) -> int:
    if not started_at:
        return 0
    def _utc(dt: datetime) -> datetime:
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)

    end = _utc(ended_at) if ended_at else (now or datetime.now(UTC))
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    delta = end - _utc(started_at)
    return max(0, int(delta.total_seconds()))


def derive_isolation_key(organization_id: str, session_id: str) -> str:
    return f"{organization_id}:{session_id}"


def derive_profile_boundary(organization_id: str, session_id: str) -> str:
    return f"workspace/{organization_id}/session/{session_id}"
