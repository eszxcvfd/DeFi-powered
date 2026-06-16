"""Browser discovery connector entry (mock fixtures + Playwright/Selenium, US-033/US-034)."""

from __future__ import annotations

from collections.abc import Callable

from livelead.domain.discovery.browser_recipe import BrowserDiscoveryRecipe
from livelead.domain.discovery.feed_filter import matches_discovery_keywords
from livelead.domain.discovery.finding import DiscoveryFinding
from livelead.domain.discovery.models import SourceRunStatus
from livelead.infrastructure.connectors.mock import (
    MockRunResult,
    mock_findings_for_domain,
    run_mock_source,
)
from livelead.infrastructure.connectors.playwright_discovery_runner import (
    PlaywrightDiscoveryRunOutcome,
    run_playwright_discovery_sync,
)
from livelead.infrastructure.connectors.selenium_discovery_runner import (
    SeleniumDiscoveryRunOutcome,
    run_selenium_discovery_sync,
)
from livelead.runtime.settings import AppSettings, parse_settings


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


def _outcome_to_mock(result: PlaywrightDiscoveryRunOutcome | SeleniumDiscoveryRunOutcome) -> MockRunResult:
    return MockRunResult(
        result.status,
        result.items_found,
        result.pages_processed,
        result.error_summary,
    )


def _mock_browser_findings(*, domain: str, automation_engine: str) -> list[DiscoveryFinding]:
    engine = (automation_engine or "playwright").lower()
    if engine == "selenium" or "selenium" in domain.lower():
        return [
            DiscoveryFinding(
                title=f"US034 Selenium Summit — {domain}",
                source_url=f"https://{domain}/events/us034-1",
                description="Fixture public website extraction for Selenium discovery.",
                organizer="Fixture Org",
                region="EU",
            )
        ]
    if "website" in domain.lower() or "playwright" in domain.lower():
        return [
            DiscoveryFinding(
                title=f"US033 Website Summit — {domain}",
                source_url=f"https://{domain}/events/us033-1",
                description="Fixture public website extraction for Playwright discovery.",
                organizer="Fixture Org",
                region="EU",
            )
        ]
    return []


def run_browser_discovery_connector(
    *,
    domain: str,
    recipe: BrowserDiscoveryRecipe,
    positive_keywords: list[str],
    exclude_keywords: list[str],
    cancel_check: Callable[[], bool],
    use_mock_connectors: bool,
    automation_engine: str = "playwright",
    settings: AppSettings | None = None,
) -> tuple[MockRunResult, list[DiscoveryFinding]]:
    settings = settings or parse_settings()
    use_mock = use_mock_connectors or domain.lower().endswith("mock.example.com")
    engine = (automation_engine or "playwright").lower()

    if use_mock:
        mock = run_mock_source(domain, cancel_check=cancel_check)
        findings: list[DiscoveryFinding] = []
        if mock.status == SourceRunStatus.SUCCEEDED and mock.items_found > 0:
            findings = _mock_browser_findings(domain=domain, automation_engine=automation_engine)
            if findings:
                mock = MockRunResult(
                    SourceRunStatus.SUCCEEDED,
                    len(findings),
                    mock.pages_processed or 1,
                    None,
                )
            else:
                findings = mock_findings_for_domain(domain, count=mock.items_found)
        findings = _filter_findings(findings, positive=positive_keywords, exclude=exclude_keywords)
        if mock.status == SourceRunStatus.SUCCEEDED and not findings and positive_keywords:
            return MockRunResult(SourceRunStatus.SUCCEEDED, 0, mock.pages_processed, "no_items_matching_campaign_keywords"), []
        return mock, findings

    if engine == "selenium":
        raw = run_selenium_discovery_sync(
            recipe=recipe,
            domain=domain,
            settings=settings,
            cancel_check=cancel_check,
        )
    else:
        raw = run_playwright_discovery_sync(
            recipe=recipe,
            domain=domain,
            settings=settings,
            cancel_check=cancel_check,
        )
    findings = list(raw.findings)
    findings = _filter_findings(findings, positive=positive_keywords, exclude=exclude_keywords)
    mock = _outcome_to_mock(raw)
    if raw.status == SourceRunStatus.SUCCEEDED and not findings and positive_keywords:
        return MockRunResult(SourceRunStatus.SUCCEEDED, 0, raw.pages_processed, "no_items_matching_campaign_keywords"), []
    if findings:
        mock = MockRunResult(raw.status, len(findings), raw.pages_processed, raw.error_summary)
    return mock, findings