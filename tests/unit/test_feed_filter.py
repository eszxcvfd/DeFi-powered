from livelead.domain.discovery.feed_filter import matches_discovery_keywords


def test_positive_keyword_required_when_set():
    assert matches_discovery_keywords("crypto webinar", positive=["webinar"], exclude=[])
    assert not matches_discovery_keywords("crypto only", positive=["webinar"], exclude=[])


def test_exclude_wins():
    assert not matches_discovery_keywords("spam webinar", positive=[], exclude=["spam"])
