"""Run real HTTP feed connectors (RSS/Atom/ICS)."""

from __future__ import annotations

import logging

from livelead.domain.discovery.feed_filter import matches_discovery_keywords
from livelead.domain.discovery.finding import DiscoveryFinding
from livelead.domain.discovery.models import SourceRunStatus
from livelead.domain.sources.models import ConnectorType
from livelead.infrastructure.connectors.feed_urls import feed_url_for_domain
from livelead.infrastructure.connectors.http_fetch import FetchResult, fetch_url
from livelead.infrastructure.connectors.ics_parse import parse_ics_text
from livelead.infrastructure.connectors.mock import (
    MockRunResult,
    mock_findings_for_domain,
    run_mock_source,
)
from livelead.infrastructure.connectors.rss_parse import parse_feed_xml

logger = logging.getLogger("livelead.connectors")

FEED_TYPES = frozenset(
    {
        ConnectorType.RSS,
        ConnectorType.ATOM,
        ConnectorType.ICS,
        ConnectorType.SITEMAP,
        ConnectorType.OFFICIAL_API,
    }
)


def _filter_findings(
    findings: list[DiscoveryFinding],
    *,
    positive: list[str],
    exclude: list[str],
) -> list[DiscoveryFinding]:
    if not positive and not exclude:
        return findings
    out: list[DiscoveryFinding] = []
    for f in findings:
        blob = f"{f.title} {f.description} {f.source_url}"
        if matches_discovery_keywords(blob, positive=positive, exclude=exclude):
            out.append(f)
    return out


def run_source_connector(
    *,
    connector_type: str,
    domain: str,
    rate_limit_json: str | None,
    positive_keywords: list[str],
    exclude_keywords: list[str],
    cancel_check: callable[[], bool],
    use_mock_connectors: bool,
    fetch_fn: callable[[str], FetchResult] | None = None,
) -> tuple[MockRunResult, list[DiscoveryFinding]]:
    if use_mock_connectors or domain.lower().endswith("mock.example.com"):
        result = run_mock_source(domain, cancel_check=cancel_check)
        findings = (
            mock_findings_for_domain(domain, count=result.items_found)
            if result.items_found > 0 and result.status == SourceRunStatus.SUCCEEDED
            else []
        )
        return result, findings

    try:
        ctype = ConnectorType(connector_type)
    except ValueError:
        ctype = ConnectorType.RSS

    if ctype == ConnectorType.BROWSER:
        return (
            MockRunResult(
                SourceRunStatus.NEEDS_USER_ACTION,
                0,
                0,
                "use_supervised_browser_session_for_this_source",
            ),
            [],
        )

    if ctype not in FEED_TYPES:
        return (
            MockRunResult(
                SourceRunStatus.FAILED,
                0,
                0,
                f"connector_type_{connector_type}_not_supported_for_feed_discovery",
            ),
            [],
        )

    feed_url = feed_url_for_domain(domain, rate_limit_json)
    if not feed_url:
        return MockRunResult(SourceRunStatus.FAILED, 0, 0, f"no_feed_url_for_{domain}"), []

    if cancel_check():
        return MockRunResult(SourceRunStatus.SKIPPED, 0, 0, "cancelled"), []

    do_fetch = fetch_fn or fetch_url
    fetched = do_fetch(feed_url)
    if fetched.error or fetched.status >= 400 or not fetched.body:
        err = fetched.error or f"http_{fetched.status}"
        if fetched.status in (401, 403):
            return MockRunResult(SourceRunStatus.NEEDS_USER_ACTION, 0, 1, err), []
        return MockRunResult(SourceRunStatus.FAILED, 0, 1, err), []

    try:
        if ctype == ConnectorType.ICS or "text/calendar" in fetched.content_type.lower():
            text = fetched.body.decode("utf-8", errors="replace")
            findings = parse_ics_text(text, source_domain=domain)
        else:
            findings = parse_feed_xml(fetched.body, source_domain=domain)
    except Exception as exc:
        logger.warning("feed_parse_failed domain=%s url=%s err=%s", domain, feed_url, exc)
        return MockRunResult(SourceRunStatus.FAILED, 0, 1, f"parse_error:{exc}"), []

    findings = _filter_findings(findings, positive=positive_keywords, exclude=exclude_keywords)
    if not findings:
        note = "no_items_matching_campaign_keywords" if positive_keywords else "feed_empty"
        return MockRunResult(SourceRunStatus.SUCCEEDED, 0, 1, note), []

    return MockRunResult(SourceRunStatus.SUCCEEDED, len(findings), 1, None), findings
