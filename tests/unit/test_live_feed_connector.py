"""Unit tests for live feed connector runner with stubbed HTTP."""

from livelead.domain.discovery.models import SourceRunStatus
from livelead.infrastructure.connectors import http_fetch
from livelead.infrastructure.connectors.runner import run_source_connector

RSS_BODY = b"""<?xml version="1.0"?>
<rss><channel>
<item><title>Live Payments Summit 2026</title><link>https://fixture.test/e/1</link>
<description>webinar payments fintech</description></item>
</channel></rss>"""


def _fake_fetch(url: str, **kwargs):
    assert "fixture.test" in url
    return http_fetch.FetchResult(200, RSS_BODY, "application/rss+xml", None)


def test_live_rss_fetch_and_parse():
    result, findings = run_source_connector(
        connector_type="rss",
        domain="fixture.test",
        rate_limit_json='{"feed_url": "https://fixture.test/rss.xml"}',
        positive_keywords=[],
        exclude_keywords=[],
        cancel_check=lambda: False,
        use_mock_connectors=False,
        fetch_fn=_fake_fetch,
    )
    assert result.status == SourceRunStatus.SUCCEEDED
    assert len(findings) == 1
    assert findings[0].title == "Live Payments Summit 2026"


def test_http_403_needs_user_action():
    result, findings = run_source_connector(
        connector_type="rss",
        domain="fixture.test",
        rate_limit_json='{"feed_url": "https://fixture.test/rss.xml"}',
        positive_keywords=[],
        exclude_keywords=[],
        cancel_check=lambda: False,
        use_mock_connectors=False,
        fetch_fn=lambda url, **kwargs: http_fetch.FetchResult(403, b"", "", "forbidden"),
    )
    assert result.status == SourceRunStatus.NEEDS_USER_ACTION
    assert findings == []


def test_keyword_filter_applied():
    result, findings = run_source_connector(
        connector_type="rss",
        domain="fixture.test",
        rate_limit_json='{"feed_url": "https://fixture.test/rss.xml"}',
        positive_keywords=["blockchain-only-keyword"],
        exclude_keywords=[],
        cancel_check=lambda: False,
        use_mock_connectors=False,
        fetch_fn=_fake_fetch,
    )
    assert result.status == SourceRunStatus.SUCCEEDED
    assert result.items_found == 0
    assert findings == []