from livelead.domain.browser.evidence_provisioning import (
    auto_provision_domain,
    domain_from_url,
    playwright_connector_name,
)


def test_domain_from_event_url():
    assert domain_from_url("https://events.techcrunch.com/foo") == "events.techcrunch.com"


def test_auto_provision_prefers_event_url():
    assert (
        auto_provision_domain("https://example.com/e/1", ["https://other.com/x"]) == "example.com"
    )


def test_playwright_connector_name():
    assert playwright_connector_name("example.com") == "Playwright · example.com"
