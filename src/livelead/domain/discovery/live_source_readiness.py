"""Policy-aware live feed/API source readiness (pure, no I/O)."""

from __future__ import annotations

from livelead.domain.discovery.models import SourceRunStatus
from livelead.domain.sources.models import ConnectorType, PolicyDecision, SourceGovernance

FEED_CONNECTOR_TYPES = frozenset(
    {
        ConnectorType.OFFICIAL_API,
        ConnectorType.RSS,
        ConnectorType.ATOM,
        ConnectorType.SITEMAP,
        ConnectorType.ICS,
    }
)


def live_connector_family(connector_type: ConnectorType) -> str:
    """Stable parser/runner family label for progress and audit."""
    if connector_type == ConnectorType.ICS:
        return "ics"
    if connector_type in (ConnectorType.RSS, ConnectorType.ATOM, ConnectorType.SITEMAP):
        return "rss_atom"
    if connector_type == ConnectorType.OFFICIAL_API:
        return "official_api"
    return "unknown"


def resolve_live_source_run(
    source: SourceGovernance,
    decision: PolicyDecision,
) -> tuple[SourceRunStatus, str | None, str | None]:
    """Decide whether a live connector may run for this source.

    Returns ``(status, error_summary, connector_family)``. When status is not
    ``PENDING``, the worker must not fetch.
    """
    family = live_connector_family(source.connector_type)

    if source.connector_type == ConnectorType.BROWSER:
        return (
            SourceRunStatus.FAILED,
            "browser_connector_use_playwright_website_discovery_path",
            "playwright_website",
        )

    if source.connector_type not in FEED_CONNECTOR_TYPES:
        return (
            SourceRunStatus.FAILED,
            f"connector_type_{source.connector_type.value}_not_supported_for_feed_discovery",
            family,
        )

    if not decision.runnable:
        return (
            SourceRunStatus.FAILED,
            "policy_denied:" + ",".join(decision.reasons),
            family,
        )

    return SourceRunStatus.PENDING, None, family