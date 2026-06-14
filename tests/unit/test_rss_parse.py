from livelead.infrastructure.connectors.rss_parse import parse_feed_xml

SAMPLE = b"""<?xml version="1.0"?>
<rss><channel>
<item><title>Real Event Alpha</title><link>https://example.com/a</link><description>About payments</description></item>
</channel></rss>"""


def test_parse_rss_item():
    items = parse_feed_xml(SAMPLE, source_domain="example.com")
    assert len(items) == 1
    assert items[0].title == "Real Event Alpha"
    assert items[0].source_url == "https://example.com/a"
