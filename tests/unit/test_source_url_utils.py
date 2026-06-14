from livelead.domain.events.source_url_utils import (
    is_synthetic_discovery_event_url,
    pick_browser_launch_url,
)


def test_detects_legacy_mock_event_url():
    assert is_synthetic_discovery_event_url("https://hnrss.org/events/hnrss-org-1")
    assert is_synthetic_discovery_event_url("https://coindesk.com/events/coindesk-com-3")


def test_real_feed_links_not_synthetic():
    assert not is_synthetic_discovery_event_url("https://hnrss.org/frontpage")
    assert not is_synthetic_discovery_event_url("https://techcrunch.com/2026/01/01/some-story/")


def test_pick_browser_launch_skips_synthetic():
    url = pick_browser_launch_url(
        event_source_url="https://hnrss.org/events/hnrss-org-1",
        observation_urls=["https://hnrss.org/events/hnrss-org-1"],
        source_domain="hnrss.org",
    )
    assert url == "https://hnrss.org/"


def test_pick_browser_launch_prefers_real_observation():
    url = pick_browser_launch_url(
        event_source_url="https://hnrss.org/events/hnrss-org-1",
        observation_urls=["https://news.ycombinator.com/item?id=1"],
        source_domain="hnrss.org",
    )
    assert url.startswith("https://news.ycombinator.com/")


def test_pick_browser_launch_mock_fixture_domain_uses_example_com():
    url = pick_browser_launch_url(
        event_source_url="https://success-mock.example.com/events/success-mock-example-com-1",
        observation_urls=[],
        source_domain="success-mock.example.com",
    )
    assert url == "https://example.com/"
