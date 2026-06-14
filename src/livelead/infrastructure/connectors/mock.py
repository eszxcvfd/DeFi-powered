"""Deterministic mock connectors — no live third-party I/O (tests / *-mock.example.com only)."""

import time
from dataclasses import dataclass

from livelead.domain.discovery.finding import DiscoveryFinding
from livelead.domain.discovery.models import SourceRunStatus


@dataclass(frozen=True, slots=True)
class MockRunResult:
    status: SourceRunStatus
    items_found: int
    pages_processed: int
    error_summary: str | None = None


def mock_profile_for_domain(domain: str) -> str:
    d = domain.lower()
    if "needs-action" in d or "needs_action" in d:
        return "needs_user_action"
    if "fail" in d:
        return "fail"
    if "slow" in d:
        return "slow"
    if "partial" in d:
        return "partial"
    return "success"


def run_mock_source(domain: str, *, cancel_check: callable[[], bool]) -> MockRunResult:
    profile = mock_profile_for_domain(domain)
    if profile == "slow":
        for _ in range(30):
            if cancel_check():
                return MockRunResult(SourceRunStatus.SKIPPED, 0, 0, "cancelled")
            time.sleep(0.05)
        return MockRunResult(SourceRunStatus.SUCCEEDED, 3, 5, None)
    if profile == "needs_user_action":
        return MockRunResult(SourceRunStatus.NEEDS_USER_ACTION, 0, 0, "auth_required_fixture")
    if profile == "fail":
        return MockRunResult(SourceRunStatus.FAILED, 0, 1, "mock_failure")
    if profile == "partial":
        return MockRunResult(SourceRunStatus.SUCCEEDED, 1, 2, "partial_fixture_note")
    if cancel_check():
        return MockRunResult(SourceRunStatus.SKIPPED, 0, 0, "cancelled")
    return MockRunResult(SourceRunStatus.SUCCEEDED, 5, 3, None)


def mock_findings_for_domain(domain: str, *, count: int) -> list[DiscoveryFinding]:
    """Fixture findings for test connectors; persisted like real feed items."""
    if count <= 0:
        return []
    base = domain.replace(".", "-")
    templates = [
        ("B2B Payments Webinar", "webinar", "EU"),
        ("Fintech Partnership Summit", "conference", "US"),
        ("Cross-border Compliance Roundtable", "roundtable", "EU"),
        ("SaaS Growth Meetup", "meetup", "APAC"),
        ("Developer API Workshop", "workshop", "Global"),
    ]
    out: list[DiscoveryFinding] = []
    for i in range(count):
        t = templates[i % len(templates)]
        out.append(
            DiscoveryFinding(
                title=f"{t[0]} — {base} #{i + 1}",
                source_url=f"https://{domain}/events/{base}-{i + 1}",
                description=f"Fixture {t[1]} from mock connector {domain}.",
                organizer=f"Org {base}",
                region=t[2],
            )
        )
    return out
