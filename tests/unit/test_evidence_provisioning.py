from livelead.domain.browser.evidence_provisioning import (
    EVIDENCE_BROWSER_ENGINES,
    auto_provision_domain,
    browser_connector_name,
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


def test_selenium_connector_name():
    assert browser_connector_name("defillama.com", "selenium") == "Selenium · defillama.com"


def test_evidence_engines_include_selenium():
    assert "playwright" in EVIDENCE_BROWSER_ENGINES
    assert "selenium" in EVIDENCE_BROWSER_ENGINES
