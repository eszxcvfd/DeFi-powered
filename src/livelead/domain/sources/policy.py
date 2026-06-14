"""Pure policy evaluation — no I/O."""

from datetime import UTC, datetime

from livelead.domain.sources.models import (
    ConnectorType,
    PolicyDecision,
    SourceGovernance,
)

FEED_LIKE = frozenset(
    {
        ConnectorType.OFFICIAL_API,
        ConnectorType.RSS,
        ConnectorType.ATOM,
        ConnectorType.SITEMAP,
        ConnectorType.ICS,
    }
)


def prefer_connector_type(a: ConnectorType, b: ConnectorType) -> ConnectorType:
    """Prefer API/feed over browser when both are viable."""
    a_feed = a in FEED_LIKE
    b_feed = b in FEED_LIKE
    if a_feed and not b_feed:
        return a
    if b_feed and not a_feed:
        return b
    return a


def evaluate_source_policy(
    source: SourceGovernance,
    *,
    now: datetime | None = None,
) -> PolicyDecision:
    reasons: list[str] = []
    if not source.enabled:
        reasons.append("disabled")
    if not source.approved:
        reasons.append("pending_approval")
    if not source.policy.valid:
        reasons.append("invalid_policy")
    if source.policy.quota_used_today >= source.policy.quota_per_day:
        reasons.append("over_quota")

    now = now or datetime.now(UTC)
    hour = now.hour
    if not (source.policy.window_start_hour <= hour <= source.policy.window_end_hour):
        reasons.append("outside_time_window")

    if source.authentication_mode.value != "none" and not source.has_secret:
        reasons.append("missing_secret")

    runnable = len(reasons) == 0
    preferred = source.connector_type in FEED_LIKE
    return PolicyDecision(
        runnable=runnable,
        reasons=tuple(reasons),
        preferred_over_browser=preferred and runnable,
    )
