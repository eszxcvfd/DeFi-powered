from livelead.domain.events.deduplication import (
    MergeReason,
    canonical_fingerprint,
    decide_merge,
    normalize_title,
)


def test_normalize_title_strips_noise():
    assert normalize_title("B2B  Payments!! Webinar") == "b2b payments webinar"


def test_merge_same_source_url():
    d = decide_merge(
        finding_title="Other title",
        finding_region="US",
        finding_source_url="https://a.com/e/1",
        existing_canonical_title="Original",
        existing_region="EU",
        existing_source_url="https://a.com/e/1",
    )
    assert d.should_merge
    assert d.reason == MergeReason.SAME_SOURCE_URL


def test_merge_same_fingerprint_different_url():
    title = "B2B Payments Webinar"
    d = decide_merge(
        finding_title=title,
        finding_region="EU",
        finding_source_url="https://b.com/events/x",
        existing_canonical_title=title,
        existing_region="EU",
        existing_source_url="https://a.com/events/y",
    )
    assert d.should_merge
    assert d.reason == MergeReason.SAME_CANONICAL_FINGERPRINT


def test_no_merge_near_duplicate_title_only():
    d = decide_merge(
        finding_title="B2B Payments Webinar 2026",
        finding_region="EU",
        finding_source_url="https://b.com/1",
        existing_canonical_title="B2B Payments Summit 2026",
        existing_region="EU",
        existing_source_url="https://a.com/2",
    )
    assert not d.should_merge
    assert d.reason == MergeReason.NEW_EVENT


def test_fingerprint_stable():
    assert canonical_fingerprint("Hello World", "EU") == canonical_fingerprint("hello   world", "eu")